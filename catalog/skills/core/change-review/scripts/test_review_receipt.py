"""Unit tests for review_receipt.py (stdlib unittest; run: python -X utf8 -B -m unittest test_review_receipt -v)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_receipt as rr  # noqa: E402

OK = {'verdict': 'accepted', 'evidence': ['ran: python -m unittest -> OK (5 tests)', 'read: tool.py:12 handles empty input'],
      'blocking': [], 'nonblocking': ['rename x']}
BAD = {'verdict': 'rejected', 'evidence': ['ran: python tool.py --dry-run -> exit 1, KeyError: id'],
       'blocking': ['tool.py:40 KeyError when id is missing'], 'nonblocking': []}
DIFF1 = {'sha256': 'a' * 64, 'patch': 'x.patch'}
DIFF2 = {'sha256': 'b' * 64, 'patch': 'y.patch'}


class VerdictTests(unittest.TestCase):
    def test_extract_from_fence_and_prose(self):
        text = 'Some notes {not json}\n```json\n' + json.dumps(OK) + '\n```\nbye'
        self.assertEqual(rr.extract_verdict(text)['verdict'], 'accepted')
        self.assertEqual(rr.extract_verdict('answer: ' + json.dumps(BAD))['verdict'], 'rejected')

    def test_extract_takes_last_and_fails_without(self):
        text = json.dumps(BAD) + '\n' + json.dumps(OK)
        self.assertEqual(rr.extract_verdict(text)['verdict'], 'accepted')
        with self.assertRaises(ValueError):
            rr.extract_verdict('no verdict here {"a": 1}')

    def test_verdict_rules(self):
        self.assertEqual(rr.verdict_problems(OK), [])
        self.assertEqual(rr.verdict_problems(BAD), [])
        only_author = dict(OK, evidence=['author-reported: tests passed'])
        self.assertTrue(any('obtained itself' in e for e in rr.verdict_problems(only_author)))
        self.assertTrue(rr.verdict_problems(dict(OK, blocking=['x'])))
        self.assertTrue(rr.verdict_problems(dict(BAD, blocking=[])))
        self.assertTrue(rr.verdict_problems(dict(OK, evidence=['looks fine'])))
        self.assertTrue(rr.verdict_problems(dict(OK, verdict='maybe')))


class ReceiptTests(unittest.TestCase):
    def mk(self, level='L1', author='claude:a'):
        return rr.new_receipt('s', level, 'task', author, '/w/repo', dict(DIFF1))

    def test_l1_accept_first_pass(self):
        rec = self.mk()
        rr.add_review(rec, 1, 'combined', 'codex:review', 'cli', OK, seconds=12)
        rr.finalize(rec, 'accepted')
        self.assertEqual(rr.problems(rec), [])
        self.assertEqual(rec['final_diff_sha256'], DIFF1['sha256'])

    def test_repair_then_accept(self):
        rec = self.mk()
        rr.add_review(rec, 1, 'combined', 'codex:review', 'cli', BAD)
        with self.assertRaises(SystemExit):
            rr.add_review(rec, 2, 'combined', 'codex:review', 'cli', OK)  # no repaired diff
        rr.add_review(rec, 2, 'combined', 'codex:review', 'cli', OK, diff=dict(DIFF2), repair='fixed KeyError')
        self.assertEqual(rec['passes'][0]['repair'], 'fixed KeyError')
        rr.finalize(rec, 'accepted')
        self.assertEqual(rr.problems(rec), [])
        self.assertEqual(rec['final_diff_sha256'], DIFF2['sha256'])

    def test_exhausted_bound(self):
        rec = self.mk()
        for n in (1, 2, 3):
            rr.add_review(rec, n, 'combined', 'codex:review', 'cli', BAD, diff=dict(DIFF1, sha256=str(n) * 64))
        rr.finalize(rec, 'exhausted')
        self.assertEqual(rr.problems(rec), [])
        rr.add_review(rec, 4, 'combined', 'codex:review', 'cli', BAD, diff=dict(DIFF2))
        self.assertTrue(any('exceed' in e for e in rr.problems(rec)))

    def test_cannot_accept_rejected_or_relax(self):
        rec = self.mk()
        rr.add_review(rec, 1, 'combined', 'codex:review', 'cli', BAD)
        rr.finalize(rec, 'accepted')
        self.assertTrue(any('not accepted' in e for e in rr.problems(rec)))
        rec2 = self.mk()
        rr.add_review(rec2, 1, 'combined', 'codex:review', 'cli', BAD)
        rr.finalize(rec2, 'exhausted')  # only 1 of 3 passes used
        self.assertTrue(any('exhausted' in e for e in rr.problems(rec2)))

    def test_l2_needs_both_roles(self):
        rec = self.mk('L2')
        rr.add_review(rec, 1, 'acceptance', 'codex:acc', 'cli', OK)
        self.assertEqual(rr.problems(rec), [])  # open pass while in review
        rr.finalize(rec, 'accepted')
        self.assertTrue(rr.problems(rec))
        rr.add_review(rec, 1, 'code', 'claude:change-reviewer', 'subagent', OK)
        rr.finalize(rec, 'accepted')
        self.assertEqual(rr.problems(rec), [])

    def test_independence(self):
        rec = self.mk()
        rr.add_review(rec, 1, 'combined', 'claude:a', 'subagent', OK)
        self.assertTrue(any('is the author' in e for e in rr.problems(rec)))
        rec = self.mk()
        rr.add_review(rec, 1, 'combined', 'claude:change-reviewer', 'subagent', OK)
        self.assertTrue(any('model family' in e for e in rr.problems(rec)))
        rec['same_family_reason'] = 'other-family CLI unavailable (timeout)'
        self.assertEqual(rr.problems(rec), [])

    def test_level_and_paths(self):
        with self.assertRaises(SystemExit):
            rr.new_receipt('s', 'L0', 't', 'a', 'r')
        with mock.patch.dict(os.environ, {rr.REFUSE_ENV: 'P,Q,H,unc'}):
            for bad in ('P:\\x', 'Q:\\data', 'H:\\', '\\\\server\\share'):
                with self.assertRaises(SystemExit):
                    rr.check_local_path(bad)
        with mock.patch.dict(os.environ, {rr.REFUSE_ENV: ''}):
            self.assertTrue(rr.check_local_path(tempfile.gettempdir()).is_absolute())   # default refuses nothing

    def test_state_dir(self):
        env = {k: v for k, v in os.environ.items() if k != rr.STATE_ENV}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(rr.state_dir('/w/repo'), Path('/w/repo') / '.review')
            self.assertEqual(rr.default_receipt_path('s', repo='/w/repo').parent, Path('/w/repo') / '.review' / 'receipts')
            self.assertEqual(rr.state_dir('/w/repo', '/w/state'), Path('/w/state'))
        with mock.patch.dict(os.environ, {rr.STATE_ENV: '/w/st'}):
            self.assertEqual(rr.state_dir('/w/repo'), Path('/w/st'))


@unittest.skipUnless(shutil.which('git'), 'git not installed')
class DiffTests(unittest.TestCase):
    def test_collect_diff_with_untracked(self):
        tmp = Path(tempfile.mkdtemp(prefix='crtest-'))
        try:
            run = lambda *a: subprocess.run(['git', '-C', str(tmp), *a], check=True, capture_output=True)
            run('init', '-q')
            run('config', 'user.email', 't@t')
            run('config', 'user.name', 't')
            (tmp / 'a.txt').write_text('one\n', encoding='utf-8')
            run('add', 'a.txt')
            run('commit', '-qm', 'init')
            (tmp / 'a.txt').write_text('one\ntwo\n', encoding='utf-8')
            (tmp / 'new.txt').write_text('fresh\n', encoding='utf-8')
            res = rr.collect_diff(str(tmp), str(tmp / '_out'), 'demo', paths=['a.txt', 'new.txt'])
            patch = Path(res['patch']).read_text(encoding='utf-8')
            self.assertIn('+two', patch)
            self.assertIn('+fresh', patch)
            self.assertEqual(res['untracked'], ['new.txt'])
            self.assertEqual(len(res['sha256']), 64)
            res2 = rr.collect_diff(str(tmp), str(tmp / '_out'), 'demo2', paths=['a.txt', 'new.txt'])
            self.assertEqual(res['sha256'], res2['sha256'])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class CliTests(unittest.TestCase):
    def test_cli_roundtrip(self):
        tmp = Path(tempfile.mkdtemp(prefix='crcli-'))
        try:
            diff = tmp / 'd.json'
            diff.write_text(json.dumps(DIFF1), encoding='utf-8')
            out = tmp / 'r.json'
            self.assertEqual(rr.main(['new', '--slug', 's', '--level', 'L1', '--task', 't', '--author', 'claude:a',
                                      '--repo', '/w/r', '--diff-json', str(diff), '--out', str(out)]), 0)
            ans = tmp / 'ans.txt'
            ans.write_text('Review done.\n```json\n' + json.dumps(OK) + '\n```', encoding='utf-8')
            self.assertEqual(rr.main(['add', str(out), '--pass', '1', '--role', 'combined', '--reviewer', 'codex:r',
                                      '--route', 'cli', '--answer', str(ans), '--seconds', '42']), 0)
            self.assertEqual(rr.main(['finalize', str(out), '--status', 'accepted']), 0)
            self.assertEqual(rr.main(['validate', str(out)]), 0)
            bad = tmp / 'bad.txt'
            bad.write_text(json.dumps(dict(OK, evidence=['fine'])), encoding='utf-8')
            self.assertEqual(rr.main(['add', str(out), '--pass', '1', '--role', 'code', '--reviewer', 'codex:r',
                                      '--route', 'cli', '--answer', str(bad)]), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
