"""Generation adapter boundary. No installed weights or running workers are assumed."""
import kit_config as config
RUNS = config.workspace('state/model-runs.jsonl')

def catalogue():
    return {'models': [], 'groups': [], 'reason': 'Generation worker adapter not configured'}

def runs(limit=30):
    return []

def start(*args, **kwargs):
    raise ValueError('Generation worker adapter is not available in this distribution')

def file(path):
    from uploads import resolve_source
    return resolve_source(path)
