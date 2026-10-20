"""Music projects belong to the configured workspace."""
import os
from pathlib import Path
def projects_root(root=None):
    return Path(os.environ.get('PIPELINE_KIT_WORKSPACE','workspace')).absolute()/'projects/music'
if __name__ == '__main__':
    print(projects_root())
