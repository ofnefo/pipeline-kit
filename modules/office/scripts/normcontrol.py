"""Validate bounded, hash-bound normcontrol evidence. No blanket certification."""
import json
from pathlib import Path
import project_checks as quality

def validate(project,config):
    result={'configured':'normcontrol' in config,'errors':[],'pending':[],'certification':False,'coverage':[]}
    if not result['configured']: return result
    def verified(ref):
        if not isinstance(ref,dict) or set(ref)-{'path','sha256','location'} or not {'path','sha256'}<=set(ref):
            raise ValueError('Evidence reference requires path and sha256')
        path=quality.relative_file(project,ref['path'])
        if quality.digest(path)!=ref['sha256']: raise ValueError('Missing/stale evidence: '+ref['path'])
        return path
    try:
        path=verified(config['normcontrol'])
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        invalid=quality.schema_errors(data,Path(__file__).with_name('schemas')/'normcontrol.schema.json')
        if invalid: raise ValueError('; '.join(invalid))
        if data['project_code']!=config['project']['code']: raise ValueError('Normcontrol belongs to another project')
        seen=set()
        for row in data['requirements']:
            key=row['id']
            if key in seen: raise ValueError('Duplicate requirement id: '+key)
            seen.add(key)
            verified(row['artifact'])
            for proof in row['evidence']: verified(proof)
            standard=row['standard']
            if standard['verification_source'] is not None: verified(standard['verification_source'])
            result['coverage'].append({'id':key,'artifact':row['artifact'],'locations':row['locations'],'coverage':row['coverage'],'state':row['state']})
            if row['applicability']=='not_applicable':
                if row['state']!='not_applicable': raise ValueError(key+': applicability/state conflict')
                if not row['reviewer'] or not row['checked_at']: result['pending'].append(key+': applicability not reviewed')
                continue
            if row['applicability']=='undetermined': result['pending'].append(key+': applicability undetermined')
            if row['state']=='not_applicable': raise ValueError(key+': applicability/state conflict')
            if row['state'] in {'conforming','nonconformity'} and (not row['reviewer'] or not row['checked_at'] or not row['evidence']):
                raise ValueError(key+': checked state requires reviewer, date and evidence')
            if row['state']!='conforming': result['pending'].append(key+': '+row['state'])
            if standard['source_verification']!='verified' or standard['verification_source'] is None or any(standard[k] is None for k in ['identifier','edition','authoritative_url','clause']):
                result['pending'].append(key+': standard source/edition/clause not verified')
            if row['coverage']=='sample': result['pending'].append(key+': sample only; full declared requirement remains unverified')
    except (OSError,ValueError,TypeError,KeyError) as exc:
        result['errors'].append('Normcontrol: '+str(exc))
    return result
