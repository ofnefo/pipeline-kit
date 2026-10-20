"""On-demand, bounded file browser. Never follows Windows reparse points."""
from pathlib import Path
import kit_config as config
import hashlib
import json
import mimetypes
import os
import re
import stat
import threading
import time
from urllib.parse import quote, unquote, urlsplit

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import Response, StreamingResponse
from project_file_events import FileEvents, EVENT_LABELS, REASONS
from project_file_previews import document_preview, csv_preview, raster_preview, model_json, rewrite_model_uris

CONTROL = Path(__file__).resolve().parent.parent
PROJECTS = config.workspace('projects')
PIPELINES = config.workspace('pipelines')
COMFY_OUTPUT = config.workspace('web/generated')
STATE = config.workspace('state/project-file-observations.json')
TAGS_STATE = config.workspace('state/project-file-tags.json')
CATALOG = config.workspace('state/project-catalog.json')
TEMPLATE = CONTROL / 'docs/PROJECT_REPORT_TEMPLATE.md'
router = APIRouter(prefix='/api/project-browser')
LOCK = threading.Lock()
TAGS_LOCK = threading.Lock()
BLOCKED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'models', 'credentials', 'secrets'}
IMAGE = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.bmp'}
VIDEO = {'.mp4', '.webm', '.mov', '.mkv'}
AUDIO = {'.wav', '.mp3', '.ogg', '.m4a', '.flac', '.opus'}
TEXT = {'.txt', '.md', '.json', '.yaml', '.yml', '.csv', '.srt', '.vtt', '.log'}
MODEL = {'.glb', '.gltf', '.obj', '.stl'}
DOWNLOAD = IMAGE | VIDEO | AUDIO | TEXT | MODEL | {'.pdf', '.svg', '.docx', '.xlsx', '.pptx', '.psd', '.ai', '.blend', '.fbx', '.c4d', '.zip', '.7z', '.ttf', '.otf'}
EVENTS = FileEvents(config.workspace('state/project-file-events.json'), BLOCKED)


@router.on_event('startup')
def start_file_events():
    if config.options().get('watch_project_files', False):
        EVENTS.start(roots())


@router.on_event('shutdown')
def stop_file_events():
    EVENTS.stop()


def native(path):
    """Check every lexical component BEFORE resolving any symlink/junction."""
    path = Path(os.path.abspath(path))
    for p in [*reversed(path.parents), path]:
        try:
            s = p.lstat()
        except FileNotFoundError:
            # A new file/folder is valid; existing ancestors were checked first.
            # lstat still exposes dangling symlinks and reparse points above.
            break
        if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Ссылки и точки подключения не открываются')
    return path


def roots():
    rows = [{'id': 'projects', 'name': 'Проекты', 'path': str(PROJECTS)}]
    try:
        if native(COMFY_OUTPUT).is_dir():
            rows.append({'id': 'comfy-output', 'name': 'ComfyUI / временные результаты', 'path': str(COMFY_OUTPUT)})
    except (OSError, ValueError):
        pass
    try:
        data = json.loads(CATALOG.read_text(encoding='utf-8'))
        for r in data.get('records', []):
            if r.get('entity') != 'pipeline' or r.get('canonical_host') != 'local':
                continue
            base = Path(r.get('canonical_path', ''))
            if not base.is_relative_to(PIPELINES):
                continue
            for suffix in ('outputs', 'output'):
                p = base / suffix
                try:
                    if not native(p).is_dir():
                        continue
                except (OSError, ValueError):
                    continue
                rows.append({'id': hashlib.sha256(str(p).casefold().encode()).hexdigest()[:16],
                             'name': f"{r.get('name') or r['id']} / {suffix}", 'path': str(p)})
    except (OSError, ValueError, TypeError):
        pass
    return rows


def resolve(root_id, relative=''):
    root = next((x for x in roots() if x['id'] == root_id), None)
    if not root:
        raise ValueError('Неизвестная папка каталога')
    rel = Path(relative)
    if rel.is_absolute() or rel.drive or any(p in {'.', '..'} or ':' in p or p.startswith('.') or p.casefold() in BLOCKED or secret_name(p) for p in rel.parts):
        raise ValueError('Путь вне разрешённой папки')
    base = native(root['path'])
    target = native(base / rel)
    if not target.is_relative_to(base):
        raise ValueError('Путь вне разрешённой папки')
    return root, target


def kind(path):
    ext = path.suffix.lower()
    return ('image' if ext in IMAGE else 'video' if ext in VIDEO else 'audio' if ext in AUDIO else
            'table' if ext in {'.xlsx','.csv'} else 'document' if ext=='.docx' else 'slides' if ext=='.pptx' else
            'model' if ext in MODEL else 'design' if ext in {'.psd','.ai'} else
            'text' if ext in TEXT else 'pdf' if ext=='.pdf' else 'download')


def secret_name(name):
    return bool(re.match(r'^(credentials?|secrets?|tokens?|api[-_]?keys?)(?:[._-]|$)', name, re.I))


def tag_key(path, info=None):
    info = info or path.stat()
    if not info.st_ino:
        # Windows DirEntry.stat may provide directory-enumeration attributes with zero file ID.
        info = path.stat()
    # A stable same-volume file identity keeps tags through rename without rewriting originals.
    value = f"{info.st_dev}:{info.st_ino}:{getattr(info, 'st_birthtime_ns', info.st_ctime_ns)}"
    return hashlib.sha256(value.encode()).hexdigest()


def load_tags():
    try:
        if TAGS_STATE.stat().st_size>8*1024*1024:
            raise ValueError('Хранилище тегов превышает лимит')
        data = json.loads(TAGS_STATE.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or not isinstance(data.get('files'),dict):
            raise ValueError('Некорректное хранилище тегов')
        return data
    except FileNotFoundError:
        return {'version':1,'files':{}}


def metadata_for(path):
    info = path.stat()
    with TAGS_LOCK:
        tags = load_tags()['files'].get(tag_key(path,info),{}).get('tags',[])
    result = {'name':path.name,'size':info.st_size,'modified':info.st_mtime,
              'extension':path.suffix.lower(),'kind':'directory' if path.is_dir() else kind(path), 'tags':tags}
    if path.is_file() and path.stat().st_size<=64*1024*1024:
        try:
            if path.suffix.lower() in IMAGE | {'.psd'}:
                from PIL import Image
                with Image.open(path) as image:
                    result.update(width=image.width,height=image.height,mode=image.mode)
            elif path.suffix.lower() in AUDIO:
                import mutagen
                audio = mutagen.File(path)
                if audio and audio.info:
                    result['duration_seconds'] = round(audio.info.length,2)
                    for key in ('sample_rate','channels','bitrate'):
                        value = getattr(audio.info,key,None)
                        if value is not None:result[key] = value
            elif path.suffix.lower()=='.pdf':
                import fitz
                with fitz.open(path) as document:
                    result['pages'] = document.page_count
        except Exception:
            # Basic metadata stays useful even when an optional format parser cannot read the file.
            result['metadata_note'] = 'Расширенные метаданные недоступны'
    return result


def observe(rows):
    """File ID + birth time; call a move only when the previous path disappeared."""
    with LOCK:
        try:
            data = json.loads(STATE.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            data = {'first_observed': time.time(), 'files': {}, 'moves': []}
        files = data['files']
        for row in rows:
            if row['directory']:
                continue
            p = Path(row['path'])
            try:
                s = p.stat()
                identity = f"{s.st_dev}:{s.st_ino}:{getattr(s, 'st_birthtime_ns', s.st_ctime_ns)}"
                old = files.get(identity)
                if old and old['path'].casefold() != str(p).casefold():
                    try:
                        Path(old['path']).lstat()
                    except FileNotFoundError:
                        data['moves'].append({'from': old['path'], 'to': str(p), 'observed_at': time.time(), 'basis': 'same volume/file ID and birth time; old path missing'})
                    except OSError:
                        pass
                files[identity] = {'path': str(p), 'observed_at': time.time()}
            except OSError:
                pass
        if len(files) > 5000:
            data['files'] = dict(sorted(files.items(), key=lambda x: x[1]['observed_at'])[-5000:])
        data['moves'] = data['moves'][-200:]
        STATE.parent.mkdir(parents=True, exist_ok=True)
        temporary = STATE.with_suffix('.tmp')
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        os.replace(temporary, STATE)
        return data


def browse(root_id, relative='', offset=0, search='', tag='', file_kind='', sort='name', direction='asc'):
    root, folder = resolve(root_id, relative)
    if not folder.is_dir():
        raise ValueError('Нужна папка')
    rows, truncated = [], False
    with TAGS_LOCK:
        tags_data = load_tags()['files']
    with os.scandir(folder) as entries:
        for scanned, entry in enumerate(entries):
            if scanned >= 1000:
                truncated = True
                break
            if entry.name.startswith('.') or entry.name.casefold() in BLOCKED or secret_name(entry.name):
                continue
            try:
                s = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                    continue
                directory = stat.S_ISDIR(s.st_mode)
                p = Path(entry.path)
                if not directory and (not stat.S_ISREG(s.st_mode) or p.suffix.lower() not in DOWNLOAD):
                    continue
                rows.append({'name': entry.name, 'path': str(p), 'relative': str(p.relative_to(Path(root['path']))),
                             'directory': directory, 'size': s.st_size if not directory else None, 'modified': s.st_mtime,
                             'kind': 'directory' if directory else kind(p), 'extension':p.suffix.lower(),
                             'tags':tags_data.get(tag_key(p,s),{}).get('tags',[]) if tags_data else []})
            except OSError:
                continue
    observations = observe(rows)
    moves = [m for m in observations['moves'] if Path(m['from']).is_relative_to(folder) or Path(m['to']).is_relative_to(folder)][-20:]
    offset = max(0, min(int(offset), 1000))
    all_tags = sorted({t for row in rows for t in row['tags']},key=str.casefold)
    if len(search)>200 or len(tag)>48:
        raise ValueError('Слишком длинный фильтр')
    needle = search.casefold()
    rows = [r for r in rows if (not needle or needle in (r['name']+' '+' '.join(r['tags'])).casefold())
            and (not tag or tag.casefold() in {t.casefold() for t in r['tags']})
            and (not file_kind or r['kind']==file_kind)]
    if sort not in {'name','type','size','modified'} or direction not in {'asc','desc'}:
        raise ValueError('Некорректная сортировка')
    key = {'name':lambda r:r['name'].casefold(), 'type':lambda r:(r['kind'],r['extension'],r['name'].casefold()),
           'size':lambda r:(r['size'] or 0,r['name'].casefold()), 'modified':lambda r:(r['modified'],r['name'].casefold())}[sort]
    rows.sort(key=key,reverse=direction=='desc')
    rows.sort(key=lambda r:not r['directory'])
    return {'root': root, 'relative': relative, 'folder': str(folder), 'entries': rows[offset:offset+200],
            'next_offset': offset+200 if offset+200 < len(rows) else None, 'truncated': truncated,
            'total':len(rows), 'available_tags':all_tags,
            'moves': moves, 'first_observed': observations['first_observed'],
            **EVENTS.snapshot(root_id, relative)}


def guarded(fn, *args):
    try:
        return fn(*args)
    except FileNotFoundError:
        raise HTTPException(404, 'Файл или папка не найдены')
    except (OSError, ValueError, KeyError):
        raise HTTPException(400, 'Путь недоступен или не разрешён')


@router.get('/roots')
def root_list():
    return {'roots': roots()}


@router.get('/list')
def listing(root: str = 'projects', path: str = '', offset: int = 0, search: str = '', tag: str = '',
            kind: str = '', sort: str = 'name', direction: str = 'asc'):
    return guarded(browse, root, path, offset, search, tag, kind, sort, direction)


@router.get('/events')
def event_listing(root: str = 'projects', path: str = ''):
    guarded(resolve, root, path)
    return EVENTS.snapshot(root, path)


def file_for(root, path):
    _, target = resolve(root,path)
    if not target.is_file() or target.suffix.lower() not in DOWNLOAD:
        raise ValueError('Формат недоступен')
    return target


@router.get('/metadata')
def metadata(root: str, path: str):
    _, target = guarded(resolve,root,path)
    if target.is_file() and target.suffix.lower() not in DOWNLOAD:
        raise HTTPException(400,'Формат недоступен')
    return guarded(metadata_for,target)


@router.post('/tags')
async def set_tags(request: Request):
    origin = request.headers.get('origin')
    if request.headers.get('sec-fetch-site')=='cross-site' or origin and (
            urlsplit(origin).scheme!=request.url.scheme or urlsplit(origin).netloc!=request.url.netloc):
        raise HTTPException(403,'Изменение тегов с другого сайта запрещено')
    if request.headers.get('content-type','').split(';')[0].strip()!='application/json':
        raise HTTPException(415,'Нужен JSON')
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>8192:
            raise HTTPException(413,'Слишком большой запрос')
    try:
        payload = json.loads(body)
        if not isinstance(payload,dict) or not isinstance(payload.get('root'),str) or not isinstance(payload.get('path'),str):
            raise ValueError()
        tags = payload.get('tags')
        if not isinstance(tags,list) or len(tags)>20 or any(not isinstance(t,str) or not 1<=len(t.strip())<=48 or any(ord(c)<32 for c in t) for t in tags):
            raise ValueError()
    except (ValueError,TypeError):
        raise HTTPException(400,'Теги: не более 20 строк по 48 символов')
    _, target = guarded(resolve,payload['root'],payload['path'])
    if target.is_file() and target.suffix.lower() not in DOWNLOAD:
        raise HTTPException(400,'Формат недоступен')
    unique = {}
    for tag in tags:unique.setdefault(tag.strip().casefold(),tag.strip())
    tags = list(unique.values())
    try:
        with TAGS_LOCK:
            data = load_tags()
            key = tag_key(target)
            if tags:
                data['files'][key] = {'tags':tags,'last_path':str(target),'updated':time.time()}
            else:data['files'].pop(key,None)
            encoded = json.dumps(data,ensure_ascii=False)
            if len(data['files'])>20000 or len(encoded.encode('utf-8'))>8*1024*1024:
                raise HTTPException(409,'Хранилище тегов заполнено; удалите ненужные теги')
            TAGS_STATE.parent.mkdir(parents=True,exist_ok=True)
            temp = TAGS_STATE.with_suffix('.tmp')
            temp.write_text(encoded,encoding='utf-8')
            os.replace(temp,TAGS_STATE)
    except (OSError,ValueError):
        raise HTTPException(409,'Не удалось сохранить теги; существующее хранилище не перезаписано')
    return {'root':payload['root'],'path':payload['path'],'tags':tags}


def browser_url(route,root,path,**extra):
    return '/api/project-browser/'+route+'?root='+quote(root,safe='')+'&path='+quote(path,safe='')+''.join('&'+quote(k)+'='+quote(v,safe='') for k,v in extra.items())


def resource_path(root,model,uri):
    decoded = unquote(uri)
    rel = Path(decoded)
    if (not decoded or len(decoded)>2048 or any(c in decoded for c in (':','\\','?','#','%'))
            or rel.is_absolute() or rel.drive or '..' in rel.parts):
        raise ValueError('Внешние ресурсы и выход из папки 3D-модели запрещены')
    if rel.suffix.lower() not in {'.bin','.png','.jpg','.jpeg','.webp'}:
        raise ValueError('Ресурс 3D-модели не поддерживается')
    root_row, base = resolve(root,model)
    relative = str((base.parent/rel).relative_to(Path(root_row['path'])))
    _, target = resolve(root,relative)
    if not target.is_file() or target.stat().st_size>64*1024*1024:
        raise ValueError('Ресурс 3D-модели недоступен или слишком большой')
    return target


def safe_model(root,path,target):
    value = model_json(target)
    if not isinstance(value,dict) or not isinstance(value.get('asset'),dict) or str(value['asset'].get('version',''))!='2.0':
        raise ValueError('Поддерживается только glTF 2.0')
    def transform(uri):
        if uri.startswith('data:'):
            if not re.match(r'^data:(application/octet-stream|application/gltf-buffer|image/png|image/jpeg|image/webp);base64,[A-Za-z0-9+/=\r\n]*$',uri):
                raise ValueError('Неподдерживаемый встроенный ресурс glTF')
            return uri
        if target.suffix.lower()=='.glb':
            raise ValueError('Для GLB доступны только встроенные ресурсы')
        resource_path(root,path,uri)
        return browser_url('model-resource',root,path,resource=uri)
    return rewrite_model_uris(value,transform)


@router.get('/preview')
def preview(root: str, path: str):
    target = guarded(file_for,root,path)
    info = guarded(metadata_for,target)
    result = {'kind':kind(target),'metadata':info,'truncated':False,'warnings':[]}
    try:
        ext = target.suffix.lower()
        if ext in {'.docx','.xlsx','.pptx'}:
            result.update(document_preview(target))
        elif ext=='.csv':result.update(csv_preview(target))
        elif ext in {'.psd','.ai'}:
            # Validate a supported composite before offering a preview link; no native application launch.
            content = raster_preview(target)
            cache_raster(target,content)
            result.update(kind='image',image_url=browser_url('preview-image',root,path),
                          warnings=['Сведённое превью; слои и редактирование доступны в профильной программе.'])
        elif ext in MODEL:
            if target.stat().st_size>128*1024*1024:
                raise ValueError('Модель превышает лимит встроенного предпросмотра 128 МБ')
            if ext in {'.gltf','.glb'}:safe_model(root,path,target)
            result.update(kind='model',format=ext[1:],model_url=browser_url('model-data',root,path),
                          warnings=['Материалы OBJ/MTL не подгружаются. Для полного вида откройте исходник в 3D-редакторе.'] if ext=='.obj' else [])
        elif ext in {'.blend','.fbx','.c4d'}:
            result.update(kind='unsupported',warnings=['Встроенное превью этого формата пока недоступно. Скачайте исходник и откройте в профильном 3D-редакторе.'])
        else:result['media_url'] = browser_url('media',root,path)
    except Exception as exc:
        result.update(kind='unsupported',warnings=[str(exc) if isinstance(exc,ValueError) else 'Этот файл не удалось прочитать встроенным просмотрщиком. Откройте его в профильной программе.'])
    return result


RASTER_CACHE = {}
RASTER_LOCK = threading.Lock()


def raster_key(target):
    info = target.stat()
    return str(target),info.st_size,info.st_mtime_ns


def cache_raster(target,content):
    with RASTER_LOCK:
        if len(RASTER_CACHE)>=8:RASTER_CACHE.pop(next(iter(RASTER_CACHE)))
        RASTER_CACHE[raster_key(target)] = content


@router.get('/preview-image')
def preview_image(root: str, path: str):
    target = guarded(file_for,root,path)
    if target.suffix.lower() not in {'.psd','.ai'}:
        raise HTTPException(400,'Формат недоступен')
    with RASTER_LOCK:
        content = RASTER_CACHE.get(raster_key(target))
    if content is None:
        try:content = raster_preview(target)
        except Exception:raise HTTPException(422,'Встроенного превью нет')
        cache_raster(target,content)
    return Response(content,media_type='image/png',headers={'X-Content-Type-Options':'nosniff','Cache-Control':'no-store'})


def static_model_response(target,media_type):
    def chunks():
        with target.open('rb') as stream:
            while block:=stream.read(256*1024):yield block
    return StreamingResponse(chunks(),media_type=media_type,
                             headers={'X-Content-Type-Options':'nosniff','Cache-Control':'no-store'})


@router.get('/model-data')
def model_data(root: str, path: str):
    target = guarded(file_for,root,path)
    if target.suffix.lower() not in MODEL or target.stat().st_size>128*1024*1024:
        raise HTTPException(400,'Модель недоступна для предпросмотра')
    if target.suffix.lower() in {'.gltf','.glb'}:
        value = guarded(safe_model,root,path,target)
        if target.suffix.lower()=='.gltf':
            return Response(json.dumps(value),media_type='model/gltf+json',headers={'X-Content-Type-Options':'nosniff','Cache-Control':'no-store'})
    return static_model_response(target,'model/gltf-binary' if target.suffix.lower()=='.glb' else 'application/octet-stream')


@router.get('/model-resource')
def model_resource(root: str, path: str, resource: str):
    model = guarded(file_for,root,path)
    if model.suffix.lower()!='.gltf':
        raise HTTPException(400,'Ресурс недоступен')
    value = guarded(model_json,model)
    uris = []
    guarded(rewrite_model_uris,value,lambda uri:uris.append(uri) or uri)
    if resource not in uris:
        raise HTTPException(400,'Ресурс не принадлежит модели')
    target = guarded(resource_path,root,path,resource)
    return static_model_response(target,mimetypes.guess_type(target.name)[0] or 'application/octet-stream')


@router.get('/text')
def text_preview(root: str, path: str):
    _, p = guarded(resolve, root, path)
    if p.suffix.lower() not in TEXT or not p.is_file():
        raise HTTPException(400, 'Текстовое превью недоступно')
    with p.open('rb') as f:
        content = f.read(256 * 1024 + 1)
    return {'text': content[:256*1024].decode('utf-8-sig', errors='replace'), 'truncated': len(content) > 256*1024}


def byte_range(value, size):
    if not value:
        return 0, size - 1, False
    m = re.fullmatch(r'bytes=(\d*)-(\d*)', value)
    if not m or not any(m.groups()) or size == 0:
        raise ValueError('Invalid range')
    a, b = m.groups()
    if not a:
        count = int(b)
        if count <= 0:
            raise ValueError('Invalid range')
        return max(0, size-count), size-1, True
    start, end = int(a), min(int(b), size-1) if b else size-1
    if start >= size or end < start:
        raise ValueError('Invalid range')
    return start, end, True


@router.get('/media')
def media(request: Request, root: str, path: str, download: bool = False):
    _, p = guarded(resolve, root, path)
    if not p.is_file() or p.suffix.lower() not in DOWNLOAD:
        raise HTTPException(400, 'Формат недоступен')
    size = p.stat().st_size
    try:
        start, end, partial = byte_range(request.headers.get('range'), size)
    except ValueError:
        return Response(status_code=416, headers={'Content-Range': f'bytes */{size}'})
    inline = not download and kind(p) in {'image', 'audio', 'video', 'pdf'}
    headers = {'Accept-Ranges': 'bytes', 'Content-Length': str(max(0, end-start+1)),
               'Content-Disposition': f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{quote(p.name)}",
               'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'}
    if partial:
        headers['Content-Range'] = f'bytes {start}-{end}/{size}'
    def chunks():
        with p.open('rb') as f:
            f.seek(start)
            left = end-start+1
            while left > 0:
                block = f.read(min(left, 256*1024))
                if not block:
                    break
                left -= len(block)
                yield block
    return StreamingResponse(chunks(), status_code=206 if partial else 200,
                             media_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream', headers=headers)


@router.get('/report-template')
def report_template():
    return Response(TEMPLATE.read_text(encoding='utf-8'), media_type='text/markdown; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename="PROJECT_REPORT.md"'})


@router.get('/report')
def report(root: str = 'projects', path: str = ''):
    data = guarded(browse, root, path, 0)
    lines = [f"# Сводка: {Path(data['folder']).name}", '', f"Дата наблюдения: {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"Папка: `{data['folder']}`", '', '## Файлы в текущей папке', '',
             'Просмотрена только текущая папка, вложенные папки не сканировались.', '']
    for row in data['entries']:
        label = row['name'].replace('\n', ' ').replace('\r', ' ').replace('`', "'")
        lines.append(f"- `{label}` — {'папка' if row['directory'] else str(row['size'])+' байт'}")
    if data['next_offset'] is not None or data['truncated']:
        lines += ['', 'Список ограничен первой страницей.']
    lines += ['', '## Изменения файлов', '', data['history_note'], '']
    for event in data['events']:
        target = f"{event['from']} → {event['to']}" if event['action'] == 'rename' else event.get('path', REASONS.get(event.get('reason'), ''))
        target = target.replace('\n', ' ').replace('\r', ' ').replace('`', "'")
        lines.append(f"- {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['at']))}: {EVENT_LABELS.get(event['action'], event['action'])} — `{target}`")
    if not data['events']:
        lines.append('Нет записанных событий.')
    lines += ['', '---', '', TEMPLATE.read_text(encoding='utf-8')]
    return Response('\n'.join(lines), media_type='text/markdown; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename="PROJECT_REPORT.md"'})
