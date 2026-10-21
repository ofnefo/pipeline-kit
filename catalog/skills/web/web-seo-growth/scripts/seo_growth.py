"""Small offline SEO evidence tool: static HTML audit and UTM link builder. No crawl, deploy or paid API.

Examples:
  python -X utf8 seo_growth.py audit --html path/to/page.html --out outputs/seo-page.json
  python -X utf8 seo_growth.py utm --url https://example.com/ --source telegram --campaign brand_202601_cases --content case01_a
"""
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
        a = {k: (v or '') for k, v in attrs}
        if tag == 'html':
            self.lang = a.get('lang', '')
        if tag == 'meta' and a.get('name', '').lower() == 'description':
            self.description.append(a.get('content', ''))
        if tag == 'meta' and a.get('name', '').lower() in ('robots', 'googlebot', 'yandex'):
            self.robots.append(a.get('content', ''))
        if tag == 'link' and 'canonical' in a.get('rel', '').lower().split():
            self.canonical.append(a.get('href', ''))
        if tag == 'img' and 'alt' not in a:
            self.images_missing_alt += 1
        if tag in ('title', 'h1') or (tag == 'script' and a.get('type') == 'application/ld+json'):
            self.active, self.buffer = tag, []

    def handle_data(self, text):
        if self.active:
            self.buffer.append(text)

    def handle_endtag(self, tag):
        if self.active == tag:
            value = ''.join(self.buffer).strip()
            if tag == 'script':
                self.jsonld.append(value)
            else:
                getattr(self, tag).append(value)
            self.active = None


def audit(html):
    p = Page()
    p.feed(html)
    findings = []
    for name in ('title', 'h1', 'canonical', 'description'):
        values = getattr(p, name)
        if len(values) != 1 or not values[0].strip():
            findings.append(f'{name}: expected exactly one non-empty value in the static HTML (found {len(values)})')
    if p.canonical:
        c = urlsplit(p.canonical[0])
        if c.scheme not in ('http', 'https') or not c.netloc:
            findings.append('canonical: must be an absolute HTTP(S) URL')
    if not p.lang:
        findings.append('html: lang attribute is missing')
    if p.images_missing_alt:
        findings.append(f'images without an alt attribute: {p.images_missing_alt}')
    for value in p.jsonld:
        try:
            json.loads(value)
        except ValueError:
            findings.append('JSON-LD: syntax error')
    if any('noindex' in r.lower() for r in p.robots):
        findings.append('noindex present: confirm it matches the purpose of the page')
    return {
        'scope': 'static-html-only', 'title': p.title, 'h1': p.h1, 'canonical': p.canonical,
        'description': p.description, 'lang': p.lang, 'jsonld_blocks': len(p.jsonld), 'findings': findings,
        'limitations': [
            'No network, indexing or ranking checks',
            'JavaScript is not executed; markup missing from static HTML does not prove it is missing after rendering',
            'robots.txt and HTTP headers are not checked',
        ],
    }


def utm(url, source, campaign, content, medium='social'):
    u = urlsplit(url)
    if u.scheme not in ('http', 'https') or not u.netloc or u.username or u.password:
        raise ValueError('an HTTP(S) URL without credentials is required')
    query = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if not k.startswith('utm_')]
    query += [('utm_source', source), ('utm_medium', medium), ('utm_campaign', campaign), ('utm_content', content)]
    return urlunsplit((u.scheme, u.netloc, u.path, urlencode(query), u.fragment))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = parser.add_subparsers(dest='command', required=True)
    a = subs.add_parser('audit', help='audit one static HTML file and write a JSON receipt')
    a.add_argument('--html', type=Path, required=True, help='input HTML file (built output, not sources)')
    a.add_argument('--out', type=Path, required=True, help='output JSON path')
    u = subs.add_parser('utm', help='print a URL with utm_* parameters (existing utm_* are replaced)')
    for arg in ('url', 'source', 'campaign', 'content'):
        u.add_argument('--' + arg, required=True)
    u.add_argument('--medium', default='social')
    args = parser.parse_args()
    if args.command == 'audit':
        result = audit(args.html.read_text(encoding='utf-8-sig'))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'out': str(args.out), 'findings': len(result['findings'])}))
    else:
        try:
            print(utm(args.url, args.source, args.campaign, args.content, args.medium))
        except ValueError as e:
            parser.exit(2, f'error: {e}\n')


if __name__ == '__main__':
    main()
