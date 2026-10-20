"""Explicit sound instructions; preserve original prompt and record effective prompt."""
import json

LTX = {'ltx25_flf', 'ltx25_i2v', 'ltx25_t2v', 'ltx25_last'}
FIELDS = {'audio_content', 'speech_language', 'speech_text'}

def supported(key):
    return key.startswith('h3_') or key in LTX

def decorate(it):
    key = it['id']
    if not supported(key):
        return it
    fields = {f['name']: f for f in it['fields']}
    ref = key == 'h3_ref2va'
    additions = [
        dict(name='generate_audio',kind='bool',label='Звук в ролике',default=ref,main=True,
             help='Выключено — готовый ролик без звуковой дорожки.'),
        dict(name='audio_content',kind='select',label='Что должно звучать',default='reference' if ref else 'scene',main=True,
             choices=['scene','speech']+(['reference'] if ref else []),
             option_labels={'scene':'Звуки сцены без речи','speech':'С репликой','reference':'По аудиореференсу'},
             visible_when={'generate_audio':True},help='Этот выбор добавляет явное указание к описанию для модели. Отсутствие речи не гарантировано.'),
        dict(name='speech_language',kind='select',label='Язык реплики',default='Русский',main=True,
             choices=['Русский','Английский'],visible_when={'generate_audio':True,'audio_content':'speech'}),
        dict(name='speech_text',kind='textarea',label='Реплика',default='',main=True,
             visible_when={'generate_audio':True,'audio_content':'speech'},help='Модель может исказить слова. Для точного текста используйте отдельную озвучку.')]
    for f in additions:
        if f['name'] not in fields:
            it['fields'].append(f)
    it['audio_info']='Звук создаёт сама видеомодель. При включении выберите звуки сцены, реплику или доступный аудиореференс.'
    return it

def validate(key, params):
    out = dict(params)
    if not supported(key): return out
    out.setdefault('generate_audio', key == 'h3_ref2va')
    out.setdefault('audio_content', 'reference' if key == 'h3_ref2va' else 'scene')
    choices = {'scene','speech'} | ({'reference'} if key == 'h3_ref2va' else set())
    if out['audio_content'] not in choices: raise ValueError('Выберите содержимое звука')
    if out['generate_audio'] and out['audio_content']=='speech':
        out.setdefault('speech_language','Русский')
        if out['speech_language'] not in ('Русский','Английский'): raise ValueError('Выберите язык реплики')
        if not str(out.get('speech_text','')).strip(): raise ValueError('Укажите реплику или выберите звуки сцены без речи')
    return out

def compose(key, params):
    if not supported(key): return dict(params), {}
    source = dict(params)
    out = {k:v for k,v in source.items() if k not in FIELDS}
    original = str(out.get('prompt',''))
    instruction = ''
    if source.get('generate_audio'):
        content = source.get('audio_content', 'reference' if key=='h3_ref2va' else 'scene')
        if content == 'scene': instruction = 'Audio: only sounds caused by the visible action and natural ambience. No speech, dialogue, narration, singing or vocalizations resembling speech.'
        elif content == 'speech': instruction = 'Spoken dialogue in '+('Russian' if source.get('speech_language','Русский')=='Русский' else 'English')+': '+json.dumps(str(source.get('speech_text','')),ensure_ascii=False)+'. Do not add other spoken words.'
    effective = original + ('\n\n'+instruction if instruction else '')
    out['prompt'] = effective
    return out, {'audio_settings':{k:source.get(k) for k in FIELDS|{'generate_audio'}},'audio_instruction':instruction}


def prepare(key, params, out_dir):
    out, details = compose(key, params)
    if supported(key):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir/'generation-prompt.json').write_text(json.dumps({'original_prompt':params.get('prompt',''), **details, 'effective_prompt':out.get('prompt','')}, ensure_ascii=False, indent=2), encoding='utf-8')
    return out



def check_references(inputs):
    import math
    import subprocess
    from pathlib import Path
    probe = __import__('kit_config').executable('ffprobe')
    for name, stream in [('ref_video','v:0'),('ref_audio','a:0')]:
        if not inputs.get(name): continue
        try:
            p = subprocess.run([str(probe),'-v','error','-select_streams',stream,'-show_entries','stream=duration:format=duration','-of','json',str(inputs[name])],capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            data = json.loads(p.stdout)
            if p.returncode or not data.get('streams'): raise ValueError()
            duration = float(data['streams'][0].get('duration') or data.get('format',{}).get('duration') or 0)
        except (OSError, ValueError, subprocess.SubprocessError):
            raise ValueError('Не удалось прочитать '+('видеореференс' if name=='ref_video' else 'аудиореференс')) from None
        if not math.isfinite(duration) or duration < 2 or (name=='ref_audio' and duration>15):
            raise ValueError('Видеореференс должен быть не короче 2 с' if name=='ref_video' else 'Аудиореференс: от 2 до 15 с')
