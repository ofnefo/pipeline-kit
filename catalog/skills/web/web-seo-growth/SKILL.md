---
name: web-seo-growth
description: "Use when expanding a site's SEO beyond metadata: search-intent clusters, content briefs, service and case pages, social-to-site funnels, measurement (Yandex-first for RU audiences) and evidence-based GEO. Ships an offline static-HTML audit and a UTM link builder. Not for deploying production or for inventing keyword volume, testimonials, rankings or traffic."
---

# web-seo-growth: from technical readiness to growth

Find and claim the site in your project map; read its rules and the accepted offer. Read existing evidence (previous audits,
analytics exports) before repeating an audit. A technical SEO checker (title, robots, sitemap, schema) is a dependency to call,
not to rewrite.

## Inputs
- Page goal, audience, facts that can be proven, CTA.
- Search data you actually have: queries, region, period, frequency, with source and observation date (e.g. Yandex Wordstat /
  Webmaster, Google Search Console). No data -> label the item a **hypothesis**.

## Workflow (7 steps)
1. Fix the page goal, audience, facts and CTA. Ask for what is missing; never invent demand.
2. Collect queries with region, period and frequency; store the source and date.
3. One intent cluster -> one target URL; check overlap with existing pages and cannibalisation across brands/sites.
4. Brief: the reader's main question, evidence, real examples, headings, the path to action (offer + CTA).
5. Check HTML/render, robots, canonical, sitemap and accessibility with your technical checker and the audit below.
6. After an approved deploy, measure a meaningful action through the existing analytics (do not replace counters).
7. After an agreed window compare fixed periods, annotate releases, update the material; do not create a page per synonym.

## Static audit and UTM helper
```
python -X utf8 scripts/seo_growth.py audit --html <built-page.html> --out <out>/seo-page.json
python -X utf8 scripts/seo_growth.py utm --url https://example.com/ --source telegram --campaign brand_202601_cases --content case01_a
```
- `audit` checks one static HTML file: single non-empty title/h1/canonical/description, absolute canonical, `lang`, `img` without
  `alt`, JSON-LD syntax, `noindex`. The receipt lists its limitations: no network/indexing/ranking, no JS rendering, no
  robots.txt/headers. An empty JSON-LD result in static HTML is **not** proof that the rendered page has no schema; use a browser
  only for that uncertainty.
- `utm` only builds a URL (replaces existing `utm_*`, `utm_medium=social` by default, rejects URLs with credentials). It does not
  change analytics or verify the destination.

## Techniques and gotchas
- Metadata length ranges are editorial heuristics, not ranking gates.
- Avoid pages that only swap keywords or locations; no fake reviews, FAQs, ratings or product capabilities.
- Reuse a real case or demonstration from social media rather than mass-producing thin pages; link author, product and proof
  naturally.
- GEO (AI answers) needs clear identity, current facts, authorship and original evidence; `llms.txt` and schema do not guarantee
  citations.
- Measurement: fixed windows, release annotations, correlation is not attribution.
- Keep internal infrastructure (hosts, tools, panels) out of public pages.

## Output
Focused findings, proposed or changed URLs, evidence, expected user benefit, measured baseline or explicit unknowns, next review
date. The site deploy stays a separate action authorised by the operator (`web-release`).

## Acceptance checklist
- [ ] Every cluster has one target URL, a data source with date, or the label "hypothesis".
- [ ] No invented volume, difficulty, ranking, traffic or testimonial.
- [ ] Brief contains question, evidence, structure, offer and CTA.
- [ ] Static audit receipt saved; its limitations stated in the report.
- [ ] Measurement plan names the action, the analytics tool and the comparison window.

## References
- Yandex Webmaster help: https://yandex.ru/support/webmaster/
- Google Search Central, helpful content: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
