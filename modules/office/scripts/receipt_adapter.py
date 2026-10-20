"""Deterministic receipt validation after docparse; no OCR, models or bookkeeping."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

VERSION = '1.0.0'
SCHEMA = Path(__file__).with_name('receipt-candidate.schema.json')
MONEY = ('unit_price', 'discount', 'total')


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(path: Path):
    def invalid_constant(value):
        raise ValueError('Non-finite JSON number: ' + value)
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_object, parse_constant=invalid_constant)


def template() -> dict:
    return {'schema_version':1, 'provenance':{'source_path':None,'source_sha256':None,'page_count':None},
            'merchant':{'name':None,'pages':[]}, 'date':{'value':None,'pages':[]},
            'currency':{'value':None,'pages':[]}, 'items':[],
            'totals':{'subtotal':None,'discount':None,'total':None,'pages':[]},'ambiguities':[]}


def decimal(value: str) -> Decimal:
    return Decimal(re.sub(r'[ \u00a0\u202f]', '', value).replace(',', '.'))


def adapt(*, candidates: Path | None = None, document_json: Path | None = None,
          document_md: Path | None = None, source: Path | None = None) -> dict:
    result = {'schema':'office-receipt-validation/1', 'tool_version':VERSION,
              'created_utc':datetime.now(timezone.utc).isoformat(), 'quality':'needs_review',
              'validation':'needs_review', 'financial_approval':False,
              'inputs':[], 'issues':[], 'receipt':None, 'calculations':{}}

    def issue(code, field, detail):
        result['issues'].append({'code':code, 'field':field, 'detail':detail})

    def record(path, role):
        path = Path(path).resolve()
        try:
            result['inputs'].append({'role':role,'path':str(path),'sha256':digest(path)})
        except OSError:
            issue('input_unavailable',role,'Input file cannot be read')
        return path

    doc = None
    if document_json is not None:
        document_json = record(document_json, 'document_json')
        try:
            doc = read_json(document_json)
            if not isinstance(doc, dict) or doc.get('schema') != 'office-docparse/1':
                raise ValueError('Expected office-docparse/1 object')
            if not isinstance(doc.get('source'), dict) or not isinstance(doc.get('outputs'), dict):
                raise ValueError('source and outputs must be objects')
            if not isinstance(doc['source'].get('path'), str) or not doc['source']['path'].strip():
                raise ValueError('Missing source.path')
            if not isinstance(doc['source'].get('sha256'), str) or not re.fullmatch('[a-fA-F0-9]{64}',doc['source']['sha256']):
                raise ValueError('Missing/invalid source.sha256')
            if doc.get('pages') is not None and (not isinstance(doc['pages'], dict) or type(doc['pages'].get('count')) is not int or doc['pages']['count'] < 1):
                raise ValueError('Invalid pages.count')
            if not isinstance(doc.get('quality'), str):
                raise ValueError('quality must be a string')
            if doc.get('quality') not in {'needs_review', 'pass'}:
                issue('extraction_quality','document_json.quality','Extraction is empty or has unknown quality')
            if not isinstance(doc.get('warnings', []), list):
                raise ValueError('warnings must be an array')
            if doc.get('warnings'):
                issue('extraction_warnings','document_json.warnings','Extraction contains warnings; inspect the original record')
        except (OSError, UnicodeError, ValueError) as exc:
            issue('malformed_extraction','document_json',str(exc))
            doc = None
        if document_md is None:
            document_md = document_json.with_name('document.md')

    if document_md is not None:
        document_md = record(document_md, 'document_md')
        try:
            if not document_md.read_text(encoding='utf-8-sig').strip():
                issue('empty_extraction','document_md','No extracted text')
            if doc is not None:
                expected = doc['outputs'].get('document.md')
                if not isinstance(expected, str) or expected.lower() != digest(document_md):
                    issue('extraction_hash_mismatch','document_md','Markdown does not match docparse output hash')
        except (OSError, UnicodeError) as exc:
            issue('malformed_extraction','document_md',str(exc))

    candidate = template()
    if candidates is not None:
        candidates = record(candidates, 'candidates')
        try:
            candidate = read_json(candidates)
        except (OSError, UnicodeError, ValueError) as exc:
            issue('malformed_candidates','candidates',str(exc))
            candidate = None
    else:
        issue('manual_fields_required','receipt','Extract fields explicitly; this adapter does not infer values from OCR text')
        if doc is not None:
            candidate['provenance'] = {'source_path':doc['source'].get('path'),
                'source_sha256':doc['source'].get('sha256'), 'page_count':(doc.get('pages') or {}).get('count')}

    validator = Draft202012Validator(read_json(SCHEMA), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(candidate), key=lambda error: str(list(error.path)))
    for error in errors:
        issue('schema', '.'.join(map(str,error.path)) or 'receipt', error.message)
    if errors:
        return result
    candidate = deepcopy(candidate)
    result['receipt'] = candidate
    provenance = candidate['provenance']
    for name, value in provenance.items():
        if value is None:
            issue('missing_provenance','provenance.'+name,'No declared source provenance')
    if provenance['source_sha256']:
        provenance['source_sha256'] = provenance['source_sha256'].lower()
    if doc is not None:
        for name, declared in [('source_path',doc['source'].get('path')),('source_sha256',doc['source'].get('sha256')),
                               ('page_count',(doc.get('pages') or {}).get('count'))]:
            actual = provenance[name]
            if name == 'source_sha256' and isinstance(declared, str):
                declared = declared.lower()
            if declared is not None and actual != declared:
                issue('provenance_conflict','provenance.'+name,'Candidate disagrees with docparse provenance')
    if source is None:
        issue('source_not_verified','provenance','Pass --source explicitly to verify source bytes')
    else:
        source = record(source, 'source')
        try:
            if provenance['source_sha256'] != digest(source):
                issue('source_hash_mismatch','provenance.source_sha256','Explicit source does not match declared SHA-256')
            if provenance['source_path'] and Path(provenance['source_path']).resolve() != source:
                issue('source_path_mismatch','provenance.source_path','Explicit source path differs from declared path')
        except (OSError, ValueError):
            issue('source_not_verified','provenance','Cannot verify explicit source')

    def check_pages(section, field):
        pages = section['pages']
        if not pages:
            issue('missing_pages',field+'.pages','Record pages used for these values')
        if provenance['page_count'] is not None and any(p > provenance['page_count'] for p in pages):
            issue('page_out_of_range',field+'.pages','Page exceeds declared page_count')

    for name in ('merchant','date','currency','totals'):
        check_pages(candidate[name], name)
    for name, key in [('merchant','name'),('date','value'),('currency','value')]:
        if candidate[name][key] is None or not candidate[name][key].strip():
            issue('unreadable',name+'.'+key,'Value is missing; do not guess')
    if candidate['currency']['value'] in {'руб','руб.','₽'}:
        candidate['currency']['value'] = 'RUB'
    for ambiguity in candidate['ambiguities']:
        issue('ambiguous','ambiguities',ambiguity)
    if not candidate['items']:
        issue('missing_items','items','No explicit receipt line items')

    def normalize(section, keys, field):
        for key in keys:
            value = section[key]
            if value is None:
                issue('unreadable',field+'.'+key,'Value is missing; do not substitute zero')
            else:
                section[key] = format(decimal(value), '.2f') if key != 'quantity' else format(decimal(value), 'f')

    with localcontext() as context:
        context.prec = 64
        line_totals = []
        for index, item in enumerate(candidate['items']):
            field = f'items.{index}'
            check_pages(item, field)
            if item['description'] is None or not item['description'].strip():
                issue('unreadable',field+'.description','Item description is unreadable')
            normalize(item, ('quantity', *MONEY), field)
            if item['quantity'] is not None and Decimal(item['quantity']) <= 0:
                issue('quantity_nonpositive',field+'.quantity','Quantity must be positive for a sale receipt')
            if all(item[key] is not None for key in ('quantity',*MONEY)):
                gross = (Decimal(item['quantity']) * Decimal(item['unit_price'])).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                expected = gross - Decimal(item['discount'])
                if expected < 0:
                    issue('discount_exceeds_gross',field+'.discount','Line discount exceeds gross price')
                if expected != Decimal(item['total']):
                    issue('line_total_mismatch',field+'.total','quantity × unit_price − line discount differs from line total')
                result['calculations'][field+'.expected_total'] = format(expected, '.2f')
            if item['total'] is not None:
                line_totals.append(Decimal(item['total']))
        totals = candidate['totals']
        normalize(totals, ('subtotal','discount','total'), 'totals')
        if candidate['items'] and len(line_totals) == len(candidate['items']):
            summed = sum(line_totals, Decimal('0'))
            result['calculations']['sum_line_totals'] = format(summed,'.2f')
            if totals['subtotal'] is not None and summed != Decimal(totals['subtotal']):
                issue('subtotal_mismatch','totals.subtotal','Sum of discounted line totals differs from subtotal')
        if all(totals[key] is not None for key in ('subtotal','discount','total')):
            expected = Decimal(totals['subtotal']) - Decimal(totals['discount'])
            result['calculations']['expected_total'] = format(expected,'.2f')
            if expected < 0:
                issue('discount_exceeds_subtotal','totals.discount','Receipt discount exceeds subtotal')
            if expected != Decimal(totals['total']):
                issue('total_mismatch','totals.total','Subtotal − receipt discount differs from total')
    if not result['issues']:
        result['validation'] = 'passed'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Validate receipt candidates locally; no inference or financial approval.')
    parser.add_argument('--candidates', type=Path)
    parser.add_argument('--document-json', type=Path)
    parser.add_argument('--document-md', type=Path)
    parser.add_argument('--source', type=Path, help='Explicit local source to verify; paths inside extraction are never opened automatically.')
    parser.add_argument('--output', type=Path, required=True, help='New JSON file; existing files cannot be overwritten.')
    parser.add_argument('--template', action='store_true', help='Write an empty candidate form; never fills unreadable values.')
    args = parser.parse_args(argv)
    if args.template and any((args.candidates,args.document_json,args.document_md,args.source)):
        parser.error('--template cannot be combined with input files')
    if not args.template and not any((args.candidates,args.document_json,args.document_md)):
        parser.error('Choose --candidates, --document-json or --document-md')
    try:
        output = args.output.resolve()
        if output.suffix.lower() != '.json':
            raise ValueError('Output must be a new .json file')
        result = template() if args.template else adapt(candidates=args.candidates, document_json=args.document_json,
            document_md=args.document_md, source=args.source)
        with output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print(json.dumps({'output':str(output),'sha256':digest(output), 'validation':result.get('validation','template'),
                          'quality':result.get('quality','needs_review'),'financial_approval':False}, ensure_ascii=False))
        return 0 if args.template or result['validation'] == 'passed' else 2
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({'error':str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
