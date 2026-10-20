"""Run the portable kit. All data lives in an explicitly selected workspace."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',default='workspace',help='Local data directory (default: ./workspace)')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('init',help='Create empty local workspace')
    server=commands.add_parser('serve',help='Start Control on loopback; no background services')
    server.add_argument('--port',type=int,default=8770)
    nn=commands.add_parser('namenode',help='Local cards, claims, journal and mailbox')
    nn.add_argument('action'); nn.add_argument('args',nargs='?',default='{}')
    commands.add_parser('doctor',help='Check optional capabilities without launching tools')
    args=parser.parse_args(argv)
    os.environ['PIPELINE_KIT_WORKSPACE']=str(Path(args.workspace).absolute())
    sys.path.insert(0,str(ROOT/'apps/control_panel'))
    import kit_config as config
    if args.command=='init':
        config.initialize()
        print(json.dumps({'workspace':str(config.ROOT),'created':True}))
    elif args.command=='serve':
        if not 1024 <= args.port <= 65535: parser.error('Use a port between 1024 and 65535')
        import uvicorn
        uvicorn.run('app:app',host='127.0.0.1',port=args.port)
    elif args.command=='namenode':
        import workboard
        print(json.dumps(workboard.nn(args.action,json.loads(args.args)),ensure_ascii=True))
    elif args.command=='doctor':
        import converters
        print(json.dumps({'python':sys.version.split()[0], 'workspace':str(config.ROOT),
                          'tools':converters.tools_present(), 'remote_actions':False,'paid_calls':False},indent=2))

if __name__=='__main__': main()
