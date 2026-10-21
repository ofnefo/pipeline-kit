"""Explicit file-list release tooling. Never imports or copies private source trees."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
TEXT={'.py','.js','.css','.html','.json','.md','.txt','.yaml','.yml','.csv','.toml'}
GENERATED={'__pycache__','.pytest_cache'}

def digest(data):return hashlib.sha256(data).hexdigest()

def members():
    data=json.loads((ROOT/'release-files.json').read_text(encoding='utf-8'))
    paths=data['files']
    if paths!=sorted(set(paths)):raise ValueError('Release file list must be unique and sorted')
    for name in paths:
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or p.as_posix()!=name:raise ValueError('Invalid release member')
        target=ROOT/p
        for parent in [target,*target.parents]:
            if parent==ROOT:break
            if parent.is_symlink() or (hasattr(parent,'is_junction') and parent.is_junction()):
                raise ValueError(f'Link/junction forbidden: {name}')
        if not target.is_file():raise ValueError(f'Missing member: {name}')
    return paths

def scan(paths,denylist=None):
    findings=[]
    patterns={
        'user-home':r'(?i)(?:[A-Z]:[\\/]+Users[\\/]+[^\\/\s]+|/ho'+r'me/[^/\s]+|/Us'+r'ers/[^/\s]+)',
        'personal-drive-root':r'(?i)\b[DEQPHZ]:[\\/]+(?:hub|projects|pipelines|Codex|assets|Pipeline)\b',
        'private-key':r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
        'token':r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{30,})',
        'telegram-token':r'\b\d{8,12}:[A-Za-z0-9_-]{30,}\b',
    }
    if denylist:
        for i,value in enumerate(json.loads(Path(denylist).read_text(encoding='utf-8'))):
            patterns[f'operator-deny-{i}']=r'(?i)(?<!\w)'+re.escape(value)+r'(?!\w)'
    for name in paths:
        path=ROOT/name
        if path.suffix.lower() not in TEXT and not path.name.startswith(('LICENSE','OFL','NOTICE')) and path.name!='.gitignore':continue
        text=path.read_text(encoding='utf-8-sig')
        for rule,pattern in patterns.items():
            for match in re.finditer(pattern,text):
                findings.append({'path':name,'line':text.count('\n',0,match.start())+1,'rule':rule})
        for match in re.finditer(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])',text):
            try:address=ipaddress.ip_address(match.group())
            except ValueError:continue
            if address.is_loopback or address.is_unspecified or str(address).startswith(('192.0.2.','198.51.100.','203.0.113.')):continue
            findings.append({'path':name,'line':text.count('\n',0,match.start())+1,'rule':'non-example-ipv4'})
    # Unknown files in public roots cannot silently enter or disappear from a release.
    for folder in ('apps','agents','catalog','config','docs','examples','modules','skills','tests','tools'):
        for path in (ROOT/folder).rglob('*'):
            if any(p in GENERATED for p in path.parts) or path.suffix=='.pyc':continue
            if path.is_file() and path.relative_to(ROOT).as_posix() not in paths:
                findings.append({'path':path.relative_to(ROOT).as_posix(),'rule':'unlisted-public-file'})
    return findings

def manifest(paths):
    return [{'path':name,'sha256':digest((ROOT/name).read_bytes()),'bytes':(ROOT/name).stat().st_size} for name in paths]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('scan','build','source-status'))
    parser.add_argument('--output',type=Path)
    parser.add_argument('--denylist',type=Path,help='Private JSON array of excluded identities; values never printed')
    parser.add_argument('--roots',type=Path,help='Private JSON mapping provenance source ids to absolute directories')
    args=parser.parse_args()
    if args.command=='source-status':
        if not args.roots:parser.error('--roots is required')
        roots=json.loads(args.roots.read_text(encoding='utf-8'))
        rows=[]
        for item in json.loads((ROOT/'provenance.json').read_text(encoding='utf-8'))['files']:
            if not item.get('source'):continue
            base=Path(roots[item['source']]).resolve();path=(base/item['source_path']).resolve()
            if not path.is_relative_to(base):raise ValueError('Source path escapes selected root')
            rows.append({'path':item['path'],'source_changed':not path.is_file() or digest(path.read_bytes())!=item['source_sha256']})
        result={'files':rows,'action':'Review changed source files individually; no copying or publication performed'}
    else:
        paths=members();findings=scan(paths,args.denylist)
        result={'status':'FAIL' if findings else 'PASS','files':len(paths),'findings':findings}
        if args.command=='build' and not findings:
            if not args.output:parser.error('--output ZIP path is required')
            output=args.output.absolute()
            if output.exists():raise FileExistsError('Output already exists; choose a new release candidate path')
            output.parent.mkdir(parents=True,exist_ok=True)
            rows=manifest(paths)
            with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
                for name in paths:
                    info=zipfile.ZipInfo('pipeline-kit/'+name,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
                    archive.writestr(info,(ROOT/name).read_bytes())
                archive.writestr('pipeline-kit/BUILD_MANIFEST.json',json.dumps(rows,indent=2))
            result.update({'archive':str(output),'sha256':digest(output.read_bytes()),'approval':'candidate; apply scope-based checks and review from docs/RELEASE.md before publication'})
    if args.command!='build' and args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    summary=result
    if args.command=='source-status' and args.output:
        summary={'files':len(result['files']),'changed':sum(row['source_changed'] for row in result['files']),'report':str(args.output),'action':result['action']}
    print(json.dumps(summary,ensure_ascii=True,indent=2))
    return 1 if result.get('status')=='FAIL' else 0

if __name__=='__main__':raise SystemExit(main())
