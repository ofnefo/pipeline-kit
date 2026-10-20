"""Phase 1.2: prompt-pack examples for the Studio generation form (catalog/prompt-packs/media, read only).

A catalogue model `base` maps to one media pack; each example becomes ready form values for the fields that model has
(the pack's `prompt` goes to the model's prompt field: tags for ACE-Step, instruct for Qwen3-TTS).
"""
import json
from pathlib import Path

PACKS_DIR = Path(__file__).resolve().parents[1] / 'catalog' / 'prompt-packs' / 'media'
PACK = {'h3': 'video-ltx', 'h3_ref2va': 'video-ltx', 'ltx25': 'video-ltx',
        'wan22': 'video-wan', 'wan22_svi_long': 'video-wan', 'wan22_fun_camera': 'video-wan', 'wan22_animate': 'video-wan',
        'wan21_uni3c': 'video-wan', 'vace': 'video-wan', 'infinitetalk_single': 'video-wan',
        'zimage': 'image-z-image', 'qwenedit': 'image-qwen-edit', 'acestep': 'music-ace-step',
        'qwen3tts': 'voice-tts', 'cosyvoice3': 'voice-tts', 'xtts2': 'voice-tts'}
PROMPT_FIELD = {'acestep': 'tags', 'qwen3tts': 'instruct', 'wan22_svi_long': 'prompt_1'}
_cache = {}


def _load(pid):
    p = PACKS_DIR / f'{pid}.json'
    m = p.stat().st_mtime
    if _cache.get(pid, (None,))[0] != m:
        _cache[pid] = (m, json.loads(p.read_text(encoding='utf-8')))
    return _cache[pid][1]


def values(base, ex, fields):
    """Form values an example fills for a model with these field names (unknown keys are dropped)."""
    out = {}
    pf = PROMPT_FIELD.get(base, 'prompt')
    if ex.get('prompt') and pf in fields:
        out[pf] = ex['prompt']
    for k in ('lyrics', 'text'):
        if ex.get(k) and k in fields:
            out[k] = ex[k]
    for k, v in (ex.get('params') or {}).items():
        if k in fields and isinstance(v, (int, float, str)):
            out[k] = v
    return out


def packs(base, fields):
    """Examples of the pack that fits `base`; only those that fill at least one of the model's fields."""
    pid = PACK.get(base)
    if not pid:
        return {'pack': None, 'examples': []}
    d = _load(pid)
    names = set(fields)
    rows = []
    for ex in d.get('examples') or []:
        v = values(base, ex, names)
        if v:
            rows.append({'id': ex.get('id'), 'title': ex.get('title') or ex.get('id'), 'context': ex.get('context') or '',
                         'values': v})
    tpl = d.get('template') or {}
    return {'pack': {'id': d.get('id', pid), 'model': d.get('model', ''), 'licence': d.get('licence', ''),
                     'pattern': tpl.get('pattern', '') if isinstance(tpl, dict) else ''}, 'examples': rows}
