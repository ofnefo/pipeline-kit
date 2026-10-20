"""Session interface for Pipeline Control tasks; never launches agents or models."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'control_panel'))
import workboard as board


def main():
    # Windows redirected consoles may default to a code page without Cyrillic.
    # Keep the JSON interface UTF-8 for both humans and calling agents.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['list', 'get', 'start', 'heartbeat', 'submit', 'block'])
    p.add_argument('id', nargs='?')
    p.add_argument('--actor')
    p.add_argument('--version', type=int)
    p.add_argument('--session-ref')
    p.add_argument('--actual-model')
    p.add_argument('--evidence')
    p.add_argument('--reason')
    a = p.parse_args()
    try:
        if a.action == 'list':
            result = board.listing()
        elif a.action == 'get':
            result = board.get(a.id)
        else:
            if not a.actor or a.version is None or not a.id:
                p.error('Изменения требуют id, --actor и --version из get')
            data = {k: v for k, v in vars(a).items() if k in ('session_ref', 'actual_model', 'evidence', 'reason') and v}
            result = board.mutate(a.id, a.version, a.action, data, actor=a.actor, session=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

