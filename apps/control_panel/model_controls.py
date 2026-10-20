"""Panel parameter contracts. Local duration caps are operating profiles, NOT model maxima.
Native numeric bounds: installed ComfyUI object_info snapshot, 2026-10-13.
Temporal grids/fps: pipeline *.params.json + *.api.json. Cloud bounds: cached provider schema.
No network, GPU work, prompt rewriting or paid calls here.
"""
import copy
import model_audio
import model_style
import video_contract
import json
import math
from pathlib import Path

NATIVE = json.loads(Path(__file__).with_name('model-numeric-contracts.json').read_text(encoding='utf-8'))['models']
PROFILE_NOTE = 'Предел текущего пресета на этом сервере. Более длинные ролики требуют отдельной настройки.'
# min frames, max frames, temporal grid, fps. These caps deliberately stay within the shipped profile.
VIDEO = {
    **{k: (73, 124, 17, 24) for k in ('h3_flf', 'h3_flf_depth', 'h3_i2v', 'h3_t2v', 'h3_last')},
    'h3_ref2va': (124, 124, 17, 24),
    'infinitetalk_single': (25, 81, 4, 25),
    'ltx25_clean_plate': (25, 49, 8, 24), **{k: (25, 121, 8, 24) for k in model_audio.LTX},
    **{k: (17, 81, 4, 16) for k in ('wan21_uni3c', 'wan22_animate', 'wan22_fun_camera',
        'wan22_i2v14b_flf', 'wan22_i2v14b', 'wan22_svi_long', 'wan22_svi_probe')},
    **{k: (17, 81, 4, 16) for k in ('wan22_vace_a14b_inpaint', 'wan22_vace_a14b_v2v')},
}


def decorate(item):
    it = copy.deepcopy(item)
    key = it['id']
    fields = {f['name']: f for f in it['fields']}
    for name, limits in NATIVE.get({'h3_last':'h3_flf','wan22_i2v14b':'wan22_i2v14b_flf','ltx25_i2v':'ltx25_flf','ltx25_t2v':'ltx25_flf','ltx25_last':'ltx25_flf'}.get(key,key), {}).items():
        if name in fields:
            fields[name].update(limits)
            # Browser/JSON cannot represent every uint64; keep new UI seeds exactly representable.
            if name.startswith('seed'):
                fields[name]['max'] = min(fields[name].get('max', 9007199254740991), 9007199254740991)
    if key in VIDEO:
        low, high, step, fps = VIDEO[key]
        f = fields['length']
        f.update(min=low, max=high, step=step, integer=True)
        label = 'Длительность фрагмента' if key.startswith('wan22_svi') else 'Длительность'
        f['duration'] = {'values': list(range(low, high+1, step)), 'fps': fps, 'label': label, 'note': PROFILE_NOTE}
        if key.startswith('wan22_svi'):
            f['duration']['note'] = 'Длина каждого из 6 фрагментов. Общая длина зависит от соединения фрагментов. ' + PROFILE_NOTE
        if key == 'ltx25_clean_plate':
            f['duration']['note'] = 'Не длиннее исходного видео. ' + PROFILE_NOTE
        if 'fps' in fields:
            f['duration']['fps_field'] = 'fps'
        if key in model_audio.LTX:
            for target, source in [('audio_frames','length'),('start_w','width'),('end_w','width'),('start_h','height'),('end_h','height')]:
                if target in fields: fields[target]['linked_to'] = source
        if key.startswith('h3_'):
            for name in ('width', 'height'):
                fields[name].update(min=32, step=32)
    for name in ('duration', 'seconds', 'extend_seconds'):
        f = fields.get(name)
        if not f:
            continue
        if key.startswith('music_acestep') and name == 'seconds' and not key.endswith('_t2m'):
            f['automatic'] = 'По длине исходного аудио' if not key.endswith('_extend') else 'Исходное аудио + продолжение'
            continue
        if key.startswith('music_'):
            cap = 47 if key == 'music_sfx_stable_audio_open' else (30 if name == 'extend_seconds' else 60)
            f.update(min=1, max=cap, integer=True)
        values = None
        if f.get('choices') and all(str(v).isdigit() for v in f['choices']):
            values = f['choices']  # preserve provider string enums
        elif f.get('min') is not None and f.get('max') is not None:
            values = list(range(math.ceil(f['min']), math.floor(f['max'])+1))
        if values:
            f['duration'] = {'values': values, 'fps': 1, 'label': 'Продолжить на' if name == 'extend_seconds' else 'Длительность',
                             'note': PROFILE_NOTE if not it.get('cloud') else 'Доступное время для выбранной модели.'}
            f['integer'] = True
    if key == 'replicate_wan-2.2-i2v-fast':
        f = fields['num_frames']
        f.update(min=81, max=121, step=4, integer=True)
        f['duration'] = {'values': list(range(81,122,4)), 'fps': 16, 'label': 'Длительность',
                         'note': 'Интерполяция увеличивает плавность, сохраняя длительность.'}
    # Cross-field provider rule in the configured Hailuo API: 1080p supports only 6 seconds.
    if key == 'replicate_hailuo-2.3':
        fields['duration']['duration']['when'] = {'field': 'resolution', 'equals': '1080p', 'values': ['6']}
    # Offer only preset durations supported by this operating profile.
    for group in ('presets', 'project_presets', 'task_presets'):
        for preset in it.get(group, []):
            values = preset.get('values', {})
            adjusted = False
            for name, field in fields.items():
                d = field.get('duration')
                if d and name in values and str(values[name]) not in [str(v) for v in d['values']]:
                    values[name] = min(d['values'], key=lambda v: abs(float(v)-float(values[name])))
                    adjusted = True
            for name, field in fields.items():
                if field.get('linked_to') in values:
                    values[name] = values[field['linked_to']]
            if group == 'task_presets' or adjusted:
                parts = [f"{values['width']}×{values['height']}"] if 'width' in values and 'height' in values else []
                for name, field in fields.items():
                    if field.get('duration') and name in values:
                        d = field['duration']; fps = values.get(d.get('fps_field'), fields.get(d.get('fps_field'), {}).get('default', d['fps']))
                        seconds = f"{float(values[name])/float(fps):.1f}".replace('.', ',')
                        parts.append(seconds + ' с')
                preset['note'] = ', '.join(parts)
    return video_contract.decorate(model_style.decorate(model_audio.decorate(it)))


def validate(item, params):
    """Validate before resource checks/queueing; keep native workflow parameter names."""
    it = decorate(item)
    fields = {f['name']: f for f in it['fields']}
    out = dict(params)
    for name, f in fields.items():
        if f.get('automatic'):
            out.pop(name, None)
            continue
        if 'fixed' in f:
            out[name] = f['fixed']
        if f.get('linked_to'):
            source = f['linked_to']
            out[name] = out.get(source, fields[source].get('default'))
        if name not in out and (f.get('duration') or (it['id'].startswith('h3_') and name == 'generate_audio')):
            out[name] = f['default']
        if name not in out:
            continue
        value = out[name]
        if f['kind'] == 'number':
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError(f'«{f["label"]}»: нужно число') from None
            if not math.isfinite(number):
                raise ValueError(f'«{f["label"]}»: нужно конечное число')
            if f.get('integer') and not number.is_integer():
                raise ValueError(f'«{f["label"]}»: нужно целое число')
            if number < f.get('min', -math.inf) or number > f.get('max', math.inf):
                raise ValueError(f'«{f["label"]}»: допустимо от {f.get("min", "—")} до {f.get("max", "—")}')
            if f.get('step') and not math.isclose((number-f.get('min',0))/f['step'], round((number-f.get('min',0))/f['step']), abs_tol=1e-7):
                raise ValueError(f'«{f["label"]}»: выберите допустимое значение ползунком')
            out[name] = int(number) if f.get('integer') else number
        d = f.get('duration')
        if d:
            values = d['values']
            rule = d.get('when')
            if rule and str(out.get(rule['field'], fields[rule['field']].get('default'))) == rule['equals']:
                values = rule['values']
            if str(out[name]) not in [str(v) for v in values] and not any(str(v) == str(float(out[name])) for v in values):
                raise ValueError('Длительность недоступна для выбранных настроек. Измените время или качество.')
    return model_audio.validate(it['id'], out)
