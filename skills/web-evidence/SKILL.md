---
name: web-evidence
description: Use when auditing saved HTML metadata or constructing explicit campaign URLs offline with Pipeline Kit.
---

# Offline web evidence

Identify the exact saved HTML, target page and intended audience. Preserve the input. Inspect `modules/web/scripts/seo_growth.py --help` for audit and UTM commands. Run only on explicit files; do not crawl unrelated sites or infer production access.

Check title, description, canonical URL, heading, language, image alternate text and JSON-LD findings in context. A canonical URL must reflect the intended public location; do not substitute a local path. UTM fields come from the campaign brief and must not include credentials or personal identifiers. Keep a copy of the input and resulting report.

Fix only the authorised page/code scope. Rerun checks invalidated by the change. For visual/interface work use actual desktop/mobile browser evidence and a project-specific design checklist; the HTML evidence tool does not perform visual, accessibility or performance acceptance.

Acceptance: every finding can be traced to supplied HTML, query parameters are encoded correctly, and the report clearly distinguishes offline results from live indexing/ranking behaviour. Publishing, production restart, search-console writes and site credentials are outside this tool's capabilities.
