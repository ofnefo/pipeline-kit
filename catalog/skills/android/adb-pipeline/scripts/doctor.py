"""Read-only Android inventory through an already running, loopback-only ADB server.

Examples:
  python -X utf8 doctor.py inventory --adb /abs/path/to/adb --out receipts/inventory.json
  python -X utf8 doctor.py inspect --adb /abs/path/to/adb --serial <SERIAL> --out receipts/inspect.json

Exit codes: 0 complete, 2 error (the receipt is still written with status "error").
The script never starts an ADB server, never writes to the device and never selects a device implicitly.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess

PROPS = ['ro.product.manufacturer', 'ro.product.model', 'ro.product.device',
         'ro.build.version.release', 'ro.build.version.sdk', 'ro.product.cpu.abilist',
         'ro.boot.verifiedbootstate', 'ro.boot.flash.locked', 'ro.build.fingerprint']
FEATURE_KEYS = ('nfc', 'wifi', 'bluetooth', 'usb.host')
BATTERY_KEYS = ('level:', 'temperature:', 'status:', 'health:', 'USB powered:')


def parse_devices(text):
    """Parse `adb devices -l` output into [{serial, state, details}]."""
    result = []
    for line in text.splitlines():
        if not line.strip() or line.startswith(('List of devices', '*')):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        result.append({'serial': parts[0], 'state': parts[1],
                       'details': dict(x.split(':', 1) for x in parts[2:] if ':' in x)})
    return result


def require_device(devices, serial):
    """Return the single device in state 'device' whose serial matches exactly, else raise."""
    if not serial or serial.startswith('-') or any(c.isspace() for c in serial):
        raise ValueError('an explicit valid --serial is required')
    matching = [d for d in devices if d['serial'] == serial]
    if len(matching) != 1 or matching[0]['state'] != 'device':
        raise ValueError('selected device is absent, duplicated, offline or unauthorized')
    return matching[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['inventory', 'inspect'])
    ap.add_argument('--adb', required=True, type=Path, help='absolute path to the adb executable')
    ap.add_argument('--port', type=int, default=5037, help='loopback ADB server port (default 5037)')
    ap.add_argument('--serial', help='exact device serial (required for inspect)')
    ap.add_argument('--out', required=True, type=Path, help='receipt JSON path')
    args = ap.parse_args(argv)
    receipt = {'time': datetime.now(timezone.utc).isoformat(), 'action': args.action,
               'read_only': True, 'adb_port': args.port, 'status': 'error'}
    try:
        if not args.adb.is_absolute() or not args.adb.is_file():
            raise ValueError('use an existing absolute adb executable path')
        # Never silently launch an unowned background ADB server: require one that is already listening.
        with socket.create_connection(('127.0.0.1', args.port), timeout=2):
            pass
        env = dict(os.environ, ADB_SERVER_SOCKET=f'tcp:127.0.0.1:{args.port}')

        def call(*tokens):
            p = subprocess.run([str(args.adb), '-H', '127.0.0.1', '-P', str(args.port), *tokens],
                               env=env, capture_output=True, stdin=subprocess.DEVNULL, timeout=20)
            if p.returncode:
                raise RuntimeError(f'adb command failed, exit {p.returncode}')
            return p.stdout.decode('utf-8', 'replace').strip()

        devices = parse_devices(call('devices', '-l'))
        receipt['devices'] = devices
        if args.action == 'inspect':
            require_device(devices, args.serial)
            receipt['serial'] = args.serial
            receipt['properties'] = {k: call('-s', args.serial, 'shell', 'getprop', k) for k in PROPS}
            features = call('-s', args.serial, 'shell', 'pm', 'list', 'features').splitlines()
            receipt['features'] = [x for x in features if any(k in x for k in FEATURE_KEYS)]
            battery = call('-s', args.serial, 'shell', 'dumpsys', 'battery').splitlines()
            receipt['battery'] = [x.strip() for x in battery if x.strip().startswith(BATTERY_KEYS)]
        receipt['status'] = 'complete'
        code = 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        receipt['error'] = str(exc)
        code = 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps({'status': receipt['status'], 'receipt': str(args.out), 'devices': len(receipt.get('devices', []))}))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
