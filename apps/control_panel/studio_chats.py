"""Studio chats (UX-01): conversations stored inside the project, not in the browser.

A chat lives in `<project>\\studio\\chats\\<id>.json`; unsorted work goes to the Inbox project `workspace/projects\\_inbox`.
Answers come from the allowlisted local chat worker or a LiteLLM route (studio_llm); a paid route answers only after
the owner confirmed its price, and every answer is streamed (Phase 1) and saved here when it ends.
"""
import asyncio
import json
import queue
import os
from pathlib import Path
import re
import threading
import time
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import local_chat_service as lcs
import studio_llm as llm
import studio_packs as packs
import project_files_service as files
import run_projects_service as rps

router = APIRouter(prefix='/api/studio')
INBOX = 'inbox'
MAX_FILE = 2 * 1024 * 1024
BUSY, BUSY_LOCK = set(), threading.Lock()
WRITE = threading.Lock()  # short read-modify-write sections; BUSY covers the long model call
STOPS = {}  # cid -> threading.Event of the answer being streamed


def inbox_root():
    return rps.PROJECTS_ROOT / '_inbox'


def real_dir(p, create=False):
    """Check the lexical path (no link or junction anywhere) BEFORE touching it; mkdir only inside a checked parent."""
    files.native(p.parent)
    if create and not os.path.lexists(p):
        p.mkdir()
    return files.native(p)


def folder(key):
    """'inbox' or '<type>/<name>' -> existing project folder; no links or junctions on the way."""
    key = str(key or '')
    if key == INBOX:
        p = real_dir(inbox_root(), create=True)
    else:
        ptype, _, name = key.partition('/')
        name, _ = rps._folder(ptype, name)  # validates type and name; the path is rebuilt lexically, not resolved
        p = rps.PROJECTS_ROOT / ptype / name
        if not os.path.lexists(p) or not files.native(p).is_dir():
            raise ValueError('Проект не найден')
    return p


def chats_dir(key, create=False):
    p = folder(key) / 'studio' / 'chats'
    if create:
        real_dir(real_dir(p.parent, create=True) / 'chats', create=True)
    elif os.path.lexists(p.parent):
        files.native(p.parent if not os.path.lexists(p) else p)
    return p


def chat_path(key, cid, create=False):
    if not re.fullmatch(r'\d{8}-\d{6}-[0-9a-f]{6}', str(cid)):
        raise ValueError('Некорректный id чата')
    return chats_dir(key, create) / f'{cid}.json'


def load(key, cid):
    p = chat_path(key, cid)
    if not p.is_file():
        raise ValueError('Чат не найден')
    files.native(p)
    if p.stat().st_size > MAX_FILE:
        raise ValueError('Чат слишком большой')
    return json.loads(p.read_text(encoding='utf-8'))


def save(key, data):
    p = chat_path(key, data['id'], create=True)
    tmp = p.with_name(p.name + '.' + uuid.uuid4().hex + '.tmp')
    with tmp.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if tmp.stat().st_size > MAX_FILE:
        tmp.unlink()
        raise ValueError('Чат слишком большой: начните новый')
    os.replace(tmp, p)
    return data


def summary(d):
    last = (d['messages'] or [{}])[-1]
    return {'id': d['id'], 'title': d['title'], 'updated': d['updated'], 'count': len(d['messages']),
            'last': str(last.get('content', ''))[:120]}


def list_chats(key):
    p = chats_dir(key)
    rows = []
    for f in sorted(p.glob('*.json')) if p.is_dir() else []:
        try:
            rows.append(summary(load(key, f.stem)))
        except (ValueError, OSError, KeyError, json.JSONDecodeError):
            continue  # a damaged or foreign file never hides the other chats
    return sorted(rows, key=lambda r: r['updated'], reverse=True)


def create(key, title=''):
    now = time.time()
    cid = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    return save(key, {'schema': 1, 'id': cid, 'title': title.strip() or 'Новый чат', 'created': now, 'updated': now,
                      'messages': []})


def claim(cid):
    with BUSY_LOCK:
        if cid in BUSY:
            raise HTTPException(409, 'Чат ещё отвечает на прошлое сообщение')
        BUSY.add(cid)


def release(cid):
    with BUSY_LOCK:
        BUSY.discard(cid)


def send(key, cid, content, model='t-lite', max_tokens=700, temperature=.4):
    claim(cid)
    try:
        d = load(key, cid)
        user = {'role': 'user', 'content': content, 'ts': time.time()}
        history = [{'role': m['role'], 'content': m['content']} for m in d['messages'] + [user]]
        answer = lcs.chat(history, max_tokens, temperature, model)
        # Re-read: a rename during the long answer must not be lost.
        with WRITE:
            return _append(key, cid, content, user, answer, model)
    finally:
        release(cid)


def _append(key, cid, content, user, answer, model):
    d = load(key, cid)
    reply = {'role': 'assistant', 'content': answer['content'], 'ts': time.time(), 'model': model,
             'receipt': answer.get('receipt'), 'truncated': answer.get('truncated', False)}
    for k in ('stopped', 'cost_usd'):
        if answer.get(k) is not None:
            reply[k] = answer[k]
    d['messages'] += [user, reply]
    if d['title'] == 'Новый чат':
        d['title'] = re.sub(r'\s+', ' ', content).strip()[:60] or d['title']
    d['updated'] = time.time()
    return save(key, d)


def _event(kind, data):
    return f'event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


def stream(key, cid, content, model, max_tokens, temperature, confirm_usd):
    """Phase 1: starts the answer now (validation, price and start errors become HTTP errors), then a worker thread
    pumps deltas into a queue and saves the chat when the answer ends — also when the browser has gone away.
    «Стоп» or a lost connection keeps the text received so far, marked as stopped."""
    claim(cid)
    stop = threading.Event()
    STOPS[cid] = stop  # «Стоп» works while the model is still starting
    try:
        d = load(key, cid)
        user = {'role': 'user', 'content': content, 'ts': time.time()}
        history = [{'role': m['role'], 'content': m['content']} for m in d['messages'] + [user]]
        events = llm.open_stream(history, max_tokens, temperature, model, confirm_usd, stop)
    except BaseException:
        STOPS.pop(cid, None)
        release(cid)
        raise
    q = queue.Queue()

    def pump():
        text, result = [], None
        try:
            for kind, val in events:
                if kind == 'delta':
                    text.append(val)
                    q.put(('delta', {'text': val}))
                else:
                    result = val
            if result is None:  # stopped before the end
                result = {'content': ''.join(text), 'stopped': True}
            if result['content'].strip():
                with WRITE:
                    q.put(('done', _append(key, cid, content, user, result, model)))
            else:
                q.put(('done', load(key, cid)))  # nothing to keep: the chat stays as it was, the draft returns
        except Exception as e:  # noqa: BLE001 — every failure ends the stream with a readable error
            saved = False
            if text:
                try:
                    with WRITE:
                        _append(key, cid, content, user, {'content': ''.join(text), 'stopped': True}, model)
                    saved = True
                except (ValueError, OSError, KeyError):
                    pass
            q.put(('error', {'message': str(e)[:400] or type(e).__name__, 'saved': saved}))
        finally:
            try:
                close = getattr(events, 'close', None)
                if close:
                    close()  # stops the model if the answer was cut short
            finally:  # the chat is freed and the browser stream ends even if closing fails
                STOPS.pop(cid, None)
                release(cid)
                q.put(None)
    threading.Thread(target=pump, name=f'studio-stream-{cid}', daemon=True).start()

    async def relay():
        try:
            yield _event('status', {'phase': 'started', 'engine': 'litellm' if str(model).startswith(llm.PREFIX) else 'worker'})
            while True:
                try:
                    item = q.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(.05)
                    continue
                if item is None:
                    return
                yield _event(*item)
        finally:
            stop.set()  # the browser left: stop generating, the pump saves what arrived
    return relay()


def stop_answer(cid):
    ev = STOPS.get(cid)
    if ev:
        ev.set()
    return {'ok': True, 'stopping': bool(ev)}


def rename(key, cid, title):
    with WRITE:
        d = load(key, cid)
        d['title'], d['updated'] = title.strip() or d['title'], time.time()
        return save(key, d)


def move(key, cid, to):
    if to == key:
        raise ValueError('Чат уже в этом проекте')
    claim(cid)
    WRITE.acquire()
    try:
        d = load(key, cid)
        src = chat_path(key, cid)
        if chat_path(to, cid).exists():
            raise ValueError('В проекте уже есть чат с этим id')
        d['moved_from'], d['updated'] = key, time.time()
        save(to, d)  # copy first, then drop the source: a failure leaves the chat where it was
        src.unlink()
        return d
    finally:
        WRITE.release()
        release(cid)


VIDEO = {'.mp4', '.mov', '.webm', '.mkv'}
SKIP = {'studio', 'node_modules', '__pycache__'}
MONTAGE_SLUG = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]{1,62}')  # what video_review.project accepts


def videos(p, limit=40, budget=4000, depth=4):
    """UX-42: project videos for the montage room, newest first; links and junctions are never followed.

    Directories are streamed and the walk stops after `budget` entries, so a huge render folder cannot stall the page."""
    rows, stack = [], [(p, 0)]
    while stack and budget > 0:
        d, level = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    budget -= 1
                    if budget < 0:
                        break
                    if e.name.startswith('.') or e.is_symlink() or getattr(e, 'is_junction', lambda: False)():
                        continue
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if level < depth and e.name not in SKIP:
                                stack.append((Path(e.path), level + 1))
                        elif Path(e.name).suffix.lower() in VIDEO:
                            st = e.stat(follow_symlinks=False)
                            rows.append({'name': e.name, 'relative': Path(e.path).relative_to(p).as_posix(),
                                         'size': st.st_size, 'modified': st.st_mtime})
                    except OSError:
                        continue
        except OSError:
            continue
    return sorted(rows, key=lambda r: r['modified'], reverse=True)[:limit]


def project_runs(key, limit=60, ledger=5000):
    """UX-42: panel runs launched into this project («Сохранять в») or saved into it («В проект»).
    Inbox (Phase 1.2): runs with no project at all — launched «без проекта» and not saved anywhere yet."""
    import models_service as mdl  # lazy: the runs ledger is only needed for this view
    ptype, _, name = key.partition('/')
    out = []
    for r in mdl.runs(ledger):  # filter first, then cap: other projects' activity must not push this one out
        t = r.get('target') or {}
        saved = str((r.get('project') or {}).get('path') or '').replace('\\', '/').lower()
        cloud = ptype == 'video' and (r.get('cloud') or {}).get('project') == name  # Replicate writes into the budget project
        if key == INBOX:
            hit = not t and not saved and not (r.get('cloud') or {}).get('project')
        else:
            hit = (t.get('type'), t.get('name')) == (ptype, name) or saved.endswith('/' + key.lower()) or cloud
        if hit:
            outs = r.get('outputs') or []
            # Phase 1.3 gallery actions: params/inputs for «Повторить» and «В чат», saved = the «В проект» copy (for «В монтажную»)
            out.append({**{k: r.get(k) for k in ('id', 'title', 'kind', 'status', 'started', 'favorite')},
                        'params': r.get('params') or {}, 'inputs': r.get('inputs') or {},
                        'saved': (r.get('project') or {}).get('dest') or '',
                        'outputs': [{'name': o.get('name'), 'path': o.get('path')} for o in outs[:4]], 'count': len(outs)})
            if len(out) >= limit:
                break
    return out


def copies(p, runs):
    """Phase 1.3: for runs saved into THIS project, each output's copy (relative to the project) from <dest>/run.json:
    «В проект» renames clashing names (clip.mp4, clip-1.mp4), so only the recorded source→path map is trusted."""
    base = os.path.normcase(os.path.abspath(p)) + os.sep
    for r in runs:
        dest = os.path.normcase(os.path.abspath(r['saved'])) if r['saved'] else ''
        if not dest.startswith(base) or os.path.dirname(dest) != os.path.join(base.rstrip(os.sep), 'generations'):
            continue  # only <project>\generations\<run folder>, never another project or a deeper path
        try:
            recipe = files.native(Path(r['saved']) / 'run.json')
            if recipe.stat().st_size > 2_000_000:
                continue
            data = json.loads(recipe.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        rows = data.get('outputs') if isinstance(data, dict) else None
        if not isinstance(rows, list):
            continue  # a hand-edited or foreign run.json never breaks the project page
        made = {os.path.normcase(str(x.get('source') or '')): str(x.get('path') or '') for x in rows if isinstance(x, dict)}
        for o in r['outputs']:
            c = made.get(os.path.normcase(str(o.get('path') or '')), '')
            if c and os.path.normcase(os.path.abspath(c)).startswith(base):
                o['copy'] = Path(os.path.relpath(os.path.abspath(c), os.path.abspath(p))).as_posix()


def overview(key):
    """UX-42: one project page — chats live in /chats; here generations, montage videos and the folder path."""
    p = folder(key)
    if key == INBOX:
        return {'project': key, 'path': str(p), 'runs': project_runs(key), 'videos': [], 'montage': None}
    ptype, _, name = key.partition('/')
    montage = name if ptype == 'video' and MONTAGE_SLUG.fullmatch(name) else None
    runs = project_runs(key)
    copies(p, runs)
    return {'project': key, 'path': str(p), 'runs': runs, 'videos': videos(p) if montage else [],
            'montage': montage}


def safe(fn, *args):
    try:
        return fn(*args)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e


class NewChat(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    title: str = Field(default='', max_length=120)


class Message(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=12000)
    model: str = Field(default='t-lite', max_length=60)
    max_tokens: int = 700
    temperature: float = .4


class StreamMessage(Message):
    model: str = Field(default='t-lite', max_length=80)
    confirm_usd: float | None = None


class Rename(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=120)


class Move(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    to: str = Field(min_length=1, max_length=200)


def chat_models():
    return llm.models()


def gpu_bar():
    return {'available': False, 'devices': [], 'busy': False, 'reason': 'No GPU adapter configured'}


_gpu_bar_lock = threading.Lock()  # concurrent polls share one snapshot instead of each running nvidia-smi and the probes


@router.get('/gpu')
def get_gpu():
    import collectors as c
    with _gpu_bar_lock:
        return safe(c.cached, 'studio-gpu', 5, gpu_bar)


@router.get('/meta')
def get_meta():
    return {'inbox': {'key': INBOX, 'label': 'Входящие', 'path': str(inbox_root())}, **safe(rps.projects),
            'models': safe(chat_models)}


@router.get('/chats')
def get_chats(project: str):
    return {'chats': safe(list_chats, project)}


@router.post('/chats')
def post_chat(body: NewChat):
    return safe(create, body.project, body.title)


@router.get('/chats/{cid}')
def get_chat(cid: str, project: str):
    return safe(load, project, cid)


@router.post('/chats/{cid}/send')
def post_send(cid: str, body: Message):
    if not body.content.strip():
        raise HTTPException(400, 'Пустое сообщение')
    return safe(send, body.project, cid, body.content, body.model, body.max_tokens, body.temperature)


@router.post('/chats/{cid}/estimate')
def post_estimate(cid: str, body: StreamMessage):
    d = safe(load, body.project, cid)
    history = [{'role': m['role'], 'content': m['content']} for m in d['messages']] + [{'role': 'user', 'content': body.content}]
    return safe(llm.estimate, history, body.max_tokens, body.temperature, body.model)


@router.post('/chats/{cid}/stream')
def post_stream(cid: str, body: StreamMessage):
    if not body.content.strip():
        raise HTTPException(400, 'Пустое сообщение')
    gen = safe(stream, body.project, cid, body.content, body.model, body.max_tokens, body.temperature, body.confirm_usd)
    return StreamingResponse(gen, media_type='text/event-stream', headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@router.post('/chats/{cid}/stop')
def post_stop(cid: str):
    return stop_answer(cid)


@router.post('/chats/{cid}/rename')
def post_rename(cid: str, body: Rename):
    return safe(rename, body.project, cid, body.title)


@router.post('/chats/{cid}/move')
def post_move(cid: str, body: Move):
    return safe(move, body.project, cid, body.to)


@router.get('/overview')
def get_overview(project: str):
    return safe(overview, project)


@router.get('/packs')
def get_packs(base: str = '', fields: str = ''):
    """Phase 1.2: prompt-pack examples for the generation form, as values for the given field names."""
    return safe(packs.packs, base, [f for f in fields.split(',') if f][:80])
