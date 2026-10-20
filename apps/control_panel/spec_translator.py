"""Shot-technique spec translator: control values -> observable features in the model's template syntax.

Single source: catalog/spec/vocab.json + catalog/spec/templates/<id>.json (design: docs/audit-20261015/SPEC_TRANSLATOR.md).
No generation calls. CLI for agents: python -X utf8 web/spec_translator.py explain "<фраза оператора>" [--model KEY]
"""
import json
import sys
from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parents[1] / 'catalog' / 'spec'
VOCAB = json.loads((SPEC_DIR / 'vocab.json').read_text(encoding='utf-8'))
TEMPLATES = {t['id']: t for t in (json.loads(p.read_text(encoding='utf-8')) for p in sorted((SPEC_DIR / 'templates').glob('*.json')))}


def template_for(key):
    """Longest matching id prefix wins; unknown models get the feature-only default."""
    best, size = TEMPLATES['default'], 0
    for t in TEMPLATES.values():
        for prefix in t['match']:
            if str(key).startswith(prefix) and len(prefix) > size:
                best, size = t, len(prefix)
    return best


def _lower(text):
    return text[:1].lower() + text[1:] if text[1:2].islower() or len(text) < 2 else text


def _phrase(control, entry, t):
    feats = entry.get('features', '')
    if t['phrase_form'] == 'edit' and entry.get('edit'):
        return entry['edit']
    if control == 'lens':
        style = t['lens_style']
        term = (entry.get('mm_term') or entry.get('type_term')) if style == 'mm+features' else entry.get('type_term') if style == 'type' else None
        return f'{term}: {_lower(feats)}' if term else feats
    if control == 'film' and t['film_style'] == 'format+features' and entry.get('format_term'):
        return f"{entry['format_term']} look: {_lower(feats)}"
    if control == 'camera':
        style, bracket, verb = t['camera_style'], entry.get('bracket'), entry.get('verb') or feats
        if style == 'verb':
            return verb
        if style == 'bracket':
            return bracket or verb
        if style == 'bracket+verb':
            return f'{bracket} {verb}' if bracket else verb
    return feats


def render(key, values, original='', extra=''):
    """values: {control: value}; returns instruction plus the spec receipt for generation-prompt.json."""
    t = template_for(key)
    controls = VOCAB['controls']
    parts, guards, spec = [], [], []
    for control in t['order']:
        value = values.get(control, 'none')
        entry = controls[control]['values'].get(value)
        if entry is None:
            raise ValueError('Недопустимое значение: ' + controls[control]['label'])
        if value == 'none':
            continue
        text = _phrase(control, entry, t)
        brand = entry.get('brand_hint')
        brand_used = bool(brand and t['brand_policy'] == 'verified_only' and brand in t['brands_verified'])
        if brand_used:
            text = text.rstrip('.') + f' ({brand}).'
        parts.append(text)
        if entry.get('guard') and entry['guard'] not in guards:
            guards.append(entry['guard'])
        spec.append({'control': control, 'layer': controls[control]['layer'], 'value': value, 'label': entry['label'],
                     'features': entry.get('features', ''), 'rendered': text, 'brand_hint': brand, 'brand_used': brand_used})
    if extra:
        parts.append(extra)
    if parts and t['phrase_form'] == 'edit':
        parts = ['Edit the image.', *parts, "Apart from the requested changes, keep the subject's identity and all other details unchanged."]
    instruction = ' '.join(parts + guards)
    return {'instruction': instruction, 'spec': spec, 'template': t['id'], 'template_version': t['template_version'],
            'template_verified': t['verified'], 'template_warnings': word_warnings(key, str(original) + ' ' + instruction)}


def word_warnings(key, prompt):
    """Warn (never cut): prompt longer than the template recommends, or a phrase combination its A/B found harmful."""
    t = template_for(key)
    words = len(str(prompt).split())
    out = []
    if t['max_words'] and words > t['max_words']:
        out.append(f"Промпт {words} слов, шаблон {t['id']} рекомендует до {t['max_words']}")
    low = str(prompt).lower()
    for w in t.get('combo_warnings', []):
        if all(s in low for s in w['all']) and any(s in low for s in w['any']):
            out.append(w['text'])
    return out


def interpret(text):
    """Operator's wording -> matching phrase entries with variants A/B (A is the default)."""
    low = str(text).lower()
    return [p for p in VOCAB['phrases'] if any(m in low for m in p['match'])]


def explain(text, key='default'):
    out = []
    for p in interpret(text):
        variants = {}
        for name in ('A', 'B'):
            v = p[name]
            variants[name] = {'means': v['means'], 'values': v['values'],
                              'prompt': render(key, v['values'], extra=v.get('extra_features', ''))['instruction']}
        out.append({'match': p['match'][0], 'ambiguous': p['ambiguous'], 'default': 'A', **variants})
    return {'model': key, 'template': template_for(key)['id'], 'phrases': out}


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] != 'explain' or len(args) < 2:
        sys.exit('usage: spec_translator.py explain "<фраза>" [--model KEY]')
    model = args[args.index('--model') + 1] if '--model' in args else 'default'
    print(json.dumps(explain(args[1], model), ensure_ascii=False, indent=2))
