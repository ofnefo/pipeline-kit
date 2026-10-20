"""Small offline SEO evidence tool; no crawl, deploy or paid API."""
import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.h1, self.canonical, self.description = [], [], [], []
        self.images_missing_alt = 0
        self.jsonld, self.robots, self.lang = [], [], ''
        self.active = None
        self.buffer = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html': self.lang = a.get('lang', '')
        if tag == 'meta' and a.get('name', '').lower() == 'description': self.description.append(a.get('content', ''))
        if tag == 'meta' and a.get('name', '').lower() in ('robots', 'googlebot', 'yandex'): self.robots.append(a.get('content', ''))
        if tag == 'link' and 'canonical' in a.get('rel', '').lower().split(): self.canonical.append(a.get('href', ''))
        if tag == 'img' and 'alt' not in a: self.images_missing_alt += 1
        if tag in ('title', 'h1') or (tag == 'script' and a.get('type') == 'application/ld+json'):
            self.active, self.buffer = tag, []

    def handle_data(self, text):
        if self.active: self.buffer.append(text)

    def handle_endtag(self, tag):
        if self.active == tag:
            value = ''.join(self.buffer).strip()
            if tag == 'script': self.jsonld.append(value)
            else: getattr(self, tag).append(value)
            self.active = None


def audit(html):
    p = Page(); p.feed(html)
    findings=[]
    for name in ('title', 'h1', 'canonical', 'description'):
        values=getattr(p,name)
        if len(values)!=1 or not values[0].strip(): findings.append(f'{name}: ожидается одно непустое значение в статическом HTML')
    if p.canonical and (urlsplit(p.canonical[0]).scheme not in ('http','https') or not urlsplit(p.canonical[0]).netloc): findings.append('canonical: нужен абсолютный HTTP(S) URL')
    if not p.lang: findings.append('html: не указан lang')
    if p.images_missing_alt: findings.append(f'Изображений без атрибута alt: {p.images_missing_alt}')
    for value in p.jsonld:
        try: json.loads(value)
        except ValueError: findings.append('JSON-LD: синтаксическая ошибка')
    if any('noindex' in r.lower() for r in p.robots): findings.append('Есть noindex: проверить, соответствует ли назначению страницы')
    return {'scope':'static-html-only', 'title':p.title, 'h1':p.h1,'canonical':p.canonical,
            'description':p.description,'jsonld_blocks':len(p.jsonld),'findings':findings,
            'limitations':['Нет проверки сети/индексации/позиций','Не исполняется JavaScript; отсутствие разметки в HTML не доказывает отсутствие в рендере','Robots.txt и HTTP-заголовки не проверены']}


def utm(url, source, campaign, content):
    u=urlsplit(url)
    if u.scheme not in ('http','https') or not u.netloc or u.username or u.password:
        raise ValueError('Нужен HTTP(S) URL без учётных данных')
    args=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if not k.startswith('utm_')]
    args += [('utm_source',source),('utm_medium','social'),('utm_campaign',campaign),('utm_content',content)]
    return urlunsplit((u.scheme,u.netloc,u.path,urlencode(args),u.fragment))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='command',required=True)
    a=subs.add_parser('audit');a.add_argument('--html',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    u=subs.add_parser('utm');
    for arg in ('url','source','campaign','content'): u.add_argument('--'+arg,required=True)
    args=parser.parse_args()
    if args.command=='audit':
        result=audit(args.html.read_text(encoding='utf-8-sig'))
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'out':str(args.out),'findings':len(result['findings'])}))
    else: print(utm(args.url,args.source,args.campaign,args.content))
