"""change-review gate (stdlib only): decide the review level of a change and check that an accepted receipt covers it.

  review_gate.py classify --repo R [--command CMD] [--mode worktree|staged|tracked | --range A..B] [--floor L1|L2]
        prints {level, reasons, files}; exit 0. Use at task start to put "[L2] ..." into your task claim or notes.
  review_gate.py check --repo R [--command CMD] [--mode ... | --range ...] [--floor ...] [--receipts DIR ...]
        exit 0 = pass (L0, or every L1/L2 file and the planned deploy/data command is covered by an accepted receipt),
        exit 2 = review needed (prints level, uncovered items and a one-line how-to), exit 1 = usage/git error.
  review_gate.py check --command CMD [--receipts DIR ...]
        deploy or data move/delete run outside any repo: needs an accepted L2 receipt listing CMD whose reviewed repo
        (absolute path from its diff) still passes `check --command CMD` there; the hook does the same for deploys from
        a non-repo or network-drive cwd. --mode/--range/--floor apply only with --repo.
  review_gate.py hook [--mode warn|block]
        PreToolUse hook (Claude Code; Codex hooks if enabled): reads the hook JSON on stdin and acts only on
        `git commit` and production deploy commands. warn (default; env CHANGE_REVIEW_GATE) adds a reminder and allows;
        block exits 2 with the reason on stderr. Any internal error -> silent exit 0 (a hook never breaks a session).

Coverage is per file: a receipt covers a changed file when its last reviewed diff recorded the same blob sha for that path,
so a change reviewed before commit stays covered after `git add`/commit. Commands are covered by an L2 receipt that lists
the same normalised command (or a prefix ending in '*'). Rules and how to extend them: references/triggers.md.

Site-specific rules (production hosts, deploy CLIs, production mounts, network drives, extra path globs) come from a
JSON config: --config, else env CHANGE_REVIEW_CONFIG, else <repo or cwd>/.review/gate.json; generic defaults otherwise.
Receipts are searched in --receipts dirs, config receipt_dirs, $CHANGE_REVIEW_STATE_DIR/receipts, <repo>/.review/receipts
and <repo>/receipts.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_receipt as rr  # noqa: E402

RANK = {'L0': 0, 'L1': 1, 'L2': 2}
NAME = {v: k for k, v in RANK.items()}
RECEIPT_DIRS: list = []   # extra receipt dirs from the config (receipt_dirs)
CONFIG_ENV = 'CHANGE_REVIEW_CONFIG'
NEVER = r'(?!x)x'
DEFAULT_CONFIG = {
    'prod_hosts': [r'prod[\w.-]*'],   # ssh/scp/rsync host names (regex fragments) that are production
    'deploy_commands': [],            # command prefixes that deploy, e.g. "sitectl deploy" or "deploy.py --env prod"
    'prod_mounts': [],                # path prefixes of mounted production storage, e.g. "/mnt/prod" or "Y:\\"
    'network_drives': [],             # drive letters of network mounts where git must never run, e.g. ["N"]
    'l1_repos': [],                   # repo folder names where any other code file is L1 (other agents run it)
    'l2_paths': [],                   # extra L2 globs (repo-relative)
    'l1_paths': [],                   # extra L1 globs
    'receipt_dirs': [],               # extra receipt directories
}

# ---------------------------------------------------------------- path rules
# Globs match the repo-relative path with '/', case-insensitive; '*' also crosses '/'. Order of evaluation:
# agent rules / deliverables (L2) -> docs (L0) -> security, deploy config, data deletes (L2) -> shared code (L1) -> repo default.
L2_FIRST = [
    ('agent rules', ['agents.md', '*/agents.md', 'claude.md', '*/claude.md', '.claude/settings*.json',
                     '*/.claude/settings*.json', '.claude/hooks/*', '*/.claude/hooks/*', '.claude/agents/*',
                     '*/.claude/agents/*', '.codex/*', '*/.codex/*']),
    ('client deliverable', ['deliver*/*', '*/deliver*/*']),
]
L0_DOCS = ['*.md', '*.txt', '*.rst', 'docs/*', '*/docs/*', 'notes/*', '*/notes/*', 'plans/*', '*/plans/*',
           'receipts/*', '*/receipts/*', '*.log']
L0_EXCEPT = ['*skill.md', 'skills/*/references/*', '*/skills/*/references/*']          # skill instructions are code for agents
SECURITY_RE = re.compile(r'(^|[/_.-])(auth|oauth|secrets?|credentials?|passwords?|tokens?|security|permissions?|'
                         r'firewall|acl)([/_.-]|$)|\.(pem|key|pfx)$', re.I)
TEST_FIXTURES = ['tests/*', '*/tests/*', 'test_*', '*/test_*', '*/fixtures/*', '*/skill_evals/*']  # names only
L2_DEPLOY = ['*deploy*.ps1', '*deploy*.sh', '*deploy*.py', '*deploy*.yml', '*deploy*.yaml', '*deploy*.json',
             '*deploy*.toml', '.github/workflows/*', '*/.github/workflows/*', '*nginx*.conf', '*.service',
             '*docker-compose*', '*dockerfile*']
DATA_EXT = ('.json', '.jsonl', '.csv', '.db', '.sqlite', '.sqlite3', '.parquet', '.yaml', '.yml', '.xlsx')
L1_PATHS = [
    ('shared tools', ['tools/*', '*/tools/*']),
    ('agent config/skills', ['agents/*', '*/agents/*', 'skills/*', '*/skills/*', '.claude/*', '*/.claude/*']),
    ('pipeline scripts', ['scripts/*', '*/scripts/*']),
    ('shared libs', ['lib/*', '*/lib/*', 'shared/*', '*/shared/*', 'common/*', '*/common/*']),
]
L1_REPOS: set = set()   # from config l1_repos
L2_EXTRA: list = []     # from config l2_paths
L1_EXTRA: list = []     # from config l1_paths

# ---------------------------------------------------------------- command rules (rebuilt by configure())
PROD_HOSTS = NEVER
DEPLOY_RES: list = []
DEPLOY_CMDS: list = []   # token lists, first token normalised like an executable name
PROD_MOUNTS: list = []   # lower-case prefixes with '/'
DATA_OP_RE = re.compile(r'Remove-Item\b[^|;&\n]*-Recurse|\brm\s+-[a-z]*r[a-z]*\b|\brmdir\s+/s|\bdel\s+/s|'
                        r'\bMove-Item\b|\brobocopy\b[^|;&\n]*/(MOV|MOVE|MIR|PURGE)\b|\[IO\.Directory\]::Move|'
                        r'\bgit\s+push\b[^|;&\n]*(--force|\s-f\b)', re.I)
COMMIT_RE = re.compile(r'(^|[;&|(]\s*|\s)git(\s+-C\s+("[^"]+"|\'[^\']+\'|\S+))?(\s+-c\s+\S+)*\s+commit(?![\w-])', re.I)


def _norm(path: str) -> str:
    p = path.replace('\\', '/')
    while p.startswith('./'):
        p = p[2:]
    return p


def _match(path: str, patterns) -> bool:
    p = _norm(path).lower()
    return any(fnmatch.fnmatchcase(p, pat.lower()) for pat in patterns)


def classify_path(path: str, blob: str = '', repo_name: str = '') -> tuple[int, str]:
    p = _norm(path)
    for reason, pats in [*L2_FIRST, ('configured L2 path', L2_EXTRA)]:
        if _match(p, pats):
            return 2, reason
    if _match(p, L0_DOCS) and not _match(p, L0_EXCEPT):
        return 0, 'docs/notes'
    if SECURITY_RE.search(p) and not _match(p, TEST_FIXTURES):
        return 2, 'security/auth'
    if _match(p, L2_DEPLOY):
        return 2, 'deploy config'
    if blob == 'deleted' and p.lower().endswith(DATA_EXT):
        return 2, 'data file deleted'
    for reason, pats in [*L1_PATHS, ('configured L1 path', L1_EXTRA)]:
        if _match(p, pats):
            return 1, reason
    if repo_name.lower() in L1_REPOS:
        return 1, f'{repo_name} code'
    return 0, 'project-local'


QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')

# ---------------------------------------------------------------- command analysis
# The command line is split shell-style into simple commands (; && || | & ( ) { } newlines) and each one is judged by
# its executable, so quoted arguments (commit messages, --grep patterns) are data. Scripts of ssh, pwsh -Command,
# bash -c, cmd /c, wsl and iex are analysed recursively. Shell keywords (if/then/do/...) are skipped, a cd inside
# ( ... ) does not leak out (bash subshell), and $( ... ) inside single quotes is literal. Unparsable input falls back
# to the regexes above (raw text, conservative). The result is an ordered event list: commit/stage/unpredictable
# (git), deploy, data-op.
PUNCT = ';&|()<>{}'
SEP_CHARS = set(';&|(){}')
LIT_DOLLAR = ''   # a $ that was single-quoted at the current shell layer (see _flatten)
NETWORK_RE = re.compile(NEVER)   # network-drive paths from config network_drives: the gate never runs git over them
GIT_VALUE_OPTS = {'-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env', '--super-prefix'}
GIT_STAGE = {'add', 'stage', 'rm', 'mv', 'apply', 'update-index', 'restore', 'checkout'}
GIT_UNPREDICTABLE = {'reset', 'read-tree', 'merge', 'cherry-pick', 'revert', 'am', 'stash', 'pull', 'rebase', 'switch'}
COMMIT_VALUE_OPTS = {'-m', '-F', '-C', '-c', '-t', '--author', '--date', '--file', '--message', '--reuse-message',
                     '--reedit-message', '--fixup', '--squash', '--cleanup', '--template', '--trailer'}
SSH_VALUE_FLAGS = set('BbcDEeFIiJLlmOoPpQRSWw')
PWSH_VALUE_OPTS = {'-executionpolicy', '-ep', '-ex', '-windowstyle', '-w', '-workingdirectory', '-wd', '-version', '-v',
                   '-configurationname', '-inputformat', '-if', '-outputformat', '-of', '-o', '-settingsfile',
                   '-psconsolefile', '-custompipename'}
WRAPPERS = {'sudo', 'env', 'nohup', 'time', 'command', 'exec', 'xargs', 'call'}
SHELLS = {'pwsh', 'powershell', 'bash', 'sh', 'zsh', 'dash', 'wsl', 'cmd', 'invoke-expression', 'iex',
          'invoke-command', 'icm', 'python', 'python3', 'py', 'node', '.', 'source'}
PROD_HOST_RE = re.compile(NEVER)   # rebuilt by configure()
PROD_DEST_RE = re.compile(NEVER)
REMOTE_ACTION_RE = re.compile(r'\b(git\s+(pull|reset|checkout|merge)|systemctl\s+(restart|reload|start|stop)|'
                              r'docker(-compose|\s+compose)?\s+(up|restart|pull|rm)|pm2\s+(restart|reload|start|delete)|'
                              r'nginx\s+-s|npm\s+(ci|install|run\s+build)|deploy)|(^|[\s;&|])(rm|mv|cp)\s', re.I)
DEPLOY_SCRIPT_RE = re.compile(r'(?<![A-Za-z0-9_])deploy[\w.-]*\.(ps1|sh|py)$', re.I)
PROD_WORD_RE = re.compile(r'\b(prod\w*|live)\b', re.I)
MOUNT_WRITERS = {'copy-item', 'move-item', 'remove-item', 'set-content', 'add-content', 'out-file', 'robocopy', 'cp', 'mv',
             'rm', 'copy', 'move', 'del'}
IO_MOVE_RE = re.compile(r'\[(system\.)?io\.directory\]::move', re.I)
KEYWORD_PREFIX = {'if', 'then', 'else', 'elif', 'do', 'while', 'until', '!', 'elseif'}   # the command follows them
KEYWORD_SKIP = {'fi', 'done', 'esac', 'for', 'foreach', 'case', 'select', 'function', 'in'}   # no command here
MAX_DEPTH = 4
REMOTE_ACTIONS = (r'git\s+(pull|reset|checkout|merge)|systemctl\s+(restart|reload|start|stop)|'
                  r'docker(-compose|\s+compose)?\s+(up|restart|pull|rm)|pm2\s+(restart|reload|start|delete)|nginx\s+-s|'
                  r'npm\s+(ci|install|run\s+build)|(^|[\s"\'])(rm|mv|cp)\s|deploy')


def _alt(fragments) -> str:
    return '(' + '|'.join(f'(?:{f})' for f in fragments) + ')' if fragments else NEVER


def load_config(path: str | None = None, base: str | None = None) -> dict:
    """Config dict: explicit path, env CHANGE_REVIEW_CONFIG, else <base>/.review/gate.json; missing -> defaults."""
    cand = path or os.environ.get(CONFIG_ENV) or (os.path.join(base, '.review', 'gate.json') if base else '')
    cfg = dict(DEFAULT_CONFIG)
    if cand and os.path.isfile(cand):
        with open(cand, encoding='utf-8') as fh:
            data = json.load(fh)
        cfg.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
    return cfg


def configure(cfg: dict | None = None) -> None:
    """Rebuild the site-specific rules (production hosts, deploy CLIs, mounts, network drives, extra globs)."""
    global PROD_HOSTS, DEPLOY_RES, DEPLOY_CMDS, PROD_MOUNTS, NETWORK_RE, PROD_HOST_RE, PROD_DEST_RE
    global L1_REPOS, L2_EXTRA, L1_EXTRA, RECEIPT_DIRS
    c = dict(DEFAULT_CONFIG, **(cfg or {}))
    PROD_HOSTS = _alt(c['prod_hosts'])
    PROD_HOST_RE = re.compile(r'^(\S+@)?' + PROD_HOSTS + r'$', re.I)
    PROD_DEST_RE = re.compile(r'^(\S+@)?' + PROD_HOSTS + r':', re.I)
    DEPLOY_CMDS = []
    for prefix in c['deploy_commands']:
        toks = str(prefix).lower().split()
        if toks:
            DEPLOY_CMDS.append([_exe(toks[0]), *toks[1:]])
    PROD_MOUNTS = [str(m).replace('\\', '/').lower() for m in c['prod_mounts'] if str(m).strip()]
    letters = ''.join(sorted({str(d).strip().rstrip(':').upper() for d in c['network_drives'] if str(d).strip()}))
    NETWORK_RE = re.compile(f'[{letters}{letters.lower()}]:' if letters else NEVER)
    L1_REPOS = {str(r).lower() for r in c['l1_repos']}
    L2_EXTRA, L1_EXTRA = list(c['l2_paths']), list(c['l1_paths'])
    RECEIPT_DIRS = [Path(d) for d in c['receipt_dirs']]
    DEPLOY_RES = [
        re.compile(r'\b(scp|rsync|sftp)\b[^|;&\n]*\s(\S+@)?' + PROD_HOSTS + r':\S*\s*($|[|;&])', re.I),   # upload to prod
        re.compile(r'\bssh\s+(\S+\s+)*?(\S+@)?' + PROD_HOSTS + r'\b[^\n]*\b(' + REMOTE_ACTIONS + ')', re.I),
        re.compile(r'\bdeploy[\w.-]*\.(ps1|sh|py)\b[^\n]*\b(prod\w*|live)\b', re.I),
    ]
    for toks in DEPLOY_CMDS:
        DEPLOY_RES.append(re.compile(r'(^|[\s;&|(/\\])' + r'\s+'.join(re.escape(t) for t in toks) + r'(\.\w+)?\b', re.I))
    if PROD_MOUNTS:
        mounts = '|'.join(re.escape(m).replace('/', r'[\\/]') for m in PROD_MOUNTS)
        DEPLOY_RES.append(re.compile(r'\b(Copy-Item|Move-Item|Remove-Item|Set-Content|Out-File|robocopy|cp|mv|rm)\b'
                                     r'[^\n]*(' + mounts + ')', re.I))


def _is_deploy_cmd(argv) -> bool:
    if not argv or not DEPLOY_CMDS:
        return False
    toks = [re.sub(r'\.(py|ps1|sh|js|mjs)$', '', _exe(argv[0])), *(a.lower() for a in argv[1:])]   # CLI or its script
    return any(toks[:len(p)] == p for p in DEPLOY_CMDS)


def _on_prod_mount(arg: str) -> bool:
    a = re.sub(r'^-\w+:', '', arg).replace('\\', '/').lower()
    return any(a.startswith(m) for m in PROD_MOUNTS)


def _strip_heredocs(cmd: str) -> str:
    """Drop heredoc bodies and PowerShell here-strings: their text is data (commit messages), not commands."""
    cmd = re.sub(r'@([\'"])\n.*?\n\1@', '"q"', cmd, flags=re.S)
    lines, out, i = cmd.split('\n'), [], 0
    while i < len(lines):
        out.append(lines[i])
        end = i
        for m in re.finditer(r'<<-?\s*([\'"]?)([A-Za-z_]\w*)\1', lines[i]):
            stop = next((k for k in range(end + 1, len(lines)) if lines[k].strip() == m.group(2)), None)
            end = stop if stop is not None else end   # no closing line -> not a heredoc, keep the text
        i = end + 1
    return '\n'.join(out)


def _flatten(cmd: str) -> str:
    """Unquoted newlines become ';', line continuations (\\ or ` before a newline) become spaces; $( inside single
    quotes is literal at this shell layer, so its $ becomes LIT_DOLLAR (never a substitution here); nested() restores
    it, because bash -c '...' hands the text to an inner shell that does expand it."""
    out, quote, i = [], '', 0
    while i < len(cmd):
        ch = cmd[i]
        if quote == "'" and cmd[i:i + 2] == '$(':
            out.append(LIT_DOLLAR + '(')
            i += 2
            continue
        if quote:
            quote = '' if ch == quote else quote
        elif ch in '"\'':
            quote = ch
        elif ch in '\\`' and cmd[i + 1:i + 2] == '\n':
            out.append(' ')
            i += 2
            continue
        elif ch == '\n':
            out.append(' ; ')
            i += 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def _simple_commands(cmd: str) -> list:
    """argv lists of the simple commands plus '(' / ')' markers for subshell scope; redirections (> f, 2>&1, <<EOF)
    dropped. Raises ValueError if unparsable."""
    lx = shlex.shlex(_flatten(_strip_heredocs(cmd.replace('\r\n', '\n'))), posix=True, punctuation_chars=PUNCT)
    lx.whitespace_split, lx.escape, lx.commenters = True, '', ''
    cmds, cur, skip = [], [], False
    for tok in lx:
        if skip:
            skip = False
        elif tok and set(tok) <= set(PUNCT) and set(tok) & set('()'):   # ( ) $( <( and joined forms like )&&
            if cur:
                cmds.append(cur)
            cur = []
            cmds.extend(ch for ch in tok if ch in '()')
        elif tok and set(tok) <= SEP_CHARS:
            if cur:
                cmds.append(cur)
            cur = []
        elif tok and set(tok) <= set('<>&'):
            if cur and cur[-1].isdigit():
                cur.pop()
            skip = True
        else:
            cur.append(tok)
    if cur:
        cmds.append(cur)
    return cmds


def _exe(tok: str) -> str:
    return re.sub(r'\.(exe|cmd|bat)$', '', tok.replace('\\', '/').rsplit('/', 1)[-1].lower())


def _join(base, path):
    return None if base is None else os.path.normpath(os.path.join(base, path))   # join keeps an absolute path


def _commit_takes_worktree(args) -> bool:
    """`commit -a/-i/-o`, --pathspec-from-file or any pathspec: worktree content ships, not only the index."""
    skip = False
    for k, tok in enumerate(args):
        if skip:
            skip = False
        elif tok == '--':
            return k + 1 < len(args)
        elif tok in COMMIT_VALUE_OPTS:
            skip = True
        elif tok in ('--all', '--include', '--only') or tok.startswith('--pathspec-from-file'):
            return True
        elif tok.startswith('--'):
            continue   # other --long or --long=value
        elif tok.startswith('-') and len(tok) > 1:
            for j, ch in enumerate(tok[1:]):
                if ch in 'aio':
                    return True
                if ch in 'mFCct':   # value option: attached (-mfix) or the next token (-am "msg")
                    skip = j == len(tok) - 2
                    break
        else:
            return True
    return False


def _git(args, cwd, events):
    # global options before the subcommand, git semantics: each -C moves the cwd (relative to the previous one);
    # --git-dir/--work-tree are relative to that cwd and do not stack; the work tree is what gets checked
    c, opts, i = cwd, {}, 0
    while i < len(args):
        a = args[i]
        if a in GIT_VALUE_OPTS:
            if i + 1 < len(args):
                if a == '-C':
                    c = _join(c, args[i + 1])
                elif a in ('--work-tree', '--git-dir'):
                    opts[a] = args[i + 1]
            i += 2
        elif a.startswith(('--work-tree=', '--git-dir=')):
            k, v = a.split('=', 1)
            opts[k] = v
            i += 1
        elif a.startswith('-'):
            i += 1
        else:
            break
    if '--work-tree' in opts:
        d = _join(c, opts['--work-tree'])
    elif '--git-dir' in opts:
        d = _join(c, opts['--git-dir'])
        if d is not None and os.path.basename(d).lower() == '.git':
            d = os.path.dirname(d)
    else:
        d = c
    if i >= len(args):
        return
    sub, rest = args[i].lower(), args[i + 1:]
    if sub == 'commit':
        events.append({'kind': 'commit', 'dir': d, 'worktree': _commit_takes_worktree(rest)})
    elif sub in GIT_STAGE:
        events.append({'kind': 'stage', 'dir': d})
    elif sub in GIT_UNPREDICTABLE:
        events.append({'kind': 'unpredictable', 'dir': d})
    elif sub == 'push' and any(r == '-f' or r.startswith(('--force', '+')) or re.fullmatch(r'-[a-zA-Z]*f[a-zA-Z]*', r)
                               for r in rest):
        events.append({'kind': 'data-op', 'dir': d})


def _script(path, args, cwd, events):
    if _is_deploy_cmd([path, *args]):
        events.append({'kind': 'deploy', 'dir': cwd})
    elif DEPLOY_SCRIPT_RE.search(path) and PROD_WORD_RE.search(' '.join(args)):
        events.append({'kind': 'deploy', 'dir': cwd})


def _ssh(args, cwd, events, depth):
    i = 0
    while i < len(args) and args[i].startswith('-'):
        i += 2 if len(args[i]) == 2 and args[i][1] in SSH_VALUE_FLAGS else 1
    script = ' '.join(args[i + 1:])
    if i >= len(args) or not script:
        return
    if PROD_HOST_RE.match(args[i]) and REMOTE_ACTION_RE.search(script):
        events.append({'kind': 'deploy', 'dir': cwd})
    if depth < MAX_DEPTH:   # remote git state is not ours to gate; deploys and data ops there count
        events.extend(e for e in _analyze(script.replace(LIT_DOLLAR, '$'), None, depth + 1) if e['kind'] in ('deploy', 'data-op'))


def _shell(name, args, cwd, events, depth):
    """Nested scripts of shells and interpreters, or the script file they run."""
    if depth >= MAX_DEPTH:
        return
    low = [a.lower() for a in args]

    def nested(script):
        events.extend(_analyze(script.replace(LIT_DOLLAR, '$'), cwd, depth + 1))

    if name == 'cmd':
        k = next((k for k, a in enumerate(low) if a in ('/c', '/k', '/r')), None)
        if k is not None:
            nested(' '.join(args[k + 1:]))
    elif name in ('invoke-expression', 'iex', 'invoke-command', 'icm'):
        nested(' '.join(a for a in args if not a.startswith('-')))
    elif name == 'wsl':
        k = 0
        while k < len(args) and args[k].startswith('-'):
            k += 2 if low[k] in ('-d', '--distribution', '-u', '--user', '--cd') else 1
        if k < len(args):
            _simple(args[k:], cwd, events, depth + 1)
    elif name in ('pwsh', 'powershell'):
        k = 0
        while k < len(args):
            a = low[k]
            if a in ('-c', '-command') or (len(a) > 3 and '-command'.startswith(a)):
                return nested(' '.join(args[k + 1:]))
            if a in ('-f', '-file'):
                return _script(args[k + 1] if k + 1 < len(args) else '', args[k + 2:], cwd, events)
            if a in ('-e', '-ec', '-encodedcommand'):
                return   # opaque
            if a.startswith('-'):
                k += 2 if a in PWSH_VALUE_OPTS else 1
                continue
            return _script(args[k], args[k + 1:], cwd, events) if a.endswith('.ps1') else nested(' '.join(args[k:]))
    elif name in ('bash', 'sh', 'zsh', 'dash'):
        k = 0
        while k < len(args) and args[k].startswith(('-', '+')):
            if args[k] in ('-o', '-O', '+o', '+O'):
                k += 2
                continue
            if not args[k].startswith('--') and 'c' in args[k][1:]:
                return nested(args[k + 1] if k + 1 < len(args) else '')
            k += 1
        if k < len(args):
            _script(args[k], args[k + 1:], cwd, events)
    else:   # python, node, '.', source
        k = 0
        while k < len(args) and args[k].startswith('-'):
            if args[k] in ('-c', '-m', '-e', '--eval'):
                return   # inline code or a module
            k += 2 if args[k] in ('-X', '-W', '-r', '--require') else 1
        if k < len(args):
            _script(args[k], args[k + 1:], cwd, events)


def _data_op(name, args) -> bool:
    low = [a.lower() for a in args]
    if name in ('remove-item', 'ri'):
        return any(a.startswith('-r') for a in low)   # -Recurse or a prefix of it
    if name in ('rm', 'del', 'erase', 'rd', 'rmdir'):
        return any(a in ('/s', '--recursive') or a.startswith('-rec') or re.fullmatch(r'-(?=[a-z]{1,4}$)[a-z]*r[a-z]*', a)
                   for a in low)
    if name in ('move-item', 'mi'):
        return True
    if name == 'robocopy':
        return any(a in ('/mov', '/move', '/mir', '/purge') for a in low)
    return False


def _simple(argv, cwd, events, depth):
    """Judge one simple command by its executable; returns the cwd for the next one (cd/Set-Location/pushd)."""
    if any(IO_MOVE_RE.search(t) and not re.search(r'\s', t) for t in argv):
        events.append({'kind': 'data-op', 'dir': cwd})
    if depth < MAX_DEPTH:   # "$(...)" inside double quotes or an assignment still runs
        for t in argv:
            for inner in _substitutions(t):
                events.extend(_analyze(inner, cwd, depth + 1))
    if argv and argv[0].lower() in KEYWORD_SKIP:
        return cwd
    while argv and (re.match(r'\w+=', argv[0]) or _exe(argv[0]) in WRAPPERS or argv[0].lower() in KEYWORD_PREFIX):
        keyword = argv[0].lower() in KEYWORD_PREFIX
        argv = argv[1:]
        while argv and argv[0].startswith('-') and not keyword:
            argv = argv[1:]
    if len(argv) > 2 and argv[0].startswith('$') and argv[1] == '=':   # PowerShell `$x = ...`
        argv = argv[2:]
    if not argv:
        return cwd
    name, args = _exe(argv[0]), argv[1:]
    if name in ('cd', 'set-location', 'sl', 'pushd', 'chdir'):
        dest = next((a for a in args if not a.startswith('-')), None)
        return _join(cwd, dest) if dest else cwd
    if _is_deploy_cmd(argv):   # configured deploy CLI, e.g. "sitectl deploy"
        events.append({'kind': 'deploy', 'dir': cwd})
    elif name == 'git':
        _git(args, cwd, events)
    elif name == 'ssh':
        _ssh(args, cwd, events, depth)
    elif name in ('scp', 'rsync', 'sftp'):
        tail = [a for a in args if not a.startswith('-')]
        if tail and PROD_DEST_RE.match(tail[-1]):   # upload to prod (download from it is not a deploy)
            events.append({'kind': 'deploy', 'dir': cwd})
    elif name in SHELLS:
        _shell(name, args, cwd, events, depth)
    elif DEPLOY_SCRIPT_RE.search(argv[0]):
        _script(argv[0], args, cwd, events)
    if PROD_MOUNTS and name in MOUNT_WRITERS and any(_on_prod_mount(a) for a in args):
        events.append({'kind': 'deploy', 'dir': cwd})
    if _data_op(name, args):
        events.append({'kind': 'data-op', 'dir': cwd})
    return cwd


def _substitutions(tok: str) -> list:
    """Bodies of $( ... ) in one token (balanced parentheses)."""
    out, i = [], tok.find('$(')
    while i != -1:
        level, j = 0, i + 1
        while j < len(tok):
            level += {'(': 1, ')': -1}.get(tok[j], 0)
            if level == 0:
                break
            j += 1
        out.append(tok[i + 2:j])
        i = tok.find('$(', j)
    return out


def _analyze(cmd: str, cwd, depth: int = 0) -> list:
    events, stack, scopes = [], [], []
    for argv in _simple_commands(cmd):
        if argv == '(':   # subshell / substitution: a cd inside does not leak out
            scopes.append((cwd, list(stack)))
            continue
        if argv == ')':
            if scopes:
                cwd, stack = scopes.pop()
            continue
        name = _exe(argv[0])
        if name in ('popd', 'pop-location'):
            cwd = stack.pop() if stack else cwd
            continue
        if name in ('pushd', 'push-location'):
            stack.append(cwd)
        cwd = _simple(argv if name != 'push-location' else ['pushd', *argv[1:]], cwd, events, depth)
    return events


def _legacy_events(cmd: str, cwd: str) -> list:
    """Unparsable command (unbalanced quotes...): raw-text regexes, commit treated as taking the worktree."""
    events = []
    if any(r.search(cmd) for r in DEPLOY_RES):
        events.append({'kind': 'deploy', 'dir': cwd})
    if DATA_OP_RE.search(cmd):
        events.append({'kind': 'data-op', 'dir': cwd})
    if COMMIT_RE.search(QUOTED_RE.sub('"q"', cmd)):
        events.append({'kind': 'commit', 'dir': _repo_for_command(cmd, cwd), 'worktree': True})
    return events


def analyze(cmd: str, cwd: str) -> list:
    if not cmd:
        return []
    try:
        return _analyze(cmd, cwd)
    except ValueError:
        return _legacy_events(cmd, cwd)


def command_kinds(cmd: str) -> set:
    """Every gated kind in a (possibly compound) command: deploy, data-op, commit."""
    return {e['kind'] for e in analyze(cmd, '.')} & {'deploy', 'data-op', 'commit'}


def classify_command(cmd: str) -> tuple[int, str, str]:
    """(level, reason, kind) with kind in deploy|data-op|commit|'' (the strongest one in a compound command)."""
    kinds = command_kinds(cmd)
    if 'deploy' in kinds:
        return 2, 'production deploy/write command', 'deploy'
    if 'data-op' in kinds:
        return 2, 'data move/delete command', 'data-op'
    if 'commit' in kinds:
        return 0, 'git commit', 'commit'
    return 0, '', ''


def project_floor(root: Path) -> tuple[int, str]:
    """`review_level: L1|L2` in project.yaml at the repo root or up to 3 parents. Advisory default; current task floors are supplied explicitly."""
    for d in [root, *list(root.parents)[:3]]:
        y = d / 'project.yaml'
        try:
            text = y.read_text(encoding='utf-8', errors='replace') if y.is_file() else ''
        except OSError:
            text = ''
        m = re.search(r'^\s*review_level\s*:\s*["\']?(L[012])\b', text, re.M)
        if m:
            return RANK[m.group(1)], f'{y}'
    return 0, ''


def classify(root: Path, files: dict, command: str = '', floor: str = '') -> dict:
    pf, pf_src = project_floor(root)
    card = RANK.get(floor or 'L0', 0)
    # Project defaults are advisory; a task floor is explicit (--floor) and always recorded.
    fl = card
    fl_src = "explicit task requirement" if card else ""
    cmd_lvl, cmd_why, kind = classify_command(command)
    per_file = {}
    for path, blob in files.items():
        lvl, why = classify_path(path, blob, root.name)
        if fl > lvl and why != 'docs/notes':
            lvl, why = fl, f'{why}; floor {NAME[fl]} from {fl_src}'
        if kind == 'deploy' and lvl < 2 and why != 'docs/notes':   # uncommitted code may ship with a deploy
            lvl, why = 2, f'{why}; dirty during deploy'
        per_file[path] = {'level': lvl, 'reason': why, 'blob': blob}
    level = max([v['level'] for v in per_file.values()] + [cmd_lvl])
    reasons = []
    if cmd_lvl:
        reasons.append(f'{NAME[cmd_lvl]} command: {cmd_why}')
    top = [f"{p} ({v['reason']})" for p, v in per_file.items() if v['level'] == level and level][:3]
    if top:
        reasons.append(f'{NAME[level]} paths: ' + '; '.join(top))
    return {'level': NAME[level], 'reasons': reasons, 'kind': kind, 'files': per_file,
            'project_default': {'level': NAME[pf], 'source': pf_src, 'advisory': True}}


def load_receipts(root: Path, extra_dirs=None) -> list[dict]:
    out, dirs = [], [*(Path(x) for x in (extra_dirs or [])), *RECEIPT_DIRS]
    if os.environ.get(rr.STATE_ENV):
        dirs.append(Path(os.environ[rr.STATE_ENV]) / 'receipts')
    if root:
        dirs += [root / '.review' / 'receipts', root / 'receipts']
    for d in dirs:
        if not d.is_dir():
            continue
        for f in d.glob('*.json'):
            try:
                rec = json.loads(f.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if isinstance(rec, dict) and rec.get('schema') == rr.SCHEMA and rec.get('status') == 'accepted' \
                    and rec.get('level') in rr.LEVELS and not rr.problems(rec):
                rec['_path'] = str(f)
                out.append(rec)
    return out


def _same_repo(rec: dict, root: Path) -> bool:
    for cand in (rec.get('repo', ''), (rec['passes'][-1].get('diff') or {}).get('repo', '')):
        try:
            if cand and Path(cand).resolve() == root:
                return True
        except OSError:
            pass
    return False


def _covers_command(rec: dict, cmd: str) -> bool:
    for c in rec.get('commands', []):
        if c == cmd or (c.endswith('*') and cmd.startswith(c[:-1])):
            return True
    return False


def command_id(cmd: str) -> str:
    """Stable non-reversible id of a command for messages and logs (raw text may contain secrets)."""
    return hashlib.sha256(cmd.encode('utf-8', 'replace')).hexdigest()[:10]


def _reviewed_revision(rec: dict, root: Path) -> bool:
    """A deploy receipt covers HEAD only if every file committed since the reviewed head is the reviewed content."""
    diff = rec['passes'][-1].get('diff') or {}
    head, reviewed = diff.get('head') or '', diff.get('files') or {}
    if not head:
        return False
    try:
        if rr.git(root, 'rev-parse', 'HEAD').decode().strip() == head:
            return True
        since = rr.changed_files(root, 'range', f'{head}..HEAD')
    except SystemExit:
        return False
    return all(reviewed.get(p) == blob for p, blob in since.items())


def check(root: Path, files: dict, command: str = '', floor: str = '', extra_dirs=None, receipts=None) -> dict:
    res = classify(root, files, command, floor)
    res.update(ok=True, uncovered=[], covered_by=[])
    if res['level'] == 'L0':
        return res
    if receipts is None:
        receipts = load_receipts(root, extra_dirs)
    uncovered, used = [], set()
    for path, v in res['files'].items():
        if not v['level']:
            continue
        hit = next((r for r in receipts if RANK[r['level']] >= v['level'] and _same_repo(r, root)
                    and ((r['passes'][-1].get('diff') or {}).get('files') or {}).get(path) == v['blob']), None)
        if hit:
            used.add(hit['_path'])
        else:
            uncovered.append(f"{path} [{NAME[v['level']]}]")
    if res['kind'] in ('deploy', 'data-op'):
        cmd = rr.norm_command(command)
        hit = next((r for r in receipts if r['level'] == 'L2' and _covers_command(r, cmd) and _same_repo(r, root)
                    and _reviewed_revision(r, root)), None)
        if hit:
            used.add(hit['_path'])
        else:   # never echo the command itself: it may carry tokens or passwords
            uncovered.append(f"command [L2]: {res['kind']} #{command_id(cmd)}")
    res.update(ok=not uncovered, uncovered=uncovered, covered_by=sorted(used))
    return res


def check_command(command: str, extra_dirs=None) -> dict:
    """Deploy/data command run where no repo can be checked (no git repo at the target or the hook cwd, or a network
    drive path): it still needs an accepted L2 receipt naming the command, and the repo that receipt reviewed (the absolute
    path its diff recorded, never the free-text --repo) must pass the full in-repo check for that command: HEAD at
    the reviewed content and no unreviewed dirty files. Only receipts bound to that repo by the same absolute path
    take part, so a free-text --repo like '.' (resolved against the process cwd) cannot lend another repo's review."""
    cmd = rr.norm_command(command)
    lvl, why, kind = classify_command(command)
    res = {'ok': True, 'level': NAME[lvl], 'reasons': [f'{NAME[lvl]} command: {why}; run outside a checkable git repo'],
           'kind': kind, 'files': {}, 'uncovered': [], 'covered_by': []}
    receipts = load_receipts(None, extra_dirs)

    def bound_root(r):
        repo = (r['passes'][-1].get('diff') or {}).get('repo') or ''
        if not os.path.isabs(repo) or NETWORK_RE.match(repo):
            return None
        try:
            return Path(repo).resolve()
        except OSError:
            return None

    for r in receipts:
        repo = bound_root(r)
        if r['level'] != 'L2' or not _covers_command(r, cmd) or repo is None:
            continue
        try:
            root = rr.repo_root(str(repo))
            if root != repo:
                continue   # a path inside some other repo is not the reviewed repo
            bound = [x for x in receipts if bound_root(x) == root]
            res_repo = check(root, rr.changed_files(root, 'worktree'), command, receipts=bound)
        except (SystemExit, OSError):
            continue
        if res_repo['ok']:
            res['covered_by'] = res_repo['covered_by']
            return res
    res.update(ok=False, uncovered=[f'command [L2]: {kind} #{command_id(cmd)}'])
    return res


def how_to(res: dict) -> str:
    if res.get('split'):
        return (f"change-review: {'; '.join(res['reasons'])}. Run that git command as its own call, then commit "
                f"(the gate then sees what ships).")
    more = ' ...' if len(res['uncovered']) > 5 else ''
    return (f"change-review {res['level']} needed ({'; '.join(res['reasons'])[:300]}); uncovered: "
            f"{', '.join(res['uncovered'][:5])}{more}. Fix: skill change-review -> review_receipt.py diff/new/add/finalize "
            f"(cross-model review, add --command for deploys), then retry.")


# ---------------------------------------------------------------- hook
def _command_from_hook(data: dict) -> str:
    ti = data.get('tool_input') or {}
    cmd = ti.get('command', ti.get('cmd', '')) if isinstance(ti, dict) else ''
    if isinstance(cmd, list):
        cmd = ' '.join(str(c) for c in cmd)
    return str(cmd or '')


def _repo_for_command(cmd: str, cwd: str) -> str:
    """Directory the gated git/deploy command acts in: leading cd (relative to the hook cwd), then git -C (relative to that)."""
    base = cwd
    m = re.match(r'\s*(?:cd|Set-Location|pushd)\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;&]+))\s*(?:;|&&)', cmd, re.I)
    if m:
        base = os.path.join(cwd, next(g for g in m.groups() if g))   # join keeps an absolute target as is
    m = re.search(r'\bgit\s+-C\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))', cmd)
    if m:
        return os.path.join(base, next(g for g in m.groups() if g))
    return base


def hook_decision(data: dict) -> dict | None:
    """None = not a gated command, or covered; else the first failing check. Every commit and deploy in a compound
    command is checked in its own repo (cd, git -C, --work-tree)."""
    cmd = _command_from_hook(data)
    cwd = data.get('cwd') or os.getcwd()
    staged_before = moved_before = False
    for e in analyze(cmd, cwd):
        kind = e['kind']
        staged_before |= kind == 'stage'
        moved_before |= kind == 'unpredictable'
        where = e['dir'] if e['dir'] is not None or kind != 'deploy' else cwd   # remote deploy: the local repo ships
        if kind not in ('commit', 'deploy') or where is None:
            continue
        root = None if NETWORK_RE.match(where) else _repo_root_or_cwd(where, cwd)   # no git over network drives
        if root is None:
            if kind == 'deploy':   # no repo to read: the command itself still needs an L2 receipt
                res = check_command(cmd)
                if not res['ok']:
                    return res
            continue   # commit outside any repo: nothing to gate
        try:
            if kind == 'deploy':
                res = check(root, rr.changed_files(root, 'worktree'), cmd)
                if not res['ok']:
                    return res
                continue
            # staged blobs always ship; worktree content too when the call stages first or names paths/-a
            # (conservative: may warn about unrelated dirty files)
            for mode in ['staged', 'worktree'] if e['worktree'] or staged_before or moved_before else ['staged']:
                res = check(root, rr.changed_files(root, mode))
                if not res['ok']:
                    return res
            if moved_before and (root.name.lower() in L1_REPOS or project_floor(root)[0]):
                return {'ok': False, 'split': True, 'level': 'L1', 'kind': 'commit', 'uncovered': [],
                        'reasons': ['git reset/merge/pull/stash/rebase/switch before commit in one call: '
                                    'what ships cannot be predicted']}
        except SystemExit:   # git refused: nothing to gate here
            continue
    return None


def _repo_root_or_cwd(where: str, cwd: str):
    """Repo of the resolved target; if that is not a repo (a path the analyser may have resolved wrongly), the repo
    of the hook cwd instead - conservative: a wrong guess warns, it never silently passes a repo commit."""
    for d in (where, cwd) if where != cwd else (where,):
        if d and not NETWORK_RE.match(d):
            try:
                return rr.repo_root(d)
            except (SystemExit, OSError):   # OSError: broken/unmounted volume -> no repo (deploys go to check_command)
                continue
    return None


def hook(mode: str, stdin=None) -> int:
    try:
        data = json.loads((stdin or sys.stdin).read() or '{}')
        configure(load_config(None, data.get('cwd') or os.getcwd()))
        res = hook_decision(data)
        if res is None:
            return 0
        msg = how_to(res)
        if mode == 'block':
            print(f'BLOCKED by change-review gate: {msg}', file=sys.stderr)
            return 2
        print(json.dumps({'systemMessage': f'change-review gate (warn): {msg}',
                          'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                                                 'additionalContext': f'change-review gate (warn mode, not blocking): {msg}'}},
                         ensure_ascii=False))
        return 0
    except BaseException:  # noqa: BLE001 - includes SystemExit from git/path refusals; a hook never breaks a session
        return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='change-review gate: classify a change L0/L1/L2 and check receipt coverage',
                                 epilog='env: CHANGE_REVIEW_CONFIG (gate JSON config), CHANGE_REVIEW_STATE_DIR '
                                        '(receipts root), CHANGE_REVIEW_GATE (hook mode warn|block)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('classify', 'check'):
        p = sub.add_parser(name)
        p.add_argument('--config', help='gate JSON config (default: env CHANGE_REVIEW_CONFIG or <repo>/.review/gate.json)')
        p.add_argument('--repo', required=name == 'classify',
                       help='repo that ships; check may omit it for a deploy/data command run outside any repo')
        p.add_argument('--command', default='', help='planned command (deploy, data move/delete)')
        p.add_argument('--mode', default='worktree', choices=['worktree', 'staged', 'tracked'])
        p.add_argument('--range', dest='rev_range', help='use a committed range instead, e.g. origin/main..HEAD')
        p.add_argument('--floor', default='', choices=['', 'L1', 'L2'], help='explicit review requirement applicable to this task (not a legacy project default)')
        if name == 'check':
            p.add_argument('--receipts', action='append', default=[], help='extra receipt directory')
    h = sub.add_parser('hook')
    h.add_argument('--mode', default=os.environ.get('CHANGE_REVIEW_GATE', 'warn'), choices=['warn', 'block'])
    args = ap.parse_args(argv)
    if args.cmd == 'hook':
        return hook(args.mode)
    try:
        configure(load_config(args.config, args.repo or os.getcwd()))
    except (OSError, ValueError) as e:
        print(json.dumps({'ok': False, 'error': f'config: {e}'}, ensure_ascii=False))
        return 1
    if not args.repo:
        if classify_command(args.command)[2] not in ('deploy', 'data-op'):
            print(json.dumps({'ok': False, 'error': 'check without --repo needs a deploy or data move/delete --command'}))
            return 1
        res = check_command(args.command, args.receipts)
        out = {k: res[k] for k in ('ok', 'level', 'reasons', 'uncovered', 'covered_by')}
        if not res['ok']:
            out['how_to'] = how_to(res)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if res['ok'] else 2
    try:
        root = rr.repo_root(args.repo)
        files = rr.changed_files(root, 'range', args.rev_range) if args.rev_range else rr.changed_files(root, args.mode)
    except SystemExit as e:
        print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False))
        return 1
    if args.cmd == 'classify':
        res = classify(root, files, args.command, args.floor)
        shown = list(res['files'].items())
        res['files'] = {p: f"{NAME[v['level']]} {v['reason']}" for p, v in shown[:40]}
        if len(shown) > 40:
            res['files_omitted'] = len(shown) - 40
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    res = check(root, files, args.command, args.floor, args.receipts)
    out = {k: res[k] for k in ('ok', 'level', 'reasons', 'uncovered', 'covered_by')}
    if not res['ok']:
        out['how_to'] = how_to(res)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if res['ok'] else 2


configure()   # generic defaults until a config is loaded

if __name__ == '__main__':
    sys.exit(main())
