"""Run feed actions (PLAN §5): favourite/note a run and save a run «В проект».

«В проект» copies the run outputs and the run JSON («золотой рецепт») into
workspace/projects/<type>/<project>/generations/<date>-<run>/, stores the settings as a project preset
(generations/presets.json), creates project.yaml + a NameNode card for a new project and logs to the card.
Assistant delivery (tools/result_delivery/delivery.py enqueue) only when asked.
"""
import hashlib, json, re, shutil, subprocess, sys, time
from pathlib import Path
import kit_config as config

import yaml

import collectors as c
import models_service as mdl
import namenode_service as nns

PROJECTS_ROOT = nns.PROJECTS_ROOT
TYPES = ('video', 'music', 'design', 'web', 'soft', 'games', 'office')
TYPE_TITLES = {'video': 'Video', 'music': 'Music', 'design': 'Design', 'web': 'Web', 'soft': 'Soft', 'games': 'Game', 'office': 'Office'}
GROUP_TYPE = {'video': 'video', 'image': 'design', 'music': 'music', 'voice': 'music'}
GROUP_PIPELINE = {k: str(config.workspace('pipelines') / v) for k,v in {'video':'video','image':'design','music':'music','voice':'music'}.items()}
DELIVERY = c.CONTROL / 'tools' / 'result_delivery' / 'delivery.py'
TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя', ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't',
                                                   'u', 'f', 'h', 'ts', 'ch', 'sh', 'sch', '', 'y', '', 'e', 'yu', 'ya']))


def slug(name):
    s = ''.join(TR.get(ch, ch) for ch in name.lower())
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:48] or hashlib.sha1(name.encode()).hexdigest()[:8]


def _find(rows, run_id):
    for r in rows:
        if r.get('id') == run_id:
            return r
    raise KeyError(run_id)


def mark(run_id, favorite=None, note=None):
    rows = mdl._read_runs()
    r = _find(rows, run_id)
    if favorite is not None:
        r['favorite'] = bool(favorite)
    if note is not None:
        r['note'] = str(note)[:500]
    mdl._write_runs(rows)
    return {'ok': True, 'id': run_id, 'favorite': r.get('favorite', False), 'note': r.get('note', '')}


def projects():
    """Existing project folders per type, for the «В проект» picker."""
    out = {}
    for t in TYPES:
        base = PROJECTS_ROOT / t
        rows = []
        if base.is_dir():
            from project_files_service import native
            try: native(base)
            except ValueError: continue
            for p in sorted(base.iterdir(), key=lambda x: x.name.lower()):
                if p.is_dir() and not p.name.startswith(('_', '.')):
                    try: native(p)
                    except ValueError: continue
                    rows.append(p.name)
        out[t] = rows
    return {'types': list(TYPES), 'projects': out}


def run_target(target):
    """UX-02: the project picked in the run form; it must already exist (new projects are made by «В проект»)."""
    if not target:
        return None
    ptype = str(target.get('type') or '')
    name, folder = _folder(ptype, target.get('name'))
    if not folder.is_dir():
        raise ValueError(f'Проект не найден: {ptype}/{name}')
    return {'type': ptype, 'name': name}


def _folder(ptype, name):
    if ptype not in TYPES:
        raise ValueError('Неизвестный тип проекта')
    name = re.sub(r'\s+', ' ', str(name or '')).strip()
    if not name or name in ('.', '..') or re.search(r'[\\/:*?"<>|]', name) or name.startswith(('_', '.')):
        raise ValueError('Название проекта: без / \\ : * ? " < > | и не с точки/подчёркивания')
    if len(name) > 80:
        raise ValueError('Название проекта длиннее 80 символов')
    from project_files_service import native
    native(PROJECTS_ROOT)
    base = PROJECTS_ROOT / ptype
    if base.exists(): native(base)
    base = base.resolve()
    if (base / name).exists(): native(base / name)
    folder = (base / name).resolve()
    if folder.parent != base:
        raise ValueError('Папка проекта вне workspace/projects')
    return name, folder


def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _card_id(folder):
    try:
        doc = yaml.safe_load((folder / 'project.yaml').read_text(encoding='utf-8')) or {}
    except (OSError, yaml.YAMLError):
        return None
    cards = (doc.get('namenode') or {}).get('cards') or []
    return cards[0] if cards else (doc.get('id') if str(doc.get('id', '')).startswith('project-') else None)


def _new_project(folder, name, ptype, run):
    card = f'project-{slug(name)}'
    group = run.get('group', '')
    doc = {'schema': 'project/v2', 'id': card, 'name': name, 'type': ptype, 'path': str(folder),
           'description': f'Создан из панели «Модели» по запуску {run["id"]} ({run["kind"]}).', 'client': 'internal', 'status': 'active',
           'pipelines': [GROUP_PIPELINE[group]] if group in GROUP_PIPELINE else [],
           'namenode': {'cards': [card]}, 'files': ['generations'],
           'changelog': [f'{time.strftime("%Y-%m-%d")}: создан из панели, запуск {run["id"]}'], 'owner': 'operator'}
    folder.mkdir(parents=True)
    (folder / 'project.yaml').write_text('# Project card v2 (LAYOUT2.md). NameNode is the shared map; keep this file in sync on changes.\n'
                                         + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding='utf-8')
    body = (f'## Где лежит\nlocal:{folder}\n\n## Куда вносить изменения\nФайлы проекта — в {folder}; генерации панели — generations\\<дата>-<запуск>\\ '
            f'(выходы + run.json), пресеты — generations\\presets.json.\n\n## Риски и открытые вопросы\nСоздан автоматически из панели; описание и клиента уточнить.\n')
    meta = {'id': card, 'type': 'project', 'title': f'{TYPE_TITLES[ptype]}: {name}', 'status': 'active', 'canonical': f'local:{folder}'}
    try:
        nns.put_card(meta, body, reason='панель «Модели» → В проект')
        return card, None
    except Exception as exc:  # the folder is the deliverable; a NameNode failure is reported, not fatal
        return card, f'NameNode put_card: {exc}'


def to_project(run_id, ptype, project, deliver=False):
    rows = mdl._read_runs()
    run = _find(rows, run_id)
    if run.get('status') == 'running':
        raise ValueError('Запуск ещё идёт — дождитесь результата')
    outs = [o for o in (run.get('outputs') or mdl._outputs(run['out_dir'])) if Path(o['path']).is_file()]
    if not outs:
        raise ValueError('У запуска нет файлов результата')
    name, folder = _folder(ptype, project)
    created, warn = not folder.exists(), []
    card = None
    if created:
        card, err = _new_project(folder, name, ptype, run)
        if err:
            warn.append(err)
    else:
        card = _card_id(folder)
    day = time.strftime('%Y-%m-%d', time.localtime(run.get('started') or time.time()))
    dest = folder / 'generations' / f'{day}-{run["id"]}-{run["kind"]}'
    if dest.exists():
        raise ValueError(f'Этот запуск уже сохранён: {dest}')
    dest.mkdir(parents=True)
    copied = []
    for o in outs:
        src = Path(o['path'])
        tgt = dest / src.name
        if tgt.exists():
            tgt = dest / f'{src.stem}-{len(copied)}{src.suffix}'
        shutil.copy2(src, tgt)
        digest = _sha(tgt)
        if tgt.stat().st_size != src.stat().st_size or (o.get('sha256') and o['sha256'] != digest):
            raise RuntimeError(f'Копия не совпала с оригиналом: {src.name}')
        copied.append({'name': tgt.name, 'path': str(tgt), 'size': tgt.stat().st_size, 'sha256': digest, 'source': str(src)})
    recipe = {'schema': 'run-recipe/v1', 'run_id': run['id'], 'kind': run['kind'], 'group': run.get('group'), 'title': run.get('title'),
              'started': run.get('started'), 'params': run.get('params', {}), 'inputs': run.get('inputs', {}), 'cmd': run.get('cmd', []),
              'source_dir': run['out_dir'], 'outputs': copied, 'saved': time.time()}
    (dest / 'run.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=1), encoding='utf-8')
    for rec in Path(run['out_dir']).glob('run-*.json'):
        shutil.copy2(rec, dest / rec.name)
    pfile = folder / 'generations' / 'presets.json'
    try:
        presets = json.loads(pfile.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        presets = {'schema': 'project-presets/v1', 'items': []}
    presets['items'].append({'name': run.get('title') or run['kind'], 'kind': run['kind'], 'values': run.get('params', {}), 'run_id': run['id'],
                             'recipe': str(dest / 'run.json')})
    pfile.write_text(json.dumps(presets, ensure_ascii=False, indent=1), encoding='utf-8')
    if card:
        try:
            nns.nn('log', {'agent': nns.AGENT, 'id': card, 'text': f'Панель «Модели»: запуск {run["id"]} ({run["kind"]}) → {dest}; {len(copied)} файл(ов), run.json, пресет в generations\\presets.json'})
        except Exception as exc:
            warn.append(f'NameNode log: {exc}')
    delivery = None
    if deliver:
        cmd = [sys.executable, str(DELIVERY), 'enqueue', '--files', *[x['path'] for x in copied], '--title', run.get('title') or run['kind'],
               '--project', str(folder)]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        delivery = {'ok': p.returncode == 0, 'output': (p.stdout or p.stderr).strip()[-800:]}
    run['project'] = {'path': str(folder), 'dest': str(dest), 'card': card, 'at': time.time(), 'delivered': bool(delivery and delivery['ok'])}
    rows = mdl._read_runs()  # re-read: a run may have started while copying
    _find(rows, run_id)['project'] = run['project']
    mdl._write_runs(rows)
    return {'ok': True, 'created': created, 'folder': str(folder), 'dest': str(dest), 'card': card, 'files': copied, 'delivery': delivery, 'warnings': warn}
