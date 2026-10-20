"""NameNode: the one shared map of Operator's systems for every agent (Claude, Codex, any host).

Local store: configured workspace/namenode. Writes are atomic; no Git operations.
  cards/<id>.md   one card per site / pipeline / project / system: where it lives, how it is deployed,
                  where changes go, current risks, last review. Front matter = "key: value" lines.
  INDEX.md        generated table of all cards (+ index.json for tools)
  WORK.md         generated from work.json: who is working on what right now (claims with TTL)
  JOURNAL.md      append-only log: time · agent · card · what changed and where

On the laptop the same functions run on Local node over SSH, so there is exactly one copy.

CLI (prints JSON):  namenode.py <action> [json-args | b64:<base64 json>]
  actions: index, card, search, claim, release, work, log, journal, put_card, set_section, rebuild, send, inbox
  messages.jsonl + messages-read.json: agent mailbox (send to an agent, "codex:*", "claude:*", "all", "card:<id>")
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(os.environ.get('PIPELINE_KIT_WORKSPACE', 'workspace')).absolute() / 'namenode'
NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
ID_RE = re.compile(r'^[a-z0-9][a-z0-9._-]{1,63}$')
TYPES = ('system', 'pipeline', 'project', 'site', 'service', 'repo', 'host')
STANDARD_SECTIONS = ('Что это', 'Где лежит', 'Репозиторий', 'Запуск и деплой', 'Куда вносить изменения',
                     'Риски и открытые вопросы', 'Ревью')
DEFAULT_CLAIM_H = 8


class NameNodeError(Exception):
    pass


def now_text():
    return time.strftime('%Y-%m-%d %H:%M')


def local_available():
    return ROOT.is_dir()


# ------------------------------------------------------------------ storage helpers (Local node side)

class Lock:
    """Exclusive write lock (O_EXCL file); stale after 60 s."""

    def __init__(self):
        self.path = ROOT / '.lock'

    def __enter__(self):
        for _ in range(100):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return self
            except FileExistsError:
                if time.time() - self.path.stat().st_mtime > 60:
                    self.path.unlink(missing_ok=True)
                    continue
                time.sleep(0.2)
        raise NameNodeError('NameNode is busy (lock held)')

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)




def commit(message):
    # Local journal is authoritative; source control is an explicit operator action.
    pass


def parse_card(text):
    meta, body = {}, text
    if text.startswith('---\n'):
        end = text.find('\n---\n', 4)
        if end > 0:
            for line in text[4:end].splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    meta[key.strip()] = value.strip()
            body = text[end + 5:]
    return meta, body


def render_card(meta, body):
    head = '\n'.join(f'{k}: {v}' for k, v in meta.items() if v not in (None, ''))
    return f'---\n{head}\n---\n{body.lstrip()}'


def card_path(card_id):
    if not ID_RE.match(card_id or ''):
        raise NameNodeError(f'bad card id {card_id!r} (lowercase letters, digits, . _ -)')
    return ROOT / 'cards' / f'{card_id}.md'


def load_cards():
    cards = []
    for path in sorted((ROOT / 'cards').glob('*.md')):
        meta, body = parse_card(path.read_text(encoding='utf-8'))
        meta.setdefault('id', path.stem)
        cards.append((meta, body))
    return cards


def load_work():
    path = ROOT / 'work.json'
    items = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    return [w for w in items if w.get('until', 0) > time.time()]


def save_work(items):
    (ROOT / 'work.json').write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding='utf-8')
    lines = ['# Сейчас в работе', '', 'Генерируется из work.json инструментом namenode (claim/release). Руками не править.', '']
    if not items:
        lines.append('_Никто ничего не занял._')
    for w in sorted(items, key=lambda x: x['card']):
        lines.append(f"- **{w['card']}** — {w['agent']} · с {w['since']} · до {time.strftime('%Y-%m-%d %H:%M', time.localtime(w['until']))} — {w['what']}")
    (ROOT / 'WORK.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def rebuild_index():
    cards = load_cards()
    work = {w['card']: w for w in load_work()}
    rows = []
    for meta, _ in cards:
        rows.append({k: meta.get(k, '') for k in ('id', 'type', 'title', 'status', 'canonical', 'repo', 'rules', 'owner', 'reviewed', 'updated')})
    (ROOT / 'index.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
    out = ['# NameNode — карта всех систем', '',
           'Одна общая карта для Claude и Codex на ноутбуке и локального узла. Перед работой прочитай карточку, займи её (claim),',
           'после работы запиши в журнал (log) и освободи (release). Подробно: README.md.', '']
    for kind in TYPES:
        group = [r for r in rows if r['type'] == kind]
        if not group:
            continue
        out += [f'## {kind}', '', '| id | Что | Статус | Канон (хост:путь) | Репозиторий | Сейчас в работе |', '|---|---|---|---|---|---|']
        for r in group:
            busy = work.get(r['id'])
            out.append(f"| [{r['id']}](cards/{r['id']}.md) | {r['title']} | {r['status']} | `{r['canonical']}` | {r['repo']} | "
                       f"{busy['agent'] + ': ' + busy['what'] if busy else ''} |")
        out.append('')
    (ROOT / 'INDEX.md').write_text('\n'.join(out), encoding='utf-8')
    return rows


def append_journal(agent, card_id, text):
    line = f"- {now_text()} · {agent} · {card_id} · {' '.join(str(text).split())[:2000]}\n"
    path = ROOT / 'JOURNAL.md'
    if not path.exists():
        path.write_text('# Журнал изменений\n\nКто, что и где поменял. Новые записи внизу.\n\n', encoding='utf-8')
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(line)


def ensure_not_claimed_by_other(card_id, agent, args):
    """Writes to a card claimed by another agent are refused unless force=true (after agreeing with that agent/Operator)."""
    others = [w for w in load_work() if w['card'] == card_id and w['agent'] != agent]
    if others and not args.get('force'):
        who = ', '.join(f"{w['agent']} ({w['what']})" for w in others)
        raise NameNodeError(f'card {card_id} is claimed by {who}; write your proposal with log, or agree first and use force=true')


def ensure_expected_version(card_id, meta, args):
    """Optional optimistic check: expect_updated = the card's meta.updated you read; refuse if someone wrote since."""
    expected = args.get('expect_updated')
    if expected is not None and str(expected).strip() != meta.get('updated', ''):
        raise NameNodeError(f"card {card_id} changed since you read it (updated now: {meta.get('updated', '')!r}); "
                            'read the card again and merge')


def need_agent(args):
    agent = ' '.join(str(args.get('agent') or '').split())[:80]
    if not agent:
        raise NameNodeError('agent is required, e.g. "claude:Расширение серверной системы" or "codex:Assistant OS"')
    return agent


# ------------------------------------------------------------------ actions (run where ROOT exists)

def short(text, limit):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= limit else text[:limit - 1] + '…'


def compact_work(items):
    return [f"{w['card']}: {w['agent']} до {time.strftime('%d.%m %H:%M', time.localtime(w['until']))} — {short(w['what'], 120)}"
            for w in items]


def journal_lines(card_id=None):
    path = ROOT / 'JOURNAL.md'
    lines = [l for l in path.read_text(encoding='utf-8').splitlines() if l.startswith('- ')] if path.exists() else []
    return [l for l in lines if f' · {card_id} · ' in l] if card_id else lines


def a_index(args):
    """Compact by default (one line per card); full=true returns every index field."""
    rows = json.loads((ROOT / 'index.json').read_text(encoding='utf-8')) if (ROOT / 'index.json').exists() else rebuild_index()
    kind = args.get('type')
    rows = [r for r in rows if not kind or r['type'] == kind]
    if args.get('full'):
        return {'cards': rows, 'work': load_work()}
    return {'cards': [f"{r['id']} | {r['status']} | {short(r['title'], 70)}" for r in rows],
            'work': compact_work(load_work()), 'hint': 'card id [sections="Где лежит,Куда вносить изменения"]'}


def a_card(args):
    """Whole card by default; sections="A,B" returns only those sections. limit = journal lines (default 5, 0 = none)."""
    path = card_path(args.get('id'))
    if not path.exists():
        raise NameNodeError(f"no card {args.get('id')}; use search")
    meta, body = parse_card(path.read_text(encoding='utf-8'))
    wanted = [s.strip().casefold() for s in str(args.get('sections') or '').split(',') if s.strip()]
    if wanted:
        parts = re.split(r'(?m)^(?=## )', body)
        body = ''.join(p for p in parts if p.startswith('## ') and p[3:].splitlines()[0].strip().casefold() in wanted)
    limit = int(args['limit']) if args.get('limit') is not None else 5
    journal = journal_lines(path.stem)[-limit:] if limit > 0 else []
    if not args.get('full'):
        journal = [short(l, 240) for l in journal]
    out = {'meta': meta, 'body': body}
    work = compact_work([w for w in load_work() if w['card'] == meta.get('id', path.stem)])
    if work:
        out['work'] = work
    if journal:
        out['recent_journal'] = journal
    return out


def a_search(args):
    """All words must match; id/title hits rank first. limit = max hits (default 8)."""
    terms = str(args.get('query') or '').casefold().split()
    if not terms:
        raise NameNodeError('query is required')
    hits = []
    for meta, body in load_cards():
        head = f"{meta.get('id', '')} {meta.get('title', '')}".casefold()
        text = (json.dumps(meta, ensure_ascii=False) + body).casefold()
        if all(t in text for t in terms):
            idx = text.find(terms[0])
            hits.append((-sum(t in head for t in terms),
                         {'id': meta['id'], 'title': short(meta.get('title', ''), 80),
                          'snippet': short(text[max(0, idx - 50): idx + 90], 140)}))
    hits.sort(key=lambda h: h[0])
    limit = int(args.get('limit') or 8)
    return {'hits': [h for _, h in hits[:limit]], 'total': len(hits)}


def a_claim(args):
    agent = need_agent(args)
    card_id = args.get('id')
    if not card_path(card_id).exists():
        raise NameNodeError(f'no card {card_id}')
    what = ' '.join(str(args.get('what') or '').split())[:300]
    if not what:
        raise NameNodeError('what is required (one line: what you are doing)')
    hours = max(0.25, min(72.0, float(args.get('hours') or DEFAULT_CLAIM_H)))
    with Lock():
        items = load_work()
        other = [w for w in items if w['card'] == card_id and w['agent'] != agent]
        if other and not args.get('force'):
            return {'ok': False, 'busy': other,
                    'note': 'Карточку уже занял другой агент. Согласуй с ним (или с оператором) и только потом force=true.'}
        items = [w for w in items if not (w['card'] == card_id and w['agent'] == agent)]
        items.append({'card': card_id, 'agent': agent, 'what': what, 'since': now_text(), 'until': time.time() + hours * 3600})
        save_work(items)
        append_journal(agent, card_id, f'CLAIM: {what}')
        rebuild_index()
        commit(f'claim {card_id} by {agent}')
    out = {'ok': True, 'work': compact_work([w for w in items if w['card'] == card_id])}
    unread = len(mailbox_for(agent, unread_only=True))
    if unread:
        out['inbox'] = f'{unread} unread message(s): namenode inbox agent="{agent}"'
    return out


# ------------------------------------------------------------------ agent mailbox (Claude <-> Codex <-> any session)

def load_messages():
    path = ROOT / 'messages.jsonl'
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]


def load_read():
    path = ROOT / 'messages-read.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def addressed_to(message, agent, claimed):
    """to = exact agent, "all", a prefix mask like "codex:*", or "card:<id>" (whoever holds that claim now)."""
    to = message['to']
    if message['from'] == agent:
        return False
    if to in (agent, 'all'):
        return True
    if to.endswith('*'):
        return agent.startswith(to[:-1])
    return to.startswith('card:') and to[5:] in claimed


def mailbox_for(agent, unread_only=False):
    claimed = {w['card'] for w in load_work() if w['agent'] == agent}
    done = set(load_read().get(agent, []))
    return [m for m in load_messages() if addressed_to(m, agent, claimed) and not (unread_only and m['id'] in done)]


def a_send(args):
    agent = need_agent(args)
    to = ' '.join(str(args.get('to') or '').split())[:120]
    text = str(args.get('text') or '').strip()
    if not to or not text:
        raise NameNodeError('to and text are required; to = agent ("codex:<task>"), "codex:*", "claude:*", "all" or "card:<id>"')
    if to.startswith('card:'):
        card_path(to[5:])
    message = {'id': f'{int(time.time() * 1000):x}', 'time': now_text(), 'from': agent, 'to': to,
               'card': args.get('id') or '', 'text': text[:4000]}
    with Lock():
        with open(ROOT / 'messages.jsonl', 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(message, ensure_ascii=False) + '\n')
        commit(f'message {agent} -> {to}')
    holders = [w['agent'] for w in load_work() if to.startswith('card:') and w['card'] == to[5:]]
    return {'ok': True, 'id': message['id'], **({'delivered_to': holders} if to.startswith('card:') else {})}


def a_inbox(args):
    """Unread messages for agent (marks them read unless peek=true); full=true returns read ones too (last limit)."""
    agent = need_agent(args)
    items = mailbox_for(agent, unread_only=not args.get('full'))[-int(args.get('limit') or 20):]
    if items and not args.get('peek'):
        with Lock():
            read = load_read()
            read[agent] = sorted(set(read.get(agent, [])) | {m['id'] for m in items})[-500:]
            (ROOT / 'messages-read.json').write_text(json.dumps(read, ensure_ascii=False, indent=1), encoding='utf-8')
            commit(f'inbox read by {agent}')
    return {'messages': [f"[{m['id']}] {m['time']} {m['from']} → {m['to']}{' (' + m['card'] + ')' if m['card'] else ''}: {m['text']}"
                         for m in items]}


def a_release(args):
    agent = need_agent(args)
    card_id = args.get('id')
    with Lock():
        items = load_work()
        kept = [w for w in items if not (w['card'] == card_id and w['agent'] == agent)]
        save_work(kept)
        if args.get('summary'):
            append_journal(agent, card_id, f"DONE: {args['summary']}")
        rebuild_index()
        commit(f'release {card_id} by {agent}')
    return {'ok': True, 'released': len(items) - len(kept)}


def a_work(args):
    return {'work': load_work()}


def a_log(args):
    agent = need_agent(args)
    card_id = args.get('id')
    card_path(card_id)
    text = str(args.get('text') or '').strip()
    if not text:
        raise NameNodeError('text is required: what changed and where (paths/commits)')
    with Lock():
        append_journal(agent, card_id, text)
        commit(f'log {card_id} by {agent}')
    return {'ok': True}


def a_journal(args):
    """Last entries (default 15), each shortened to 300 chars unless full=true."""
    lines = journal_lines(args.get('id'))[-int(args.get('limit') or 15):]
    return {'entries': lines if args.get('full') else [short(l, 300) for l in lines]}


def a_put_card(args):
    """Create or fully replace a card: meta (dict) + body (markdown with the standard ## sections)."""
    agent = need_agent(args)
    meta = dict(args.get('meta') or {})
    card_id = meta.get('id') or args.get('id')
    path = card_path(card_id)
    if meta.get('type') not in TYPES:
        raise NameNodeError(f'meta.type must be one of {TYPES}')
    if not meta.get('title'):
        raise NameNodeError('meta.title is required')
    body = str(args.get('body') or '').strip()
    missing = [s for s in STANDARD_SECTIONS if f'## {s}' not in body]
    if missing and not args.get('allow_missing_sections'):
        raise NameNodeError(f'body lacks sections: {missing}')
    meta = {'id': card_id, **{k: v for k, v in meta.items() if k != 'id'}}
    meta['updated'] = f'{now_text()} {agent}'
    with Lock():
        existed = path.exists()
        if existed and not args.get('replace'):
            raise NameNodeError(f'card {card_id} exists; use set_section for parts, or put_card with replace=true to rewrite it whole')
        if existed:
            ensure_not_claimed_by_other(card_id, agent, args)
            ensure_expected_version(card_id, parse_card(path.read_text(encoding='utf-8'))[0], args)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_card(meta, body + '\n'), encoding='utf-8')
        append_journal(agent, card_id, ('UPDATE card' if existed else 'NEW card') + (f": {args['reason']}" if args.get('reason') else ''))
        rebuild_index()
        commit(f"{'update' if existed else 'new'} card {card_id} by {agent}")
    return {'ok': True, 'id': card_id, 'created': not existed, 'updated': meta['updated']}


def a_set_section(args):
    """Replace (or add) one '## Section' of a card; optionally update meta keys."""
    agent = need_agent(args)
    card_id = args.get('id')
    path = card_path(card_id)
    if not path.exists():
        raise NameNodeError(f'no card {card_id}')
    section = str(args.get('section') or '').strip()
    if not section:
        raise NameNodeError('section is required (e.g. "Ревью")')
    text = str(args.get('text') or '').strip()
    with Lock():
        ensure_not_claimed_by_other(card_id, agent, args)
        meta, body = parse_card(path.read_text(encoding='utf-8'))
        ensure_expected_version(card_id, meta, args)
        pattern = re.compile(rf'(^## {re.escape(section)}\s*\n)(.*?)(?=^## |\Z)', re.S | re.M)
        if pattern.search(body):
            body = pattern.sub(lambda m: m.group(1) + text + '\n\n', body, count=1)
        else:
            body = body.rstrip() + f'\n\n## {section}\n{text}\n'
        for key, value in (args.get('meta') or {}).items():
            if key != 'id':
                meta[key] = str(value)
        meta['updated'] = f'{now_text()} {agent}'
        path.write_text(render_card(meta, body), encoding='utf-8')
        append_journal(agent, card_id, f"SECTION {section}" + (f": {args['reason']}" if args.get('reason') else ''))
        rebuild_index()
        commit(f'section {section} of {card_id} by {agent}')
    return {'ok': True, 'updated': meta['updated']}


def a_rebuild(args):
    with Lock():
        rows = rebuild_index()
        save_work(load_work())
        commit('rebuild index')
    return {'ok': True, 'cards': len(rows)}


ACTIONS = {'index': a_index, 'card': a_card, 'search': a_search, 'claim': a_claim, 'release': a_release, 'work': a_work,
           'log': a_log, 'journal': a_journal, 'put_card': a_put_card, 'set_section': a_set_section, 'rebuild': a_rebuild,
           'send': a_send, 'inbox': a_inbox}


# ------------------------------------------------------------------ entry points

def call(action, args=None):
    if action not in ACTIONS:
        raise NameNodeError('Unknown NameNode action')
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'cards').mkdir(exist_ok=True)
    return ACTIONS[action](dict(args or {}))


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    action = argv[0]
    raw = argv[1] if len(argv) > 1 else '{}'
    if raw.startswith('b64:'):
        raw = base64.b64decode(raw[4:]).decode('utf-8')
    try:
        out = call(action, json.loads(raw))
    except NameNodeError as exc:
        out = {'error': str(exc)}
    print(json.dumps(out, ensure_ascii=False))
    return 1 if 'error' in out else 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv[1:]))
