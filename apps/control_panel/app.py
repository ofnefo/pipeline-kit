"""Portable application boundary for the existing Control panel."""
from pathlib import Path
from contextlib import asynccontextmanager
import json
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import kit_config as config
import collectors as c
import workboard
import namenode_service as nns
import converters
import uploads
from project_files_service import router as files_router
from project_files_actions import router as actions_router
from video_review import router as video_router
from studio_chats import router as studio_router
from smm_service import router as smm_router

HERE = Path(__file__).resolve().parent
VERSION = '0.1.0'

@asynccontextmanager
async def lifespan(app):
    config.initialize()
    from project_files_service import start_file_events, stop_file_events
    start_file_events()
    try:
        yield
    finally:
        stop_file_events()

app = FastAPI(title='Pipeline Kit Control', version=VERSION, lifespan=lifespan)
app.mount('/static', StaticFiles(directory=HERE/'static'), name='static')
for router in (files_router, actions_router, video_router, studio_router, smm_router):
    app.include_router(router)

@app.middleware('http')
async def local_boundary(request: Request, call_next):
    from urllib.parse import urlsplit
    if request.url.hostname not in ('127.0.0.1','localhost','::1','testserver'):
        return JSONResponse({'detail':'Only loopback hosts are allowed'},status_code=403)
    origin=request.headers.get('origin')
    if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and (urlsplit(origin).netloc != request.url.netloc or urlsplit(origin).scheme != request.url.scheme)):
        return JSONResponse({'detail':'Cross-origin requests refused'},status_code=403)
    # Personal integrations are absent. Return an explicit capability error before any host action.
    path=request.url.path
    if any(x in path for x in ('/deliver','/generate','/generations/sync','/sequence/title','/sequence/filmcraft')):
        return JSONResponse({'detail':'This optional production adapter is not included; see /api/capabilities'},status_code=501)
    return await call_next(request)

@app.get('/')
def index():
    return FileResponse(HERE/'static/index.html')

@app.get('/api/health')
def health():
    return c.health()

@app.get('/api/version')
def version():
    return {'version':VERSION}

class BoardCreate(BaseModel):
    title: str
    description: str = ''
    acceptance: str = ''
    project_id: str = ''
    executor: str = 'codex'
    model: str = ''
    priority: str = 'P2'

class BoardAction(BaseModel):
    version: int
    action: str
    data: dict = {}

def board_call(fn, *args):
    try:
        return fn(*args)
    except workboard.Conflict as exc:
        raise HTTPException(409, str(exc))
    except KeyError:
        raise HTTPException(404, 'Задача не найдена')
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@app.get('/api/board')
def board_list():
    return {'tasks': workboard.listing(), 'read_at': __import__('time').time()}

@app.get('/api/board/projects')
def board_projects():
    return board_call(workboard.projects)

@app.post('/api/board')
def board_create(body: BoardCreate):
    return board_call(workboard.create, body.model_dump())

@app.get('/api/board/{task_id}')
def board_get(task_id: str):
    return board_call(workboard.get, task_id)

@app.get('/api/board/{task_id}/handoff')
def board_handoff(task_id: str):
    return board_call(workboard.handoff, task_id)

@app.post('/api/board/{task_id}')
def board_action(task_id: str, body: BoardAction):
    return board_call(workboard.mutate, task_id, body.version, body.action, body.data)

def nn_call(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except workboard.Conflict as exc:
        raise HTTPException(409, str(exc))
    except KeyError as exc:
        raise HTTPException(404, f'Не найдено: {exc.args[0] if exc.args else ""}')
    except FileNotFoundError:
        raise HTTPException(404, 'Файл не найден')
    except OSError as exc:
        raise HTTPException(400, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))

class LockBody(BaseModel):
    card: str
    reason: str = ''
    force: bool = False

class SectionBody(BaseModel):
    section: str
    text: str | None = None
    reason: str = ''
    expect_updated: str | None = None
    force: bool = False
    meta: dict | None = None

class CardBody(BaseModel):
    meta: dict
    body: str = ''
    reason: str = ''
    replace: bool = False
    force: bool = False

class FileBody(BaseModel):
    path: str
    text: str = ''
    expect_mtime: float | None = None

@app.get('/api/namenode/work')
def namenode_work():
    return nn_call(nns.work)

@app.get('/api/namenode/search')
def namenode_search(q: str = '', limit: int = 8):
    return nn_call(nns.search, q, limit)

@app.get('/api/namenode/card/{card_id}')
def namenode_card(card_id: str):
    return nn_call(nns.card, card_id)

@app.post('/api/namenode/card/{card_id}/section')
def namenode_section(card_id: str, body: SectionBody):
    if body.text is None and body.meta:
        # meta-only update: keep the section text as it is
        current = nn_call(nns.card, card_id)
        found = next((s for s in current['sections'] if s['title'] == body.section), None)
        text = found['text'] if found else ''
    else:
        text = body.text or ''
    return nn_call(nns.set_section, card_id, body.section, text, body.reason, body.expect_updated, body.force,
                   meta=body.meta)

@app.post('/api/namenode/card')
def namenode_put_card(body: CardBody):
    return nn_call(nns.put_card, body.meta, body.body, body.reason, body.replace, body.force)

@app.post('/api/projects/lock')
def project_lock(body: LockBody):
    return nn_call(nns.lock, body.card, body.reason, body.force)

@app.post('/api/projects/unlock')
def project_unlock(body: LockBody):
    return nn_call(nns.unlock, body.card)

@app.get('/api/projects/files')
def project_files(folder: str):
    return nn_call(nns.project_files, folder)

@app.get('/api/projects/file')
def project_file_read(path: str):
    return nn_call(nns.read_file, path)

@app.post('/api/projects/file')
def project_file_write(body: FileBody):
    return nn_call(nns.write_file, body.path, body.text, body.expect_mtime)

def svc_call(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except workboard.Conflict as exc:
        raise HTTPException(409, str(exc))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    except KeyError as exc:
        raise HTTPException(404, f'Не найдено: {exc.args[0] if exc.args else ""}')
    except FileNotFoundError:
        raise HTTPException(404, 'Файл не найден')
    except OSError as exc:
        raise HTTPException(400, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@app.get('/api/convert/catalog')
def convert_catalog():
    return converters.catalog()

@app.get('/api/convert/runs')
def convert_runs(limit: int = 30):
    return {'runs': converters.runs(limit)}

@app.post('/api/convert')
def convert_run(kind: str = Form(...), options: str = Form('{}'), src: str = Form(''), file: UploadFile | None = File(None)):
    import json as _json
    try:
        opts = _json.loads(options or '{}')
    except ValueError:
        raise HTTPException(400, 'options: нужен JSON')
    if file is not None and file.filename:
        saved = svc_call(uploads.save_upload, file)
        source = saved['path']
    else:
        source = str(svc_call(uploads.resolve_source, src))
    return svc_call(converters.convert, kind, source, opts)

@app.get('/api/convert/file')
def convert_file(path: str):
    p = svc_call(uploads.inside, path, [converters.OUT_ROOT, uploads.UPLOADS])
    if not p.is_file():
        raise HTTPException(404, 'Файл не найден')
    return FileResponse(p, filename=p.name)

@app.get('/api/capabilities')
def capabilities():
    return {'version': VERSION, 'workspace': str(config.ROOT), 'local': [
        'projects', 'board', 'namenode', 'project-files', 'studio-chats', 'converters', 'montage', 'smm'],
        'optional': ['local-chat', 'ffmpeg', 'soffice', 'pandoc', 'pymupdf'],
        'unavailable': ['generation-workers', 'remote-hosts', 'cloud-models', 'delivery', 'secrets-manager',
                        'download-manager', 'effectcraft', 'filmcraft', 'personal-agent-sessions']}

@app.get('/api/projects')
def projects():
    import run_projects_service as rps
    cards=workboard.nn('index',{'type':'project','full':True}).get('cards',[])
    by_path={str(Path(c.get('canonical',''))):c for c in cards if c.get('canonical')}
    rows=[]
    for kind,names in rps.projects()['projects'].items():
        for name in names:
            path=config.workspace('projects')/kind/name
            card=by_path.get(str(path),{})
            rows.append({'key':card.get('id',f'folder:{kind}/{name}'), 'name':name, 'domain':kind,
                         'kind':'project', 'entity':'project', 'group':'working', 'status':'active', 'authority':'local',
                         'path':str(path), 'local_path':str(path), 'studio_key':f'{kind}/{name}',
                         'detail':('NameNode: '+card['id']) if card else 'Local workspace project', 'source':'workspace'})
    existing={r['key'] for r in rows}
    for card in cards:
        if card['id'] not in existing:
            rows.append({'key':card['id'],'name':card.get('title',card['id']),'domain':'general',
                         'kind':'project','entity':'project','group':'working','status':card.get('status','active'),
                         'authority':'local','path':card.get('canonical',''),'local_path':'',
                         'detail':'NameNode: '+card['id'],'source':'namenode'})
    return {'rows':rows, 'read_at':__import__('time').time(), 'groups':{}, 'warnings':[]}

class NewProject(BaseModel):
    type: str
    name: str

@app.post('/api/projects/create')
def create_project(body: NewProject):
    import run_projects_service as rps
    import hashlib
    import re
    if body.type=='video' and not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,62}',body.name):
        raise HTTPException(400,'Video project names require 2–63 lowercase letters, digits or hyphens')
    name,path=svc_call(rps._folder,body.type,body.name)
    # Validate ancestors before creating directories (no links or junctions).
    from project_files_service import native
    native(config.workspace('projects'))
    if path.parent.exists(): native(path.parent)
    if path.exists(): raise HTTPException(409,'Project already exists')
    path.mkdir(parents=True)
    card_id='project-'+body.type+'-'+hashlib.sha256(name.encode()).hexdigest()[:12]
    (path/'project.yaml').write_text('name: '+json.dumps(name,ensure_ascii=False)+'\ntype: '+body.type+'\nnamenode: '+card_id+'\n',encoding='utf-8')
    sections={'Что это':name,'Где лежит':str(path),'Репозиторий':'Not configured',
              'Запуск и деплой':'Local workspace only','Куда вносить изменения':str(path),
              'Риски и открытые вопросы':'Define project acceptance before production','Ревью':'Not reviewed'}
    nn_call(nns.put_card,{'id':card_id,'type':'project','title':name,'status':'active','canonical':str(path)},
            '\n\n'.join('## '+k+'\n'+v for k,v in sections.items()),'Local project created')
    return {'ok':True,'path':str(path),'key':f'{body.type}/{name}','studio_key':f'{body.type}/{name}'}

@app.get('/api/models/projects')
def model_projects():
    import run_projects_service as rps
    return rps.projects()

@app.get('/api/models/runs')
def model_runs():
    return {'runs':[], 'queue':[], 'available':False, 'reason':'No generation worker configured'}

@app.get('/api/inventory')
def inventory():
    return {'available':False,'reason':'Local kit has no private inventory registry','top10':[]}

@app.get('/api/agents/projects')
def agent_projects():
    return {'projects':[], 'sessions':[], 'available':False, 'reason':'No agent session adapter configured'}

@app.get('/api/tools')
def skill_tools():
    skills=[]
    root=config.PACKAGE/'skills'
    for skill in sorted(root.glob('*/SKILL.md')):
        import yaml
        front=skill.read_text(encoding='utf-8').split('---',2)
        meta=yaml.safe_load(front[1]) if len(front)==3 else {}
        skills.append({'name':meta.get('name',skill.parent.name),'description':meta.get('description',''),
                       'path':str(skill), 'group':'Pipeline Kit', 'available':True})
    return {'skills':skills,'tools':[], 'groups':[], 'pipelines':[], 'catalog':[], 'summary':{},
            'review':{'unique_names':len(skills),'count':len(skills),'source':'Bundled skills',
                      'groups':[{'key':'pipeline-kit','title':'Pipeline Kit','use':'Local workflows',
                                 'items':[{'name':s['name'],'role':'primary'} for s in skills]}]}}

@app.get('/api/editors')
def editors():
    return {'editors':[], 'available':False,'reason':'Install optional editors separately'}

@app.get('/api/keys')
def keys():
    return {'available':False,'keys':[], 'providers':[], 'groups':[]}

@app.api_route('/api/{path:path}',methods=['GET','POST','PUT','DELETE'])
def unavailable(path: str):
    raise HTTPException(501,'Optional integration is not included in Pipeline Kit; see /api/capabilities')
