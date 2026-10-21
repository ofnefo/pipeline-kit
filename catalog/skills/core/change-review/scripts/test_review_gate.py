"""Unit tests for review_gate.py (stdlib unittest; run: python -X utf8 -B -m unittest test_review_gate -v)."""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_gate as rg  # noqa: E402
import review_receipt as rr  # noqa: E402

OK = {'verdict': 'accepted', 'evidence': ['ran: python -m unittest -> OK', 'read: tools/x.py:1 fine'],
      'blocking': [], 'nonblocking': []}
# synthetic site config: production hosts, a deploy CLI, a production mount, a network drive, an L1 repo, an L2 glob
CFG = {'prod_hosts': ['prod-web', r'prod-db\d*'], 'deploy_commands': ['sitectl deploy'], 'prod_mounts': ['Y:\\', '/mnt/prod'],
       'network_drives': ['N'], 'l1_repos': ['workspace'], 'l2_paths': ['infra/payments*']}


class PathRuleTests(unittest.TestCase):
    def setUp(self):
        rg.configure(CFG)

    def tearDown(self):
        rg.configure()

    def lvl(self, path, blob='x', repo='proj'):
        return rg.classify_path(path, blob, repo)[0]

    def test_levels(self):
        cases = {
            'README.md': 0, 'docs/setup/guide.txt': 0, 'notes/2026.md': 0, 'src/app.py': 0,
            'tools/sync.py': 1, 'scripts/render.ps1': 1, 'lib/util.py': 1, 'agents/skills/x/SKILL.md': 1,
            'skills/x/references/loop.md': 1, 'tools/registry/registry.py': 1,
            '.claude/settings.json': 2, 'AGENTS.md': 2, 'sub/CLAUDE.md': 2,
            '.claude/hooks/session_start.py': 2, 'deliverables/final/cut.pdf': 2,
            'src/auth/login.py': 2, 'config/secrets.yaml': 2, 'deploy_site.ps1': 2, '.github/workflows/ci.yml': 2,
            'docs/auth.md': 0, 'src/author_name.py': 0, 'tests/test_auth.py': 0,
            'agents/skill_evals/cases/security-baseline.json': 1,
        }
        for path, want in cases.items():
            self.assertEqual(self.lvl(path), want, path)
        self.assertEqual(self.lvl('data/items.json', 'deleted'), 2)
        self.assertEqual(self.lvl('data/items.json', 'abc'), 0)
        self.assertEqual(self.lvl('panel/app.js', repo='workspace'), 1)   # l1_repos from the config
        self.assertEqual(self.lvl('panel/app.js', repo='other'), 0)
        self.assertEqual(self.lvl('infra/payments.cfg'), 2)                 # l2_paths from the config

    def test_commands(self):
        kind = lambda c: rg.classify_command(c)[2]
        self.assertEqual(kind('scp dist/app.js prod-web:/var/www/site/'), 'deploy')
        self.assertEqual(kind('ssh prod-web "cd /srv/site && git pull && systemctl restart site"'), 'deploy')
        self.assertEqual(kind('ssh prod-web "tail -n 50 /var/log/nginx/error.log"'), '')
        self.assertEqual(kind('scp prod-web:/var/log/app.log ./app.log'), '')
        self.assertEqual(kind('sitectl deploy shop'), 'deploy')
        self.assertEqual(kind('Copy-Item .\\dist\\* Y:\\srv\\site -Recurse'), 'deploy')
        self.assertEqual(kind('Remove-Item .\\data\\old -Recurse -Force'), 'data-op')
        self.assertEqual(kind('git push --force origin main'), 'data-op')
        self.assertEqual(kind('git -C "/w/x" commit -m "msg"'), 'commit')
        self.assertEqual(kind('git add a && git commit -am "x"'), 'commit')
        self.assertEqual(kind('git commit-tree abc'), '')
        self.assertEqual(kind('git status'), '')
        self.assertEqual(kind('git log --grep="sitectl deploy"'), '')                  # quoted data is not a deploy
        self.assertEqual(kind('echo "ssh prod-web systemctl restart x"'), '')
        self.assertEqual(kind('powershell -NoProfile -Command "git commit -am fix"'), 'commit')
        self.assertEqual(kind('bash -lc "cd /x && git commit -m y"'), 'commit')
        self.assertEqual(kind('cmd /c "sitectl deploy site"'), 'deploy')
        self.assertEqual(kind('python -X utf8 deploy_site.py --target prod'), 'deploy')
        self.assertEqual(kind('python deploy_site.py --target staging'), '')
        self.assertEqual(kind("git commit -F - <<'EOF'\nRemove-Item x -Recurse; sitectl deploy y\nEOF"), 'commit')
        self.assertEqual(kind('rm -rf build'), 'data-op')
        self.assertEqual(kind('git commit -m "x" 2>&1 | tail -n 3'), 'commit')
        self.assertEqual(kind('x="$(sitectl deploy site)"'), 'deploy')                 # substitution in quotes runs
        ev = rg.analyze('pushd /w/r && git add . && popd && git commit -m x', '/w/cwd')
        self.assertEqual([(e['kind'], e['dir']) for e in ev], [('stage', os.path.normpath('/w/r')), ('commit', '/w/cwd')])
        self.assertEqual(kind("git log --grep='$(sitectl deploy site)'"), '')         # single quotes: literal
        self.assertEqual(kind("bash -lc 'r=\"$(git commit -am fix)\"; echo \"$r\"'"), 'commit')   # inner shell expands
        self.assertEqual(kind("bash -lc 'r=\"$(sitectl deploy site)\"'"), 'deploy')
        self.assertEqual(kind("bash -lc \"git log --grep='$(sitectl deploy site)'\""), 'deploy')   # outer "..." expands it
        self.assertEqual(kind("bash -lc 'bash -c \"echo x\" && git log --grep=x'"), '')
        self.assertEqual(kind("ssh build-box 'r=\"$(sitectl deploy site)\"'"), 'deploy')   # the remote shell expands it
        self.assertEqual(kind("ssh build-box \"git log --grep='x'\""), '')
        self.assertEqual(kind('if git diff --quiet; then git commit -m fix; fi'), 'commit')
        self.assertEqual(kind('while read f; do git add $f; done && ! git commit -m x'), 'commit')
        self.assertEqual(kind('if ($?) { git commit -am x }'), 'commit')
        ev = rg.analyze('(cd .. && pwd) && echo $(cd /x) && git commit -am fix', '/w/a/b')
        self.assertEqual([(e['kind'], e['dir']) for e in ev], [('commit', '/w/a/b')])   # subshell cd does not leak
        ev = rg.analyze('git --git-dir=ws/.git --work-tree=ws commit -am fix', '/w/h')
        self.assertEqual(ev[0]['dir'], os.path.normpath('/w/h/ws'))
        ev = rg.analyze('git -C a --git-dir=.git commit -m x', '/w/h')
        self.assertEqual(ev[0]['dir'], os.path.normpath('/w/h/a'))
        self.assertEqual(kind('rsync -a dist/ deploy@prod-db2:/srv/app/'), 'deploy')
        self.assertEqual(kind('cp -r dist /mnt/prod/site'), 'deploy')            # configured production mount
        self.assertEqual(kind('python sitectl.py deploy shop'), 'deploy')        # configured CLI run as a script

    def test_generic_defaults(self):
        rg.configure()
        kind = lambda c: rg.classify_command(c)[2]
        self.assertEqual(kind('sitectl deploy shop'), '')                         # no deploy CLI configured
        self.assertEqual(kind('scp app.js prod-api:/srv/'), 'deploy')             # default: hosts named prod*
        self.assertEqual(kind('cp -r dist /mnt/prod/site'), '')
        self.assertEqual(rg.classify_path('panel/app.js', 'x', 'workspace')[0], 0)
        self.assertIsNone(rg.NETWORK_RE.match('N:\\x'))


@unittest.skipUnless(shutil.which('git'), 'git not installed')
class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='crgate-'))
        self.repo = self.tmp / 'repo'
        self.repo.mkdir()
        self.receipts = self.tmp / 'receipts-store'
        self.receipts.mkdir()
        cfg = self.tmp / 'gate.json'
        cfg.write_text(json.dumps(dict(CFG, receipt_dirs=[str(self.receipts)])), encoding='utf-8')
        env = {k: v for k, v in os.environ.items() if k != rr.STATE_ENV}
        self._env = mock.patch.dict(os.environ, dict(env, CHANGE_REVIEW_CONFIG=str(cfg)), clear=True)
        self._env.start()
        rg.configure(rg.load_config())
        self.git('init', '-q')
        self.git('config', 'user.email', 't@t')
        self.git('config', 'user.name', 't')
        self.git('config', 'core.autocrlf', 'false')
        self.write('README.md', 'hi\n')
        self.write('tools/x.py', 'print(1)\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'init')
        self.root = rr.repo_root(str(self.repo))

    def tearDown(self):
        self._env.stop()
        rg.configure()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *a):
        subprocess.run(['git', '-C', str(self.repo), *a], check=True, capture_output=True)

    def write(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8', newline='\n')

    def review(self, level='L1', roles=('combined',), commands=None, slug='t'):
        diff = rr.collect_diff(str(self.repo), str(self.tmp / 'diffs'), slug)
        rec = rr.new_receipt(slug, level, 'task', 'claude:writer', str(self.root), diff, commands=commands)
        for role in roles:
            rr.add_review(rec, 1, role, 'codex:reviewer', 'cli', OK)
        rr.finalize(rec, 'accepted')
        self.assertEqual(rr.problems(rec), [])
        rr.save(str(self.receipts / f'{slug}.json'), rec)
        return rec

    def check(self, mode='worktree', command='', floor=''):
        return rg.check(self.root, rr.changed_files(self.root, mode), command, floor)

    def test_docs_only_is_l0_pass(self):
        self.write('README.md', 'hi there\n')
        res = self.check()
        self.assertEqual((res['level'], res['ok']), ('L0', True))

    def test_l1_needs_receipt_and_survives_commit(self):
        self.write('tools/x.py', 'print(2)\n')
        self.write('tools/new.py', 'print(3)\n')
        res = self.check()
        self.assertEqual((res['level'], res['ok']), ('L1', False))
        self.assertEqual(len(res['uncovered']), 2)
        self.review()
        self.assertTrue(self.check()['ok'])
        self.git('add', '.')
        self.assertTrue(self.check('staged')['ok'])          # same blobs after staging
        self.write('tools/x.py', 'print(4)\n')              # change after review -> uncovered again
        res = self.check('tracked')
        self.assertFalse(res['ok'])
        self.assertEqual(res['uncovered'], ['tools/x.py [L1]'])

    def test_l1_receipt_does_not_cover_l2(self):
        self.write('src/auth/login.py', 'x = 1\n')
        self.review('L1')
        res = self.check()
        self.assertEqual((res['level'], res['ok']), ('L2', False))
        self.review('L2', roles=('acceptance', 'code'), slug='t2')
        self.assertTrue(self.check()['ok'])

    def test_project_and_card_floor(self):
        self.write('src/app.py', 'x = 1\n')
        self.assertEqual(self.check()['level'], 'L0')
        self.assertEqual(self.check(floor='L1')['level'], 'L1')
        (self.repo / 'project.yaml').write_text('name: demo\nreview_level: L2\n', encoding='utf-8')
        res = self.check()
        self.assertEqual(res['level'], 'L0')
        self.assertEqual(res['project_default']['level'], 'L2')
        self.assertTrue(res['project_default']['advisory'])
        self.assertEqual(self.check(floor='L2')['level'], 'L2')
        self.write('src/auth/login.py', 'auth = True\n')
        self.assertEqual(self.check(floor='L1')['level'], 'L2')

    def test_deploy_command_needs_l2_receipt_listing_it(self):
        cmd = 'sitectl deploy shop'
        res = self.check(command=cmd)
        self.assertEqual((res['level'], res['ok']), ('L2', False))
        self.assertTrue(any(u.startswith('command [L2]') for u in res['uncovered']))
        self.review('L2', roles=('acceptance', 'code'), commands=['sitectl deploy *'])
        self.assertTrue(self.check(command=cmd)['ok'])

    def run_hook(self, cmd, mode):
        out, err = io.StringIO(), io.StringIO()
        stdin = io.StringIO(json.dumps({'tool_name': 'Bash', 'cwd': str(self.repo), 'tool_input': {'command': cmd}}))
        with redirect_stdout(out), redirect_stderr(err):
            code = rg.hook(mode, stdin)
        return code, out.getvalue(), err.getvalue()

    def test_hook_warn_block_and_silence(self):
        self.write('tools/x.py', 'print(9)\n')
        self.git('add', '.')
        code, out, _ = self.run_hook('git commit -m "x"', 'warn')
        self.assertEqual(code, 0)
        self.assertIn('change-review L1 needed', json.loads(out)['systemMessage'])
        code, _, err = self.run_hook('git commit -m "x"', 'block')
        self.assertEqual(code, 2)
        self.assertIn('BLOCKED', err)
        self.assertEqual(self.run_hook('git status', 'block')[0], 0)
        self.review()
        self.assertEqual(self.run_hook('git commit -m "x"', 'block'), (0, '', ''))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(rg.hook('block', io.StringIO('not json')), 0)
        code, out, err = self.run_hook(f'git -C "{self.tmp / "nope"}" commit -m x', 'block')
        self.assertEqual(code, 0)   # not a repo -> falls back to the cwd repo, which is covered now

    def test_deploy_secret_never_echoed(self):
        code, out, err = self.run_hook('sitectl deploy shop --token SYNTHETIC_SECRET_42', 'warn')
        self.assertEqual(code, 0)
        self.assertNotIn('SYNTHETIC_SECRET_42', out + err)
        self.assertIn('command [L2]: deploy #', json.loads(out)['systemMessage'])

    def test_deploy_receipt_bound_to_repo_and_revision(self):
        cmd = 'sitectl deploy shop'
        self.write('tools/x.py', 'print(6)\n')
        self.review('L2', roles=('acceptance', 'code'), commands=['sitectl deploy *'])
        self.git('commit', '-qam', 'reviewed')
        self.assertTrue(self.check(command=cmd)['ok'])            # committed content == reviewed content
        self.write('tools/x.py', 'print(7)\n')
        self.git('commit', '-qam', 'unreviewed')
        self.assertFalse(self.check(command=cmd)['ok'])           # new commit after review -> receipt is stale
        other = self.tmp / 'other'
        other.mkdir()
        subprocess.run(['git', '-C', str(other), 'init', '-q'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(other), '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q',
                        '--allow-empty', '-m', 'i'], check=True, capture_output=True)
        res = rg.check(rr.repo_root(str(other)), {}, cmd)
        self.assertFalse(res['ok'])                               # receipt of another repo does not cover it

    def test_deploy_outside_any_repo_still_needs_l2_receipt(self):
        plain = self.tmp / 'plain'                                # not a git repo (tmp is outside any repo)
        plain.mkdir()

        def hook_at(cwd, cmd='sitectl deploy shop'):
            stdin = io.StringIO(json.dumps({'tool_name': 'Bash', 'cwd': str(cwd), 'tool_input': {'command': cmd}}))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return rg.hook('block', stdin)

        self.assertEqual(hook_at(plain), 2)
        self.assertEqual(hook_at('N:\\sites\\shop'), 2)          # network-drive cwd: no git there, the command is still gated
        self.assertEqual(hook_at(plain, 'git commit -m x'), 0)   # a commit outside any repo has nothing to gate
        self.write('tools/x.py', 'print(13)\n')
        self.review('L2', roles=('acceptance', 'code'), commands=['sitectl deploy *'])
        self.git('commit', '-qam', 'reviewed')
        self.assertEqual(hook_at(plain), 0)                       # receipt names the command, its repo is at reviewed HEAD
        with redirect_stdout(io.StringIO()):
            self.assertEqual(rg.main(['check', '--command', 'sitectl deploy shop']), 0)
        self.write('tools/x.py', 'print(15)\n')
        self.assertEqual(hook_at(plain), 2)                       # unreviewed dirty file in that repo
        self.git('checkout', '--', 'tools/x.py')
        clone = self.tmp / 'clone'                                # a clone still at the reviewed HEAD ...
        subprocess.run(['git', 'clone', '-q', str(self.repo), str(clone)], check=True, capture_output=True)
        self.write('tools/x.py', 'print(14)\n')
        self.git('commit', '-qam', 'unreviewed')
        self.assertEqual(hook_at(plain), 2)                       # ... while the reviewed repo moved on: stale
        rec = json.loads((self.receipts / 't.json').read_text(encoding='utf-8'))
        rec['repo'] = '.'                                         # free-text --repo must not rebind the receipt
        (self.receipts / 't.json').write_text(json.dumps(rec), encoding='utf-8')
        old = os.getcwd()
        os.chdir(clone)
        try:
            self.assertEqual(hook_at(plain), 2)
        finally:
            os.chdir(old)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(rg.main(['check', '--command', 'sitectl deploy shop']), 2)
            self.assertEqual(rg.main(['check', '--command', 'rm -rf /w/foo/bar']), 2)   # data op, no receipt
            self.assertEqual(rg.main(['check', '--command', 'git status']), 1)   # no --repo only for deploy/data

    def test_deploy_outside_repo_ignores_receipts_bound_elsewhere(self):
        plain = self.tmp / 'plain'
        plain.mkdir()
        self.write('tools/x.py', 'print(21)\n')
        self.review('L2', roles=('acceptance', 'code'), commands=['sitectl deploy *'], slug='b')
        self.git('commit', '-qam', 'reviewed b')
        self.write('tools/x.py', 'print(22)\n')
        self.git('commit', '-qam', 'unreviewed b')                # repo B is now stale for receipt b
        other = self.tmp / 'other'                                # repo A: a clone at B's current HEAD ...
        subprocess.run(['git', 'clone', '-q', str(self.repo), str(other)], check=True, capture_output=True)

        def git_a(*a):
            subprocess.run(['git', '-C', str(other), '-c', 'user.email=t@t', '-c', 'user.name=t', *a],
                           check=True, capture_output=True)

        (other / 'tools/x.py').write_text('print(23)\n', encoding='utf-8', newline='\n')
        diff = rr.collect_diff(str(other), str(self.tmp / 'diffs'), 'a')
        rec = rr.new_receipt('a', 'L2', 'task', 'claude:writer', '.', diff, commands=['sitectl deploy *'])   # repo '.'
        for role in ('acceptance', 'code'):
            rr.add_review(rec, 1, role, 'codex:reviewer', 'cli', OK)
        rr.finalize(rec, 'accepted')
        rr.save(str(self.receipts / 'a.json'), rec)
        git_a('commit', '-qam', 'reviewed a')
        (other / 'tools/x.py').write_text('print(24)\n', encoding='utf-8', newline='\n')
        git_a('commit', '-qam', 'unreviewed a')                   # ... and A is stale for receipt a too
        old = os.getcwd()
        os.chdir(self.repo)                                       # receipt a's '.' now resolves to B, at its reviewed head
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(rg.main(['check', '--command', 'sitectl deploy shop']), 2)
        finally:
            os.chdir(old)

    def test_hook_add_and_commit_in_one_call(self):
        self.write('tools/x.py', 'print(8)\n')                   # nothing staged when the hook runs
        code, out, _ = self.run_hook('git add -A && git commit -m "add x"', 'block')
        self.assertEqual(code, 2)
        self.assertEqual(self.run_hook('git commit -m "add feature"', 'block')[0], 0)   # message text is not `git add`

    def test_hook_pathspec_and_staged_survive_compound(self):
        self.write('tools/x.py', 'print(11)\n')                  # unstaged, named on the command line
        self.assertEqual(self.run_hook('git commit tools/x.py -m fix', 'block')[0], 2)
        self.assertEqual(self.run_hook('git commit -m "fix tools/x.py"', 'block')[0], 0)   # path only in the message
        self.git('add', 'tools/x.py')                             # unreviewed blob staged ...
        (self.repo / 'tools/x.py').write_text('print(1)\n', encoding='utf-8', newline='\n')   # ... worktree back to HEAD
        self.write('README.md', 'docs\n')
        self.assertEqual(self.run_hook('git add README.md; git commit -m fix', 'block')[0], 2)

    def test_quoted_message_does_not_mask_commit(self):
        self.write('tools/x.py', 'print(12)\n')
        self.git('add', '.')
        self.assertEqual(rg.classify_command('git commit -m "fix Move-Item handling"')[2], 'commit')
        self.assertEqual(self.run_hook('git commit -m "fix Move-Item handling"', 'block')[0], 2)
        self.assertEqual(self.run_hook('git commit -m "use -a flag"', 'block')[0], 2)   # staged L1 still checked
        self.assertEqual(rg.classify_command('git log --grep "git commit"')[2], '')

    def test_hook_skips_network_drives(self):
        stdin = io.StringIO(json.dumps({'tool_name': 'Bash', 'cwd': 'N:\\share\\x', 'tool_input': {'command': 'git commit -m x'}}))
        with mock.patch.object(rr, 'repo_root', side_effect=AssertionError('git over a network drive')):
            self.assertIsNone(rg.hook_decision(json.load(stdin)))

    def test_hook_relative_git_c(self):
        self.write('tools/x.py', 'print(10)\n')
        self.git('add', '.')
        out, err = io.StringIO(), io.StringIO()
        stdin = io.StringIO(json.dumps({'tool_name': 'Bash', 'cwd': str(self.tmp),
                                        'tool_input': {'command': 'git -C repo commit -m x'}}))
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(rg.hook('block', stdin), 2)   # resolved against payload cwd, not the hook process cwd

    def test_hook_per_invocation_git(self):
        self.write('tools/x.py', 'print(13)\n')                  # unstaged; global -c before `add` still stages
        self.assertEqual(self.run_hook('git -c core.quotepath=off add tools/x.py && git commit -m x', 'block')[0], 2)
        other = self.tmp / 'clean'
        other.mkdir()
        subprocess.run(['git', '-C', str(other), 'init', '-q'], check=True, capture_output=True)
        self.git('add', '.')                                      # staged L1 in repo, nothing in clean
        self.assertEqual(self.run_hook(f'git -C "{other}" status && git -C "{self.repo}" commit -am fix', 'block')[0], 2)
        self.assertEqual(self.run_hook(f'git -C "{self.repo}" status && git -C "{other}" commit -m fix', 'block')[0], 0)
        self.assertEqual(self.run_hook('powershell -NoProfile -Command "git commit -am fix"', 'block')[0], 2)

    def test_hook_heredoc_message_and_unpredictable_chain(self):
        self.assertEqual(self.run_hook("git commit -F - <<'EOF'\ngit add -A\nEOF", 'block')[0], 0)   # nothing staged
        self.assertEqual(self.run_hook('git stash && git commit -m x', 'block')[0], 0)   # repo floor L0: no split
        with mock.patch.object(rg, 'project_floor', return_value=(1, 'card')):
            code, _, err = self.run_hook('git stash pop && git commit -m x', 'block')
        self.assertEqual(code, 2)
        self.assertIn('as its own call', err)

    def test_hook_keywords_subshell_and_git_dir(self):
        self.write('tools/x.py', 'print(14)\n')
        self.git('add', '.')
        self.assertEqual(self.run_hook('if git diff --quiet; then git commit -m fix; fi', 'block')[0], 2)
        self.assertEqual(self.run_hook('(cd .. && pwd) && git commit -am fix', 'block')[0], 2)
        out, err = io.StringIO(), io.StringIO()
        stdin = io.StringIO(json.dumps({'tool_name': 'Bash', 'cwd': str(self.tmp), 'tool_input': {
            'command': 'git --git-dir=repo/.git --work-tree=repo commit -am fix'}}))
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(rg.hook('block', stdin), 2)
        self.assertEqual(self.run_hook(f'git -C "{self.tmp / "nope"}" commit -m x', 'block')[0], 2)   # cwd repo

    def test_cli_exit_codes(self):
        self.write('tools/x.py', 'print(5)\n')
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rg.main(['check', '--repo', str(self.repo)]), 2)
        self.assertIn('how_to', json.loads(out.getvalue()))
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rg.main(['classify', '--repo', str(self.repo)]), 0)
        self.assertEqual(json.loads(out.getvalue())['level'], 'L1')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(rg.main(['check', '--repo', str(self.tmp)]), 1)   # not a git repo


if __name__ == '__main__':
    unittest.main()
