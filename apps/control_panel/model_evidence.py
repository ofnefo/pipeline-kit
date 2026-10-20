"""Reuse explicit execution evidence without conflating a tested engine and a panel workflow."""
import json, hashlib
from pathlib import Path
REGISTRY=Path(__file__).resolve().parents[1]/'catalog/models/workflow-evidence.json'

def resolve(path):
    import kit_config
    p=Path(path)
    if not p.is_absolute(): p=kit_config.ROOT/p
    if not p.resolve().is_relative_to(kit_config.ROOT.resolve()): raise ValueError('Evidence outside workspace')
    return p

def lookup(kind):
    try: row=json.loads(REGISTRY.read_text(encoding='utf-8')).get(kind)
    except (OSError,ValueError): return None
    if not row: return None
    try:
        if row.get('workflow_sha256') and hashlib.sha256(resolve(row['workflow']).read_bytes()).hexdigest()!=row['workflow_sha256']:
            return None
        d=json.loads(resolve(row['receipt']).read_text(encoding='utf-8'))
        if not isinstance(d,dict) or d.get('status') in ('failed','error'): return None
        if row.get('schema')=='qwen':
            good=d.get('mode') in ('design','clone','clone-batch') and d.get('duration_s',0)>0 and resolve(d.get('output','')).is_file()
        elif row.get('schema')=='postprocess':
            artifact=resolve(row.get('artifact',''))
            expected=next((a.get('sha256') for a in d.get('artifacts',[]) if Path(a.get('path','')).name==artifact.name),None)
            good=d.get('operation') in ('interpolate','upscale-esrgan') and bool(expected) and artifact.is_file() and hashlib.sha256(artifact.read_bytes()).hexdigest()==expected
        elif row.get('schema')=='audio':
            good=d.get('status')=='success' and d.get('duration_s',0)>0 and resolve(d.get('output','')).is_file()
        else:
            good=d.get('status') in ('success','passed','pass','ok') and any(resolve(o.get('path','')).is_file() for o in d.get('outputs',[]) if o.get('type')!='input')
        if not good: return None
    except (OSError,ValueError,KeyError,TypeError): return None
    return dict(row,status='passed')
