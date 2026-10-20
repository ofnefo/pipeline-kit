"""Release boundary checks use isolated fixtures, never private sources."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SPEC=importlib.util.spec_from_file_location('kit_release',Path(__file__).resolve().parents[1]/'tools/release.py')
release=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.owner=patch.object(release,'ROOT',self.root)
        self.owner.start()
        self.addCleanup(self.owner.stop)
        self.addCleanup(self.temp.cleanup)

    def fixture(self):
        (self.root/'README.md').write_text('Public fixture',encoding='utf-8')
        (self.root/'release-files.json').write_text(json.dumps({'files':['README.md','release-files.json']}),encoding='utf-8')

    def test_reject_escaping_member(self):
        (self.root/'release-files.json').write_text(json.dumps({'files':['../outside.txt']}),encoding='utf-8')
        with self.assertRaises(ValueError):release.members()

    def test_secret_and_unlisted_file_report_without_values(self):
        self.fixture()
        secret='gh'+'p_'+'a'*36
        (self.root/'README.md').write_text(secret,encoding='utf-8')
        (self.root/'apps').mkdir()
        (self.root/'apps/forgotten.py').write_text('# fixture',encoding='utf-8')
        report=release.scan(release.members())
        self.assertEqual({x['rule'] for x in report},{'token','unlisted-public-file'})
        self.assertNotIn(secret,json.dumps(report))

    def test_archive_allowlist_manifest_and_no_overwrite(self):
        self.fixture()
        (self.root/'private-not-listed.txt').write_text('Excluded fixture',encoding='utf-8')
        output=self.root/'candidate.zip'
        with patch('sys.argv',['release','build','--output',str(output)]),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(release.main(),0)
            with self.assertRaises(FileExistsError):release.main()
        with zipfile.ZipFile(output) as z:
            self.assertEqual(set(z.namelist()),{'pipeline-kit/README.md','pipeline-kit/release-files.json','pipeline-kit/BUILD_MANIFEST.json'})
            for item in json.loads(z.read('pipeline-kit/BUILD_MANIFEST.json')):
                self.assertEqual(release.digest(z.read('pipeline-kit/'+item['path'])),item['sha256'])

    def test_source_status_detects_change_without_writes(self):
        source=self.root/'source';source.mkdir()
        original=source/'helper.py';original.write_text('# changed',encoding='utf-8')
        (self.root/'provenance.json').write_text(json.dumps({'files':[{'path':'public.py','source':'example','source_path':'helper.py','source_sha256':'old'}]}),encoding='utf-8')
        roots=self.root/'roots.json';roots.write_text(json.dumps({'example':str(source)}),encoding='utf-8')
        report=self.root/'report.json'
        with patch('sys.argv',['release','source-status','--roots',str(roots),'--output',str(report)]),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(release.main(),0)
        self.assertTrue(json.loads(report.read_text())['files'][0]['source_changed'])
        self.assertEqual(original.read_text(),'# changed')

if __name__=='__main__':unittest.main()
