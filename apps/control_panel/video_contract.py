"""Generation capability boundary; no worker validation is inherited."""
import json
import kit_config as config
PATH=config.PACKAGE/'modules/video/config/video-mode-contract.json'
def load():
    return json.loads(PATH.read_text(encoding='utf-8'))
def decorate(item):
    if item.get('group')=='video':
        item={**item,'contract_error':'Generation worker is not included in Pipeline Kit'}
    return item
def validate_sources(kind):
    raise ValueError('Configure and validate a generation adapter before use')
