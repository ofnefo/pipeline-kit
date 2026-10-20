"""Project-owned video annotations and candidate decisions. No model auto-launch."""
import array
import hashlib
import json
import math
import os
from pathlib import Path
import kit_config as config
import re
import shutil
import subprocess
import threading
import time
import urllib.request
import uuid
from fractions import Fraction

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
import project_files_service as files

router = APIRouter(prefix='/api/video-review')
LOCK = threading.Lock()
FFPROBE = config.executable('ffprobe')
FFMPEG = config.executable('ffmpeg')
# Background ffmpeg: no console window, below-normal CPU priority so the panel and other jobs stay responsive.
QUIET = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0)


def project(slug):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{1,62}',slug):  # existing projects: sample projects
        raise ValueError('Некорректное имя проекта')
    _, p = files.resolve('projects','video/'+slug)
    if not p.is_dir(): raise ValueError('Проект не найден')
    return p


def media(slug, relative):
    p=project(slug)
    _, f=files.resolve('projects','video/'+slug+'/'+relative)
    if not f.is_relative_to(p) or not f.is_file() or f.suffix.lower() not in {'.mp4','.webm','.mov','.mkv'}:
        raise ValueError('Выберите видео внутри проекта')
    return f


def identity(p):
    s=p.stat()
    # Windows file IDs and nanosecond timestamps exceed JavaScript's safe integer
    # range. Strings survive a browser JSON round trip without false changes.
    return {'size':str(s.st_size),'mtime_ns':str(s.st_mtime_ns),'file_id':str(s.st_ino)}


def info(p):
    result=subprocess.run([str(FFPROBE),'-v','error','-select_streams','v:0','-show_streams',
                           '-show_format','-of','json',str(p)],stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',
                          timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode: raise ValueError('Не удалось прочитать видео')
    data=json.loads(result.stdout); stream=data['streams'][0]
    fps=Fraction(stream.get('avg_frame_rate','0/1'))
    real=Fraction(stream.get('r_frame_rate','0/1'))
    duration=float(stream.get('duration') or data['format'].get('duration',0))
    if not 1<=fps<=120 or not 0<duration<=1800: raise ValueError('Для правки нужен ролик до 30 минут, 1–120 кадров/с')
    raw_frames=str(stream.get('nb_frames',''))
    exact=raw_frames.isdigit() and int(raw_frames)>0
    frames=int(raw_frames) if exact else round(duration*float(fps))
    return {'fps':str(fps),'fps_value':float(fps),'frames':frames,'duration':duration,
            'width':stream['width'],'height':stream['height'],'identity':identity(p),
            'frame_count_exact':exact,'vfr':real!=fps}


def state_path(slug, create=False):
    base=project(slug)/'50-edit'
    if base.exists(): files.native(base)
    elif create: base.mkdir()
    p=base/'video-review.json'
    if p.exists(): files.native(p)
    return p


def load(slug):
    p=state_path(slug)
    if not p.exists(): return {'schema':1,'project':slug,'requests':[],'comments':[]}
    if p.stat().st_size>8*1024*1024: raise ValueError('Журнал слишком большой')
    return json.loads(p.read_text(encoding='utf-8'))


def save(slug, data):
    p=state_path(slug,create=True); tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
    with tmp.open('x',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
    os.replace(tmp,p)


def safe(fn,*args):
    try: return fn(*args)
    except (ValueError,OSError,KeyError,IndexError,subprocess.SubprocessError,ZeroDivisionError) as e:
        raise HTTPException(400,str(e)) from e


class NewRequest(BaseModel):
    source: str = Field(min_length=1,max_length=800)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    note: str = Field(min_length=1,max_length=4000)
    mode: str = 'flf'
    source_identity: dict
    nonce: str = Field(min_length=8,max_length=80)


class Candidate(BaseModel):
    path: str = Field(min_length=1,max_length=800)
    label: str = Field(default='Вариант',max_length=100)


class Decision(BaseModel):
    variant_id: str


@router.get('/{slug}')
def get_state(slug:str):
    with LOCK: return safe(load,slug)


@router.get('/{slug}/media')
def get_media(slug:str,path:str):
    return safe(lambda:info(media(slug,path)))


def create(slug, body):
    p=media(slug,body.source); meta=info(p)
    if body.source_identity!=meta['identity']: raise ValueError('Исходник изменился. Откройте его снова')
    if not body.note.strip() or body.mode not in ('flf','v2v','inpaint'): raise ValueError('Укажите задачу и способ правки')
    if not body.start<body.end<=meta['frames']: raise ValueError('Проверьте границы фрагмента')
    data=load(slug)
    duplicate=next((r for r in data['requests'] if r['nonce']==body.nonce),None)
    if duplicate:
        if any(duplicate[k]!=v for k,v in {'source':body.source,'start':body.start,'end_exclusive':body.end,'note':body.note.strip(),'mode':body.mode}.items()):
            raise ValueError('Повторный запрос отличается. Сохраните его с новым идентификатором')
        return duplicate
    if len(data['requests'])>=500: raise ValueError('Достигнут лимит замечаний в проекте')
    row={'id':uuid.uuid4().hex,'created_at':time.time(),'source':body.source,'media':meta,
         'start':body.start,'end_exclusive':body.end,'note':body.note.strip(),'mode':body.mode,
         'nonce':body.nonce,'state':'requested','variants':[],'selected_variant':None,
         'execution':'manual_claim_required','inference_run':False}
    data['requests'].append(row);save(slug,data);return row


@router.post('/{slug}/requests')
def add_request(slug:str,body:NewRequest):
    with LOCK:return safe(create,slug,body)


def add_variant(slug,rid,body):
    data=load(slug);row=next(r for r in data['requests'] if r['id']==rid)
    attach(slug,row,body.path,body.label);save(slug,data);return row


def attach(slug,row,path,label,receipt=None):
    if row['state']=='selected':raise ValueError('Сначала создайте новое замечание для другой редакции')
    p=media(slug,path);meta=info(p)
    # UI variants cover exactly the selected interval, no handles.
    expected=row['end_exclusive']-row['start']
    if any(meta[k]!=row['media'][k] for k in ('fps','width','height')) or abs(meta['duration']-expected/meta['fps_value'])>1.1/meta['fps_value']:
        raise ValueError('Вариант должен совпадать по размеру, FPS и длительности выделенного участка. Сначала подготовьте копию')
    if len(row['variants'])>=12:raise ValueError('Не больше 12 вариантов на замечание')
    v={'id':uuid.uuid4().hex,'path':path,'label':label,'media':meta}
    if receipt:v['receipt']=receipt
    row['variants'].append(v);row['state']='review';return v


@router.post('/{slug}/requests/{rid}/variants')
def variant(slug:str,rid:str,body:Candidate):
    with LOCK:
        try:return safe(add_variant,slug,rid,body)
        except StopIteration:raise HTTPException(404,'Замечание не найдено')


def select(slug,rid,body):
    data=load(slug);row=next(r for r in data['requests'] if r['id']==rid)
    v=next(x for x in row['variants'] if x['id']==body.variant_id)
    if identity(media(slug,row['source']))!=row['media']['identity'] or identity(media(slug,v['path']))!=v['media']['identity']:
        raise ValueError('Файлы изменились после просмотра. Добавьте актуальный вариант')
    row.update(state='selected',selected_variant=v['id'],selected_at=time.time())
    row['assembly']='pending: repair-prepare with zero handles, repair-apply; original unchanged'
    save(slug,data);return row


@router.post('/{slug}/requests/{rid}/select')
def decision(slug:str,rid:str,body:Decision):
    with LOCK:
        try:return safe(select,slug,rid,body)
        except StopIteration:raise HTTPException(404,'Вариант не найден')


# Montage M0 (Studio): an all-intra proxy, a thumbnail strip and audio peaks per source, so the editor shows exact
# frames and a timeline. Assets live in <project>\50-edit\.proxy\<key>; the key pins the source file version, so an
# edited source gets fresh assets. The original is only read. One CPU build at a time, below-normal priority.
THUMBS, THUMB_H, PEAKS_PER_S, PEAKS_MAX = 120, 90, 50, 4000
BUILD = threading.Semaphore(1)
BUILDS = {}  # key -> {'state': 'queued'|'building'|'error', 'error': str}
ASSETS = {'proxy.mp4': 'video/mp4', 'sprite.jpg': 'image/jpeg'}


def ff(args, timeout):
    r=subprocess.run([str(FFMPEG),'-v','error','-nostdin','-y',*args],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,timeout=timeout,creationflags=QUIET)
    if r.returncode: raise ValueError('ffmpeg: '+r.stderr.decode('utf-8','replace').strip()[-300:])
    return r.stdout


def probe(p, *args):
    r=subprocess.run([str(FFPROBE),'-v','error',*args,'-of','json',str(p)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,encoding='utf-8',timeout=120,creationflags=QUIET)
    if r.returncode: raise ValueError('Не удалось прочитать видео')
    return json.loads(r.stdout)


def asset_dir(slug, rel, meta, create=False):
    i=meta['identity']; key=hashlib.sha1('\0'.join([rel,i['size'],i['mtime_ns'],i['file_id']]).encode()).hexdigest()[:16]
    base=project(slug)/'50-edit'
    for d in (base,base/'.proxy'):
        if d.exists(): files.native(d)
        elif create: d.mkdir()
    return key, base/'.proxy'/key


def peaks(src):
    """Max |amplitude| per bucket, 0..100, and the bucket length in seconds; None when the file has no audio."""
    if not probe(src,'-select_streams','a:0','-show_entries','stream=index').get('streams'): return None,None
    raw=array.array('h'); raw.frombytes(ff(['-i',str(src),'-map','0:a:0','-ac','1','-ar','4000','-f','s16le','-'],600))
    if not raw: return None,None
    n=max(1,min(PEAKS_MAX,round(len(raw)/4000*PEAKS_PER_S))); step=len(raw)/n
    out=[]
    for k in range(n):
        seg=raw[int(k*step):max(int(k*step)+1,int((k+1)*step))]
        out.append(round(100*max(max(seg),-min(seg))/32768) if seg else 0)
    return out,step/4000


def ready(d):
    m=d/'timeline.json'
    if not m.is_file(): return None
    return json.loads(files.native(m).read_text(encoding='utf-8'))


def build(slug, rel, meta, key, final):
    tmp=final.with_name(key+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with BUILD:
            with LOCK: BUILDS[key]['state']='building'
            for old in final.parent.glob('*.tmp'):  # builds run one at a time, so a temp folder here was left by a crash
                try: shutil.rmtree(files.native(old))
                except (OSError,ValueError): pass
            t0=time.time(); src=media(slug,rel)
            if identity(src)!=meta['identity']: raise ValueError('Исходник изменился во время подготовки')
            tmp.mkdir()
            # -g 1: every frame is a keyframe, so a seek to any frame is exact and cheap; passthrough keeps the frame count.
            ff(['-i',str(src),'-map','0:v:0','-map','0:a:0?','-sn','-dn','-vf','scale=-2:trunc(min(720\\,ih)/2)*2',
                '-fps_mode','passthrough','-c:v','libx264','-preset','veryfast','-crf','20','-g','1','-bf','0',
                '-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-threads','2','-movflags','+faststart',str(tmp/'proxy.mp4')],3600)
            v=probe(tmp/'proxy.mp4','-select_streams','v:0','-show_entries','stream=width,height:packet=pts_time')
            pts=sorted(float(k['pts_time']) for k in v['packets']); frames=len(pts); v=v['streams'][0]
            if meta['frame_count_exact'] and frames!=meta['frames']: raise ValueError(f'Прокси: {frames} кадров вместо {meta["frames"]}')
            step=max(1,math.ceil(frames/THUMBS)); count=math.ceil(frames/step); tw=2*round(THUMB_H*v['width']/v['height']/2)
            ff(['-i',str(tmp/'proxy.mp4'),'-an','-vf',f'select=not(mod(n\\,{step})),scale={tw}:{THUMB_H},tile={count}x1',
                '-fps_mode','vfr','-frames:v','1','-q:v','5','-threads','2',str(tmp/'sprite.jpg')],600)
            values,bucket=peaks(src)
            doc={'source':rel,'identity':meta['identity'],'frames':frames,'width':v['width'],'height':v['height'],
                 'step':step,'thumbs':count,'thumb_w':tw,'thumb_h':THUMB_H,'peaks':values,'peak_seconds':bucket,
                 # Variable frame rate: the page maps playback time to a frame through the frame start times.
                 'times':[round(t-pts[0],6) for t in pts] if meta['vfr'] else None,
                 'seconds':round(time.time()-t0,1),'created':time.time()}
            (tmp/'timeline.json').write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
            with LOCK:  # timeline() checks readiness under the same lock, so a ready set is never rebuilt
                if final.exists(): shutil.rmtree(files.native(final))  # a damaged set without a manifest
                os.replace(tmp,final); BUILDS.pop(key,None)
    except Exception as e:  # the worker thread records every failure for the page instead of dying silently
        with LOCK: BUILDS[key]={'state':'error','error':str(e)[:300] or type(e).__name__}
        shutil.rmtree(tmp,ignore_errors=True)


def timeline(slug, rel, start=False):
    meta=info(media(slug,rel)); key,d=asset_dir(slug,rel,meta,create=start)
    with LOCK:
        doc=ready(d); job=BUILDS.get(key)
        if not doc and start and (not job or job['state']=='error'):
            job=BUILDS[key]={'state':'queued'}
            threading.Thread(target=build,args=(slug,rel,meta,key,d),daemon=True,name='montage-proxy').start()
    if doc: return {**meta,'assets':{'state':'ready','key':key,**doc}}
    return {**meta,'assets':{'state':job['state'] if job else 'none','key':key,'error':(job or {}).get('error')}}


@router.get('/{slug}/timeline')
def get_timeline(slug:str,path:str):
    return safe(timeline,slug,path)


@router.post('/{slug}/timeline')
def make_timeline(slug:str,path:str):
    return safe(timeline,slug,path,True)


@router.get('/{slug}/timeline/{key}/{name}')
def timeline_asset(request:Request,slug:str,key:str,name:str):
    if not re.fullmatch(r'[0-9a-f]{16}',key) or name not in ASSETS: raise HTTPException(404,'Нет такого файла')
    def find():
        p=project(slug)/'50-edit'/'.proxy'/key/name
        if not p.is_file(): raise ValueError('Файл ещё не готов')
        return files.native(p)
    p=safe(find); size=p.stat().st_size
    try: a,b,partial=files.byte_range(request.headers.get('range'),size)
    except ValueError: return Response(status_code=416,headers={'Content-Range':f'bytes */{size}'})
    def chunks():
        with p.open('rb') as f:
            f.seek(a); left=b-a+1
            while left>0:
                block=f.read(min(left,256*1024))
                if not block: break
                left-=len(block); yield block
    # The key names the source version, so a cached asset never goes stale.
    headers={'Accept-Ranges':'bytes','Content-Length':str(max(0,b-a+1)),'Cache-Control':'private, max-age=3600','X-Content-Type-Options':'nosniff'}
    if partial: headers['Content-Range']=f'bytes {a}-{b}/{size}'
    return StreamingResponse(chunks(),status_code=206 if partial else 200,media_type=ASSETS[name],headers=headers)


# Comments pinned to a frame or a range. Each keeps a still of its frame (50-edit\comments\<id>.jpg) for the board
# task; the task link is a marker in the task description, as for requests.
class NewComment(BaseModel):
    source: str = Field(min_length=1,max_length=800)
    frame: int = Field(ge=0)
    end: int | None = None
    text: str = Field(min_length=1,max_length=2000)
    source_identity: dict
    nonce: str = Field(min_length=8,max_length=80)


class Resolve(BaseModel):
    resolved: bool


def grab(src, frame, meta, out, scale='scale=480:-2,'):
    """The still of frame N (scale=None: full size). Constant rate: an accurate seek to (N-1/4)/fps lands on frame N. Variable rate: frame
    times are uneven, so pick frame N by its index (decodes from the start; slower but exact)."""
    if meta['vfr']: pick,ss=f'select=eq(n\\,{frame}),',[]
    else: pick,ss='',['-ss',f'{max(0.0,(frame-0.25)/meta["fps_value"]):.6f}']
    ff([*ss,'-i',str(src),'-an','-vf',(pick+(scale or '')).rstrip(',') or 'null','-fps_mode','vfr','-frames:v','1','-q:v','4','-threads','2',str(out)],900)


def comment(slug, body):
    p=media(slug,body.source); meta=info(p); text=body.text.strip()
    if body.source_identity!=meta['identity']: raise ValueError('Исходник изменился. Откройте его снова')
    if not text: raise ValueError('Напишите комментарий')
    if not body.frame<meta['frames'] or (body.end is not None and not body.frame<body.end<=meta['frames']): raise ValueError('Проверьте кадры комментария')
    same={'source':body.source,'frame':body.frame,'end_exclusive':body.end,'text':text}
    def known(data):
        row=next((c for c in data.get('comments',[]) if c['nonce']==body.nonce),None)
        if row and any(row[k]!=v for k,v in same.items()): raise ValueError('Повторный комментарий отличается. Сохраните его заново')
        return row
    with LOCK:
        if row:=known(load(slug)): return row
        state_path(slug,create=True)
    cid=uuid.uuid4().hex; folder=project(slug)/'50-edit'/'comments'; thumb=None
    try:  # the still is a convenience: a failed grab still saves the comment
        if not folder.exists(): folder.mkdir()
        files.native(folder); grab(p,body.frame,meta,folder/(cid+'.jpg')); thumb='50-edit/comments/'+cid+'.jpg'
    except (ValueError,OSError,subprocess.SubprocessError): pass
    with LOCK:
        data=load(slug)
        if row:=known(data):
            if thumb: (folder/(cid+'.jpg')).unlink(missing_ok=True)
            return row
        if len(data.setdefault('comments',[]))>=2000: raise ValueError('Достигнут лимит комментариев в проекте')
        row={'id':cid,'created_at':time.time(),**same,'nonce':body.nonce,'identity':meta['identity'],'thumb':thumb,'resolved':False}
        data['comments'].append(row); save(slug,data); return row


@router.post('/{slug}/comments')
def add_comment(slug:str,body:NewComment):
    return safe(comment,slug,body)


def resolve(slug, cid, body):
    with LOCK:
        data=load(slug); row=next(c for c in data.get('comments',[]) if c['id']==cid)
        row['resolved']=body.resolved; save(slug,data); return row


@router.post('/{slug}/comments/{cid}/resolve')
def resolve_comment(slug:str,cid:str,body:Resolve):
    try: return safe(resolve,slug,cid,body)
    except StopIteration: raise HTTPException(404,'Комментарий не найден')


# Montage M1a: a new take of a request's span from a local first+last-frame model. The span's first and last frames go
# to LTX-2.5 or Wan 2.2 through the panel's model runner (busy GPU -> shared GPU queue); when the run finishes, the clip
# is retimed to the span (source FPS and size, exact frame count) and attached as a variant with a receipt.
# Files: <project>/50-edit/segments/<request>/g<n>-<id8>-start.png, -end.png, .mp4, .json (unique per generation). Nothing paid.
GEN_MODELS = {  # frames = step*k+1 at fps, k_min..k_max; size: long side, multiple of 32
    'ltx25_flf': {'label': 'LTX-2.5', 'fps': 24, 'step': 8, 'k_min': 2, 'k_max': 15, 'long': {'draft': 768, 'final': 1280}},
    'wan22_i2v14b_flf': {'label': 'Wan 2.2', 'fps': 16, 'step': 4, 'k_min': 4, 'k_max': 20, 'long': {'draft': 832, 'final': 1280}},
}
GEN_ACTIVE = ('starting', 'queued', 'running', 'conforming')
CONFORMING = set()  # generation ids whose conform thread runs in this process
STARTING = set()  # generation ids whose generate() call (stills + model start) runs in this process
RANK = {'starting': 0, 'queued': 1, 'running': 2, 'conforming': 3, 'error': 4}  # sync never moves a generation back


class Generate(BaseModel):
    model: str
    prompt: str = Field(min_length=3, max_length=4000)
    quality: str = 'draft'
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)


def gen_params(spec, meta, frames, quality, seed):
    """Model width/height/length for a span: source aspect at the model's long side, nearest frame count on its grid."""
    seconds = frames / meta['fps_value']
    k = round((seconds * spec['fps'] - 1) / spec['step'])
    if k > spec['k_max']:
        raise ValueError(f'Участок {seconds:.1f} с длиннее, чем берёт {spec["label"]} ({spec["step"] * spec["k_max"] / spec["fps"]:.0f} с). Разбейте его на части')
    long, w, h = spec['long'][quality], meta['width'], meta['height']
    a, b = (long, long * h / w) if w >= h else (long * w / h, long)
    return {'width': max(256, 32 * round(a / 32)), 'height': max(256, 32 * round(b / 32)),
            'length': spec['step'] * max(spec['k_min'], k) + 1, 'seed': seed}


def find_gen(data, rid, gid):
    row = next(r for r in data['requests'] if r['id'] == rid)
    return row, next(g for g in row.get('generations', []) if g['id'] == gid)


def generate(slug, rid, body):
    import models_service as mdl  # the panel's runner and GPU queue
    spec = GEN_MODELS.get(body.model)
    if not spec or body.quality not in spec['long']: raise ValueError('Выберите модель и качество')
    with LOCK:
        data = load(slug); row = next(r for r in data['requests'] if r['id'] == rid)
        if row['state'] == 'selected': raise ValueError('Вариант уже выбран. Для новой правки отметьте участок заново')
        if row.get('mode') != 'flf': raise ValueError('Генерация по первому и последнему кадру работает только для режима «Первый и последний кадр»')
        gens = row.setdefault('generations', [])
        if any(g['state'] in GEN_ACTIVE for g in gens): raise ValueError('Для этого участка уже идёт генерация')
        if len(gens) >= 12 or len(row['variants']) >= 12: raise ValueError('Не больше 12 генераций на участок')
        src = media(slug, row['source']); meta = info(src)
        if meta['identity'] != row['media']['identity']: raise ValueError('Исходник изменился после замечания. Отметьте участок заново')
        n = len(gens) + 1
        seed = body.seed if body.seed is not None else int.from_bytes(os.urandom(4), 'big') >> 1
        params = gen_params(spec, meta, row['end_exclusive'] - row['start'], body.quality, seed)
        g = {'id': uuid.uuid4().hex, 'n': n, 'model': body.model, 'label': f'{spec["label"]} · {n}', 'prompt': body.prompt.strip(),
             'quality': body.quality, 'params': params, 'state': 'starting', 'created_at': time.time()}
        gens.append(g); save(slug, data); STARTING.add(g['id'])

    def finish(**kw):  # only a generation still 'starting' takes the result of its own start
        with LOCK:
            STARTING.discard(g['id'])
            d = load(slug); x = find_gen(d, rid, g['id'])[1]
            if x['state'] == 'starting': x.update(kw); save(slug, d)
            return x
    stem = f'g{n}-{g["id"][:8]}'
    try:  # stills and the model start run outside the journal lock: ComfyUI may take a minute to come up
        folder = project(slug) / '50-edit' / 'segments' / rid
        for d in (folder.parent, folder):
            if d.exists(): files.native(d)
            else: d.mkdir()
        stills = {'start_image': folder / f'{stem}-start.png', 'end_image': folder / f'{stem}-end.png'}
        grab(src, row['start'], meta, stills['start_image'], None)
        grab(src, row['end_exclusive'] - 1, meta, stills['end_image'], None)
        p = {'prompt': g['prompt'], **params}
        if body.model == 'ltx25_flf':
            p.update(start_w=params['width'], start_h=params['height'], end_w=params['width'], end_h=params['height'], audio_frames=params['length'])
        else: p['fps'] = spec['fps']
        inputs = {k: str(v) for k, v in stills.items()}
        title = f'Монтаж {slug} · кадры {row["start"]}–{row["end_exclusive"] - 1} · {spec["label"]} · #{g["id"][:8]}'  # sync finds the ticket by the tag
        tag = {'montage': {'project': slug, 'request': rid, 'generation': g['id']}}
        try:
            run = mdl.start_run(body.model, p, inputs, title, tag)['run']
            return finish(state='running', run_id=run['id'])
        except mdl.GpuBusy as exc:
            t = mdl.enqueue_run(body.model, p, inputs, title, tag)['ticket']
            return finish(state='queued', ticket=t['id'], position=t.get('position'), note=str(exc)[:300])
    except Exception as exc:
        finish(state='error', error=str(exc)[:400] or type(exc).__name__)
        raise ValueError(str(exc)[:400] or 'Генерация не запустилась') from exc
    finally:
        with LOCK: STARTING.discard(g['id'])


@router.post('/{slug}/requests/{rid}/generate')
def start_generation(slug: str, rid: str, body: Generate):
    try: return safe(generate, slug, rid, body)
    except StopIteration: raise HTTPException(404, 'Замечание не найдено')


def conform(gen_file, row, out):
    """Retime a generated clip onto the span: source FPS and size, exactly end-start frames, no audio, H.264."""
    m, n = row['media'], row['end_exclusive'] - row['start']
    s = probe(gen_file, '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets,avg_frame_rate')['streams'][0]
    have, fps = int(s['nb_read_packets']), Fraction(s['avg_frame_rate'])
    if have < 2 or not fps: raise ValueError('Модель вернула пустой ролик')
    stretch = (Fraction(n) / Fraction(m['fps'])) / (have / fps)  # the generated clip spans the request exactly
    ff(['-i', str(gen_file), '-an', '-sn', '-vf',
        f'setpts={float(stretch):.9f}*PTS,fps={m["fps"]},scale={m["width"]}:{m["height"]}:force_original_aspect_ratio=increase:flags=lanczos,'
        f'crop={m["width"]}:{m["height"]},setsar=1,tpad=stop_mode=clone:stop=4', '-frames:v', str(n), '-fps_mode', 'cfr',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-threads', '4', '-movflags', '+faststart', str(out)], 1800)
    return {'generated_frames': have, 'generated_fps': str(fps), 'stretch': float(stretch), 'frames': n}


def sha256(path):
    with open(path, 'rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def claimable(slug, data, rid, gid, out):
    """Under LOCK: the generation is still conforming and its output path is free (no file, no variant under any spelling)."""
    row, g = find_gen(data, rid, gid)
    if g['state'] != 'conforming': return None  # a stale sync or an earlier conform already settled it
    if row['state'] == 'selected': raise ValueError('вариант участка уже выбран')
    key = lambda x: os.path.normcase(os.path.abspath(x))
    if (out.exists() or out.with_suffix('.json').exists()
            or any(key(project(slug) / v['path']) == key(out) for r in data['requests'] for v in r.get('variants', []))):
        raise ValueError(f'файл {out.name} уже занят')
    return row, g


def conform_job(slug, rid, gid, run):
    try:
        with BUILD:
            with LOCK:
                data = load(slug); g = find_gen(data, rid, gid)[1]
                rel = f'50-edit/segments/{rid}/g{g["n"]}-{gid[:8]}.mp4'; out = project(slug) / rel; receipt_path = out.with_suffix('.json')
                found = claimable(slug, data, rid, gid, out)
                if not found: return
                row, g = found
            clip = next((Path(o['path']) for o in run.get('outputs') or [] if Path(o.get('path', '')).suffix.lower() in ('.mp4', '.webm', '.mov')), None)
            if not clip or not clip.is_file(): raise ValueError('Запуск завершился без видео')
            tmp = out.with_name(f'{out.stem}.{uuid.uuid4().hex[:8]}.tmp.mp4')
            try:
                facts = conform(clip, row, tmp)
                receipt = {'generation': gid, 'model': g['model'], 'prompt': g['prompt'], 'params': g['params'], 'run_id': run.get('id'),
                           'run_dir': run.get('out_dir'), 'generated': str(clip), 'generated_sha256': sha256(clip),
                           'output': rel, 'output_sha256': sha256(tmp), 'conform': facts, 'source': row['source'], 'source_identity': row['media']['identity'],
                           'start': row['start'], 'end_exclusive': row['end_exclusive'], 'created_at': time.time()}
                with LOCK:  # recheck, publish and attach in one step: no route can attach or select in between
                    data = load(slug); found = claimable(slug, data, rid, gid, out)
                    if not found: return
                    row, g = found; made = []
                    try:
                        os.link(tmp, out); made.append(out)  # a hard link never replaces an existing file
                        with open(receipt_path, 'x', encoding='utf-8') as f:
                            made.append(receipt_path); f.write(json.dumps(receipt, ensure_ascii=False, indent=1))
                        v = attach(slug, row, rel, g['label'], rel[:-4] + '.json')
                    except BaseException:
                        for x in made: x.unlink(missing_ok=True)
                        raise
                    g.update(state='done', variant=v['id'], path=rel, finished_at=time.time()); save(slug, data)
            finally: tmp.unlink(missing_ok=True)
    except Exception as exc:  # every failure lands on the generation for the page
        with LOCK:
            try:
                data = load(slug); g = find_gen(data, rid, gid)[1]
                if g['state'] == 'conforming': g.update(state='error', error=('Подгонка: ' + str(exc))[:400]); save(slug, data)
            except (StopIteration, ValueError, OSError): pass
    finally:
        with LOCK: CONFORMING.discard(gid)


def sync(slug):
    """Advance active generations from the panel's run list and GPU queue; a finished run starts its conform."""
    import models_service as mdl
    with LOCK:
        data = load(slug)
        active = [(r['id'], dict(g)) for r in data['requests'] for g in r.get('generations', [])
                  if g['state'] in GEN_ACTIVE and g['id'] not in STARTING]  # a start in progress here settles itself
    if not active: return data
    runs, queue, now = mdl.runs(200), mdl.queue_list(), time.time()
    changes, jobs = {}, []
    for rid, g in active:  # a 'starting' one here lost its start call (panel restart): adopt its run or ticket if they exist
        run = next((r for r in runs if (r.get('montage') or {}).get('generation') == g['id']
                    or (g.get('ticket') and r.get('queue_ticket') == g['ticket'])), None)
        if run is None:
            t = next((t for t in queue if t['id'] == g.get('ticket') or str(t.get('title') or '').endswith('#' + g['id'][:8])), None)
            seen = (g['state'], g.get('missing_since'))  # 'missing' holds only while the journal still says exactly this
            if t: changes[g['id']] = {'state': 'queued', 'ticket': t['id'], 'position': t.get('position'), 'note': t.get('note') or '', 'missing_since': None}
            elif not g.get('missing_since'): changes[g['id']] = {'missing_since': now, '_seen': seen}  # the queue hands a ticket to a run in between
            elif now - g['missing_since'] > 60:
                changes[g['id']] = {'state': 'error', '_seen': seen,
                                    'error': 'Запуск пропал из очереди и списка запусков' if g['state'] != 'starting' else 'Запуск прервался (панель перезапускалась?)'}
        elif run.get('status') == 'running': changes[g['id']] = {'state': 'running', 'run_id': run['id'], 'missing_since': None}
        elif run.get('status') == 'done':
            changes[g['id']] = {'state': 'conforming', 'run_id': run['id'], 'missing_since': None}; jobs.append((rid, g['id'], run))
        else:
            tail = [x for x in (run.get('log_tail') or []) if str(x).strip()]
            changes[g['id']] = {'state': 'error', 'run_id': run.get('id'), 'error': (str(tail[-1]) if tail else 'Запуск завершился с ошибкой')[:400]}
    with LOCK:
        data = load(slug); dirty = False
        for r in data['requests']:
            for g in r.get('generations', []):
                upd = {k: v for k, v in changes.get(g['id'], {}).items() if g.get(k) != v and k != '_seen'}
                if not upd or g['state'] not in GEN_ACTIVE or g['id'] in STARTING or g['id'] in CONFORMING: continue  # settled meanwhile
                seen = changes[g['id']].get('_seen')
                if seen and seen != (g['state'], g.get('missing_since')): continue  # another sync found the run meanwhile
                if RANK[upd.get('state', g['state'])] < RANK[g['state']]: continue  # a slower sync saw an older state
                g.update(upd); dirty = True
        if dirty: save(slug, data)
        for rid, gid, run in jobs:
            g = find_gen(data, rid, gid)[1]
            if g['state'] == 'conforming' and gid not in CONFORMING:
                CONFORMING.add(gid)
                threading.Thread(target=conform_job, args=(slug, rid, gid, run), daemon=True, name='montage-conform').start()
        return data


@router.post('/{slug}/generations/sync')
def sync_generations(slug: str):
    return safe(sync, slug)


# Montage M1b: a multi-track sequence in <project>/50-edit/sequence.json. V1 is the base picture with its own sound, V2 lies
# on top of V1 without sound (a generated take covers its span), A1 adds audio under V1. A clip is
# {id, path, start, end (source frames at the sequence FPS, end exclusive), at (sequence frame), mute, label}; clips on one
# track never overlap. The format (FPS, size) comes from the first video clip. Export renders the visible picture piece by
# piece, renders each audio track the same way, mixes them and publishes 50-edit/exports/<name>.mp4 with a receipt next to
# it. Sources are only read; CPU only, one build at a time (BUILD); nothing paid. M1c adds T1, titles over everything (a
# transparent video, usually made by EffectCraft below), and hand-offs to the craft tools.
SEQ_TRACKS = ('V1', 'V2', 'A1', 'T1')
SEQ_VIDEO, SEQ_AUDIO = {'.mp4', '.webm', '.mov', '.mkv'}, set(files.AUDIO)
SEQ_MAX_CLIPS, SEQ_MAX_SECONDS, RATE = 200, 3 * 3600, 48000
SEQ_RUNNING = ('queued', 'running')
SEQ_SKIP = {'studio', '50-edit'} | files.BLOCKED  # the library lists sources (and 50-edit/titles); takes come from the journal
EXPORTING = set()  # export ids whose job runs in this process
FACTS = {}  # (path, size, mtime, file id) -> probe facts


class SeqClip(BaseModel):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,40}$')
    path: str = Field(min_length=1, max_length=800)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    at: int = Field(ge=0)
    mute: bool = False
    label: str = Field(default='', max_length=100)


class SeqBody(BaseModel):
    version: int = Field(ge=0)
    tracks: dict[str, list[SeqClip]]


class SeqPlace(BaseModel):
    version: int = Field(ge=0)
    request_id: str
    variant_id: str


class SeqExport(BaseModel):
    version: int = Field(ge=0)


def clip_file(slug, rel):
    p = project(slug)
    _, f = files.resolve('projects', 'video/' + slug + '/' + rel)
    if not f.is_relative_to(p) or not f.is_file() or f.suffix.lower() not in SEQ_VIDEO | SEQ_AUDIO:
        raise ValueError(f'Нет такого видео или звука в проекте: {rel}')
    return files.native(f)


def clip_facts(slug, rel):
    """Name, length, picture and sound of a project file; cached by the file version."""
    f = clip_file(slug, rel); ident = identity(f); key = (rel, *ident.values())
    if key in FACTS: return FACTS[key]
    d = probe(f, '-show_streams', '-show_format'); streams = d.get('streams') or []
    v = next((s for s in streams if s.get('codec_type') == 'video' and not (s.get('disposition') or {}).get('attached_pic')), None)
    a = next((s for s in streams if s.get('codec_type') == 'audio'), None); sound = bool(a)
    seconds = float((v or {}).get('duration') or (d.get('format') or {}).get('duration') or 0)
    if not (v or sound) or not 0 < seconds <= SEQ_MAX_SECONDS: raise ValueError(f'Не удалось прочитать {f.name}')
    # Clip time 0 is where its picture starts (or its sound, without one): the export counts both from there.
    start = lambda s: float((s or {}).get('start_time') or (d.get('format') or {}).get('start_time') or 0)
    facts = {'path': rel, 'name': f.name, 'seconds': seconds, 'video': bool(v), 'audio': sound, 'identity': ident,
             'origin': start(v or a)}
    if a: facts.update(audio_start=start(a), rate=int(a.get('sample_rate') or 0) or RATE)
    if v:
        rate = str(v.get('avg_frame_rate') or '0/1'); fps = Fraction(0) if rate.endswith('/0') else Fraction(rate)
        # VP8/VP9 keep transparency in a side layer (alpha_mode), read only by the libvpx decoders
        alpha = (v.get('tags') or {}).get('alpha_mode') == '1' or bool(re.match(r'(yuva|rgba|argb|bgra|abgr|gbrap|ya\d)', v.get('pix_fmt') or ''))
        facts.update(codec=v.get('codec_name'), alpha=alpha, width=int(v['width']) // 2 * 2, height=int(v['height']) // 2 * 2,
                     fps=str(fps.limit_denominator(1001)) if 1 <= fps <= 120 else None)
    if len(FACTS) > 4000: FACTS.clear()
    FACTS[key] = facts
    return facts


def seq_frames(facts, fps):
    return max(1, round(facts['seconds'] * fps))


def seq_video(tracks):
    """The format is fixed by video: until a clip lies on V1/V2 it is provisional (music may come first)."""
    return any(tracks.get(t) for t in ('V1', 'V2'))


def seq_rescale(clips, old, new, facts):
    """Clips moved to another frame rate at the same times: music laid before the first video keeps its place."""
    k, fps, out = Fraction(new) / Fraction(old), Fraction(new), []
    r = lambda x: math.floor(x * k + Fraction(1, 2))  # half up, as Math.round on the page
    for c in clips:
        at, pos, start = r(c['at']), r(c['at'] + c['end'] - c['start']), r(c['start'])
        out.append({**c, 'at': at, 'start': start, 'end': max(start + 1, min(start + max(1, pos - at), seq_frames(facts[c['path']], fps)))})
    return out


def seq_path(slug, create=False):
    p = state_path(slug, create).with_name('sequence.json')
    if p.exists(): files.native(p)
    return p


def seq_load(slug):
    p = seq_path(slug)
    if not p.exists():
        return {'schema': 1, 'project': slug, 'version': 0, 'fps': None, 'width': None, 'height': None,
                'tracks': {t: [] for t in SEQ_TRACKS}, 'exports': []}
    if p.stat().st_size > 4 * 1024 * 1024: raise ValueError('Файл монтажа слишком большой')
    return json.loads(p.read_text(encoding='utf-8'))


def seq_save(slug, doc):
    p = seq_path(slug, create=True); tmp = p.with_name(p.name + '.' + uuid.uuid4().hex + '.tmp')
    doc['updated_at'] = time.time()
    with tmp.open('x', encoding='utf-8') as f: json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def seq_check(slug, tracks, doc):
    """Validated tracks (sorted plain clips), the format and the facts of every file in them."""
    if set(tracks) - set(SEQ_TRACKS): raise ValueError('Дорожки монтажа: V1, V2, A1, T1')
    rows = {t: sorted((c if isinstance(c, dict) else c.model_dump() for c in tracks.get(t) or []), key=lambda c: c['at']) for t in SEQ_TRACKS}
    if sum(map(len, rows.values())) > SEQ_MAX_CLIPS: raise ValueError(f'Не больше {SEQ_MAX_CLIPS} клипов в монтаже')
    facts = {c['path']: clip_facts(slug, c['path']) for t in SEQ_TRACKS for c in rows[t]}
    if not facts: return rows, {'fps': None, 'width': None, 'height': None}, facts  # an empty sequence takes the next first clip's format
    fmt = {k: doc.get(k) for k in ('fps', 'width', 'height')}
    if not fmt['fps'] or not seq_video(doc['tracks']):  # the first video sets the format (A1 comes already in its frames)
        first = next((facts[c['path']] for t in ('V1', 'V2') for c in rows[t]), None)
        if first: fmt = {'fps': first.get('fps') or fmt['fps'] or '24', 'width': first['width'], 'height': first['height']}
        elif not fmt['fps']: fmt = {'fps': '24', 'width': 1920, 'height': 1080}
    fps, ids = Fraction(fmt['fps']), set()
    for t in SEQ_TRACKS:
        end = 0
        for c in rows[t]:
            f = facts[c['path']]
            if c['id'] in ids: raise ValueError('Повторяется id клипа')
            ids.add(c['id'])
            if t != 'A1' and not f['video']: raise ValueError(f'{f["name"]}: на {t} кладётся только видео')
            if t == 'A1' and not f['audio']: raise ValueError(f'{f["name"]}: в файле нет звука')
            if not c['start'] < c['end'] <= seq_frames(f, fps): raise ValueError(f'{f["name"]}: клип выходит за длину файла')
            if c['at'] < end: raise ValueError(f'{t}: клипы наложились на кадре {c["at"]}')
            end = c['at'] + c['end'] - c['start']
            if end > SEQ_MAX_SECONDS * fps: raise ValueError('Монтаж длиннее 3 часов')
    return rows, fmt, facts


def seq_view(slug, doc):
    """The document plus facts of its files (a missing file is marked, not an error) for the page."""
    fps, media = Fraction(doc['fps']) if doc.get('fps') else None, {}
    for c in (c for t in SEQ_TRACKS for c in doc['tracks'].get(t) or []):
        if c['path'] in media: continue
        try:
            f = clip_facts(slug, c['path'])
            media[c['path']] = {**f, 'frames': seq_frames(f, fps) if fps else None, 'changed': f['identity'] != (doc.get('sources') or {}).get(c['path'])}
        except (ValueError, OSError, subprocess.SubprocessError): media[c['path']] = {'path': c['path'], 'name': Path(c['path']).name, 'missing': True}
    return {**doc, 'media': media}


def seq_get(slug):
    project(slug)
    with LOCK:
        doc = seq_load(slug)
        stale = [e for e in doc.get('exports') or [] if e['state'] in SEQ_RUNNING and e['id'] not in EXPORTING]
        for e in stale: e.update(state='error', error='Экспорт прервался (панель перезапускалась?)')
        if stale: seq_save(slug, doc)
    return seq_view(slug, doc)


def seq_commit(slug, version, tracks):
    """Save new tracks if nobody saved since `version` (optimistic: the page sends the version it edited)."""
    conflict = HTTPException(409, 'Монтаж изменили в другом окне. Обновите страницу')
    with LOCK: doc = seq_load(slug)
    if doc['version'] != version: raise conflict
    rows, fmt, facts = seq_check(slug, tracks, doc)  # probes run outside the lock
    with LOCK:
        doc = seq_load(slug)
        if doc['version'] != version: raise conflict
        doc.update(fmt, tracks=rows, version=version + 1, sources={p: f['identity'] for p, f in facts.items()}); seq_save(slug, doc)
    return seq_view(slug, doc)


def seq_clip(slug, rel):
    with LOCK: doc = seq_load(slug)
    f = clip_facts(slug, rel); fixed = seq_video(doc['tracks']) and doc.get('fps')
    fps = Fraction(fixed or (f['video'] and f.get('fps')) or doc.get('fps') or '24')
    return {**f, 'frames': seq_frames(f, fps), 'sequence_fps': str(fps)}


def seq_library(slug):
    """Project video and audio files (newest first; links and junctions are never followed) and the takes of every request."""
    p, rows, stack, budget = project(slug), [], [(project(slug), 0)], 6000
    titles = p / '50-edit' / 'titles'  # made titles are listed too (their .mov twins are for FilmCraft)
    if titles.is_dir() and not (titles.is_symlink() or titles.is_junction() or titles.parent.is_symlink() or titles.parent.is_junction()):
        stack.append((titles, 4))
    while stack and budget > 0:
        d, level = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    budget -= 1
                    if budget < 0: break
                    if e.name.startswith('.') or e.is_symlink() or getattr(e, 'is_junction', lambda: False)(): continue
                    try:
                        suffix = Path(e.name).suffix.lower()
                        if e.is_dir(follow_symlinks=False):
                            if level < 5 and e.name.casefold() not in SEQ_SKIP: stack.append((Path(e.path), level + 1))
                        elif suffix in SEQ_VIDEO | SEQ_AUDIO and not (d == titles and suffix == '.mov' and Path(e.path).with_suffix('.webm').is_file()):
                            st = e.stat(follow_symlinks=False)
                            rows.append({'path': Path(e.path).relative_to(p).as_posix(), 'name': e.name, 'size': st.st_size,
                                         'modified': st.st_mtime, 'kind': 'audio' if suffix in SEQ_AUDIO else 'video'})
                    except OSError: continue
        except OSError: continue
    with LOCK: data = load(slug)
    takes = [{'path': v['path'], 'label': v.get('label') or 'Вариант', 'request': r['id'], 'variant': v['id'], 'source': r['source'],
              'start': r['start'], 'end_exclusive': r['end_exclusive'], 'note': r['note'][:200],
              'selected': r.get('selected_variant') == v['id']} for r in data['requests'] for v in r.get('variants', [])]
    return {'files': sorted(rows, key=lambda r: r['modified'], reverse=True)[:300], 'takes': takes[::-1][:200]}


def seq_place(slug, body):
    """Put a request's take on V2 exactly over its span; the source goes on V1 first (at the end) when it is not there."""
    with LOCK:
        data = load(slug); row = next(r for r in data['requests'] if r['id'] == body.request_id)
        v = next(x for x in row['variants'] if x['id'] == body.variant_id); doc = seq_load(slug)
    if doc['version'] != body.version: raise HTTPException(409, 'Монтаж изменили в другом окне. Обновите страницу')
    src, take = clip_facts(slug, row['source']), clip_facts(slug, v['path'])
    if src['identity'] != row['media']['identity'] or take['identity'] != v['media']['identity']:
        raise ValueError('Файлы изменились после просмотра. Добавьте актуальный вариант')
    fixed = seq_video(doc['tracks']) and doc.get('fps')
    fps = Fraction(fixed or src.get('fps') or doc.get('fps') or '24')
    tracks = {t: [dict(c) for c in doc['tracks'].get(t) or []] for t in SEQ_TRACKS}
    if not fixed and doc.get('fps') and Fraction(doc['fps']) != fps:
        for t in ('A1', 'T1'):  # sound and titles laid before the first video keep their times
            tracks[t] = seq_rescale(tracks[t], doc['fps'], fps, {c['path']: clip_facts(slug, c['path']) for c in tracks[t]})
    k = fps / Fraction(row['media']['fps'])  # the span in the source, in sequence frames
    s, e = round(row['start'] * k), round(row['end_exclusive'] * k)
    n, have = e - s, seq_frames(take, fps)
    if not n <= have <= n + 1: raise ValueError(f'Вариант: {have} кадр. вместо {n} — участок не закроется целиком')
    base = next((c for c in tracks['V1'] if c['path'] == row['source'] and c['start'] <= s and e <= c['end']), None)
    if base is None and any(c['path'] == row['source'] and c['start'] < e and s < c['end'] for c in tracks['V1']):
        raise ValueError('На V1 исходник обрезан внутри участка. Верните участок целиком в один клип')
    if base is None:
        base = {'id': uuid.uuid4().hex[:12], 'path': row['source'], 'start': 0, 'end': seq_frames(src, fps),
                'at': max((c['at'] + c['end'] - c['start'] for c in tracks['V1']), default=0), 'mute': False, 'label': ''}
        tracks['V1'].append(base)
    at = base['at'] + s - base['start']
    if any(c['at'] < at + n and at < c['at'] + c['end'] - c['start'] for c in tracks['V2']):
        raise ValueError('На V2 в этом месте уже лежит клип. Уберите или сдвиньте его')
    tracks['V2'].append({'id': uuid.uuid4().hex[:12], 'path': v['path'], 'start': 0, 'end': n, 'at': at, 'mute': False,
                         'label': v.get('label') or ''})
    return seq_commit(slug, body.version, tracks)


def seq_pieces(top, base):
    """What is seen: `top` over `base`, None in gaps; [(clip|None, at, frames)], neighbours of one clip merged."""
    span = lambda c: (c['at'], c['at'] + c['end'] - c['start'])
    cuts, out = sorted({0, *(x for c in top + base for x in span(c))}), []
    for a, b in zip(cuts, cuts[1:]):
        c = next((c for c in top if span(c)[0] <= a < span(c)[1]), None) or next((c for c in base if span(c)[0] <= a < span(c)[1]), None)
        if out and out[-1][0] is c: out[-1] = (c, out[-1][1], out[-1][2] + b - a)
        else: out.append((c, a, b - a))
    return out


def concat(work, names, out, cmds):
    (work / (out + '.txt')).write_text(''.join(f"file '{x}'\n" for x in names), encoding='utf-8')
    args = ['-f', 'concat', '-safe', '0', '-i', str(work / (out + '.txt')), '-c', 'copy', str(work / out)]
    ff(args, 3600); cmds.append(args)


def audio_track(slug, clips, total, fps, facts, work, tag, cmds):
    """One audio track as a 48 kHz stereo WAV of exactly the sequence length: clip sound, silence in gaps and muted clips."""
    sample = lambda frame: round(frame * RATE / fps)  # per boundary, so the pieces add up without drift
    rows, end = [], 0
    for c, at, n in seq_pieces(clips, []):
        if at >= total: break
        rows.append((c, at, min(n, total - at))); end = at + rows[-1][2]
    if end < total: rows.append((None, end, total - end))
    names = []
    for i, (c, at, n) in enumerate(rows):
        ns, out = sample(at + n) - sample(at), f'{tag}{i:04d}.wav'
        if c and not c.get('mute') and facts[c['path']]['audio']:
            # Timestamps from the clip's origin, as for its picture (-copyts -itsoffset), so sound late in the file keeps its
            # place and a split clip sounds as the whole one. The cut and the lead silence fall on the file's own samples
            # before resampling; the seek is a second early and imprecise, atrim cuts exactly. A cut between two samples
            # of the file (8 kHz at 30 fps) takes the earlier one and drops the rest after resampling, so no phase is lost.
            f = facts[c['path']]; off = c['start'] + at - c['at']; ss = off / fps - 1
            i0 = math.floor(off * f['rate'] / fps); lead = max(0, round((f['audio_start'] - f['origin']) * f['rate']) - i0)
            drop = round(off * RATE / fps - Fraction(i0 * RATE, f['rate']))
            inp = ['-copyts', '-itsoffset', f'{-f["origin"]:.6f}', *(['-noaccurate_seek', '-ss', f'{float(ss):.6f}'] if ss > 0 else []),
                   '-i', str(clip_file(slug, c['path'])), '-map', '0:a:0', '-vn', '-sn', '-dn', '-af',
                   f'atrim=start_pts={i0},asetpts=PTS-STARTPTS{f",adelay=delays={lead}S:all=1" if lead else ""},aresample={RATE},'
                   f'{f"atrim=start_sample={drop},asetpts=PTS-STARTPTS," if drop else ""}aformat=sample_fmts=s16:channel_layouts=stereo,apad=whole_len={ns},atrim=end_sample={ns}']
        else: inp = ['-f', 'lavfi', '-i', f'anullsrc=r={RATE}:cl=stereo', '-af', f'atrim=end_sample={ns}']
        args = [*inp, '-c:a', 'pcm_s16le', str(work / out)]; ff(args, 1800); cmds.append(args); names.append(out)
    concat(work, names, tag + '.wav', cmds)


def titles_over(slug, titles, base, total, fps, W, H, facts, work, cmds):
    """T1 over the glued picture in one pass: each title from its origin, as a V1 piece, at its sequence frame; the
    picture shows through its transparency and around it (padding is transparent), nothing after its last frame."""
    inputs, graph, last = ['-copyts', '-i', str(base)], [], '0:v'
    for i, c in enumerate(titles, 1):
        f = facts[c['path']]; ss = c['start'] / fps - 1
        dec = {'vp9': 'libvpx-vp9', 'vp8': 'libvpx'}.get(f.get('codec')) if f.get('alpha') else None
        inputs += ['-itsoffset', f'{-f["origin"]:.6f}', *(['-noaccurate_seek', '-ss', f'{float(ss):.6f}'] if ss > 0 else []),
                   *(['-c:v', dec] if dec else []), '-i', str(clip_file(slug, c['path']))]
        graph.append(f'[{i}:v]fps={fps}{"" if ss > 0 else ":start_time=0"},trim=start_pts={c["start"]}:end_pts={c["end"]},'
                     f'setpts=PTS-STARTPTS+{c["at"]},scale={W}:{H}:force_original_aspect_ratio=decrease,format=yuva420p,'
                     f'pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black@0,setsar=1[t{i}];[{last}][t{i}]overlay=eof_action=pass:repeatlast=0[o{i}]')
        last = f'o{i}'
    out = work / 'titled.mp4'
    args = [*inputs, '-filter_complex', ';'.join(graph) + f';[{last}]format=yuv420p[v]', '-map', '[v]', '-frames:v', str(total),
            '-fps_mode', 'passthrough', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p', '-threads', '4', str(out)]
    ff(args, 3600); cmds.append(args)
    if packets(out, 'v:0') != total: raise ValueError('Титры дали другое число кадров')
    return out


def packets(path, stream):
    return int(probe(path, '-select_streams', stream, '-count_packets', '-show_entries', 'stream=nb_read_packets')['streams'][0]['nb_read_packets'])


def export_job(slug, eid, doc):
    t0, work = time.time(), None

    def mark(**kw):
        with LOCK:
            d = seq_load(slug); e = next((x for x in d.get('exports') or [] if x['id'] == eid), None)
            if e: e.update(kw); seq_save(slug, d)
    try:
        with BUILD:
            mark(state='running', started_at=time.time())
            fps, W, H = Fraction(doc['fps']), doc['width'], doc['height']
            v1, v2, a1, t1 = (sorted(doc['tracks'].get(t) or [], key=lambda c: c['at']) for t in SEQ_TRACKS)
            facts = {c['path']: clip_facts(slug, c['path']) for c in v1 + v2 + a1 + t1}
            seq_changed(doc, facts)
            pieces = seq_pieces(v2, v1); total = sum(n for _, _, n in pieces)
            out_dir = project(slug) / '50-edit' / 'exports'
            if out_dir.exists(): files.native(out_dir)
            else: out_dir.mkdir()
            for old in out_dir.glob('.*.tmp'):  # left by a crash: exports run one at a time, so no job owns it
                try: shutil.rmtree(files.native(old))
                except (OSError, ValueError): pass
            work = out_dir / f'.{eid}.tmp'; work.mkdir(); cmds, names = [], []
            fit = f'scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p'
            for i, (c, at, n) in enumerate(pieces):
                if c:
                    # Timestamps count from the clip's origin (-copyts -itsoffset, as in audio_track), so the sequence-frame grid
                    # is the same for every piece: a split clip shows the same pictures as the whole one at any frame rate. The
                    # seek lands on a keyframe at least a second early, so the picture still showing at the cut is decoded even
                    # in a sparse VFR file; trim cuts at the exact sequence frame; tpad covers a short source.
                    off = c['start'] + at - c['at']; ss = off / fps - 1
                    inp = ['-copyts', '-itsoffset', f'{-facts[c["path"]]["origin"]:.6f}',
                           *(['-noaccurate_seek', '-ss', f'{float(ss):.6f}'] if ss > 0 else []),
                           '-i', str(clip_file(slug, c['path'])),
                           '-map', '0:v:0', '-an', '-sn', '-dn', '-vf',
                           f'fps={fps}{"" if ss > 0 else ":start_time=0"},trim=start_pts={off},setpts=PTS-STARTPTS,{fit},tpad=stop_mode=clone:stop=2']
                else: inp = ['-f', 'lavfi', '-i', f'color=c=black:s={W}x{H}:r={fps}', '-vf', 'setsar=1,format=yuv420p']
                args = [*inp, '-frames:v', str(n), '-fps_mode', 'cfr', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16',
                        '-pix_fmt', 'yuv420p', '-threads', '4', str(work / f'p{i:04d}.mp4')]
                ff(args, 3600); cmds.append(args); names.append(f'p{i:04d}.mp4')
            concat(work, names, 'video.mp4', cmds)
            if packets(work / 'video.mp4', 'v:0') != total: raise ValueError('Склейка дала другое число кадров')
            picture = titles_over(slug, t1, work / 'video.mp4', total, fps, W, H, facts, work, cmds) if t1 else work / 'video.mp4'
            audio_track(slug, v1, total, fps, facts, work, 'V1', cmds)
            audio_track(slug, a1, total, fps, facts, work, 'A1', cmds)
            final = work / 'final.mp4'
            args = ['-i', str(picture), '-i', str(work / 'V1.wav'), '-i', str(work / 'A1.wav'), '-filter_complex',
                    f'[1:a][2:a]amix=inputs=2:normalize=0:duration=longest,atrim=end_sample={round(total * RATE / fps)}[a]',
                    '-map', '0:v:0', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(final)]
            ff(args, 3600); cmds.append(args)
            if packets(final, 'v:0') != total: raise ValueError('В итоговом файле другое число кадров')
            for rel, f in facts.items():
                if identity(clip_file(slug, rel)) != f['identity']: raise ValueError(f'{f["name"]} изменился во время экспорта')
            rel = f'50-edit/exports/{slug}-v{doc["version"]}-{time.strftime("%Y%m%d-%H%M%S")}-{eid[:6]}.mp4'
            out = project(slug) / rel; receipt_path = out.with_suffix('.json'); digest = sha256(final)
            receipt = {'export': eid, 'project': slug, 'sequence_version': doc['version'],
                       'sequence_sha256': hashlib.sha256(json.dumps(doc['tracks'], sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                       'fps': doc['fps'], 'width': W, 'height': H, 'frames': total, 'seconds': float(total / fps), 'tracks': doc['tracks'],
                       'sources': {k: f['identity'] for k, f in facts.items()}, 'pieces': [[c and c['id'], at, n] for c, at, n in pieces],
                       'output': rel, 'output_sha256': digest, 'commands': [[str(FFMPEG), *a] for a in cmds],
                       'render_seconds': round(time.time() - t0, 1), 'created_at': time.time()}
            made = []
            try:
                os.link(final, out); made.append(out)  # a hard link never replaces an existing file
                with open(receipt_path, 'x', encoding='utf-8') as f:
                    made.append(receipt_path); f.write(json.dumps(receipt, ensure_ascii=False, indent=1))
            except BaseException:
                for x in made: x.unlink(missing_ok=True)
                raise
            mark(state='done', path=rel, receipt=rel[:-4] + '.json', frames=total, output_sha256=digest,
                 render_seconds=receipt['render_seconds'], finished_at=time.time())
    except Exception as exc:  # every failure lands on the export for the page
        try: mark(state='error', error=str(exc)[:400] or type(exc).__name__)
        except (ValueError, OSError): pass
    finally:
        if work: shutil.rmtree(work, ignore_errors=True)
        with LOCK: EXPORTING.discard(eid)


def seq_changed(doc, facts):
    """Refuse files replaced since the save: their clips were checked against the old files."""
    saved = doc.get('sources') or {}
    names = [f['name'] for p, f in facts.items() if f['identity'] != saved.get(p)]
    if names: raise ValueError('После сохранения монтажа заменили: ' + ', '.join(names[:5]) + '. Проверьте клипы и сохраните монтаж заново')


def seq_export(slug, body):
    stale = HTTPException(409, 'Монтаж изменился. Дождитесь сохранения и повторите')
    with LOCK: doc = seq_load(slug)
    if doc['version'] != body.version: raise stale
    if not (doc['tracks'].get('V1') or doc['tracks'].get('V2')): raise ValueError('В монтаже нет видео')
    _, _, facts = seq_check(slug, doc['tracks'], doc)  # the saved clips still fit their files (probes outside the lock)
    seq_changed(doc, facts)
    with LOCK:
        doc = seq_load(slug)
        if doc['version'] != body.version: raise stale
        exports = doc.get('exports') or []
        if any(e['state'] in SEQ_RUNNING and e['id'] in EXPORTING for e in exports): raise ValueError('Экспорт уже идёт')
        e = {'id': uuid.uuid4().hex, 'version': doc['version'], 'state': 'queued', 'created_at': time.time()}
        doc['exports'] = exports[-19:] + [e]; seq_save(slug, doc); EXPORTING.add(e['id'])
    threading.Thread(target=export_job, args=(slug, e['id'], doc), daemon=True, name='montage-export').start()
    return e


# Montage M1c: hand-offs to the craft tools on Local node (local, CPU, nothing paid; the service never opens their windows).
# A title is an EffectCraft project rendered to ProRes 4444 (.mov: FilmCraft reads its alpha) and to VP9 with alpha (.webm:
# the page and the export read it) in 50-edit/titles; the .webm goes on T1. FilmCraft gets a new .fcproj of the saved
# sequence in 50-edit/filmcraft (never one Operator may have edited). Stems are V1/A1 as WAVs in 50-edit/audio for openDAW.
def craft_cli(name):
    """The <name>-cli.exe the agents' MCP entry runs (agents/manifest.json), so a version update moves both at once."""
    try:
        m = json.loads((Path(__file__).resolve().parents[1] / 'agents' / 'manifest.json').read_text(encoding='utf-8'))
        return Path(m['mcp_servers'][name]['command'])
    except (OSError, ValueError, KeyError, TypeError): return Path(f'{name}-cli.exe')  # not a file: craft() says it is missing


EFFECTCRAFT = craft_cli('effectcraft')
FILMCRAFT = craft_cli('filmcraft')
TICKS = 254016000000  # FilmCraft time units per second
CRAFT = threading.Lock()  # one title or FilmCraft project at a time
TITLE_SIZE = {'small': .05, 'medium': .075, 'large': .11}  # of the frame height
OPENDAW = {'url': 'http://localhost:8080/', 'start': 'See upstream OpenDAW installation instructions', 'note': 'Optional external editor'}


class SeqTitle(BaseModel):
    version: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=200)
    seconds: float = Field(ge=0.5, le=30)
    place: str = Field(default='bottom', pattern=r'^(bottom|center|top)$')
    size: str = Field(default='medium', pattern=r'^(small|medium|large)$')


def craft(exe, args, cwd, timeout=300):
    if not exe.is_file(): raise ValueError(f'Не найден {exe.name} на Local node')
    r = subprocess.run([str(exe), *args], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd,
                       timeout=timeout, creationflags=QUIET)
    out = r.stdout.decode('utf-8', 'replace')
    if r.returncode: raise ValueError(f'{exe.stem}: ' + (r.stderr.decode('utf-8', 'replace') + out).strip()[-300:])
    return out


def edit_dir(slug, name):
    """50-edit/<name> (made if missing) with the work folders a crash left removed; callers hold the lock that owns them."""
    d = state_path(slug, True).parent / name
    if d.exists(): files.native(d)
    else: d.mkdir()
    for old in d.glob('.*.tmp'):
        try: shutil.rmtree(files.native(old))
        except (OSError, ValueError): pass
    return d


def seq_fixed(slug, version):
    with LOCK: doc = seq_load(slug)
    if doc['version'] != version: raise HTTPException(409, 'Монтаж изменился. Дождитесь сохранения и повторите')
    return doc


def seq_title(slug, body):
    """A white title with a black outline and soft fades, in the sequence format; returns the .webm to lay on T1."""
    doc = seq_fixed(slug, body.version)
    if not (seq_video(doc['tracks']) and doc.get('fps')): raise ValueError('Сначала положите видео на V1: титр делается в формате монтажа')
    lines = [x for x in (re.sub(r'[\x00-\x1f\x7f]', '', x).strip() for x in body.text.splitlines()) if x]
    if not 1 <= len(lines) <= 3: raise ValueError('Титр: от одной до трёх строк')
    fps, W, H = Fraction(doc['fps']), doc['width'], doc['height']
    frames = max(1, round(body.seconds * fps)); dur = float(frames / fps)
    size = round(H * TITLE_SIZE[body.size]); lead, n = size * 1.2, len(lines)  # the position is the first line's baseline
    y = {'top': H * .1 + size, 'center': H / 2 - (n - 1) * lead / 2 + size * .35, 'bottom': H * .9 - (n - 1) * lead}[body.place]
    fade = min(.3, dur / 4)
    jsx = '\n'.join([
        f'var c = app.project.items.addComp("Title", {W}, {H}, 1, {dur!r}, {float(fps)!r});',
        f'var t = c.layers.addText({json.dumps(chr(10).join(lines))});',
        'var p = t.property("ADBE Text Properties").property("ADBE Text Document"); var d = p.value;',
        f'd.fontSize = {size}; d.fillColor = [1,1,1]; d.applyStroke = true; d.strokeColor = [0,0,0]; d.strokeWidth = {max(2, size // 16)};',
        'd.strokeOverFill = false; d.justification = ParagraphJustification.CENTER_JUSTIFY; p.setValue(d);',
        f'var g = t.property("ADBE Transform Group"); g.property("ADBE Position").setValue([{W / 2!r}, {round(y, 1)!r}]);',
        'var o = g.property("ADBE Opacity");',
        f'o.setValueAtTime(0, 0); o.setValueAtTime({fade!r}, 100); o.setValueAtTime({dur - fade!r}, 100); o.setValueAtTime({dur!r}, 0);', ''])
    if not CRAFT.acquire(blocking=False): raise ValueError('Титр или проект FilmCraft уже собирается. Повторите через минуту')
    try:
        out_dir = edit_dir(slug, 'titles'); name = f'title-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}'
        work = out_dir / f'.{name}.tmp'; work.mkdir()
        try:
            (work / 't.jsx').write_text(jsx, encoding='utf-8')
            craft(EFFECTCRAFT, ['script', 't.jsx', '--empty', '--save-as', 't.ecproj'], work, 120)
            craft(EFFECTCRAFT, ['render', '--project', 't.ecproj', '--comp', 'Title', '--out', 't.mov', '--format', 'prores',
                                '--prores', '4444', '--channels', 'rgba'], work, 600)
            ff(['-i', str(work / 't.mov'), '-map', '0:v:0', '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-deadline', 'realtime',
                '-cpu-used', '8', '-crf', '20', '-b:v', '0', '-auto-alt-ref', '0', '-threads', '4', str(work / 't.webm')], 600)
            got = packets(work / 't.webm', 'v:0')
            if abs(got - frames) > 1: raise ValueError(f'EffectCraft дал {got} кадр. вместо {frames}')
            made = []
            try:
                for ext in ('ecproj', 'mov', 'webm'):
                    os.link(work / f't.{ext}', out_dir / f'{name}.{ext}'); made.append(out_dir / f'{name}.{ext}')
            except BaseException:
                for x in made: x.unlink(missing_ok=True)
                raise
        finally: shutil.rmtree(work, ignore_errors=True)
    finally: CRAFT.release()
    rel = f'50-edit/titles/{name}'
    return {'path': rel + '.webm', 'mov': rel + '.mov', 'project': rel + '.ecproj', 'frames': got}


def fc_run(lines, work, tag, *opts):
    """One filmcraft-cli batch saved as <tag>.fcproj: every command must succeed; returns their results in order."""
    (work / f'{tag}.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in lines), encoding='utf-8')
    out = craft(FILMCRAFT, [*opts, 'run', f'{tag}.jsonl', '--json', '--save-as', f'{tag}.fcproj'], work, 600)
    rows = [json.loads(x) for x in out.splitlines() if x.startswith('{')]
    bad = next((r for r in rows if not r.get('ok')), None)
    if bad or len(rows) != len(lines): raise ValueError(f'FilmCraft: {json.dumps(bad or rows[-1:], ensure_ascii=False)[:300]}')
    return [r.get('result') or {} for r in rows]


def seq_filmcraft(slug, body):
    """The saved sequence as a new FilmCraft project: V1 with its sound on V1/A1, V2 on V2, T1 on V3 (its .mov, which keeps
    the alpha for FilmCraft), our A1 on A2; muted sound is placed disabled. Built headless in three batches (clip ids come
    from each batch's answers) and checked by reading the sequence back."""
    doc = seq_fixed(slug, body.version)
    if not (doc['tracks'].get('V1') or doc['tracks'].get('V2')): raise ValueError('В монтаже нет видео')
    rows, _, facts = seq_check(slug, doc['tracks'], doc); seq_changed(doc, facts)
    fps, W, H = Fraction(doc['fps']), doc['width'], doc['height']
    lanes = {'V1': ('V1', 'A1'), 'V2': ('V2', 'A3'), 'T1': ('V3', 'A4'), 'A1': ('V4', 'A2')}  # place puts both halves; spare ones are cleared
    order, src, warn = [(t, c) for t in SEQ_TRACKS for c in rows[t]], {}, []
    for t, c in order:
        f = clip_file(slug, c['path'])
        if t == 'T1' and f.suffix.lower() == '.webm':  # the twin passes the same checks and must match the title it stands for
            rel, w = Path(c['path']).with_suffix('.mov').as_posix(), facts[c['path']]
            try: m = clip_facts(slug, rel); ok = m.get('alpha') and all(m.get(k) == w.get(k) for k in ('fps', 'width', 'height')) and seq_frames(m, fps) == seq_frames(w, fps)
            except (ValueError, OSError): m = ok = None
            if ok: f = clip_file(slug, rel)
            else: warn.append(f'{f.name}: ' + ('рядом нет .mov' if m is None else '.mov рядом не совпадает с титром') + ' — в FilmCraft прозрачность может стать чёрной')
        src[c['id']] = str(f)
    if not CRAFT.acquire(blocking=False): raise ValueError('Титр или проект FilmCraft уже собирается. Повторите через минуту')
    try:
        out_dir = edit_dir(slug, 'filmcraft'); name = f'{slug}-v{doc["version"]}-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:4]}'
        work = out_dir / f'.{name}.tmp'; work.mkdir()
        try:
            paths = list(dict.fromkeys(src.values()))
            res = fc_run([{'id': 'file.newSequence', 'params': {'name': slug, 'width': W, 'height': H, 'fps': float(fps), 'video': 4, 'audio': 4}},
                          *({'id': 'file.import', 'params': {'paths': [x]}} for x in paths)], work, 'a')
            items = {x: r['items'][0] for x, r in zip(paths, res[1:]) if len(r.get('items') or []) == 1}
            if len(items) != len(paths): raise ValueError('FilmCraft не импортировал: ' + ', '.join(Path(x).name for x in paths if x not in items)[:200])
            ticks = lambda frames: round(frames * TICKS / fps)
            res = fc_run([{'id': 'timeline.place', 'params': {'item': items[src[c['id']]], 'track': lanes[t][0], 'audioTrack': lanes[t][1],
                                                              'frame': c['at'], 'insert': False, 'sourceIn': ticks(c['start']),
                                                              'duration': ticks(c['end'] - c['start'])}} for t, c in order],
                         work, 'b', '--project', 'a.fcproj')
            clear, off = [], []
            for (t, c), r in zip(order, res):
                f = facts[c['path']]; got = r.get('clips') or []
                halves = dict(zip([k for k in ('video', 'audio') if f[k]], got))
                if len(got) != len(halves) or (t != 'A1' and 'video' not in halves): raise ValueError(f'FilmCraft положил {f["name"]} не так: {got}')
                if t in ('V2', 'T1') and 'audio' in halves: clear.append(halves['audio'])
                if t == 'A1' and 'video' in halves: clear.append(halves['video'])
                if t in ('V1', 'A1') and c.get('mute') and 'audio' in halves: off.append(halves['audio'])
            cmds = [{'id': 'sequence.linkedSelection', 'params': {'on': False}}]
            if clear: cmds += [{'id': 'timeline.select', 'params': {'clips': clear, 'add': False, 'toggle': False}}, {'id': 'edit.clear', 'params': {}}]
            if off: cmds += [{'id': 'timeline.select', 'params': {'clips': off, 'add': False, 'toggle': False}}, {'id': 'clip.enable', 'params': {}}]
            fc_run(cmds, work, 'c', '--project', 'b.fcproj')
            seq = json.loads(craft(FILMCRAFT, ['--project', 'c.fcproj', 'inspect', 'sequence'], work, 120))
            # every item read back: its track, file, frame, length, trim (to half a frame) and on/off state
            want = {(k, i): [] for k in ('video', 'audio') for i in range(4)}
            for t, c in order:
                row = (Path(src[c['id']]).name, c['at'], c['end'] - c['start'], ticks(c['start']))
                if t != 'A1': want['video', {'V1': 0, 'V2': 1, 'T1': 2}[t]].append((*row, True))
                if t == 'V1' and facts[c['path']]['audio'] or t == 'A1': want['audio', 0 if t == 'V1' else 1].append((*row, not c.get('mute')))
            have = {(k, i): [(x['name'], x['startFrame'], x['durationFrames'], x['sourceIn'], x['enabled']) for x in tr['items']]
                    for k in ('video', 'audio') for i, tr in enumerate(seq[k])}
            same = lambda a, b: a[:3] == b[:3] and a[4] == b[4] and abs(a[3] - b[3]) * 2 * fps <= TICKS
            st = seq.get('settings') or {}; cfg = (st.get('frame_rate') or {}, st.get('width'), st.get('height'))
            bad = [k for k in want if len(have.get(k, [])) != len(want[k]) or not all(map(same, sorted(want[k]), sorted(have[k])))]
            if bad or set(have) != set(want) or Fraction(cfg[0].get('num') or 0, cfg[0].get('den') or 1) != fps or cfg[1:] != (W, H):
                raise ValueError(f'FilmCraft собрал не то: дорожки {bad or sorted(have)}, формат {cfg}')
            out = out_dir / f'{name}.fcproj'; os.link(work / 'c.fcproj', out)
        finally: shutil.rmtree(work, ignore_errors=True)
    finally: CRAFT.release()
    return {'path': f'50-edit/filmcraft/{name}.fcproj', 'native': str(out), 'clips': len(order), 'warnings': warn}


def daw_up():
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8080/', timeout=2) as r: return r.status < 500
    except (OSError, ValueError): return False


def seq_stems(slug, body):
    """V1 and A1 sound as 48 kHz WAVs from sequence frame 0 to the end of the last clip, for a DAW (openDAW on Local node)."""
    doc = seq_fixed(slug, body.version)
    rows, fmt, facts = seq_check(slug, doc['tracks'], doc); seq_changed(doc, facts)
    if not (rows['V1'] or rows['A1']): raise ValueError('В монтаже нет звука: положите клипы на V1 или A1')
    fps = Fraction(fmt['fps'] or '24')
    total = max(c['at'] + c['end'] - c['start'] for t in SEQ_TRACKS for c in rows[t])
    if not BUILD.acquire(blocking=False): raise ValueError('Идёт экспорт или сборка превью. Повторите, когда закончится')
    stems = []
    try:
        out_dir = edit_dir(slug, 'audio'); name = f'{slug}-v{doc["version"]}-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:4]}'
        work = out_dir / f'.{name}.tmp'; work.mkdir(); cmds = []
        try:
            for t in ('V1', 'A1'):
                if not rows[t]: continue
                audio_track(slug, rows[t], total, fps, facts, work, t, cmds)
                out = out_dir / f'{name}-{t}.wav'; os.link(work / f'{t}.wav', out)
                stems.append({'track': t, 'path': f'50-edit/audio/{out.name}', 'native': str(out), 'seconds': float(total / fps)})
        finally: shutil.rmtree(work, ignore_errors=True)
    finally: BUILD.release()
    return {'stems': stems, 'frames': total, 'fps': str(fps), 'daw': {**OPENDAW, 'responding': daw_up()}}


@router.get('/{slug}/sequence')
def get_sequence(slug: str):
    return safe(seq_get, slug)


@router.post('/{slug}/sequence')
def put_sequence(slug: str, body: SeqBody):
    return safe(seq_commit, slug, body.version, body.tracks)


@router.get('/{slug}/sequence/clip')
def sequence_clip(slug: str, path: str):
    return safe(seq_clip, slug, path)


@router.get('/{slug}/sequence/library')
def sequence_library(slug: str):
    return safe(seq_library, slug)


@router.post('/{slug}/sequence/place')
def sequence_place(slug: str, body: SeqPlace):
    try: return safe(seq_place, slug, body)
    except StopIteration: raise HTTPException(404, 'Вариант не найден')


@router.post('/{slug}/sequence/export')
def sequence_export(slug: str, body: SeqExport):
    return safe(seq_export, slug, body)


@router.post('/{slug}/sequence/title')
def sequence_title(slug: str, body: SeqTitle):
    return safe(seq_title, slug, body)


@router.post('/{slug}/sequence/filmcraft')
def sequence_filmcraft(slug: str, body: SeqExport):
    return safe(seq_filmcraft, slug, body)


@router.post('/{slug}/sequence/stems')
def sequence_stems(slug: str, body: SeqExport):
    return safe(seq_stems, slug, body)
