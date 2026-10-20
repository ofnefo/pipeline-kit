"""Russian pronunciation preview for TTS. Stdlib only; no models or inference.

Keep subtitles/clean text untouched. Ambiguous forms require an explicit choice.
The default Qwen profile deliberately emits plain orthography: base Qwen does
not reliably obey accent marks. The annotated script is a separate review aid.
"""
from __future__ import annotations
import argparse,gzip,json,re,unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'data/ru-pronunciation'
WORD=re.compile(r'[А-Яа-яЁё]+(?:\u0301[А-Яа-яЁё]*)*')
VOWELS='аеёиоуыэюяАЕЁИОУЫЭЮЯ'
ENGINES=('qwen3-tts','xtts-v2','cosyvoice3','ruaccent-plus','qwen3-tts-ru-stress-experimental')

def plain(word):return unicodedata.normalize('NFC',word).replace('+','').replace('\u0301','')
def acute(word):return re.sub(r'\+(['+VOWELS+'])',lambda m:m[1]+'\u0301',word)
def match_case(value,original):
 if original.isupper():return value.upper()
 if original[:1].isupper():
  for i,c in enumerate(value):
   if c.isalpha():return value[:i]+c.upper()+value[i+1:]
 return value

class Lexicon:
 def __init__(self,root=ROOT):
  self.root=Path(root)
  def read(name):return json.loads(gzip.decompress((self.root/'sources'/f'{name}.json.gz').read_bytes()))
  self.accents=read('accents');self.homographs=read('omographs')
  self.yo=read('yo_words');self.yo_homographs=read('yo_homographs')
  self.senses=json.loads((self.root/'senses.json').read_text(encoding='utf8'))['entries']

 def lookup(self,word):
  key=plain(word).lower();forms=set();sources=[]
  yo_ambiguous=key in self.yo_homographs
  normalized=self.yo.get(key,key) if not yo_ambiguous else key
  for k in dict.fromkeys([key,normalized]):
   if k in self.homographs:
    forms.update(self.homographs[k]);sources.append('ruaccent/omographs')
   elif k in self.accents:
    forms.add(self.accents[k]);sources.append('ruaccent/accents')
  if normalized!=key:
   # Prefer the unambiguous ё spelling over the ё-omitted duplicate.
   forms={s for s in forms if 'ё' in plain(s)} or forms
  if yo_ambiguous:
   y=self.yo_homographs[key]
   for value in ([y] if isinstance(y,str) else y):
    forms.update(self.homographs.get(value,[self.accents.get(value,value)]))
   sources.append('ruaccent/yo_homographs')
  senses=[]
  for e in self.senses:
   if key in e['forms']:
    forms.add(e['forms'][key]);senses.append({'id':e['id'],'meaning':e['meaning'],'stress':e['forms'][key],'source':e['source']})
  return {'word':word,'key':key,'candidates':sorted(forms),'ambiguous':len(forms)>1 or yo_ambiguous,'senses':senses,'sources':sorted(set(sources)),'unknown':not forms}

 def prepare(self,text,engine='qwen3-tts',choices=None,sense=None,project=None,segment_id=None):
  if engine not in ENGINES:raise ValueError('Unknown engine '+engine)
  choices=choices or {};rows=[];annotated=[];tts=[];pos=0
  project_entries=(project or {}).get('entries',[])
  for m in WORD.finditer(text):
   original=m[0];info=self.lookup(original);chosen=None;why=None
   if '\u0301' in original:
    annotated.append(text[pos:m.end()]);tts.append(text[pos:m.end()]);pos=m.end();continue
   if info['key'] in choices:
    chosen=choices[info['key']]
    if chosen not in info['candidates']:raise ValueError('Choice is not a dictionary candidate: '+original+'='+chosen)
    why='explicit choice'
   elif sense:
    selected=[x for x in info['senses'] if x['id']==sense]
    if selected:chosen=selected[0]['stress'];why='explicit sense '+sense
   if chosen is None and len(info['candidates'])==1 and not info['ambiguous']:
    chosen=info['candidates'][0];why='dictionary'
   display=match_case(acute(chosen),original) if chosen else original
   rendered=original
   if chosen:
    rendered=match_case(chosen if engine=='ruaccent-plus' else acute(chosen) if engine=='qwen3-tts-ru-stress-experimental' else plain(chosen),original)
   overrides=[]
   for e in project_entries:
    scope=e.get('scope','all')
    if scope!='all' and (not isinstance(scope,list) or segment_id not in scope):continue
    if e.get('clean','').lower()!=info['key']:continue
    t=e.get('tts',{}).get(engine,{})
    if e.get('status')=='active' and t.get('result')=='ok' and t.get('verified') and t.get('take') and t.get('text'):
     overrides.append(t['text'])
   if len(set(overrides))>1:raise ValueError('Conflicting active project overrides for '+original)
   if overrides:rendered=match_case(overrides[0],original);why='verified project take'
   rows.append({**info,'start':m.start(),'end':m.end(),'selected':chosen,'reason':why,'tts':rendered,'needs_review':chosen is None and not overrides})
   annotated.extend([text[pos:m.start()],display]);tts.extend([text[pos:m.start()],rendered]);pos=m.end()
  annotated.append(text[pos:]);tts.append(text[pos:])
  return {'schema':'ru-pronunciation/preview@1','engine':engine,'clean_text':text,'annotated_text':''.join(annotated),'tts_text':''.join(tts),'review_required':[r['word'] for r in rows if r['needs_review']],'words':rows,'note':'Dictionary candidates are not an audio QA result. No censorship or word deletion is performed.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['lookup','preview'])
 src=p.add_mutually_exclusive_group(required=True);src.add_argument('--text');src.add_argument('--text-file',type=Path)
 p.add_argument('--engine',choices=ENGINES,default='qwen3-tts');p.add_argument('--select',action='append',default=[],metavar='WORD=STRESS_PLUS')
 p.add_argument('--sense');p.add_argument('--project-dictionary',type=Path);p.add_argument('--segment-id');p.add_argument('--output',type=Path);p.add_argument('--tts-output',type=Path)
 a=p.parse_args();text=a.text if a.text is not None else a.text_file.read_text(encoding='utf-8-sig');lex=Lexicon()
 choices=dict(x.split('=',1) for x in a.select)
 project=json.loads(a.project_dictionary.read_text(encoding='utf-8-sig')) if a.project_dictionary else None
 result=[lex.lookup(m[0]) for m in WORD.finditer(text)] if a.command=='lookup' else lex.prepare(text,a.engine,choices,a.sense,project,a.segment_id)
 encoded=json.dumps(result,ensure_ascii=False,indent=2)
 if a.output:a.output.write_text(encoded,encoding='utf8')
 else:print(encoded)
 if a.tts_output:
  if a.command!='preview':p.error('--tts-output requires preview')
  a.tts_output.write_text(result['tts_text'],encoding='utf8')

if __name__=='__main__':main()
