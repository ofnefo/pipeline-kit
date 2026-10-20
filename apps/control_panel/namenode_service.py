"""NameNode and project editing for Pipeline Web: claims ("кто занял"), Operator's personal project locks,
card viewing/editing and project.yaml editing.

All writes go through tools/namenode/namenode.py as agent `operator:web` (card edits) or `operator:lock`
(personal locks), so they appear in the shared journal like any other agent's work. A personal lock is
a NameNode claim (max 72 h, re-asserted while the lock record exists) plus a record in
<state>/project-locks.json; other agents see it as a busy card and must not edit the project.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
import kit_config as config

import collectors as c
import workboard

AGENT = 'operator:web'
LOCK_AGENT = 'operator:lock'
LOCK_HOURS = 72.0
LOCKS = c.STATE / 'project-locks.json'
EDITS = c.STATE / 'project-edits.jsonl'
BACKUPS = c.STATE / 'project-file-backups'
PROJECTS_ROOT = config.workspace('projects')
EDITABLE = {'.yaml', '.yml', '.md', '.txt', '.json', '.toml', '.ini', '.cfg'}
MAX_FILE = 512 * 1024


def nn(action, args):
    try:
        result = workboard.nn(action, args)
    except Exception as exc:  # NameNodeError lives in a dynamically loaded module
        if type(exc).__name__ == 'NameNodeError':
            text = str(exc)
            if 'claimed by' in text or 'занял' in text or 'changed since' in text:
                raise workboard.Conflict(text)
            raise ValueError(text)
        raise
    if isinstance(result, dict) and result.get('error'):
        raise ValueError(str(result['error']))
    return result


# ---------- locks ----------

def read_locks():
    try:
        data = json.loads(LOCKS.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_locks(locks):
    LOCKS.parent.mkdir(parents=True, exist_ok=True)
    tmp = LOCKS.with_suffix('.tmp')
    tmp.write_text(json.dumps(locks, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tmp, LOCKS)


def _claim_lock(card_id, reason, force):
    what = f'Заблокировано оператором лично: {reason}' if reason else 'Заблокировано оператором лично'
    out = nn('claim', {'agent': LOCK_AGENT, 'id': card_id, 'what': what, 'hours': LOCK_HOURS, 'force': bool(force)})
    if not out.get('ok'):
        busy = ', '.join(f"{w['agent']} ({str(w.get('what', ''))[:80]})" for w in out.get('busy', []))
        raise workboard.Conflict(f'Карточку {card_id} уже занял {busy}. Заблокировать можно только принудительно.')
    return out


def lock(card_id, reason='', force=False):
    card_id = str(card_id or '').strip()
    if not card_id:
        raise ValueError('Нужен id карточки NameNode')
    reason = ' '.join(str(reason or '').split())[:200]
    _claim_lock(card_id, reason, force)
    locks = read_locks()
    locks[card_id] = {'by': 'Оператор', 'reason': reason, 'since': time.strftime('%Y-%m-%d %H:%M'), 'forced': bool(force)}
    write_locks(locks)
    return {'ok': True, 'lock': locks[card_id], 'card': card_id}


def unlock(card_id):
    card_id = str(card_id or '').strip()
    locks = read_locks()
    entry = locks.pop(card_id, None)
    if entry is None:
        raise KeyError(card_id)
    write_locks(locks)
    nn('release', {'agent': LOCK_AGENT, 'id': card_id, 'summary': 'Блокировка снята оператором'})
    return {'ok': True, 'card': card_id}


def work():
    """Active claims (all agents) + Operator's locks. A lock whose claim expired is re-asserted here."""
    items = nn('work', {}).get('work', [])
    locks = read_locks()
    active = {(w['card'], w['agent']) for w in items}
    for card_id, entry in locks.items():
        if (card_id, LOCK_AGENT) not in active:
            try:
                _claim_lock(card_id, entry.get('reason', ''), True)
                items = nn('work', {}).get('work', [])
            except (ValueError, workboard.Conflict) as exc:
                entry['warning'] = str(exc)
    rows = []
    for w in items:
        rows.append({'card': w['card'], 'agent': w['agent'], 'what': w.get('what', ''), 'since': w.get('since', ''),
                     'until': w.get('until'), 'lock': w['agent'] == LOCK_AGENT})
    rows.sort(key=lambda r: (not r['lock'], r['card']))
    return {'work': rows, 'locks': locks, 'read_at': time.time()}


# ---------- cards ----------

def split_sections(body):
    parts = [p for p in re.split(r'(?m)^(?=## )', body or '') if p.strip()]
    head = '' if not parts or parts[0].startswith('## ') else parts[0]
    sections = []
    for p in parts:
        if p.startswith('## '):
            title, _, text = p[3:].partition('\n')
            sections.append({'title': title.strip(), 'text': text.strip()})
    return head.strip(), sections


def card(card_id):
    card_id = str(card_id or '').strip()
    if not card_id:
        raise ValueError('Нужен id карточки')
    out = nn('card', {'id': card_id, 'limit': 8, 'full': True})
    out['head'], out['sections'] = split_sections(out.get('body', ''))
    out['locked'] = card_id in read_locks()
    return out


def set_section(card_id, section, text, reason='', expect_updated=None, force=False, meta=None):
    section = str(section or '').strip()
    if not section:
        raise ValueError('Нужно имя раздела')
    args = {'agent': AGENT, 'id': card_id, 'section': section, 'text': str(text or ''), 'force': bool(force)}
    if reason:
        args['reason'] = str(reason)[:200]
    if expect_updated:
        args['expect_updated'] = str(expect_updated)
    if meta:
        args['meta'] = {k: str(v) for k, v in dict(meta).items() if k != 'id' and str(v).strip()}
    return nn('set_section', args)


def put_card(meta, body, reason='', replace=False, force=False):
    meta = dict(meta or {})
    if not meta.get('id'):
        raise ValueError('meta.id обязателен')
    args = {'agent': AGENT, 'meta': meta, 'body': str(body or ''), 'replace': bool(replace), 'force': bool(force)}
    if reason:
        args['reason'] = str(reason)[:200]
    return nn('put_card', args)


def search(query, limit=8):
    return nn('search', {'query': str(query or '')[:80], 'limit': int(limit)})


# ---------- project files ----------

def _inside_projects(path_text, must_exist=False):
    raw = str(path_text or '').strip().replace('\\', '/')
    if not raw:
        raise ValueError('Нужен путь')
    from uploads import guarded_path
    resolved = guarded_path(raw, [PROJECTS_ROOT])
    if must_exist and not resolved.exists():
        raise KeyError(raw)
    return resolved


def _resolve(path_text):
    resolved = _inside_projects(path_text)
    if resolved.suffix.lower() not in EDITABLE:
        raise ValueError('Разрешены только текстовые файлы: ' + ', '.join(sorted(EDITABLE)))
    return resolved


def project_files(folder):
    """Editable text files at the top level of a project folder (project.yaml, AGENTS.md, README…)."""
    base = _inside_projects(folder, must_exist=True)
    if not base.is_dir():
        raise KeyError(str(base))
    rows = []
    for p in sorted(base.iterdir()):
        try:
            _inside_projects(str(p))
        except ValueError:
            continue
        if p.is_file() and p.suffix.lower() in EDITABLE and p.stat().st_size <= MAX_FILE:
            rows.append({'name': p.name, 'path': str(p), 'size': p.stat().st_size,
                         'mtime': time.strftime('%Y-%m-%d %H:%M', time.localtime(p.stat().st_mtime))})
    return {'folder': str(base), 'files': rows, 'can_create': 'project.yaml' not in {r['name'].lower() for r in rows}}


def read_file(path_text):
    path = _resolve(path_text)
    if not path.exists():
        return {'path': str(path), 'text': '', 'mtime': 0, 'exists': False}
    if path.stat().st_size > MAX_FILE:
        raise ValueError('Файл больше 512 КБ — правьте его в редакторе')
    return {'path': str(path), 'text': path.read_text(encoding='utf-8', errors='replace'),
            'mtime': path.stat().st_mtime, 'exists': True}


def _validate(path, text):
    suffix = path.suffix.lower()
    if suffix in ('.yaml', '.yml'):
        try:
            import yaml
        except ImportError:
            return
        try:
            yaml.safe_load(text)
        except Exception as exc:
            raise ValueError(f'YAML не разбирается: {exc}')
    elif suffix == '.json':
        try:
            json.loads(text or '{}')
        except ValueError as exc:
            raise ValueError(f'JSON не разбирается: {exc}')


def write_file(path_text, text, expect_mtime=None):
    path = _resolve(path_text)
    text = str(text or '')
    if len(text.encode('utf-8')) > MAX_FILE:
        raise ValueError('Файл больше 512 КБ')
    _validate(path, text)
    backup = None
    if path.exists():
        current = path.stat().st_mtime
        if expect_mtime not in (None, 0, '') and abs(float(expect_mtime) - current) > 0.001:
            raise workboard.Conflict('Файл изменился с момента открытия. Откройте его заново.')
        BACKUPS.mkdir(parents=True, exist_ok=True)
        backup = BACKUPS / f"{time.strftime('%Y%m%d-%H%M%S')}-{path.name}"
        backup.write_bytes(path.read_bytes())
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp-web')
    tmp.write_text(text, encoding='utf-8', newline='\n')
    os.replace(tmp, path)
    EDITS.parent.mkdir(parents=True, exist_ok=True)
    with EDITS.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps({'ts': time.strftime('%Y-%m-%d %H:%M:%S'), 'path': str(path), 'bytes': len(text),
                             'backup': str(backup) if backup else None, 'by': AGENT}, ensure_ascii=False) + '\n')
    return {'ok': True, 'path': str(path), 'mtime': path.stat().st_mtime, 'backup': str(backup) if backup else None}
