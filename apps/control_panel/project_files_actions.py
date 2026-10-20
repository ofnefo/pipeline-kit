"""File-manager actions for the project browser: search below a folder, upload, folder ZIP,
rename/move/new folder, quarantine instead of delete, Assistant delivery and an action journal.
Writes are allowed only inside the 'projects' root (workspace/projects); originals are never deleted."""
from pathlib import Path
import kit_config as config
import json
import os
import shutil
import stat
import tempfile
import threading
import time
import uuid
import zipfile
from urllib.parse import quote, urlsplit

from fastapi import APIRouter, HTTPException, Request
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from project_files_service import BLOCKED, DOWNLOAD, guarded, kind, resolve, secret_name

router = APIRouter(prefix='/api/project-browser')
STATE = config.workspace('state')
JOURNAL = STATE / 'file-actions.jsonl'
QUARANTINE = config.workspace('quarantine')
ZIP_TMP = STATE / 'zip-tmp'
WRITE_ROOTS = {'projects'}
LOCAL_PORT = 8770
UPLOAD_LIMIT = 20 * 1024**3
UPLOAD_RESERVE = 64 * 1024**2
ZIP_LIMIT = {True: 8 * 1024**3, False: 2 * 1024**3}   # local / via the online tunnel
JOURNAL_LOCK = threading.Lock()


def is_local(request):
    server = request.scope.get('server') or ('', 0)
    return server[0] == '127.0.0.1' and server[1] == LOCAL_PORT


def same_origin(request):
    origin = request.headers.get('origin')
    if request.headers.get('sec-fetch-site') == 'cross-site' or origin and (
            urlsplit(origin).scheme != request.url.scheme or urlsplit(origin).netloc != request.url.netloc):
        raise HTTPException(403, 'Изменение файлов с другого сайта запрещено')


def record(request, action, **detail):
    row = {'at': time.time(), 'action': action, 'remote': not is_local(request), **detail}
    with JOURNAL_LOCK:
        STATE.mkdir(parents=True, exist_ok=True)
        with JOURNAL.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


def valid_name(name, directory=False):
    name = (name or '').strip()
    if (not name or len(name) > 180 or name in {'.', '..'} or name.startswith('.') or name.endswith((' ', '.'))
            or any(c in '<>:"/\\|?*' or ord(c) < 32 for c in name) or name.casefold() in BLOCKED or secret_name(name)
            or name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}):
        raise HTTPException(400, 'Недопустимое имя')
    if not directory and Path(name).suffix.lower() not in DOWNLOAD:
        raise HTTPException(400, 'Этот формат панель не показывает; загрузите его в архиве .zip')
    return name


def writable(root, path):
    if root not in WRITE_ROOTS:
        raise HTTPException(403, 'Изменения разрешены только в «Проекты»')
    root_row, target = guarded(resolve, root, path)
    return Path(root_row['path']), target


def relative(base, target):
    return str(target.relative_to(base)).replace('\\', '/')


async def body_json(request):
    same_origin(request)
    if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
        raise HTTPException(415, 'Нужен JSON')
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 8192:
            raise HTTPException(413, 'Слишком большой запрос')
    try:
        payload = json.loads(data)
        if not isinstance(payload, dict) or not all(isinstance(v, str) for v in payload.values()):
            raise ValueError
        return payload
    except ValueError:
        raise HTTPException(400, 'Некорректный запрос')


@router.get('/find')
def find(root: str, path: str = '', q: str = ''):
    """Name search below the current folder: bounded by entries, depth and time."""
    needle = q.strip().casefold()
    if not 2 <= len(needle) <= 100:
        raise HTTPException(400, 'Введите от 2 до 100 символов')
    root_row, folder = guarded(resolve, root, path)
    base = Path(root_row['path'])
    rows, scanned, deadline, stack = [], 0, time.monotonic() + 4, [(folder, 0)]
    complete = True
    while stack:
        current, depth = stack.pop()
        if scanned > 30000 or time.monotonic() > deadline or len(rows) >= 300:
            complete = False
            break
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for e in entries:
            scanned += 1
            if e.name.startswith('.') or e.name.casefold() in BLOCKED or secret_name(e.name):
                continue
            try:
                s = e.stat(follow_symlinks=False)
            except OSError:
                continue
            if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                continue
            directory = stat.S_ISDIR(s.st_mode)
            p = Path(e.path)
            if directory and depth < 12:
                stack.append((p, depth + 1))
            if not directory and p.suffix.lower() not in DOWNLOAD:
                continue
            if needle in e.name.casefold():
                rows.append({'name': e.name, 'path': str(p), 'relative': relative(base, p), 'directory': directory,
                             'folder': relative(base, p.parent) if p.parent != base else '',
                             'size': None if directory else s.st_size, 'modified': s.st_mtime,
                             'kind': 'directory' if directory else kind(p), 'extension': p.suffix.lower(), 'tags': []})
    rows.sort(key=lambda r: (not r['directory'], r['name'].casefold()))
    return {'entries': rows, 'complete': complete, 'scanned': scanned}


@router.put('/upload')
async def upload(request: Request, root: str, path: str, name: str):
    same_origin(request)
    base, folder = writable(root, path)
    name = valid_name(name)
    if not folder.is_dir():
        raise HTTPException(400, 'Нужна папка')
    declared = int(request.headers.get('content-length') or 0)
    if declared > UPLOAD_LIMIT:
        raise HTTPException(413, 'Файл больше 20 ГБ')
    if shutil.disk_usage(folder).free < declared + UPLOAD_RESERVE:
        raise HTTPException(507, 'На диске мало места')
    target = folder / name
    stem, n = target.stem, 1
    while target.exists():
        n += 1
        target = folder / f'{stem} ({n}){target.suffix}'
    partial = folder / f'.{target.name}.{uuid.uuid4().hex[:8]}.part'
    written = 0
    try:
        with partial.open('xb') as f:
            async for chunk in request.stream():
                written += len(chunk)
                if written > UPLOAD_LIMIT:
                    raise HTTPException(413, 'Файл больше 20 ГБ')
                f.write(chunk)
        if declared and written != declared:
            raise HTTPException(400, 'Загрузка прервана')
        os.rename(partial, target)
    finally:
        if partial.exists():
            partial.unlink()
    record(request, 'upload', path=str(target), size=written)
    return {'path': relative(base, target), 'name': target.name, 'size': written}


@router.get('/zip')
def folder_zip(request: Request, root: str, path: str = ''):
    root_row, folder = guarded(resolve, root, path)
    if not folder.is_dir():
        raise HTTPException(400, 'Нужна папка')
    limit, files, total = ZIP_LIMIT[is_local(request)], [], 0
    for current, dirs, names in os.walk(folder, followlinks=False):
        here = Path(current)
        keep = []
        for d in dirs:
            try:
                s = (here / d).lstat()
            except OSError:
                continue
            if not (d.startswith('.') or d.casefold() in BLOCKED or secret_name(d) or stat.S_ISLNK(s.st_mode)
                    or getattr(s, 'st_file_attributes', 0) & 0x400):
                keep.append(d)
        dirs[:] = keep
        for n in names:
            p = here / n
            if n.startswith('.') or secret_name(n) or p.suffix.lower() not in DOWNLOAD:
                continue
            try:
                s = p.lstat()
            except OSError:
                continue
            if not stat.S_ISREG(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                continue
            total += s.st_size
            if total > limit:
                raise HTTPException(413, f'Папка больше {limit // 1024**3} ГБ; скачайте её частями')
            files.append(p)
    if not files:
        raise HTTPException(400, 'В папке нет файлов для архива')
    ZIP_TMP.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(suffix='.zip', dir=ZIP_TMP)
    os.close(handle)
    try:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
            for p in files:
                z.write(p, str(p.relative_to(folder)))
    except OSError:
        os.unlink(tmp)
        raise HTTPException(500, 'Не удалось собрать архив')
    record(request, 'zip', path=str(folder), files=len(files), size=total)
    name = (folder.name or root_row['name']) + '.zip'
    return FileResponse(tmp, media_type='application/zip', background=BackgroundTask(os.unlink, tmp),
                        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{quote(name)}", 'Cache-Control': 'no-store'})


@router.post('/mkdir')
async def make_folder(request: Request):
    p = await body_json(request)
    base, folder = writable(p.get('root', ''), p.get('path', ''))
    target = folder / valid_name(p.get('name'), directory=True)
    if not folder.is_dir() or target.exists():
        raise HTTPException(409, 'Такая папка уже есть')
    target.mkdir()
    record(request, 'mkdir', path=str(target))
    return {'path': relative(base, target)}


@router.post('/rename')
async def rename(request: Request):
    p = await body_json(request)
    base, source = writable(p.get('root', ''), p.get('path', ''))
    if source == base:
        raise HTTPException(400, 'Корень нельзя переименовать')
    name = valid_name(p.get('name'), directory=source.is_dir())
    target = source.with_name(name)
    if target.exists() and target.name.casefold() != source.name.casefold():
        raise HTTPException(409, 'Файл с таким именем уже есть')
    os.rename(source, target)
    record(request, 'rename', **{'from': str(source), 'to': str(target)})
    return {'path': relative(base, target)}


@router.post('/move')
async def move(request: Request):
    p = await body_json(request)
    base, source = writable(p.get('root', ''), p.get('path', ''))
    _, dest = writable(p.get('root', ''), p.get('dest', ''))
    if source == base or dest == base or not dest.is_dir():
        raise HTTPException(400, 'Нужна папка назначения внутри проекта')
    if dest == source or dest.is_relative_to(source):
        raise HTTPException(400, 'Папку нельзя перенести внутрь самой себя')
    target = dest / source.name
    if target.exists():
        raise HTTPException(409, 'В папке назначения уже есть файл с таким именем')
    os.rename(source, target)
    record(request, 'move', **{'from': str(source), 'to': str(target)})
    return {'path': relative(base, target)}


@router.post('/trash')
async def trash(request: Request):
    p = await body_json(request)
    base, source = writable(p.get('root', ''), p.get('path', ''))
    if source == base or source.parent == base:
        raise HTTPException(400, 'Корень и папки проектов целиком в карантин не переносятся')
    item = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    holder = QUARANTINE / time.strftime('%Y-%m-%d') / item
    holder.mkdir(parents=True)
    os.rename(source, holder / source.name)
    (holder / 'MANIFEST.json').write_text(json.dumps({'id': item, 'original': str(source), 'at': time.time(),
                                                      'remote': not is_local(request)}, ensure_ascii=False), encoding='utf-8')
    record(request, 'trash', id=item, path=str(source), quarantine=str(holder))
    return {'id': item}


def quarantined():
    rows = []
    if QUARANTINE.is_dir():
        for manifest in sorted(QUARANTINE.glob('*/*/MANIFEST.json'), reverse=True)[:200]:
            try:
                data = json.loads(manifest.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            stored = manifest.parent / Path(data['original']).name
            if stored.exists():
                rows.append({**data, 'name': stored.name, 'holder': str(manifest.parent), 'stored': stored})
    return rows


@router.get('/trash')
def trash_list():
    return {'items': [{k: v for k, v in r.items() if k != 'stored'} for r in quarantined()], 'folder': str(QUARANTINE)}


@router.post('/restore')
async def restore(request: Request):
    p = await body_json(request)
    row = next((r for r in quarantined() if r['id'] == p.get('id')), None)
    if not row:
        raise HTTPException(404, 'В карантине нет такого файла')
    original = Path(row['original'])
    base, _ = writable('projects', '')
    if not original.is_relative_to(base):
        raise HTTPException(400, 'Исходный путь вне «Проекты»')
    for part in original.relative_to(base).parent.parts:
        valid_name(part, directory=True)
    original.parent.mkdir(parents=True, exist_ok=True)
    writable('projects', relative(base, original.parent))  # re-check: no links/junctions on the way back
    target = original
    n = 1
    while target.exists():
        n += 1
        target = original.with_name(f'{original.stem} (восстановлено {n}){original.suffix}')
    os.rename(row['stored'], target)
    (Path(row['holder']) / 'MANIFEST.json').rename(Path(row['holder']) / 'RESTORED.json')
    record(request, 'restore', id=row['id'], path=str(target))
    return {'path': relative(base, target)}


@router.post('/deliver')
async def deliver(request: Request):
    p = await body_json(request)
    if set(p) - {'root', 'path', 'title', 'mode'}:
        raise HTTPException(400, 'Неизвестные параметры доставки')
    mode = p.get('mode', '')
    if mode not in {'preview', 'file'}:
        raise HTTPException(400, 'Выберите режим preview или file')
    root_row, target = guarded(resolve, p.get('root', ''), p.get('path', ''))
    if not target.is_file() or target.suffix.lower() not in DOWNLOAD:
        raise HTTPException(400, 'Отправить можно только файл')
    title = (p.get('title') or target.stem).strip()[:120]
    from report_delivery import enqueue_file, run_action
    result = await run_action(enqueue_file, target, title, mode)
    record(request, 'deliver', path=str(target), title=title, mode=mode,
           delivery_id=result['id'], status=result['status'])
    return result


@router.get('/delivery/{identifier}')
async def delivery_status(identifier: str):
    from report_delivery import run_action, status
    return await run_action(status, identifier)


@router.get('/journal')
def journal(limit: int = 50):
    try:
        lines = JOURNAL.read_text(encoding='utf-8').splitlines()[-max(1, min(limit, 200)):]
    except OSError:
        lines = []
    return {'items': [json.loads(x) for x in reversed(lines) if x.strip()]}
