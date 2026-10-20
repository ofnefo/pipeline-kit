"""Bounded, semantic previews. No Office/Adobe application launch or active content."""
import csv
import io
import json
from pathlib import Path
import struct
import warnings
import zipfile
import xml.etree.ElementTree as ET

XML_LIMIT = 8 * 1024 * 1024
INPUT_LIMIT = 64 * 1024 * 1024
CHAR_LIMIT = 256 * 1024
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      's':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def xml_member(archive, name):
    info = archive.getinfo(name)
    if info.file_size > XML_LIMIT or info.compress_size and info.file_size / info.compress_size > 1000:
        raise ValueError('Слишком большой XML внутри документа')
    content = archive.read(name)
    checked = content.replace(b'\x00',b'').upper()
    if b'<!DOCTYPE' in checked or b'<!ENTITY' in checked:
        raise ValueError('XML с DTD и сущностями не поддерживается')
    return ET.fromstring(content)


def text(element, prefix):
    return ''.join(node.text or '' for node in element.iter('{'+NS[prefix]+'}t'))[:4000]


def document_preview(path):
    if path.stat().st_size > INPUT_LIMIT:
        raise ValueError('Документ превышает лимит предпросмотра 64 МБ')
    ext = path.suffix.lower()
    output = {'kind':'document','blocks':[], 'truncated':False,
              'warnings':['Смысловое превью: оформление, изображения, макросы и формулы не воспроизводятся.']}
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > 10000:
            raise ValueError('Слишком много частей документа')
        if ext == '.docx':
            body = xml_member(archive, 'word/document.xml').find('w:body', NS)
            if body is None:
                return output
            total = 0
            for index, element in enumerate(body):
                if index >= 200 or total >= CHAR_LIMIT:
                    output['truncated'] = True
                    break
                if element.tag.endswith('}p'):
                    value = text(element, 'w')
                    output['blocks'].append({'type':'paragraph','text':value})
                    total += len(value)
                elif element.tag.endswith('}tbl'):
                    records = element.findall('w:tr', NS)
                    rows = []
                    table_chars = 0
                    for record in records[:50]:
                        cells = record.findall('w:tc', NS)
                        row = []
                        for cell in cells[:20]:
                            value = text(cell,'w')
                            remaining = max(0,CHAR_LIMIT-total-table_chars)
                            row.append(value[:remaining])
                            table_chars += len(row[-1])
                            if len(value)>remaining or not remaining:
                                output['truncated'] = True
                                break
                        rows.append(row)
                        output['truncated'] |= len(cells) > 20
                        if total+table_chars>=CHAR_LIMIT:break
                    output['truncated'] |= len(records) > 50
                    output['blocks'].append({'type':'table','rows':rows})
                    total += sum(len(c) for row in rows for c in row)
        elif ext == '.pptx':
            output.update(kind='slides', slides=[])
            names = [n for n in archive.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml') and n[16:-4].isdigit()]
            names.sort(key=lambda n:int(n[16:-4]))
            if 'ppt/presentation.xml' in archive.namelist() and 'ppt/_rels/presentation.xml.rels' in archive.namelist():
                presentation = xml_member(archive,'ppt/presentation.xml')
                relationships = xml_member(archive,'ppt/_rels/presentation.xml.rels')
                links = {r.get('Id'):r.get('Target','') for r in relationships if r.get('TargetMode')!='External'}
                ordered = []
                for slide in presentation.iter():
                    if slide.tag.endswith('}sldId'):
                        target = links.get(slide.get('{'+NS['r']+'}id'),'')
                        target = target.lstrip('/') if target.startswith('/') else 'ppt/'+target
                        if target in names:ordered.append(target)
                names = ordered
            output['truncated'] = len(names) > 30
            total = 0
            for slide_number,name in enumerate(names[:30],1):
                if total >= CHAR_LIMIT:
                    output['truncated'] = True
                    break
                slide = xml_member(archive, name)
                paragraphs = slide.findall('.//a:p', NS)
                values = [text(p,'a') for p in paragraphs[:100]]
                total += sum(len(v) for v in values)
                output['truncated'] |= len(paragraphs) > 100
                output['slides'].append({'number':slide_number,'text':values})
        elif ext == '.xlsx':
            output.update(kind='table', sheets=[])
            names = archive.namelist()
            strings = []
            if 'xl/sharedStrings.xml' in names:
                shared = xml_member(archive, 'xl/sharedStrings.xml')
                strings = [text(item,'s') for item in list(shared)[:30000]]
                output['truncated'] |= len(shared) > 30000
            workbook = xml_member(archive, 'xl/workbook.xml')
            rels = xml_member(archive, 'xl/_rels/workbook.xml.rels')
            links = {r.get('Id'):r.get('Target','') for r in rels if r.get('TargetMode') != 'External'}
            sheets = workbook.findall('s:sheets/s:sheet', NS)
            output['truncated'] |= len(sheets)>5
            total = 0
            for sheet in sheets[:5]:
                target = links.get(sheet.get('{'+NS['r']+'}id'),'')
                # Read only known workbook parts, never follow ZIP relationships outside worksheets.
                target = target.lstrip('/') if target.startswith('/') else 'xl/'+target
                if not target.startswith('xl/worksheets/') or '..' in Path(target).parts or not target.endswith('.xml'):
                    continue
                worksheet = xml_member(archive, target)
                records = worksheet.findall('s:sheetData/s:row',NS)
                rows = []
                for record in records[:200]:
                    row = ['']*30
                    last_column = 0
                    for cell in record.findall('s:c',NS):
                        ref = cell.get('r','')
                        column = 0
                        for character in ref:
                            if not 'A' <= character <= 'Z':break
                            column = column*26+ord(character)-64
                        if not 1 <= column <= 30:
                            output['truncated'] = True
                            continue
                        typ = cell.get('t')
                        value = cell.findtext('s:v','',NS)
                        if typ == 's':
                            try:value = strings[int(value)]
                            except (ValueError,IndexError):value = ''
                        elif typ == 'inlineStr':value = text(cell,'s')
                        elif typ == 'b':value = 'TRUE' if value == '1' else 'FALSE'
                        elif cell.find('s:f',NS) is not None and not value:value = '[формула: нет сохранённого значения]'
                        row[column-1] = value[:4000]
                        last_column = max(last_column,column)
                    rows.append(row[:last_column])
                    total += sum(len(c) for c in row)
                    if total >= CHAR_LIMIT:
                        output['truncated'] = True
                        break
                output['truncated'] |= len(records)>200
                output['sheets'].append({'name':sheet.get('name','Лист'),'rows':rows})
                if total >= CHAR_LIMIT:break
    return output


def csv_preview(path):
    with path.open('rb') as stream:
        content = stream.read(1024*1024+1)
    truncated = len(content)>1024*1024
    content = content[:1024*1024]
    try:decoded = content.decode('utf-8-sig')
    except UnicodeError:decoded = content.decode('cp1251', errors='replace')
    try:dialect = csv.Sniffer().sniff(decoded[:8192], delimiters=',;\t|')
    except csv.Error:dialect = csv.excel
    rows, chars = [], 0
    for index, row in enumerate(csv.reader(io.StringIO(decoded), dialect)):
        if index >= 200 or chars >= CHAR_LIMIT:
            truncated = True
            break
        truncated |= len(row)>30 or any(len(c)>4000 for c in row[:30])
        rows.append([c[:4000] for c in row[:30]])
        chars += sum(len(c) for c in rows[-1])
    return {'kind':'table','sheets':[{'name':path.name,'rows':rows}], 'truncated':truncated,
            'warnings':['Первые 200 строк и 30 столбцов; формулы отображаются как текст.']}


def raster_preview(path):
    """Existing Pillow composite or PDF-compatible AI via existing PyMuPDF. No native process."""
    if path.stat().st_size > INPUT_LIMIT:
        raise ValueError('Файл превышает лимит предпросмотра 64 МБ')
    from PIL import Image
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        if path.suffix.lower() == '.ai':
            with path.open('rb') as stream:
                if not stream.read(1024).lstrip().startswith(b'%PDF-'):
                    raise ValueError('AI без PDF-совместимого содержимого: откройте в Illustrator')
            import fitz
            with fitz.open(path) as document:
                if document.needs_pass or not document.page_count:
                    raise ValueError('Защищённый или пустой AI')
                page = document.load_page(0)
                ratio = min(1, 1280/max(page.rect.width,page.rect.height,1))
                pixmap = page.get_pixmap(matrix=fitz.Matrix(ratio,ratio), alpha=False)
                return pixmap.tobytes('png')
        with Image.open(path) as image:
            if image.width*image.height > 40_000_000:
                raise ValueError('Изображение слишком большое для встроенного превью')
            image.thumbnail((1280,1280))
            output = io.BytesIO()
            image.convert('RGB').save(output,format='PNG')
            return output.getvalue()


def model_json(path):
    """Return JSON document/chunk for validation before any model loader sees it."""
    if path.suffix.lower() == '.glb':
        with path.open('rb') as stream:
            header = stream.read(12)
            if len(header)!=12:raise ValueError('Некорректный GLB')
            magic, version, length = struct.unpack('<4sII',header)
            if magic!=b'glTF' or version!=2 or length!=path.stat().st_size:
                raise ValueError('Некорректный GLB')
            chunk = stream.read(8)
            if len(chunk)!=8:raise ValueError('Некорректный GLB JSON')
            size, chunk_type = struct.unpack('<II',chunk)
            if chunk_type!=0x4E4F534A or size>XML_LIMIT:
                raise ValueError('Некорректный или слишком большой GLB JSON')
            return json.loads(stream.read(size))
    if path.stat().st_size>XML_LIMIT:
        raise ValueError('GLTF JSON превышает 8 МБ')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rewrite_model_uris(value, transform, depth=0):
    if depth>64:
        raise ValueError('Слишком глубокий GLTF')
    if isinstance(value,dict):
        for key, child in value.items():
            if key=='uri':
                if not isinstance(child,str):raise ValueError('Некорректный URI в GLTF')
                value[key]=transform(child)
            else:rewrite_model_uris(child,transform,depth+1)
    elif isinstance(value,list):
        for child in value:rewrite_model_uris(child,transform,depth+1)
    return value
