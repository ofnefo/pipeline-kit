"""Explicit CPU-only FFmpeg acceptance using generated synthetic fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
def run(args):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError(result.stderr[-5000:])
    return result.stdout

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.absolute()
    if out.exists():raise FileExistsError('Choose a new evidence directory')
    for tool in ('ffmpeg','ffprobe'):
        if not shutil.which(tool):raise FileNotFoundError(tool+' must be on PATH')
    out.mkdir(parents=True);os.environ['PIPELINE_KIT_WORKSPACE']=str(out/'workspace')
    sys.path.insert(0,str(ROOT/'apps/control_panel'))
    from fastapi.testclient import TestClient
    import app
    receipt={'ffmpeg':run(['ffmpeg','-version']).splitlines()[0],'ffprobe':run(['ffprobe','-version']).splitlines()[0]}
    with TestClient(app.app) as client:
        response=client.post('/api/projects/create',json={'type':'video','name':'media-test'})
        response.raise_for_status();project=Path(response.json()['path']);source=project/'fixture.mp4'
        run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=320x180:r=24:d=2',
             '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2',
             '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',source])
        before=hashlib.sha256(source.read_bytes()).hexdigest();url='/api/video-review/media-test/sequence'
        initial=client.get(url).json()
        payload={'version':initial['version'],'tracks':{'V1':[{'id':'fixture','path':'fixture.mp4','start':0,'end':48,'at':0,'mute':False,'label':'Synthetic'}],'V2':[],'A1':[],'T1':[]}}
        saved=client.post(url,json=payload);saved.raise_for_status()
        assert client.post(url,json=payload).status_code==409
        exported=client.post(url+'/export',json={'version':saved.json()['version']});exported.raise_for_status()
        ident=exported.json()['id'];deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            record=next(e for e in client.get(url).json()['exports'] if e['id']==ident)
            if record['state'] not in ('queued','running','rendering'):break
            time.sleep(.25)
        receipt['montage']=record
        if record['state']!='done':raise AssertionError(record)
        outputs=list((project/'50-edit/exports').glob('*.mp4'))
        assert len(outputs)==1,outputs
        probe=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',outputs[0]]))
        video=next(s for s in probe['streams'] if s['codec_type']=='video')
        assert (video['width'],video['height'])==(320,180)
        assert abs(float(probe['format']['duration'])-2)<.15
        assert hashlib.sha256(source.read_bytes()).hexdigest()==before
        receipt['video_probe']=probe
    audio=out/'sine.wav'
    run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=8',audio])
    receipt['master_stdout']=run([sys.executable,ROOT/'modules/music/scripts/master_audio.py',audio,'--output',out/'master.wav','--profile','speech'])
    assert (out/'master.wav').is_file()
    receipt['status']='PASS';receipt['human_review']='Listen to audio and inspect exported video before creative acceptance'
    (out/'media-check.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'status':'PASS','receipt':str(out/'media-check.json')}))

if __name__=='__main__':main()
