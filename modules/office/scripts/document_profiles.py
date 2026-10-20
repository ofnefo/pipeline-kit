"""Read-only, project-bound organization/template checks. Never approve documents."""
from __future__ import annotations
import json
from pathlib import Path
import project_checks as quality

SCHEMAS=Path(__file__).with_name('schemas')

def validate(project: Path, config: dict) -> dict:
    errors, pending, evidence = [], [], []
    settings=config.get('document_profiles')
    if settings is None:
        return {'configured':False,'errors':errors,'pending':pending,'evidence':evidence}
    invalid=quality.schema_errors(settings,SCHEMAS/'document-profiles.schema.json')
    if invalid:
        return {'configured':True,'errors':['document_profiles: '+s for s in invalid],'pending':pending,'evidence':evidence}
    def checked(ref, role):
        path=quality.relative_file(project,ref['path'])
        actual=quality.digest(path)
        if actual != ref['sha256']:
            raise ValueError(f'{role}: stale source hash for {ref["path"]}')
        evidence.append({'role':role,'path':ref['path'],'sha256':actual})
        return path
    profiles={}
    for reference in settings['profiles']:
        org=reference['organization_id']
        try:
            if org in profiles: raise ValueError('Duplicate organization_id: '+org)
            path=checked(reference,'profile')
            profile=json.loads(path.read_text(encoding='utf-8-sig'))
            invalid=quality.schema_errors(profile,SCHEMAS/'organization-profile.schema.json')
            if invalid: raise ValueError('; '.join(invalid))
            if profile['project_code'] != config['project']['code']: raise ValueError('Profile belongs to another project')
            if profile['organization_id'] != org or profile['version'] != reference['version']: raise ValueError('Organization/version binding mismatch')
            for source in profile['sources']: checked(source,'organization_source')
            for source in profile['intended_signer']['sources']: checked(source,'signer_source')
            if not profile['legal_name'] or not all(profile['intended_signer'][k] for k in ['name','role']):
                pending.append(org+': unresolved legal name or intended signer')
            if profile['unknown_fields'] or any(value is None for value in profile['requisites'].values()):
                pending.append(org+': unresolved profile fields')
            templates={}
            for template in profile['templates']:
                if template['id'] in templates: raise ValueError('Duplicate template id: '+template['id'])
                if template['organization_id'] != org: raise ValueError('Cross-organization template binding')
                checked(template,'template')
                if template['approval_source'] is not None: checked(template['approval_source'],'template_approval')
                if template['status']=='approved_template' and template['approval_source'] is None:
                    raise ValueError('Approved template requires a hash-bound approval source')
                templates[template['id']]=template
            profiles[org]=templates
        except (OSError,ValueError,TypeError,KeyError) as exc:
            errors.append(f'Profile {org}: {exc}')
    seen=set()
    for binding in settings['bindings']:
        key=(binding['organization_id'],binding['document_type'])
        try:
            if key in seen: raise ValueError('Duplicate document type binding')
            seen.add(key)
            template=profiles[binding['organization_id']][binding['template_id']]
            if template['document_type'] != binding['document_type']: raise ValueError('Template type mismatch')
            if template['status']!='approved_template': pending.append(f'{key}: template is {template["status"]}, not approved')
        except (KeyError,ValueError) as exc:
            errors.append(f'Binding {key}: {exc}')
    return {'configured':True,'errors':errors,'pending':pending,'evidence':evidence}
