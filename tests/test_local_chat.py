"""Protocol and opt-in boundaries. No model or network is launched."""
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/control_panel'))
import local_chat_service as chat

class LocalChatTests(unittest.TestCase):
    def config(self,url='http://127.0.0.1:8080/v1',enabled=True):
        return patch.object(chat.config,'options',return_value={'local_chat':{'enabled':enabled,'base_url':url,'model':'local'}})

    def test_disabled_and_remote_refused(self):
        with self.config(enabled=False),patch.object(chat.urllib.request,'build_opener') as network:
            self.assertEqual(chat.models(),[])
            with self.assertRaises(ValueError):chat.chat([{'role':'user','content':'hello'}],model='local')
            network.assert_not_called()
        for url in ['https://example.com/v1','http://192.0.2.1/v1','http://name:pass@localhost/v1','http://localhost/v1?key=x']:
            with self.subTest(url=url),self.config(url):
                with self.assertRaises(ValueError):chat.settings()

    def test_stream_content_completion_and_close(self):
        response=io.BytesIO(b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\ndata: [DONE]\n')
        opener=MagicMock();opener.open.return_value=response
        with self.config(),patch.object(chat.urllib.request,'build_opener',return_value=opener):
            result=list(chat.chat_stream([{'role':'user','content':'test'}],model='local'))
        self.assertEqual(result,[('delta','hello'),('done',{'content':'hello','model':'local'})])
        self.assertTrue(response.closed)
        self.assertEqual(opener.open.call_args.args[0].full_url,'http://127.0.0.1:8080/v1/chat/completions')

    def test_incomplete_stream_and_redirect_refused(self):
        response=io.BytesIO(b'data: {"choices":[]}\n')
        opener=MagicMock();opener.open.return_value=response
        with self.config(),patch.object(chat.urllib.request,'build_opener',return_value=opener):
            with self.assertRaisesRegex(ValueError,'without completion'):
                list(chat.chat_stream([{'role':'user','content':'test'}],model='local'))
        self.assertTrue(response.closed)
        with self.assertRaises(ValueError):chat.NoRedirect().redirect_request(None,None,302,'',{},'https://example.com')

if __name__=='__main__':unittest.main()
