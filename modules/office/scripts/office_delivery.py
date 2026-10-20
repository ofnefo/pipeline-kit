"""Explicit, QA-gated PDF delivery through the shared Pipeline Control outbox."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path





def load_outbox(config_path=None):
    raise RuntimeError('Messaging delivery is not bundled. Export and review files locally.')


def plan_delivery(office, project: Path, document_ids: list[str]) -> dict:
    project = project.resolve()
    if not document_ids or len(document_ids) > 30:
        raise ValueError('Choose 1..30 document IDs explicitly')
    if len(set(document_ids)) != len(document_ids):
        raise ValueError('Duplicate document IDs')
    diagnostic = office.diagnose(project)
    if diagnostic.get('current_gate') != 'delivery':
        raise ValueError('Delivery requires current_gate=delivery')
    if diagnostic.get('delivery_readiness') != 'ready_for_authorized_delivery':
        raise ValueError('Delivery blocked: ' + '; '.join(diagnostic.get('delivery_blockers') or diagnostic.get('blockers') or ['not ready']))
    config = office.load_json(project / office.PROJECT_FILE)
    files = config['files']
    estimate_path = office.safe_relative(project, files['estimate_json'], field='estimate_json')
    estimate = office.load_json(estimate_path)
    register = office.safe_relative(project, files['documents_register'], field='documents_register')
    rows, errors, _ = office.quality.register_rows(register, 'documents_register', project, estimate, True)
    if errors:
        raise ValueError('; '.join(errors))
    by_id = {row['document_id']: row for row in rows}
    artifacts, paths, hashes = [], set(), set()
    for identifier in sorted(document_ids):
        row = by_id.get(identifier)
        if not row or row.get('status') not in {'approved', 'issued'}:
            raise ValueError(f'Document {identifier}: not an active final document')
        if row.get('estimate_sha256') != office.quality.digest(estimate_path):
            raise ValueError(f'Document {identifier}: stale estimate hash')
        path = office.safe_relative(project, row['pdf_file'], field=f'{identifier}.pdf_file')
        if path.suffix.lower() != '.pdf' or not path.is_file():
            raise ValueError(f'Document {identifier}: requires a final PDF')
        if path.relative_to(project).parts[0] in {'00_ВХОДЯЩИЕ', '99_АРХИВ'}:
            raise ValueError(f'Document {identifier}: incoming/archive file cannot be delivered')
        size = path.stat().st_size
        if not 0 < size <= 48 * 1024**2:
            raise ValueError(f'Document {identifier}: PDF empty or exceeds 48 MiB')
        digest = office.quality.digest(path)
        if path in paths or digest in hashes:
            raise ValueError('Duplicate selected PDF path or content')
        paths.add(path)
        hashes.add(digest)
        artifacts.append({'document_id': identifier, 'path': str(path), 'sha256': digest, 'bytes': size})
    # Bind the selection to QA again after reading the register and file hashes.
    evidence = office.load_json(office.safe_relative(project, files['qa_evidence'], field='qa_evidence'))
    errors = office.quality.check_evidence(project, evidence, {str(Path(a['path']).relative_to(project)) for a in artifacts})
    if errors:
        raise ValueError('; '.join(errors))
    return {'schema_version': 1, 'project': str(project), 'project_code': config['project']['code'],
            'project_name': config['project']['name'], 'current_gate': 'delivery',
            'delivery_readiness': 'ready_for_authorized_delivery', 'documents': artifacts,
            'delivery_dir': str(office.safe_relative(project, files['delivery_dir'], field='delivery_dir'))}


def deliver(office, project: Path, document_ids: list[str], *, dry_run=False, local_only=False, outbox_factory=None) -> dict:
    plan = plan_delivery(office, project, document_ids)
    receipt = {**plan, 'created_utc': datetime.now(timezone.utc).isoformat(),
               'status': 'local_only' if local_only else 'dry_run' if dry_run else 'prepared'}
    if local_only or dry_run:
        return receipt  # No outbox import, no receipt/snapshot writes.
    # Stable caption and sorted selection preserve the outbox's publication identity.
    title = 'Office: ' + plan['project_code'] + ' — ' + ', '.join(a['document_id'] for a in plan['documents'])
    receipt_dir = Path(plan['delivery_dir']) / 'delivery-receipts'
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / (uuid.uuid4().hex + '.json')
    receipt['receipt'] = str(receipt_path)

    def save():
        temporary = receipt_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, receipt_path)

    save()
    try:
        # Freeze only selected, QA-bound bytes before calling the public API. This
        # closes the source-change window between QA and the outbox's snapshot.
        with tempfile.TemporaryDirectory(prefix='office-delivery-', dir=plan['delivery_dir']) as temporary:
            snapshots = []
            for index, artifact in enumerate(plan['documents']):
                source = Path(artifact['path'])
                content = source.read_bytes()
                if hashlib.sha256(content).hexdigest() != artifact['sha256']:
                    raise ValueError('Selected PDF changed after QA; run preflight again')
                snapshot = Path(temporary) / str(index) / source.name
                snapshot.parent.mkdir()
                snapshot.write_bytes(content)
                snapshots.append(snapshot)
            outbox = (outbox_factory or load_outbox)()
            receipt['outbox'] = outbox.enqueue(snapshots, title, project=plan['project_name'], pipeline='office')
        receipt['status'] = 'duplicate' if receipt['outbox'].get('duplicate') else 'enqueued'
        save()
        return receipt
    except Exception as exc:
        # An exception can occur after an outbox commit. Preserve evidence and
        # never retry automatically or describe enqueue as Telegram delivery.
        receipt['status'] = 'enqueue_failed_check_outbox'
        receipt['error'] = type(exc).__name__ + ': ' + str(exc)
        save()
        raise RuntimeError(f'Delivery not confirmed; inspect receipt {receipt_path}: {exc}') from exc
