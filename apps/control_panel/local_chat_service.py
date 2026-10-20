"""Explicit opt-in local OpenAI-compatible chat endpoint, no cloud routing."""
import json
import math
import urllib.request
from urllib.parse import urlsplit
import kit_config as config

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Model redirects are refused')

def settings():
    row = config.options().get('local_chat', {})
    if not row.get('enabled'):
        return None
    url = str(row.get('base_url', '')).rstrip('/')
    parsed = urlsplit(url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Configure an HTTP loopback model endpoint')
    if not row.get('model'):
        raise ValueError('Configure a local model identifier')
    return {**row, 'base_url': url}

def models():
    cfg = settings()
    return [{'id': cfg['model'], 'name': cfg['model'], 'note': 'Configured local endpoint',
             'ready': True, 'present': True}] if cfg else []

def validate(messages, max_tokens=700, temperature=.4, model=''):
    if not isinstance(messages,list) or not 1 <= len(messages) <= 200:
        raise ValueError('Expected 1–200 messages')
    if not isinstance(max_tokens,int) or not 1 <= max_tokens <= 8192 or not math.isfinite(temperature) or not 0 <= temperature <= 2:
        raise ValueError('Invalid generation limits')
    for m in messages:
        if m.get('role') not in ('system','user','assistant') or not isinstance(m.get('content'),str):
            raise ValueError('Invalid chat message')
    if len(json.dumps(messages)) > 500000:
        raise ValueError('Conversation too large')
    return messages

def chat(messages, max_tokens=700, temperature=.4, model=''):
    cfg = settings()
    if not cfg or model != cfg['model']:
        raise ValueError('Configure and enable a local chat model first')
    validate(messages,max_tokens,temperature,model)
    body = json.dumps({'model':model, 'messages':messages, 'max_tokens':max_tokens,
                       'temperature':temperature, 'stream':False}).encode()
    req = urllib.request.Request(cfg['base_url']+'/chat/completions',data=body,headers={'Content-Type':'application/json'})
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
    with http.open(req, timeout=120) as response:
        data=json.loads(response.read(2*1024*1024))
    return {'content':data['choices'][0]['message']['content'], 'model':model}

clean = validate

def chat_stream(messages, max_tokens=700, temperature=.4, model='', stop=None):
    cfg=settings()
    if not cfg or model != cfg['model']:
        raise ValueError('Configure and enable a local chat model first')
    validate(messages,max_tokens,temperature,model)
    body=json.dumps({'model':model,'messages':messages,'max_tokens':max_tokens,
                     'temperature':temperature,'stream':True}).encode()
    req=urllib.request.Request(cfg['base_url']+'/chat/completions',data=body,headers={'Content-Type':'application/json'})
    http=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
    response=http.open(req,timeout=30)
    def events():
        parts=[]
        try:
            for raw in response:
                if stop and stop.is_set(): return
                if not raw.startswith(b'data:'): continue
                payload=raw[5:].strip()
                if payload==b'[DONE]':
                    yield ('done',{'content':''.join(parts),'model':model})
                    return
                data=json.loads(payload)
                choices=data.get('choices') or []
                text=choices[0].get('delta',{}).get('content','') if choices else ''
                if text:
                    parts.append(text)
                    yield ('delta',text)
            raise ValueError('Local model stream ended without completion')
        finally:
            response.close()
    return events()
