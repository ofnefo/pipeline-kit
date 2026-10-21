"""change-review receipt helper (stdlib only).

Subcommands:
  diff      collect `git diff --stat` + full patch of a change into files; prints JSON with sha256.
            Run git on the host that owns the repo. Optional refusal of network drives / UNC paths via
            env CHANGE_REVIEW_REFUSE_PATHS (comma list of drive letters and/or "unc", e.g. "P,Q,unc").
  new       create a receipt JSON (default <state dir>/receipts/<date>-<slug>.json).
  add       append one reviewer verdict to a pass (creates the pass if needed; parses the verdict JSON
            out of a raw reviewer answer, also from a ```json fence).
  finalize  set status accepted|exhausted|stopped after checking the loop rules.
  validate  check a receipt; exit 1 on errors.

State dir (receipts, diffs): --state-dir, else env CHANGE_REVIEW_STATE_DIR, else <repo>/.review (or ./.review).
Receipt schema "change-review/1" is documented in references/loop.md of the change-review skill.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = 'change-review/1'
STATE_ENV = 'CHANGE_REVIEW_STATE_DIR'
REFUSE_ENV = 'CHANGE_REVIEW_REFUSE_PATHS'
LEVELS = {'L1': 2, 'L2': 3}          # level -> max repair passes
ROLES = {'acceptance', 'code', 'combined'}
VERDICTS = {'accepted', 'rejected'}
STATUSES = {'in_review', 'accepted', 'exhausted', 'stopped'}
ROUTES = {'cli', 'subagent', 'mcp', 'mailbox', 'other'}   # how the reviewer was reached
EVIDENCE_PREFIXES = ('ran:', 'read:', 'author-reported:')


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def norm_command(cmd: str) -> str:
    return ' '.join(str(cmd).split())


def family(agent: str) -> str:
    """Model family of an agent id 'family:name' (e.g. 'claude:session-1', 'codex:gpt-x')."""
    return agent.split(':', 1)[0].strip().lower() if agent else ''


def state_dir(repo: str | None = None, override: str | None = None) -> Path:
    """Where receipts and diffs live: explicit override, env CHANGE_REVIEW_STATE_DIR, else <repo>/.review."""
    if override:
        return Path(override)
    if os.environ.get(STATE_ENV):
        return Path(os.environ[STATE_ENV])
    return Path(repo or '.') / '.review'


def refused_paths() -> tuple[set, bool]:
    """(drive letters, refuse UNC) from env CHANGE_REVIEW_REFUSE_PATHS. Default: refuse nothing."""
    items = {x.strip().rstrip(':').upper() for x in os.environ.get(REFUSE_ENV, '').split(',') if x.strip()}
    return items - {'UNC'}, 'UNC' in items


# ---------------------------------------------------------------- diff collector
def check_local_path(path: str) -> Path:
    drives, unc = refused_paths()
    raw = str(path)
    if unc and (raw.startswith('\\\\') or raw.startswith('//')):
        raise SystemExit(f'refused: UNC/network path {raw}; run git on the host that owns the files')
    m = re.match(r'^([A-Za-z]):', raw)
    if m and m.group(1).upper() in drives:
        raise SystemExit(f'refused: {m.group(1).upper()}: is a network drive; run git on the host that owns it')
    return Path(path).resolve()


def git(repo: Path, *args: str, ok=(0,)) -> bytes:
    r = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    if r.returncode not in ok:
        raise SystemExit(f'git {" ".join(args)} failed ({r.returncode}): {r.stderr.decode("utf-8", "replace")[-400:]}')
    return r.stdout


def repo_root(repo: str) -> Path:
    p = check_local_path(repo)
    return Path(git(p, 'rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()


def changed_files(root: Path, mode: str, rev_range: str | None = None, paths: list[str] | None = None,
                  untracked: bool = True) -> dict:
    """{path: blob sha of the new content | 'deleted'} for a change; paths relative to the repo top level.

    mode: 'range' (rev_range A..B), 'staged' (index vs HEAD), 'tracked' (worktree vs HEAD, tracked files only, as
    `git commit -a`), 'worktree' (tracked + untracked, the default for a pending change).
    """
    tail = ['--', *paths] if paths else []
    spec = {'range': [rev_range or 'HEAD~1..HEAD'], 'staged': ['--cached'], 'tracked': ['HEAD'], 'worktree': ['HEAD']}[mode]
    raw = git(root, 'diff', '--name-status', '--no-renames', '-z', *spec, *tail).decode('utf-8', 'replace').split('\0')
    entries = [(raw[i], raw[i + 1]) for i in range(0, len(raw) - 1, 2) if raw[i]]
    if mode == 'worktree' and untracked:
        names = git(root, 'ls-files', '--others', '--exclude-standard', '-z', *tail).decode('utf-8', 'replace')
        entries += [('A', n) for n in names.split('\0') if n]
    end = (rev_range or 'HEAD~1..HEAD').split('..')[-1].lstrip('.') or 'HEAD'
    files = {}
    for status, path in entries:
        if status.startswith('D'):
            files[path] = 'deleted'
        elif mode == 'range':
            files[path] = git(root, 'rev-parse', f'{end}:{path}').decode().strip()
        elif mode == 'staged':
            files[path] = git(root, 'rev-parse', f':{path}').decode().strip()
        else:
            files[path] = git(root, 'hash-object', '--', path).decode().strip()
    return files


def collect_diff(repo: str, out_dir: str, slug: str, rev_range: str | None = None, staged: bool = False,
                 paths: list[str] | None = None, untracked: bool = True) -> dict:
    root = repo_root(repo)
    base = ['diff', '--no-color', '--no-ext-diff']
    if staged:
        base.append('--cached')
    elif rev_range:
        base.append(rev_range)
    else:
        base.append('HEAD')
    tail = ['--', *paths] if paths else []
    stat = git(root, *base, '--stat', *tail)
    patch = git(root, *base, *tail)
    extra = []
    if untracked and not staged and not rev_range:
        names = git(root, 'ls-files', '--others', '--exclude-standard', '-z', *tail).split(b'\0')
        for name in filter(None, names):
            extra.append(name.decode('utf-8', 'replace'))
            patch += git(root, 'diff', '--no-color', '--no-index', '--', '/dev/null', name.decode('utf-8'), ok=(0, 1))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    patch_path = out / f'{slug}.patch'
    stat_path = out / f'{slug}.stat.txt'
    patch_path.write_bytes(patch)
    stat_text = stat.decode('utf-8', 'replace') + ''.join(f' (untracked) {n}\n' for n in extra)
    stat_path.write_text(stat_text, encoding='utf-8')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    mode = 'staged' if staged else ('range' if rev_range else ('worktree' if untracked else 'tracked'))
    files = changed_files(root, mode, rev_range, paths, untracked)
    return {'repo': str(root), 'head': head, 'mode': mode, 'files': files,
            'range': rev_range or ('--cached' if staged else 'HEAD..worktree'),
            'paths': paths or [], 'untracked': extra, 'patch': str(patch_path), 'stat': str(stat_path),
            'sha256': hashlib.sha256(patch).hexdigest(), 'bytes': len(patch),
            'stat_summary': stat_text.strip().splitlines()[-1] if stat_text.strip() else 'empty diff'}


# ---------------------------------------------------------------- verdict parsing
def extract_verdict(text: str) -> dict:
    """Return the last JSON object in `text` that has a "verdict" key."""
    candidates = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S)
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == '{':
            try:
                obj, _ = dec.raw_decode(text[i:])
            except ValueError:
                continue
            if isinstance(obj, dict) and 'verdict' in obj:
                candidates.append(json.dumps(obj))
    for raw in reversed(candidates):
        try:
            obj = json.loads(raw)
        except ValueError:
            continue
        if isinstance(obj, dict) and 'verdict' in obj:
            return obj
    raise ValueError('no JSON object with a "verdict" key found in reviewer answer')


def verdict_problems(v: dict) -> list[str]:
    errs = []
    if v.get('verdict') not in VERDICTS:
        errs.append(f'verdict must be accepted|rejected, got {v.get("verdict")!r}')
    for key in ('evidence', 'blocking', 'nonblocking'):
        if not isinstance(v.get(key), list) or not all(isinstance(x, str) and x.strip() for x in v.get(key, [])):
            errs.append(f'{key} must be a list of non-empty strings')
    if errs:
        return errs
    if v['verdict'] == 'accepted':
        if v['blocking']:
            errs.append('accepted verdict must have empty blocking[]')
        own = [e for e in v['evidence'] if e.lower().startswith(('ran:', 'read:'))]
        if not own:
            errs.append('accepted verdict needs at least one evidence item the reviewer obtained itself (ran:/read:)')
    else:
        if not v['blocking']:
            errs.append('rejected verdict must list at least one blocking item')
    bad = [e for e in v['evidence'] if not e.lower().startswith(EVIDENCE_PREFIXES)]
    if bad:
        errs.append(f'evidence items must start with ran:/read:/author-reported: ({len(bad)} do not)')
    return errs


# ---------------------------------------------------------------- receipt
def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path: str, rec: dict) -> None:
    rec['updated'] = now()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, p)


def default_receipt_path(slug: str, project_dir: str | None = None, repo: str | None = None,
                         state: str | None = None) -> Path:
    date = dt.date.today().isoformat()
    if project_dir and (Path(project_dir) / 'receipts').is_dir():
        return Path(project_dir) / 'receipts' / f'change-review-{date}-{slug}.json'
    return state_dir(repo, state) / 'receipts' / f'{date}-{slug}.json'


def new_receipt(slug: str, level: str, task: str, author: str, repo: str, diff: dict | None = None,
                same_family_reason: str = '', commands: list[str] | None = None) -> dict:
    if level not in LEVELS:
        raise SystemExit('level must be L1 or L2 (L0 does not use change-review)')
    rec = {'schema': SCHEMA, 'slug': slug, 'created': now(), 'updated': now(), 'level': level,
           'max_repairs': LEVELS[level], 'task': task, 'author': author, 'repo': repo,
           'same_family_reason': same_family_reason, 'passes': [], 'status': 'in_review',
           'final_diff_sha256': None, 'commands': [norm_command(c) for c in (commands or [])]}
    if diff:
        rec['passes'].append({'n': 1, 'diff': diff, 'reviews': [], 'repair': ''})
    return rec


def add_review(rec: dict, n: int, role: str, reviewer: str, route: str, verdict: dict, thread_id: str = '',
               seconds: float | None = None, diff: dict | None = None, repair: str = '') -> dict:
    if role not in ROLES:
        raise SystemExit(f'role must be one of {sorted(ROLES)}')
    if route not in ROUTES:
        raise SystemExit(f'route must be one of {sorted(ROUTES)}')
    passes = rec['passes']
    if n > len(passes) + 1 or n < 1:
        raise SystemExit(f'pass {n} out of order (have {len(passes)})')
    if n == len(passes) + 1:
        if diff is None and passes:
            raise SystemExit('a new pass after a repair needs --diff-json (the repaired diff)')
        passes.append({'n': n, 'diff': diff or {}, 'reviews': [], 'repair': ''})
    p = passes[n - 1]
    if diff:
        p['diff'] = diff
    if repair and n >= 2:
        passes[n - 2]['repair'] = repair
    p['reviews'].append({'role': role, 'reviewer': reviewer, 'route': route, 'thread_id': thread_id,
                         'seconds': seconds, 'recorded': now(), **{k: verdict.get(k) for k in
                                                                   ('verdict', 'evidence', 'blocking', 'nonblocking')}})
    return rec


def pass_outcome(p: dict, level: str) -> str:
    """accepted | rejected | incomplete for one pass."""
    roles = {r['role']: r['verdict'] for r in p['reviews']}
    need = [{'acceptance', 'code'}] if level == 'L2' else [{'combined'}, {'acceptance', 'code'}]
    if any(v == 'rejected' for v in roles.values()):
        return 'rejected'
    if any(req <= set(roles) for req in need):
        return 'accepted'
    return 'incomplete'


def problems(rec: dict) -> list[str]:
    errs = []
    if rec.get('schema') != SCHEMA:
        errs.append(f'schema must be {SCHEMA}')
    level = rec.get('level')
    if level not in LEVELS:
        return errs + ['level must be L1 or L2']
    if rec.get('max_repairs') != LEVELS[level]:
        errs.append(f'max_repairs for {level} must be {LEVELS[level]}')
    if rec.get('status') not in STATUSES:
        errs.append(f'status must be one of {sorted(STATUSES)}')
    author = rec.get('author', '')
    if not author:
        errs.append('author is required')
    passes = rec.get('passes', [])
    if len(passes) > LEVELS[level] + 1:
        errs.append(f'{len(passes)} passes exceed 1 + {LEVELS[level]} repairs')
    for p in passes:
        tag = f'pass {p.get("n")}'
        if not p.get('diff', {}).get('sha256'):
            errs.append(f'{tag}: diff.sha256 missing')
        for r in p.get('reviews', []):
            if r.get('reviewer') == author:
                errs.append(f'{tag}: reviewer {author} is the author')
            for e in verdict_problems(r):
                errs.append(f'{tag} {r.get("role")}: {e}')
        fams = {family(r.get('reviewer', '')) for r in p.get('reviews', [])}
        if p.get('reviews') and family(author) in fams and len(fams) == 1 and not rec.get('same_family_reason'):
            errs.append(f'{tag}: all reviewers share the author model family; set same_family_reason or use the other model')
        open_last = p is passes[-1] and rec.get('status') == 'in_review'
        if level == 'L2' and p.get('reviews') and not open_last:
            roles = {r['role'] for r in p['reviews']}
            if not {'acceptance', 'code'} <= roles and pass_outcome(p, level) != 'rejected':
                errs.append(f'{tag}: L2 needs both acceptance and code reviews')
        if p is not passes[-1] and pass_outcome(p, level) == 'accepted':
            errs.append(f'{tag}: accepted pass followed by another pass')
    status = rec.get('status')
    if status == 'accepted':
        if not passes or pass_outcome(passes[-1], level) != 'accepted':
            errs.append('status accepted but the last pass is not accepted by all required reviewers')
        elif rec.get('final_diff_sha256') != passes[-1]['diff'].get('sha256'):
            errs.append('final_diff_sha256 must equal the last reviewed diff sha256')
    if status == 'exhausted':
        if len(passes) != LEVELS[level] + 1 or pass_outcome(passes[-1], level) != 'rejected':
            errs.append('status exhausted needs 1 + max_repairs passes with the last one rejected')
    return errs


def finalize(rec: dict, status: str, note: str = '') -> dict:
    if status not in STATUSES - {'in_review'}:
        raise SystemExit('status must be accepted|exhausted|stopped')
    rec['status'] = status
    if status == 'accepted' and rec['passes']:
        rec['final_diff_sha256'] = rec['passes'][-1]['diff'].get('sha256')
    if note:
        rec['note'] = note
    return rec


# ---------------------------------------------------------------- CLI
def _read_json_arg(value: str | None):
    if not value:
        return None
    if value == '-':
        return json.loads(sys.stdin.read())
    return json.loads(Path(value).read_text(encoding='utf-8'))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='change-review receipt helper (stdlib only)',
                                 epilog='env: CHANGE_REVIEW_STATE_DIR (receipts/diffs root), '
                                        'CHANGE_REVIEW_REFUSE_PATHS (e.g. "P,Q,unc")')
    sub = ap.add_subparsers(dest='cmd', required=True)

    d = sub.add_parser('diff', help='collect git diff stat + patch (run on the host that owns the repo)')
    d.add_argument('--repo', required=True)
    d.add_argument('--slug', required=True)
    d.add_argument('--out-dir', default=None, help='default: <state dir>/diffs')
    d.add_argument('--state-dir', help='default: env CHANGE_REVIEW_STATE_DIR or <repo>/.review')
    d.add_argument('--range', dest='rev_range', help='e.g. HEAD~1..HEAD (default: HEAD vs worktree + untracked)')
    d.add_argument('--staged', action='store_true')
    d.add_argument('--no-untracked', action='store_true')
    d.add_argument('paths', nargs='*')

    n = sub.add_parser('new', help='create a receipt')
    n.add_argument('--slug', required=True)
    n.add_argument('--level', required=True, choices=sorted(LEVELS))
    n.add_argument('--task', required=True)
    n.add_argument('--author', required=True, help='agent id as family:name, e.g. claude:session-1')
    n.add_argument('--repo', required=True)
    n.add_argument('--diff-json', help='JSON from the diff subcommand (file or -)')
    n.add_argument('--same-family-reason', default='', help='why no other-family reviewer was available')
    n.add_argument('--command', action='append', default=[], help='exact planned command this review covers (deploy, data move/delete); repeatable')
    n.add_argument('--project-dir', help='write into <project-dir>/receipts/ when that folder exists')
    n.add_argument('--state-dir', help='default: env CHANGE_REVIEW_STATE_DIR or <repo>/.review')
    n.add_argument('--out', help='explicit receipt path')

    a = sub.add_parser('add', help='record one reviewer verdict')
    a.add_argument('receipt')
    a.add_argument('--pass', dest='n', type=int, required=True)
    a.add_argument('--role', required=True, choices=sorted(ROLES))
    a.add_argument('--reviewer', required=True, help='reviewer id as family:name, e.g. codex:gpt-x')
    a.add_argument('--route', required=True, choices=sorted(ROUTES))
    a.add_argument('--answer', required=True, help='raw reviewer answer file (or -); verdict JSON is extracted')
    a.add_argument('--thread-id', default='')
    a.add_argument('--seconds', type=float)
    a.add_argument('--diff-json', help='diff JSON for a new pass after a repair')
    a.add_argument('--repair', default='', help='one-line summary of the repair that led to this pass')

    f = sub.add_parser('finalize')
    f.add_argument('receipt')
    f.add_argument('--status', required=True, choices=['accepted', 'exhausted', 'stopped'])
    f.add_argument('--note', default='')

    v = sub.add_parser('validate')
    v.add_argument('receipt')

    args = ap.parse_args(argv)
    if args.cmd == 'diff':
        out_dir = args.out_dir or str(state_dir(args.repo, args.state_dir) / 'diffs')
        res = collect_diff(args.repo, out_dir, args.slug, args.rev_range, args.staged, args.paths,
                           untracked=not args.no_untracked)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == 'new':
        rec = new_receipt(args.slug, args.level, args.task, args.author, args.repo, _read_json_arg(args.diff_json),
                          args.same_family_reason, args.command)
        out = args.out or str(default_receipt_path(args.slug, args.project_dir, args.repo, args.state_dir))
        if Path(out).exists():
            raise SystemExit(f'refused: {out} exists')
        save(out, rec)
        print(out)
        return 0
    if args.cmd == 'add':
        raw = sys.stdin.read() if args.answer == '-' else Path(args.answer).read_text(encoding='utf-8')
        verdict = extract_verdict(raw)
        errs = verdict_problems(verdict)
        if errs:
            print(json.dumps({'ok': False, 'verdict_errors': errs}, ensure_ascii=False, indent=2))
            return 1
        rec = load(args.receipt)
        add_review(rec, args.n, args.role, args.reviewer, args.route, verdict, args.thread_id, args.seconds,
                   _read_json_arg(args.diff_json), args.repair)
        save(args.receipt, rec)
        p = rec['passes'][args.n - 1]
        print(json.dumps({'ok': True, 'pass': args.n, 'verdict': verdict['verdict'],
                          'pass_outcome': pass_outcome(p, rec['level']),
                          'repairs_left': rec['max_repairs'] - (len(rec['passes']) - 1)}))
        return 0
    if args.cmd == 'finalize':
        rec = finalize(load(args.receipt), args.status, args.note)
        errs = problems(rec)
        if errs:
            print(json.dumps({'ok': False, 'errors': errs}, ensure_ascii=False, indent=2))
            return 1
        save(args.receipt, rec)
        print(json.dumps({'ok': True, 'status': rec['status'], 'final_diff_sha256': rec['final_diff_sha256']}))
        return 0
    if args.cmd == 'validate':
        errs = problems(load(args.receipt))
        print(json.dumps({'ok': not errs, 'errors': errs}, ensure_ascii=False, indent=2))
        return 1 if errs else 0
    return 2


if __name__ == '__main__':
    sys.exit(main())
