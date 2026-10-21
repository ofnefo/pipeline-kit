import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_skills', ROOT / 'tools/setup_skills.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class SetupSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pipeline-kit-setup-')
        self.project = Path(self.temp.name).resolve() / 'project with spaces'

    def tearDown(self):
        self.temp.cleanup()

    def test_editing_plan_excludes_unselected_routes_and_writes_nothing(self):
        plan = installer.setup(self.project, 'codex', 'tasks', ['editing'])
        self.assertFalse(self.project.exists())
        self.assertEqual(plan['apps'], ['FFmpeg'])
        self.assertEqual(plan['models'], [])
        self.assertEqual({x['skill'] for x in plan['skills']},
                         {'pipeline-control', 'release-review', 'video-editing', 'audio-finishing'})

    def test_apply_both_clients_repeat_and_no_panel(self):
        first = installer.setup(self.project, 'both', 'none', ['graphics'], True)
        self.assertEqual(len(first['skills']), 2)
        self.assertTrue(all(x['status'] == 'installed' for x in first['skills']))
        for prefix in ('.agents', '.claude'):
            self.assertTrue((self.project / prefix / 'skills/graphic-production/SKILL.md').is_file())
            self.assertFalse((self.project / prefix / 'skills/pipeline-control').exists())
        second = installer.setup(self.project, 'both', 'none', ['graphics'], True)
        self.assertTrue(all(x['status'] == 'unchanged' for x in second['skills']))

    def test_conflict_prevents_all_copies_and_preserves_edits(self):
        conflict = self.project / '.claude/skills/graphic-production'
        conflict.mkdir(parents=True)
        (conflict / 'SKILL.md').write_text('Local rules', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'differs'):
            installer.setup(self.project, 'both', 'tasks', ['graphics'], True)
        self.assertFalse((self.project / '.agents').exists())
        self.assertEqual((conflict / 'SKILL.md').read_text('utf-8'), 'Local rules')

    def test_invalid_selection_and_kit_target_rejected(self):
        for target, profiles in ((ROOT, ['editing']), (self.project, ['typo']), (Path('relative'), [])):
            with self.assertRaises(ValueError):
                installer.setup(target, 'codex', 'tasks', profiles, True)
        self.assertFalse(self.project.exists())

    def test_cli_report_survives_ascii_pipe_with_unicode_project(self):
        project = self.project / 'Монтаж_日本'
        result = subprocess.run(
            [sys.executable, str(ROOT / 'tools/setup_skills.py'), '--project', str(project),
             '--client', 'codex', '--panel', 'none', '--profiles', 'graphics', '--apply'],
            env={**os.environ, 'PYTHONIOENCODING': 'ascii'}, capture_output=True,
            creationflags=0x08000000 if os.name == 'nt' else 0, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout.decode('ascii'))
        self.assertEqual(report['project'], str(project))
        self.assertEqual(report['skills'][0]['status'], 'installed')


if __name__ == '__main__':
    unittest.main()
