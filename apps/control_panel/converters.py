"""File and document converters for the «Быстрые правки» tab. Only tools already on Local node: ffmpeg/ffprobe,
LibreOffice (soffice headless), PyMuPDF, Pillow, python-docx, openpyxl. Each run writes into
<hub>/PipelineWeb/converted/<ts>-<converter>/ and appends a line to <state>/convert-runs.jsonl (the receipt).
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
import kit_config as config

import collectors as c
import uploads

OUT_ROOT = uploads.WEB_ROOT / 'converted'
RUNS = c.STATE / 'convert-runs.jsonl'
SOFFICE = config.executable('soffice')
VIDEO = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v', '.mpg', '.mpeg', '.ts', '.wmv', '.gif'}
AUDIO = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.opus', '.wma', '.aiff'}
IMAGE = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff', '.gif'}
OFFICE = {'.docx', '.doc', '.odt', '.rtf', '.xlsx', '.xls', '.ods', '.pptx', '.ppt', '.odp', '.txt', '.html', '.htm', '.csv'}
QUICK_TOOLS = config.workspace('tools')


def tool_path(name):
    """Portable tools do not depend on the scheduled task inheriting a new PATH."""
    found = shutil.which(name)
    if found:
        return found
    try:
        receipt = json.loads((QUICK_TOOLS / 'install-receipt.json').read_text(encoding='utf-8'))
        for row in receipt.get('packages', []):
            if row.get('name') == name and Path(row.get('path', '')).is_file():
                return row['path']
    except (OSError, ValueError):
        pass
    return None


def _ffmpeg():
    return shutil.which('ffmpeg')


def _sel(name, label, choices, default):
    return {'name': name, 'label': label, 'kind': 'select', 'choices': choices, 'default': default}


def _num(name, label, default, lo, hi, help=''):
    return {'name': name, 'label': label, 'kind': 'number', 'default': default, 'min': lo, 'max': hi, 'help': help}


def _txt(name, label, default='', help=''):
    return {'name': name, 'label': label, 'kind': 'text', 'default': default, 'help': help}


CONVERTERS = [
    {'id': 'markdown-docx', 'group': 'Документы', 'title': 'Markdown / HTML → DOCX', 'tool': 'pandoc', 'src': {'.md', '.markdown', '.html', '.htm'},
     'about': 'Текст, заголовки и таблицы в Word через Pandoc. Результат сохраняется отдельно.', 'options': []},
    {'id': 'docx-markdown', 'group': 'Документы', 'title': 'DOCX → Markdown (Pandoc)', 'tool': 'pandoc', 'src': {'.docx'},
     'about': 'Структурированный Markdown из документа Word.', 'options': []},
    {'id': 'pdf-optimize', 'group': 'Документы', 'title': 'Оптимизировать PDF (qpdf)', 'tool': 'qpdf', 'src': {'.pdf'},
     'about': 'Сжатие потоков и структуры без снижения разрешения картинок. Размер уменьшается не у каждого PDF.', 'options': []},
    {'id': 'metadata-read', 'group': 'Картинки', 'title': 'Посмотреть метаданные (ExifTool)', 'tool': 'exiftool', 'src': IMAGE | VIDEO | AUDIO | {'.pdf'},
     'about': 'EXIF, GPS, авторство и технические поля в JSON.', 'options': []},
    {'id': 'metadata-clean', 'group': 'Картинки', 'title': 'Удалить метаданные из копии', 'tool': 'exiftool', 'src': {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'},
     'about': 'Удаляет доступные EXIF, GPS и описательные поля, сохраняя ICC-профиль цвета. Исходник не меняется.', 'options': []},
    {'id': 'image-svg', 'group': 'Картинки', 'title': 'PNG / JPG → SVG (VTracer)', 'tool': 'vtracer', 'src': {'.png', '.jpg', '.jpeg', '.bmp'},
     'about': 'Цветная векторизация логотипов, рисунков и плоской графики на CPU.', 'options': []},
    {'id': 'video-mp4', 'group': 'Видео', 'title': 'Видео → MP4 (H.264)', 'tool': 'ffmpeg', 'src': VIDEO,
     'about': 'Пережать любое видео в MP4 для Telegram, сайта или превью. Ширина 0 = без изменения.',
     'options': [_num('width', 'Ширина, px', 0, 0, 7680), _num('crf', 'Качество (CRF, меньше = лучше)', 20, 14, 35),
                 _num('fps', 'Кадров/с (0 = как в исходнике)', 0, 0, 120), _sel('audio', 'Звук', ['оставить', 'убрать'], 'оставить')]},
    {'id': 'video-webm', 'group': 'Видео', 'title': 'Видео → WebM (VP9)', 'tool': 'ffmpeg', 'src': VIDEO,
     'about': 'Лёгкое видео для сайтов (фон, анимация).', 'options': [_num('width', 'Ширина, px', 0, 0, 7680), _num('crf', 'Качество (CRF)', 32, 15, 50)]},
    {'id': 'video-gif', 'group': 'Видео', 'title': 'Видео → GIF', 'tool': 'ffmpeg', 'src': VIDEO,
     'about': 'Короткая анимация с палитрой (2 прохода).', 'options': [_num('width', 'Ширина, px', 480, 64, 1920), _num('fps', 'Кадров/с', 12, 1, 30),
                                                                      _num('start', 'Начало, с', 0, 0, 36000), _num('duration', 'Длительность, с (0 = всё)', 0, 0, 600)]},
    {'id': 'video-trim', 'group': 'Видео', 'title': 'Вырезать фрагмент', 'tool': 'ffmpeg', 'src': VIDEO | AUDIO,
     'about': 'Кусок без перекодирования (быстро, по ключевым кадрам) или с перекодированием (точно).',
     'options': [_num('start', 'Начало, с', 0, 0, 36000), _num('duration', 'Длительность, с', 10, 0.1, 36000), _sel('mode', 'Режим', ['быстро', 'точно'], 'быстро')]},
    {'id': 'video-frames', 'group': 'Видео', 'title': 'Видео → кадры PNG', 'tool': 'ffmpeg', 'src': VIDEO,
     'about': 'Кадры для референсов, раскадровки или первого/последнего кадра под FLF.',
     'options': [_num('fps', 'Кадров/с', 1, 0.01, 60), _num('limit', 'Не больше кадров', 60, 1, 600), _num('width', 'Ширина, px (0 = исходная)', 0, 0, 7680)]},
    {'id': 'video-audio', 'group': 'Видео', 'title': 'Достать звук из видео', 'tool': 'ffmpeg', 'src': VIDEO,
     'about': 'Дорожка для стемов, транскрипции или музыки.', 'options': [_sel('format', 'Формат', ['wav', 'flac', 'mp3'], 'wav')]},
    {'id': 'audio-convert', 'group': 'Звук', 'title': 'Аудио → другой формат', 'tool': 'ffmpeg', 'src': AUDIO | VIDEO,
     'about': 'mp3 для отправки, wav/flac для обработки, ogg для ботов.',
     'options': [_sel('format', 'Формат', ['mp3', 'wav', 'flac', 'ogg', 'm4a'], 'mp3'), _sel('rate', 'Частота', ['как есть', '48000', '44100', '24000', '16000'], 'как есть'),
                 _num('bitrate', 'Битрейт kbps (mp3/ogg/m4a)', 192, 32, 320)]},
    {'id': 'audio-loudness', 'group': 'Звук', 'title': 'Выровнять громкость', 'tool': 'ffmpeg', 'src': AUDIO | VIDEO,
     'about': 'EBU R128 loudnorm: речь −16 LUFS, музыка −14, вещание −23.',
     'options': [_sel('target', 'Цель', ['-16 (речь, подкаст)', '-14 (музыка, стриминг)', '-23 (вещание)'], '-16 (речь, подкаст)'), _sel('format', 'Формат', ['wav', 'flac', 'mp3'], 'wav')]},
    {'id': 'image-convert', 'group': 'Картинки', 'title': 'Картинка → PNG / JPG / WebP', 'tool': 'pillow', 'src': IMAGE,
     'about': 'Смена формата и уменьшение по длинной стороне. JPG теряет прозрачность (белый фон).',
     'options': [_sel('format', 'Формат', ['png', 'jpg', 'webp'], 'png'), _num('max_side', 'Длинная сторона, px (0 = как есть)', 0, 0, 16384), _num('quality', 'Качество jpg/webp', 90, 40, 100)]},
    {'id': 'image-pdf', 'group': 'Картинки', 'title': 'Картинки → один PDF', 'tool': 'pillow', 'src': IMAGE,
     'about': 'Страница на картинку. Для нескольких файлов загрузите их по одному в тот же запуск.', 'options': []},
    {'id': 'doc-pdf', 'group': 'Документы', 'title': 'Документ → PDF', 'tool': 'soffice', 'src': OFFICE,
     'about': 'Word, Excel, PowerPoint, ODF, RTF, TXT, HTML → PDF через LibreOffice без интерфейса.', 'options': []},
    {'id': 'doc-docx', 'group': 'Документы', 'title': 'Документ → DOCX', 'tool': 'soffice', 'src': {'.doc', '.odt', '.rtf', '.txt', '.html', '.htm'},
     'about': 'Старый .doc, ODT, RTF или HTML → современный DOCX.', 'options': []},
    {'id': 'doc-xlsx', 'group': 'Документы', 'title': 'Таблица → XLSX', 'tool': 'soffice', 'src': {'.xls', '.ods', '.csv'},
     'about': 'XLS, ODS, CSV → XLSX.', 'options': []},
    {'id': 'pdf-png', 'group': 'Документы', 'title': 'PDF → картинки страниц', 'tool': 'pymupdf', 'src': {'.pdf'},
     'about': 'Для превью, презентаций и OCR.', 'options': [_num('dpi', 'DPI', 150, 50, 400), _txt('pages', 'Страницы (пусто = все)', '', 'например 1-3,7')]},
    {'id': 'pdf-txt', 'group': 'Документы', 'title': 'PDF → текст', 'tool': 'pymupdf', 'src': {'.pdf'},
     'about': 'Текстовый слой PDF (без OCR для сканов).', 'options': []},
    {'id': 'docx-txt', 'group': 'Документы', 'title': 'DOCX → текст / Markdown', 'tool': 'python-docx', 'src': {'.docx'},
     'about': 'Абзацы и таблицы в чистый текст для ТЗ, правок и выдачи моделям.', 'options': [_sel('format', 'Формат', ['txt', 'md'], 'md')]},
    {'id': 'xlsx-csv', 'group': 'Документы', 'title': 'XLSX → CSV (каждый лист)', 'tool': 'openpyxl', 'src': {'.xlsx'},
     'about': 'UTF-8 CSV с «;» для Excel RU или «,» для систем.', 'options': [_sel('sep', 'Разделитель', [';', ','], ';')]},
]
_BY_ID = {cv['id']: cv for cv in CONVERTERS}
_NOT_INSTALLED = {
    'Удаление фона': 'делает BiRefNet во вкладке «Модели» (ComfyUI), не здесь.',
}


def tools_present():
    return {'ffmpeg': bool(_ffmpeg()), 'soffice': SOFFICE.is_file(), 'pymupdf': _has('fitz'), 'pillow': _has('PIL'),
            'python-docx': _has('docx'), 'openpyxl': _has('openpyxl'),
            **{name: bool(tool_path(name)) for name in ('pandoc', 'qpdf', 'exiftool', 'vtracer')}}


def _has(mod):
    import importlib.util
    return importlib.util.find_spec(mod) is not None


def catalog():
    present = tools_present()
    rows = []
    for cv in CONVERTERS:
        rows.append({k: v for k, v in cv.items() if k != 'src'} | {'src': sorted(cv['src']), 'available': present.get(cv['tool'], False)})
    return {'converters': rows, 'tools': present, 'not_available': _NOT_INSTALLED, 'out_root': str(OUT_ROOT),
            'source_roots': [str(r) for r in uploads.SOURCE_ROOTS]}


def _opt(cv, opts, name):
    spec = next((o for o in cv['options'] if o['name'] == name), None)
    if spec is None:
        return None
    raw = (opts or {}).get(name, spec.get('default'))
    if spec['kind'] == 'number':
        try:
            val = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f'{spec["label"]}: нужно число')
        val = max(spec['min'], min(spec['max'], val))
        return int(val) if float(val).is_integer() else val
    if spec['kind'] == 'select':
        return raw if raw in spec['choices'] else spec['default']
    return str(raw or '')[:200]


def _run(cmd, timeout, log):
    log.append('$ ' + ' '.join(str(x) for x in cmd))
    try:
        proc = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired:
        raise ValueError(f'Команда не уложилась в {timeout} с')
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-12:]
    log.extend(tail)
    if proc.returncode:
        raise ValueError('Ошибка инструмента: ' + ' | '.join(tail[-4:])[:600])


def _even(n):
    return int(n) // 2 * 2


def _scale(width):
    return ['-vf', f'scale={_even(width)}:-2'] if width else []


def convert(converter_id, src, opts=None, out_dir=None):
    cv = _BY_ID.get(converter_id)
    if not cv:
        raise KeyError(converter_id)
    src = Path(src).resolve()
    if not src.is_file():
        raise KeyError(str(src))
    if src.suffix.lower() not in cv['src']:
        raise ValueError(f'{cv["title"]}: не принимает {src.suffix or "файлы без расширения"}')
    if not tools_present().get(cv['tool']):
        raise ValueError(f'{cv["tool"]} недоступен на этом компьютере')
    out_dir = Path(out_dir) if out_dir else OUT_ROOT / f"{time.strftime('%Y%m%d-%H%M%S')}-{converter_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log, started = [], time.time()
    stem = uploads.safe_name(src.stem, 80)
    o = lambda name: _opt(cv, opts, name)  # noqa: E731
    ff = [_ffmpeg(), '-hide_banner', '-nostdin', '-y']
    if converter_id in ('markdown-docx', 'docx-markdown'):
        out = out_dir / (stem + ('.docx' if converter_id == 'markdown-docx' else '.md'))
        # No user-supplied filters, commands or arbitrary CLI options.
        _run([tool_path('pandoc'), '--sandbox', '--standalone', src, '-o', out], 120, log)
    elif converter_id == 'pdf-optimize':
        out = out_dir / f'{stem}-optimized.pdf'
        _run([tool_path('qpdf'), '--object-streams=generate', '--stream-data=compress', '--recompress-flate', '--compression-level=9', src, out], 300, log)
    elif converter_id == 'metadata-read':
        out = out_dir / f'{stem}-metadata.json'
        with out.open('w', encoding='utf-8') as fh:
            proc = subprocess.run([tool_path('exiftool'), '-json', '-G1', '-charset', 'filename=UTF8', str(src)], stdout=fh, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', timeout=120, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if proc.returncode:
            raise ValueError('ExifTool: ' + proc.stderr[-600:])
        log.append('ExifTool JSON: ' + out.name)
    elif converter_id == 'metadata-clean':
        out = out_dir / f'{stem}-clean{src.suffix.lower()}'
        if out.resolve() == src:
            raise ValueError('Результат должен отличаться от исходника')
        shutil.copy2(src, out)
        _run([tool_path('exiftool'), '-overwrite_original', '-all=', '-tagsFromFile', src, '-ICC_Profile', out], 120, log)
    elif converter_id == 'image-svg':
        out = out_dir / f'{stem}.svg'
        _run([tool_path('vtracer'), '--input', src, '--output', out], 300, log)
    elif converter_id == 'video-mp4':
        out = out_dir / f'{stem}.mp4'
        cmd = ff + ['-i', src] + _scale(o('width')) + (['-r', str(o('fps'))] if o('fps') else []) + ['-c:v', 'libx264', '-preset', 'medium', '-crf', str(o('crf')), '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
        cmd += ['-an'] if o('audio') == 'убрать' else ['-c:a', 'aac', '-b:a', '160k']
        _run(cmd + [out], 1800, log)
    elif converter_id == 'video-webm':
        out = out_dir / f'{stem}.webm'
        _run(ff + ['-i', src] + _scale(o('width')) + ['-c:v', 'libvpx-vp9', '-crf', str(o('crf')), '-b:v', '0', '-row-mt', '1', '-c:a', 'libopus', out], 3600, log)
    elif converter_id == 'video-gif':
        out = out_dir / f'{stem}.gif'
        rng = (['-ss', str(o('start'))] if o('start') else []) + (['-t', str(o('duration'))] if o('duration') else [])
        filt = f"fps={o('fps')},scale={_even(o('width'))}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5"
        _run(ff + rng + ['-i', src, '-filter_complex', filt, '-loop', '0', out], 900, log)
    elif converter_id == 'video-trim':
        out = out_dir / f'{stem}-cut{src.suffix.lower()}'
        if o('mode') == 'быстро':
            _run(ff + ['-ss', str(o('start')), '-i', src, '-t', str(o('duration')), '-c', 'copy', '-avoid_negative_ts', 'make_zero', out], 600, log)
        else:
            codec = ['-c:a', 'libmp3lame', '-q:a', '2'] if src.suffix.lower() == '.mp3' else ['-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac'] if src.suffix.lower() in VIDEO else []
            _run(ff + ['-ss', str(o('start')), '-i', src, '-t', str(o('duration'))] + codec + [out], 1800, log)
    elif converter_id == 'video-frames':
        pattern = out_dir / f'{stem}-%04d.png'
        _run(ff + ['-i', src, '-vf', f"fps={o('fps')}" + (f",scale={_even(o('width'))}:-2" if o('width') else ''), '-frames:v', str(o('limit')), pattern], 1200, log)
    elif converter_id == 'video-audio':
        fmt = o('format')
        out = out_dir / f'{stem}.{fmt}'
        codec = {'wav': ['-c:a', 'pcm_s16le'], 'flac': ['-c:a', 'flac'], 'mp3': ['-c:a', 'libmp3lame', '-q:a', '2']}[fmt]
        _run(ff + ['-i', src, '-vn'] + codec + [out], 900, log)
    elif converter_id == 'audio-convert':
        fmt = o('format')
        out = out_dir / f'{stem}.{fmt}'
        rate = [] if o('rate') == 'как есть' else ['-ar', o('rate')]
        br = str(o('bitrate')) + 'k'
        codec = {'mp3': ['-c:a', 'libmp3lame', '-b:a', br], 'wav': ['-c:a', 'pcm_s16le'], 'flac': ['-c:a', 'flac'],
                 'ogg': ['-c:a', 'libopus', '-b:a', br], 'm4a': ['-c:a', 'aac', '-b:a', br]}[fmt]
        _run(ff + ['-i', src, '-vn'] + rate + codec + [out], 900, log)
    elif converter_id == 'audio-loudness':
        fmt = o('format')
        target = o('target').split(' ')[0]
        out = out_dir / f'{stem}-loud{target}.{fmt}'
        codec = {'wav': ['-c:a', 'pcm_s16le'], 'flac': ['-c:a', 'flac'], 'mp3': ['-c:a', 'libmp3lame', '-q:a', '2']}[fmt]
        _run(ff + ['-i', src, '-vn', '-af', f'loudnorm=I={target}:TP=-1.5:LRA=11'] + codec + [out], 1200, log)
    elif converter_id == 'image-convert':
        from PIL import Image
        fmt = o('format')
        out = out_dir / f'{stem}.{fmt}'
        with Image.open(src) as im:
            im.load()
            if o('max_side') and max(im.size) > o('max_side'):
                im.thumbnail((o('max_side'), o('max_side')), Image.LANCZOS)
            if fmt == 'jpg':
                if im.mode in ('RGBA', 'LA', 'P'):
                    bg = Image.new('RGB', im.size, (255, 255, 255))
                    bg.paste(im.convert('RGBA'), mask=im.convert('RGBA').split()[-1])
                    im = bg
                else:
                    im = im.convert('RGB')
                im.save(out, 'JPEG', quality=int(o('quality')), optimize=True)
            elif fmt == 'webp':
                im.save(out, 'WEBP', quality=int(o('quality')), method=6)
            else:
                im.save(out, 'PNG', optimize=True)
        log.append(f'Pillow: {src.name} → {out.name}')
    elif converter_id == 'image-pdf':
        from PIL import Image
        out = out_dir / f'{stem}.pdf'
        with Image.open(src) as im:
            im.convert('RGB').save(out, 'PDF', resolution=150.0)
        log.append(f'Pillow: {src.name} → {out.name}')
    elif converter_id in ('doc-pdf', 'doc-docx', 'doc-xlsx'):
        target = {'doc-pdf': 'pdf', 'doc-docx': 'docx', 'doc-xlsx': 'xlsx'}[converter_id]
        profile = out_dir / '.lo-profile'
        _run([SOFFICE, f'-env:UserInstallation={profile.resolve().as_uri()}', '--headless', '--norestore', '--convert-to', target, '--outdir', out_dir, src], 300, log)
        shutil.rmtree(profile, ignore_errors=True)
    elif converter_id in ('pdf-png', 'pdf-txt'):
        import fitz
        doc = fitz.open(src)
        if converter_id == 'pdf-txt':
            out = out_dir / f'{stem}.txt'
            out.write_text('\n\n'.join(page.get_text() for page in doc), encoding='utf-8')
        else:
            pages = _pages(o('pages'), doc.page_count)
            zoom = o('dpi') / 72
            for n in pages:
                doc[n].get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(out_dir / f'{stem}-p{n + 1:03d}.png')
        log.append(f'PyMuPDF: {doc.page_count} стр.')
        doc.close()
    elif converter_id == 'docx-txt':
        import docx
        d = docx.Document(str(src))
        md = o('format') == 'md'
        lines = []
        for block in d.element.body.iterchildren():
            tag = block.tag.rsplit('}', 1)[-1]
            if tag == 'p':
                p = docx.text.paragraph.Paragraph(block, d)
                text = p.text.strip()
                if not text:
                    continue
                style = (p.style.name or '').lower() if p.style is not None else ''
                if md and style.startswith('heading'):
                    level = ''.join(ch for ch in style if ch.isdigit()) or '1'
                    lines.append('#' * min(int(level), 6) + ' ' + text)
                elif md and 'list' in style:
                    lines.append('- ' + text)
                else:
                    lines.append(text)
            elif tag == 'tbl':
                t = docx.table.Table(block, d)
                for i, r in enumerate(t.rows):
                    cells = [cl.text.strip().replace('\n', ' ') for cl in r.cells]
                    lines.append(('| ' + ' | '.join(cells) + ' |') if md else '\t'.join(cells))
                    if md and i == 0:
                        lines.append('|' + '---|' * len(cells))
            lines.append('') if md else None
        out = out_dir / f"{stem}.{'md' if md else 'txt'}"
        out.write_text('\n'.join(lines).strip() + '\n', encoding='utf-8')
        log.append(f'python-docx: {len(lines)} строк')
    elif converter_id == 'xlsx-csv':
        import openpyxl
        wb = openpyxl.load_workbook(str(src), read_only=True, data_only=True)
        for ws in wb.worksheets:
            out = out_dir / f'{stem}-{uploads.safe_name(ws.title, 40)}.csv'
            with out.open('w', encoding='utf-8-sig', newline='') as fh:
                w = csv.writer(fh, delimiter=o('sep'))
                for r in ws.iter_rows(values_only=True):
                    w.writerow(['' if v is None else v for v in r])
        log.append(f'openpyxl: {len(wb.worksheets)} лист(ов)')
    outputs = [{'name': p.name, 'path': str(p), 'size': p.stat().st_size} for p in sorted(out_dir.iterdir()) if p.is_file() and not p.name.startswith('.')]
    if not outputs:
        raise ValueError('Инструмент отработал, но файлов на выходе нет: ' + ' | '.join(log[-3:]))
    rec = {'ts': time.strftime('%Y-%m-%d %H:%M:%S'), 'id': converter_id, 'title': cv['title'], 'src': str(src), 'out_dir': str(out_dir),
           'outputs': outputs, 'seconds': round(time.time() - started, 1), 'log': log[-8:]}
    RUNS.parent.mkdir(parents=True, exist_ok=True)
    with RUNS.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return {'ok': True, **rec}


def _pages(spec, count):
    spec = str(spec or '').strip()
    if not spec:
        return list(range(count))
    pages = set()
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            a, _, b = part.partition('-')
            lo, hi = int(a or 1), int(b or count)
            pages.update(range(max(1, lo) - 1, min(count, hi)))
        elif part.isdigit():
            n = int(part)
            if 1 <= n <= count:
                pages.add(n - 1)
    if not pages:
        raise ValueError('Страницы вне диапазона')
    return sorted(pages)


def runs(limit=30):
    rows = []
    try:
        lines = RUNS.read_text(encoding='utf-8', errors='replace').splitlines()[-limit:]
    except OSError:
        return []
    for ln in reversed(lines):
        try:
            rec = json.loads(ln)
            rec['outputs'] = [o for o in rec.get('outputs', []) if os.path.exists(o.get('path', ''))]
            rows.append(rec)
        except ValueError:
            continue
    return rows
