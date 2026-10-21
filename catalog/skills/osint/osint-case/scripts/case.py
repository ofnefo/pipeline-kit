"""Create a local OSINT case folder and manifest. No network requests, lookups or scanning.

Example:
  python -X utf8 case.py --root cases --case-id own-domain-001 --target-class own \
      --scope "Domain example.org; passive sources only (CT logs, passive DNS, public pages)" \
      --authorized-by "<who authorised>" --authorization "<their words, date>"

Target classes: own (your own assets/accounts/identity), authorized-org (an organisation that gave written
authorisation), public-entity (a company or public body researched from public records only).
There is deliberately no class for private individuals.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

# Evidence contract (one JSON object per line in <case>/evidence.jsonl); validated by report.py.
EVIDENCE_REQUIRED = ['id', 'kind', 'statement', 'source_url_or_file', 'retrieved_at', 'tool', 'tool_version',
                     'confidence', 'verification_status']
EVIDENCE_OPTIONAL = ['source_sha256', 'limitations', 'related', 'notes']
TARGET_CLASSES = ('own', 'authorized-org', 'public-entity')


def create_case(root, case_id, scope, target_class, authorized_by=None, authorization=None):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,63}', case_id):
        raise ValueError('case-id must be 3..64 lowercase letters/digits/hyphens')
    if not scope.strip():
        raise ValueError('an explicit scope is required')
    if target_class not in TARGET_CLASSES:
        raise ValueError(f'target class must be one of {TARGET_CLASSES}')
    if bool((authorized_by or '').strip()) != bool((authorization or '').strip()):
        raise ValueError('--authorized-by and --authorization go together')
    if target_class == 'authorized-org' and not (authorization or '').strip():
        raise ValueError('an authorized-org case needs an authorization record')
    folder = Path(root) / case_id
    folder.mkdir(parents=True, exist_ok=False)  # never overwrite an existing case
    now = datetime.now(timezone.utc).isoformat()
    data = {'case_id': case_id, 'created_at': now, 'scope': scope, 'target_class': target_class,
            'status': 'prepared', 'network_actions_executed': False,
            'authorization': ({'by': authorized_by.strip(), 'basis': authorization.strip(), 'recorded_at': now}
                              if authorized_by else None),
            'collection_mode': 'passive',
            'evidence_file': 'evidence.jsonl', 'raw_dir': 'raw', 'reports_dir': 'reports',
            'observation_fields': EVIDENCE_REQUIRED + EVIDENCE_OPTIONAL}
    (folder / 'raw').mkdir()
    (folder / 'reports').mkdir()
    (folder / 'case.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
    return folder


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', required=True, type=Path, help='folder that holds cases (keep it out of version control)')
    ap.add_argument('--case-id', required=True)
    ap.add_argument('--scope', required=True, help='concrete targets and allowed checks')
    ap.add_argument('--target-class', required=True, choices=TARGET_CLASSES)
    ap.add_argument('--authorized-by', help='who authorised the case')
    ap.add_argument('--authorization', help="basis of authorisation in the authoriser's own words, with date")
    a = ap.parse_args(argv)
    try:
        print(create_case(a.root, a.case_id, a.scope, a.target_class, a.authorized_by, a.authorization))
    except (OSError, ValueError) as exc:
        ap.exit(2, f'error: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
