"""Run against an operator-started isolated test workspace, never production."""
import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlsplit

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url',default='http://127.0.0.1:8770')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--executable',type=Path,help='Optional installed Chromium executable; no download')
    args=p.parse_args()
    if urlsplit(args.base_url).hostname not in ('127.0.0.1','localhost','::1'):p.error('Loopback test server required')
    from playwright.sync_api import sync_playwright
    args.output.mkdir(parents=True,exist_ok=True)
    findings=[]
    screenshots=[]
    journeys=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,**({'executable_path':str(args.executable)} if args.executable else {}))
        try:
            for width in (1440,375):
                page=browser.new_page(viewport={'width':width,'height':900})
                page.on('pageerror',lambda e:findings.append({'type':'script','error':str(e)}))
                try:
                    slug=f'browser-{width}-{int(time.time())}'
                    page.goto(args.base_url+'/#projects',wait_until='networkidle')
                    page.locator('#kit-new-project').click()
                    page.locator('#kit-project-form select[name=type]').select_option('video')
                    page.locator('#kit-project-form input[name=name]').fill(slug)
                    page.locator('#kit-project-form button').first.click()
                    page.wait_for_url('**/#studio/video/'+slug)
                    page.goto(args.base_url+'/#projects',wait_until='networkidle')
                    page.get_by_text(slug,exact=True).first.wait_for()
                    page.goto(args.base_url+'/#board',wait_until='networkidle')
                    page.locator('[data-board-new]').click()
                    page.locator('#board-form input[name=title]').fill('Browser task '+slug)
                    page.locator('#board-form textarea[name=acceptance]').fill('Persist and display this task after reload')
                    page.locator('#board-form button[type=submit]').click()
                    page.locator('#board-dialog').wait_for(state='hidden')
                    page.reload(wait_until='networkidle')
                    page.get_by_text('Browser task '+slug,exact=True).first.wait_for()
                    journeys.append({'width':width,'project_create_and_list':'PASS','task_create_and_reload':'PASS'})
                except Exception as exc:
                    findings.append({'type':'journey','width':width,'error':str(exc)})
                    page.keyboard.press('Escape')
                for route in ('home','projects','board','studio','quick','tools','smm','settings'):
                    page.goto(args.base_url+'/#'+route,wait_until='networkidle')
                    page.wait_for_timeout(500)
                    filename=f'{width}-{route}.png'
                    page.screenshot(path=str(args.output/filename),full_page=True)
                    screenshots.append({'file':filename,'width':width,'route':route})
                    if page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'):
                        findings.append({'type':'overflow','width':width,'route':route})
                page.close()
        finally:browser.close()
    (args.output/'browser.json').write_text(json.dumps({'findings':findings,'screenshots':screenshots,'journeys':journeys,'note':'Screenshots require human reference comparison; API integration tests cover mutations.'},indent=2),encoding='utf-8')
    print(json.dumps({'screenshots':16,'findings':len(findings)}))
    return bool(findings)

if __name__=='__main__':raise SystemExit(main())
