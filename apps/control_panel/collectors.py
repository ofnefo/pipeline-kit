"""Portable local collector boundary. Never scans hosts or starts services."""
from pathlib import Path
import time
import kit_config as config

CONTROL = Path(__file__).resolve().parents[1]
HUB = config.ROOT
STATE = config.workspace('state')

def cached(key, ttl, fn):
    return fn()

cached_ok = cached

def run(*args, **kwargs):
    raise ValueError('Host command adapters are not enabled in Pipeline Kit')

def gpu_info():
    return {'available': False, 'reason': 'GPU execution is an optional adapter'}

def health():
    return {'local': {'online': True, 'services': [], 'disks': {}, 'gpu': None, 'ram': {}},
            'alerts': {'active': [], 'enabled': False}, 'read_at': time.time(),
            'mode': 'local', 'version': '0.1.0'}
