"""Opt-in visual instructions, shared by preview and runners; no generation calls."""
import json
import model_audio
import spec_translator

# label, choices: (label, default features); the vocabulary lives in catalog/spec/vocab.json
CONTROLS = {key: (c['label'], {v: (e['label'], e.get('features', '')) for v, e in c['values'].items()})
            for key, c in spec_translator.VOCAB['controls'].items()}
PREFIX = 'visual_'
from pathlib import Path
RECIPE_DOCUMENT=json.loads((Path(__file__).resolve().parents[1]/'catalog/visual-recipes.json').read_text(encoding='utf-8'))
PRESETS=[{'id':'none','name':'Без пресета','values':dict.fromkeys(CONTROLS,'none')}, *RECIPE_DOCUMENT['recipes']]

def decorate(it):
    if it.get('group') not in ('video','image') or not any(f['name']=='prompt' for f in it['fields']): return it
    existing={f['name'] for f in it['fields']}
    it['visual_groups']=['look','lens','angle','camera','composition','film','skin','light']
    for key,(label,options) in CONTROLS.items():
        name=PREFIX+key
        if it.get('group')=='image' and key=='camera': continue
        if name not in existing:
            it['fields'].append(dict(name=name,label=label,kind='select',default='none',choices=list(options),option_labels={k:v[0] for k,v in options.items()},visual=True))
    presets = PRESETS
    if it['group']=='image':
        checks={'cinema':'Главный объект читается, лицо и фон без деформаций.', 'product':'Материал, геометрия и маркировка соответствуют исходнику.', 'clip':'Свет подчёркивает объект, детали не теряются в дымке.', 'symmetry':'Объект и линии кадра образуют осознанную симметрию.'}
        presets=[dict(p,check=checks.get(p['id'],'')) for p in PRESETS if p['id'] in {'none',*checks}]
    it['visual_presets']=[dict(p,values={PREFIX+k:v for k,v in p['values'].items() if it['group']!='image' or k!='camera'}) for p in presets]
    return it

def compose(key, params):
    source=dict(params)
    out={k:v for k,v in source.items() if not k.startswith(PREFIX)}
    settings={}
    values={}
    for name,(label,options) in CONTROLS.items():
        choice=source.get(PREFIX+name,'none')
        if choice not in options: raise ValueError('Недопустимое значение: '+label)
        settings[label]=options[choice][0]
        values[name]=choice
    original=str(source.get('prompt',''))
    spec=spec_translator.render(key,values,original)
    instruction=spec.pop('instruction')
    if instruction:
        if not original.strip(): raise ValueError('Опишите сюжет: одного пресета недостаточно')
        out['prompt']=original+'\n\nVisual direction: '+instruction
    out,audio=model_audio.compose(key,out)
    spec['template_warnings']=spec_translator.word_warnings(key,out.get('prompt',''))
    receipt={'original_prompt':original,'visual_settings':settings,'visual_instruction':instruction,'spec_source':'visual_controls',**spec,**audio,'effective_prompt':out.get('prompt','')}
    return out,receipt

def prepare(key,params,out_dir):
    out,receipt=compose(key,params)
    if 'prompt' in params or any(k.startswith(PREFIX) for k in params):
        out_dir.mkdir(parents=True,exist_ok=True)
        (out_dir/'generation-prompt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return out
