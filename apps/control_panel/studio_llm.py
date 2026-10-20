"""Studio adapter for an explicitly configured loopback chat server."""
import local_chat_service as lcs
PREFIX = 'unavailable:'

def models():
    return [dict(m, engine='worker', tier='local', available=True, reason='', price=None) for m in lcs.models()]

def estimate(messages, max_tokens, temperature, model):
    lcs.validate(messages, max_tokens, temperature, model)
    if model not in {m['id'] for m in models()}:
        raise ValueError('Configure and enable a local model first')
    return {'model':model, 'tier':'local', 'usd':0, 'price':None, 'max_tokens':max_tokens}

def open_stream(messages, max_tokens, temperature, model, confirm_usd=None, stop=None):
    return lcs.chat_stream(messages, max_tokens, temperature, model, stop)
