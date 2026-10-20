"""Read-only checks shared by project diagnostics and production reconciliation."""
from __future__ import annotations

import csv
import hashlib
import json
import posixpath
import re
import zipfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def relative_file(project: Path, value: str) -> Path:
    if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
        raise ValueError('Expected a project-relative path')
    path = (project / value).resolve()
    if not path.is_relative_to(project.resolve()):
        raise ValueError(f'Path escapes project: {value}')
    return path


def schema_errors(data, schema_path: Path) -> list[str]:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        return ['JSON Schema validator unavailable: install plugin requirements.txt into the core Python environment']
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [f"{'.'.join(map(str, e.absolute_path)) or '$'}: {e.message}"
            for e in sorted(validator.iter_errors(data), key=lambda e: str(list(e.absolute_path)))]


def decimal(text, field: str) -> Decimal:
    if text is None or isinstance(text, bool) or not str(text).strip():
        raise ValueError(f'{field}: missing decimal')
    try:
        value = Decimal(str(text).replace(' ', '').replace(',', '.'))
    except InvalidOperation as exc:
        raise ValueError(f'{field}: invalid decimal') from exc
    if not value.is_finite():
        raise ValueError(f'{field}: non-finite decimal')
    return value


DOCUMENT_STATUSES = {'planned', 'drafting', 'review', 'approved', 'issued', 'superseded', 'archived'}
PAYMENT_STATUSES = {'PLANNED', 'TO_PAY', 'QUEUED', 'PAID', 'CANCELLED'}


def register_rows(path: Path, kind: str, project: Path, estimate: dict, late: bool):
    errors, warnings, rows = [], [], []
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            errors.append(f'{path.name}: duplicate columns')
        for row_number, row in enumerate(reader, 2):
            if not any(row.values()):
                continue
            label = f'{path.name}:{row_number}'
            if None in row or any(value is None for value in row.values()):
                errors.append(f'{label}: column count differs from header')
                continue
            row = {key: value.strip() for key, value in row.items()}
            rows.append(row)
            key = 'payment_id' if kind == 'payments_register' else 'document_id'
            if not row.get(key):
                errors.append(f'{label}: missing {key}')
            if kind == 'payments_register':
                try:
                    decimal(row.get('amount'), f'{label}.amount')
                except ValueError as exc:
                    errors.append(str(exc))
                if row.get('status', '').upper() not in PAYMENT_STATUSES:
                    errors.append(f'{label}: invalid payment status')
                if row.get('source', '').upper() not in {'OWN', 'CREDIT', 'CUSTOMER_ADVANCE'}:
                    errors.append(f'{label}: invalid payment source')
                for field in ('planned_date', 'paid_date', 'credit_start_date'):
                    if row.get(field):
                        try:
                            date.fromisoformat(row[field])
                        except ValueError:
                            errors.append(f'{label}: invalid {field}')
                if row.get('status', '').upper() == 'PAID' and not row.get('paid_date'):
                    errors.append(f'{label}: PAID requires paid_date')
                if row.get('status', '').upper() not in {'PAID', 'CANCELLED'} and not row.get('planned_date'):
                    (errors if late else warnings).append(f'{label}: missing planned_date')
                if not row.get('contractor'):
                    (errors if late else warnings).append(f'{label}: missing contractor')
            else:
                status = row.get('status')
                if status not in DOCUMENT_STATUSES:
                    errors.append(f'{label}: invalid document status')
                if status in {'superseded', 'archived'}:
                    continue
                for field in ('owner', 'title', 'type', 'source_refs'):
                    if not row.get(field):
                        (errors if late else warnings).append(f'{label}: missing {field}')
                version = (estimate.get('version') or {}).get('id')
                if row.get('estimate_version') and row['estimate_version'] != version:
                    (errors if late else warnings).append(f'{label}: stale estimate_version {row["estimate_version"]}; active {version}')
                elif late and not row.get('estimate_version'):
                    errors.append(f'{label}: missing estimate_version')
                for field in ('native_file', 'pdf_file'):
                    value = row.get(field)
                    if not value:
                        if late or status in {'review', 'approved', 'issued'}:
                            errors.append(f'{label}: missing {field}')
                        continue
                    try:
                        if not relative_file(project, value).is_file():
                            errors.append(f'{label}: missing file {value}')
                    except ValueError as exc:
                        errors.append(f'{label}: {exc}')
                if status in {'approved', 'issued'} and row.get('approval') not in {'internal', 'client', 'legal', 'signed'}:
                    errors.append(f'{label}: approved/issued document lacks approval')
    key = 'payment_id' if kind == 'payments_register' else 'document_id'
    identifiers = [row.get(key) for row in rows if row.get(key)]
    for identifier in sorted(set(identifiers)):
        if identifiers.count(identifier) > 1:
            errors.append(f'{path.name}: duplicate {key} {identifier}')
    return rows, errors, warnings


def reconcile_payments(rows: list[dict], payments: list[dict]) -> list[str]:
    """Neither representation silently overrides the other; compare by stable id."""
    fields = ('contractor', 'purpose', 'amount', 'source', 'status', 'planned_date', 'paid_date', 'credit_start_date')
    def normalized(entries, id_key):
        result = {}
        for row in entries:
            if not isinstance(row, dict) or not row.get(id_key):
                raise ValueError(f'payments: missing {id_key}')
            key = str(row[id_key])
            if key in result:
                raise ValueError(f'payments: duplicate {key}')
            values = {field: str(row.get(field) or '').strip() for field in fields}
            values['amount'] = decimal(values['amount'], f'payments.{key}.amount')
            for field in ('source', 'status'):
                values[field] = values[field].upper()
            result[key] = values
        return result
    try:
        left, right = normalized(rows, 'payment_id'), normalized(payments, 'id')
    except ValueError as exc:
        return [str(exc)]
    errors = []
    for key in sorted(left.keys() | right.keys()):
        if key not in left or key not in right:
            errors.append(f'payments mismatch: {key} missing from CSV or estimate JSON')
        else:
            for field in fields:
                if left[key][field] != right[key][field]:
                    errors.append(f'payments mismatch: {key}.{field}')
    return errors


def workbook_cells(path: Path):
    """Read formulas/cached values only. Never execute macros, links or formulas."""
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    rel_ns = '{http://schemas.openxmlformats.org/package/2006/relationships}'
    cells, errors = {}, []
    with zipfile.ZipFile(path) as archive:
        rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {r.attrib['Id']: r.attrib['Target'] for r in rels.findall(f'{rel_ns}Relationship') if r.get('TargetMode') != 'External'}
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared = [''.join(t.text or '' for t in node.findall('.//s:t', ns))
                      for node in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        root = ET.fromstring(archive.read('xl/workbook.xml'))
        for sheet in root.findall('s:sheets/s:sheet', ns):
            rel_id = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target = targets[rel_id]
            member = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
            if not member.startswith('xl/'):
                raise ValueError('Workbook worksheet path escapes xl/')
            sheet_root = ET.fromstring(archive.read(member))
            hidden_rows = {row.get('r') for row in sheet_root.findall('s:sheetData/s:row', ns) if row.get('hidden') in {'1', 'true'}}
            hidden_cols = [(int(col.get('min')), int(col.get('max'))) for col in sheet_root.findall('s:cols/s:col', ns) if col.get('hidden') in {'1', 'true'}]
            for cell in sheet_root.findall('.//s:sheetData/s:row/s:c', ns):
                key = (sheet.attrib['name'], cell.attrib['r'])
                formula, value = cell.find('s:f', ns), cell.find('s:v', ns)
                cells[key] = {'formula': formula is not None, 'value': value.text if value is not None else None, 'type': cell.get('t')}
                match = re.fullmatch(r'([A-Z]+)([1-9][0-9]*)', key[1])
                if not match:
                    raise ValueError('Invalid workbook cell reference')
                column = 0
                for char in match[1]:
                    column = column * 26 + ord(char) - 64
                text_value = None
                if cell.get('t') == 'inlineStr':
                    text_value = ''.join(t.text or '' for t in cell.findall('s:is//s:t', ns))
                elif cell.get('t') == 's' and value is not None:
                    index = int(value.text)
                    if not 0 <= index < len(shared):
                        raise ValueError('Invalid shared string index')
                    text_value = shared[index]
                elif cell.get('t') == 'str' and formula is None:
                    text_value = value.text if value is not None else None
                cells[key].update(formula_text=formula.text if formula is not None else None,
                                  formula_kind=formula.get('t', 'normal') if formula is not None else None,
                                  text_value=text_value,
                                  hidden=sheet.get('state', 'visible') != 'visible' or match[2] in hidden_rows or any(a <= column <= b for a, b in hidden_cols))
                if cell.get('t') == 'e':
                    errors.append(f'Workbook formula error: {key[0]}!{key[1]}')
                if formula is not None and (value is None or value.text is None):
                    errors.append(f'Workbook formula has no cached value: {key[0]}!{key[1]}')
    return cells, errors


def reconcile_workbook(project: Path, workbook: Path, mapping: dict, calculation: dict):
    checks = []
    cells, errors = workbook_cells(workbook)
    entries = mapping.get('checks')
    if not isinstance(entries, list) or not entries:
        return {'status': 'blocked', 'blockers': ['workbook_map.checks must be a non-empty array'], 'checks': []}
    import spreadsheet_findings
    findings = spreadsheet_findings.audit(workbook, mapping, cells)
    errors.extend(f"{item['code']}: {item['sheet']}!{item['cell_or_range']}" for item in findings if item['severity'] == 'error')
    covered = set()
    for entry in entries:
        try:
            target = entry['oracle']
            if not isinstance(target, str):
                raise ValueError('oracle must be a dotted path')
            expected = calculation
            for part in target.split('.'):
                expected = expected[int(part)] if isinstance(expected, list) else expected[part]
            expected = decimal(expected, target)
            ref = (entry['sheet'], entry['cell'])
            cell = cells.get(ref)
            if not cell or cell['type'] in {'s', 'str', 'b', 'inlineStr', 'e'}:
                raise ValueError(f'{ref}: missing numeric cell')
            if entry.get('formula', True) and not cell['formula']:
                raise ValueError(f'{ref}: expected formula')
            actual = decimal(cell['value'], str(ref))
            # Compare rounded money exactly; a one-kopeck difference is a blocker.
            precision = Decimal('0.000001') if target.endswith('.margin') else Decimal('0.01')
            from decimal import ROUND_HALF_UP
            match = actual.quantize(precision, rounding=ROUND_HALF_UP) == expected.quantize(precision, rounding=ROUND_HALF_UP)
            checks.append({'oracle': target, 'sheet': ref[0], 'cell': ref[1], 'expected': str(expected), 'actual': str(actual), 'ok': match})
            covered.add(target)
            if not match:
                errors.append(f'Workbook mismatch: {target} at {ref[0]}!{ref[1]}')
        except (ValueError, KeyError, TypeError, IndexError, InvalidOperation) as exc:
            errors.append(f'Invalid workbook check: {exc}')
    required = {'financial_result.' + key for key in ('contract_price', 'estimate_total', 'net_profit', 'margin')}
    required |= {f'items.{i}.amount' for i in range(len(calculation.get('items', [])))}
    for missing in sorted(required - covered):
        errors.append(f'Workbook map misses {missing}')
    return {'status': 'blocked' if errors else 'pass', 'blockers': errors, 'checks': checks,
            'workbook_sha256': digest(workbook), 'findings': findings, 'note': 'Cached values compared; freshness requires hash-bound recalculation evidence.'}


def check_evidence(project: Path, evidence: dict, required_paths: set[str]) -> list[str]:
    errors = []
    records = evidence.get('artifacts')
    if not isinstance(records, list):
        return ['qa_evidence.artifacts must be an array']
    covered = set()
    for record in records:
        try:
            if not isinstance(record, dict):
                raise ValueError('artifact evidence must be an object')
            path = relative_file(project, record.get('path'))
            if not path.is_file() or record.get('sha256') != digest(path):
                raise ValueError(f'{record.get("path")}: stale/missing artifact')
            if record.get('visual_status') != 'pass' or not record.get('reviewer') or not record.get('reviewed_at'):
                raise ValueError(f'{record.get("path")}: missing visual review')
            proof = relative_file(project, record.get('evidence_file'))
            if not proof.is_file() or record.get('evidence_sha256') != digest(proof):
                raise ValueError('missing/stale visual evidence file')
            if path.suffix.lower() == '.xlsx' and not record.get('recalculated_by'):
                raise ValueError('workbook needs recalculated_by')
            covered.add(path)
        except (ValueError, TypeError, OSError) as exc:
            errors.append(f'QA: {exc}')
    for value in required_paths:
        if relative_file(project, value) not in covered:
            errors.append(f'QA: no current evidence for {value}')
    return errors
