"""Extract one local source into an immutable, content-addressed project packet."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


def extract(source: Path, backend: str):
    suffix = source.suffix.lower()
    if backend == 'markitdown':
        try:
            from markitdown import MarkItDown
        except ImportError as exc:
            raise ValueError('MarkItDown is optional and not installed in this Python environment') from exc
        return [{'locator': 'document', 'text': MarkItDown(enable_plugins=False).convert_local(str(source)).text_content}]
    if suffix in {'.txt', '.md', '.csv', '.json'}:
        return [{'locator': f'line:{i}', 'text': text} for i, text in enumerate(source.read_text(encoding='utf-8-sig').splitlines(), 1)]
    if suffix == '.docx':
        ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        with zipfile.ZipFile(source) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
        return [{'locator': f'paragraph:{i}', 'text': ''.join(t.text or '' for t in p.iter(f'{ns}t'))}
                for i, p in enumerate(root.iter(f'{ns}p'), 1)]
    if suffix == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError('Install pypdf in this Python environment for PDF extraction') from exc
        return [{'locator': f'page:{i}', 'text': page.extract_text() or ''} for i, page in enumerate(PdfReader(source).pages, 1)]
    raise ValueError(f'No built-in extractor for {suffix}; use format skill or --backend markitdown')


def run(project: Path, source: Path, backend='builtin', packet_root='00_ИЗВЛЕЧЕНИЕ'):
    project, source = project.resolve(), source.resolve()
    if not source.is_relative_to(project) or not source.is_file():
        raise ValueError('Source must be an existing file within the project')
    fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()
    identity = hashlib.sha256((str(source.relative_to(project)) + fingerprint + backend + 'v1').encode()).hexdigest()
    if Path(packet_root).is_absolute() or '..' in Path(packet_root).parts:
        raise ValueError('--packet-root must be a project-relative folder')
    packet = project / packet_root / identity
    if packet.exists():
        record = json.loads((packet / 'source.json').read_text(encoding='utf-8'))
        for name, expected in record['outputs'].items():
            if hashlib.sha256((packet / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Cached extraction changed; preserve it and use a new extraction version')
        return packet
    fragments = extract(source, backend)
    if hashlib.sha256(source.read_bytes()).hexdigest() != fingerprint:
        raise ValueError('Source changed during extraction; retry')
    packet.mkdir(parents=True, exist_ok=False)
    text = '\n\n'.join(f'[{f["locator"]}]\n{f["text"]}' for f in fragments)
    (packet / 'text.md').write_text(text, encoding='utf-8')
    (packet / 'fragments.json').write_text(json.dumps(fragments, ensure_ascii=False, indent=2), encoding='utf-8')
    record = {'schema_version': 1, 'source': source.relative_to(project).as_posix(), 'source_sha256': fingerprint,
              'backend': backend, 'extractor_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
              'quality': 'needs_review' if any(f['text'].strip() for f in fragments) else 'needs_ocr',
              'limitations': 'Extraction is unverified data. DOCX locators are paragraphs, not pages; PDF table structure is not guaranteed.',
              'outputs': {name: hashlib.sha256((packet / name).read_bytes()).hexdigest() for name in ('text.md', 'fragments.json')}}
    (packet / 'source.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return packet


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--backend', choices=('builtin', 'markitdown'), default='builtin')
    parser.add_argument('--packet-root', default='00_ИЗВЛЕЧЕНИЕ', help='project-relative folder for extraction packets')
    args = parser.parse_args()
    try:
        print(run(args.project, args.source, args.backend, args.packet_root))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
