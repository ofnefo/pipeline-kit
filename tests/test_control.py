"""Integration tests against an isolated workspace, without a listening server."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
TEMP=tempfile.TemporaryDirectory(prefix='pipeline-kit-test-')
os.environ['PIPELINE_KIT_WORKSPACE']=TEMP.name
sys.path.insert(0,str(ROOT/'apps/control_panel'))
from fastapi.testclient import TestClient
import app
import kit_config
import workboard
from PIL import Image

class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx=TestClient(app.app)
        cls.client=cls.ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.__exit__(None,None,None)
        TEMP.cleanup()

    def request(self,method,path,expected=200,**kwargs):
        r=getattr(self.client,method)(path,**kwargs)
        self.assertEqual(r.status_code,expected,(path,r.text[:1200]))
        return r.json()

    def test_01_import_no_external_effects(self):
        code="""import sys,os,socket,subprocess,threading,tempfile
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
with tempfile.TemporaryDirectory() as root:
 os.environ['PIPELINE_KIT_WORKSPACE']=root+'/empty'
 with patch.object(socket.socket,'connect',side_effect=AssertionError('network')), patch.object(subprocess,'Popen',side_effect=AssertionError('process')), patch.object(threading.Thread,'start',side_effect=AssertionError('thread')):
  import app
  assert not os.path.exists(root+'/empty'), 'import created workspace'
print('import has no external effects')"""
        out=subprocess.run([sys.executable,'-c',code,str(ROOT/'apps/control_panel')],capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(out.returncode,0,out.stderr)

    def test_02_core_views(self):
        for url in ['/api/health','/api/capabilities','/api/board','/api/namenode/work','/api/projects','/api/convert/catalog','/api/convert/runs','/api/studio/meta','/api/smm','/api/tools']:
            self.request('get',url)
        self.assertEqual(self.client.get('/').status_code,200)
        self.request('post','/api/models/generate',expected=501,json={})

    def test_03_board_version_and_persistence(self):
        created=self.request('post','/api/board',json={'title':'Integration task','executor':'human'})
        task=created.get('task',created)
        ident=task['id'];version=task['version']
        result=self.request('post',f'/api/board/{ident}',json={'version':version,'action':'edit','data':{'title':'Edited'}})
        self.request('post',f'/api/board/{ident}',expected=409,json={'version':version,'action':'edit','data':{'title':'Stale'}})
        self.assertEqual(workboard.get(ident)['title'],'Edited')

    def test_04_project_files(self):
        p=self.request('post','/api/projects/create',json={'type':'video','name':'integration'})
        path=Path(p['path'])
        self.assertTrue((path/'project.yaml').is_file())
        rows=self.request('get','/api/projects')['rows']
        row=next(row for row in rows if row.get('studio_key')=='video/integration')
        self.assertEqual(row['kind'],'project')  # Original UI's default Projects filter.
        self.request('post','/api/projects/create',expected=400,json={'type':'video','name':'../outside'})
        self.request('post','/api/project-browser/mkdir',json={'root':'projects','path':'video/integration','name':'incoming'})
        self.request('put','/api/project-browser/upload?root=projects&path=video/integration/incoming&name=note.txt',content=b'original',headers={'Content-Type':'application/octet-stream'})
        self.assertEqual((path/'incoming/note.txt').read_text(),'original')
        r=self.client.get('/api/project-browser/text',params={'root':'projects','path':'../config.json'})
        self.assertIn(r.status_code,(400,403,404))

    def test_05_upload_and_converter(self):
        buf=io.BytesIO();Image.new('RGB',(16,10),'red').save(buf,'PNG')
        r=self.client.post('/api/convert',data={'kind':'image-convert','opts':'{"format":"webp"}'},files={'file':('sample.png',buf.getvalue(),'image/png')})
        self.assertEqual(r.status_code,200,r.text[:1500])
        self.assertTrue(r.json()['ok'],r.json())

    def test_06_namenode(self):
        body='\n\n'.join('## '+s+'\nLocal workspace' for s in ['Что это','Где лежит','Репозиторий','Запуск и деплой','Куда вносить изменения','Риски и открытые вопросы','Ревью'])
        result=self.request('post','/api/namenode/card',json={'meta':{'id':'project-example','type':'project','title':'Example'},'body':body})
        self.request('get','/api/namenode/card/project-example')
        claimed=workboard.nn('claim',{'id':'project-example','agent':'test:one','what':'Integration','hours':1})
        self.assertTrue(claimed['ok'])
        denied=workboard.nn('claim',{'id':'project-example','agent':'test:two','what':'Collision','hours':1})
        self.assertFalse(denied['ok'])
        workboard.nn('release',{'id':'project-example','agent':'test:one','summary':'Complete'})

    def test_07_smm_and_chat(self):
        post=self.request('post','/api/smm/posts',json={'posts':[{'brand':'sample','network':'website','title':'Draft'}]})
        self.assertEqual(len(post['ids']),1)
        exported=self.request('get','/api/smm/export')
        self.assertFalse(exported['published'])
        chat=self.request('post','/api/studio/chats',json={'project':'inbox','title':'Draft chat'})
        self.assertIn('id',chat)

    def test_08_origin_boundary(self):
        for headers in ({'Origin':'https://evil.invalid'},{'Origin':'https://testserver'},{'Sec-Fetch-Site':'cross-site'},{'Host':'evil.invalid'}):
            self.request('get','/api/health',expected=403,headers=headers)

    def test_09_quarantine_restore_and_private_paths(self):
        rel='video/integration/incoming/note.txt'
        removed=self.request('post','/api/project-browser/trash',json={'root':'projects','path':rel})
        self.assertFalse((kit_config.workspace('projects')/rel).exists())
        self.request('post','/api/project-browser/restore',json={'id':removed['id']})
        self.assertEqual((kit_config.workspace('projects')/rel).read_text(),'original')
        import uploads
        for name in ('.env','credentials.json'):
            path=kit_config.workspace('projects/video/integration')/name
            path.write_text('fixture only')
            with self.assertRaises(ValueError):uploads.resolve_source(str(path))
            response=self.client.get('/api/project-browser/text',params={'root':'projects','path':'video/integration/'+name})
            self.assertIn(response.status_code,(400,403,404))
            response=self.client.get('/api/projects/file',params={'path':str(path)})
            self.assertIn(response.status_code,(400,403,404))
        with tempfile.TemporaryDirectory() as other:
            path=Path(other)/'outside.txt';path.write_text('outside')
            with self.assertRaises(ValueError):uploads.resolve_source(str(path))

    def test_10_create_missing_project_yaml(self):
        self.request('post','/api/project-browser/mkdir',json={'root':'projects','path':'','name':'empty-project'})
        target=kit_config.workspace('projects/empty-project/project.yaml')
        result=self.request('get','/api/projects/file',params={'path':str(target)})
        self.assertFalse(result['exists'])
        created=self.request('post','/api/projects/file',json={'path':str(target),'text':'name: Example\n','expect_mtime':0})
        self.assertEqual(target.read_text(),'name: Example\n')
        self.request('post','/api/projects/file',expected=409,json={'path':str(target),'text':'name: Stale\n','expect_mtime':created['mtime']-100})
        self.assertEqual(target.read_text(),'name: Example\n')
        missing=kit_config.workspace('web/uploads/missing.png')
        self.request('get','/api/convert/file',expected=404,params={'path':str(missing)})
        self.request('post','/api/convert',expected=404,data={'kind':'image-convert','src':str(missing)})

    def test_11_missing_path_keeps_link_and_reparse_guards(self):
        import stat
        from types import SimpleNamespace
        from project_files_service import native
        pivot=kit_config.workspace('projects/blocked-link')
        original=Path.lstat
        for mode,attributes in ((stat.S_IFLNK,0),(stat.S_IFDIR,0x400)):
            def observed(path,*args,**kwargs):
                if path==pivot:return SimpleNamespace(st_mode=mode,st_file_attributes=attributes)
                return original(path,*args,**kwargs)
            with patch.object(Path,'lstat',observed),self.assertRaises(ValueError):
                native(pivot/'missing/project.yaml')

    def test_12_file_error_http_mapping(self):
        for error,status in ((FileNotFoundError('Missing fixture'),404),(PermissionError('Denied fixture'),400)):
            with patch.object(app.nns,'read_file',side_effect=error):
                self.request('get','/api/projects/file',expected=status,params={'path':'fixture'})
            with patch.object(app.uploads,'inside',side_effect=error):
                self.request('get','/api/convert/file',expected=status,params={'path':'fixture'})

    def test_13_upload_small_free_space_reserve(self):
        from types import SimpleNamespace
        import project_files_actions as actions
        url='/api/project-browser/upload?root=projects&path=&name=reserve.txt'
        with patch.object(actions.shutil,'disk_usage',return_value=SimpleNamespace(free=128*1024**2)):
            self.request('put',url,content=b'fixture')
        with patch.object(actions.shutil,'disk_usage',return_value=SimpleNamespace(free=32*1024**2)):
            self.request('put',url,expected=507,content=b'fixture')

if __name__=='__main__': unittest.main(verbosity=2)
