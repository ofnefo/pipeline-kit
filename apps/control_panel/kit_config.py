"""One explicit local workspace; importing this module performs no I/O."""
import json
import os
import shutil
from pathlib import Path

ROOT = Path(os.environ.get('PIPELINE_KIT_WORKSPACE', 'workspace')).absolute()
PACKAGE = Path(__file__).resolve().parents[2]

def workspace(relative=''):
    path = ROOT / relative
    if not path.absolute().is_relative_to(ROOT) or '..' in Path(relative).parts:
        raise ValueError('Path must be inside the configured workspace')
    return path

def options():
    path = workspace('config.json')
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}

def executable(name):
    # No host-specific installation paths or bundled third-party binaries.
    return Path(shutil.which(name) or name)

def initialize():
    for name in ('projects', 'state', 'namenode/cards', 'web/uploads', 'pipelines', 'quarantine'):
        workspace(name).mkdir(parents=True, exist_ok=True)
