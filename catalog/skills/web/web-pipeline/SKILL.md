---
name: web-pipeline
description: "Use when starting, continuing or diagnosing any work on a website or web app (text or SEO fix, new page, redesign, product UI, backend, QA audit, release). Entry skill of a web pipeline: finds the project in your project map, picks the smallest route and hands off to the focused web skills. Not for production deploys without the operator's explicit request for that exact site."
---

# web-pipeline: entry to web work

Role: the **primary** web skill. It picks the route and the checks; details live in the focused skills below.

## 0. Where things are
- Pipeline (kits, tools, rules, reports): `<PIPELINE_ROOT>/web`, with its own `AGENTS.md` and `README.md`.
- Sites and web apps: `<PROJECT_ROOT>/web/<site>` (worktrees and production snapshots next to it). Edit only there, never the copy
  on the production server.
- Production: deploy, restart or DB changes **only on the operator's explicit request for that site** (`web-release`, step 7).
- Run git, search and builds on the machine that holds the files, not over a network drive.

## 1. Before work
1. Look the site up in your project map (search -> card -> "where it lives", "where changes go", deploy, risks) and claim the card.
   No card -> create one for the new site before editing.
2. Read the site's `AGENTS.md` (or equivalent rules file).
3. Read-only state check: build scripts, branch and dirty state, domain, last deploy. Record it.

## 2. Route: take the narrowest one
| Task | Skill / tool | Done when |
|---|---|---|
| Promotion, search intent, SEO cases, measurement | `web-seo-growth` (+ a search-copy skill); social -> `smm-pipeline` | intent, target page, fact source and metric exist; demand and rankings are not invented |
| Text, meta, robots, links fix | copy skill + an SEO checker on the **built output** (`dist` after build, or the static root; not the sources) | diff reviewed, checker has no FAIL |
| New landing or promo page | a landing/taste design skill (+ an offer-copy skill) | `web-qa` on changed pages |
| Redesign of an existing site | a redesign skill; a reference site -> extract its design tokens first | before/after visual diff |
| Product UI (admin, dashboard, panels) | an interface-design skill; React/Next best-practice skills | journeys walked in a browser |
| Server, API, DB, bots | `backend-baseline` (+ Postgres best practices) | API smoke and checklist pass |
| Accessibility, speed, visual changes | `web-qa`; UI code vs guidelines and usability heuristics as needed | report table with owners |
| Release | `web-release` (staging, gates, snapshot, release notes) | release candidate + report; deploy only on request |
| Wow site, portfolio, 3D, scroll scenes, transitions, preview video | `web-immersive` | its acceptance list, `preview.mp4` with receipt |
| Animation, scroll video, 2D canvas | existing motion helpers in the project first | demo checked at 390 and 1440 |

One primary skill per task, others step by step. Do not escalate a text/config fix into a redesign or a full audit.

### Design stages (one piece of work, not four processes)
| Stage | Kind of skill | Checkable result |
|---|---|---|
| Direction, "taste" | landing/taste skill | references, tokens, first screen + a real example |
| Dashboard, table, form | interface-design skill | task hierarchy and product states |
| Palette, fonts (incl. Cyrillic), UX pattern | design-system skill | choice for this brief, reconciled with the existing system |
| Components, gestures, micro-interactions | design-engineering skill | response, interruption, focus, touch, reduced motion |
| Critique and polish | critique skill | comparison with the reference, ranked defects, proof of fixes |

Flow for new or substantially changed UI: chosen direction -> **one sample** -> critique before replicating -> fixes -> walk the real
user path. Give reviewers the checklist and screenshots. Technical PASS does not replace the operator's creative approval.
Before releasing forms, auth or uploads also run accessibility, performance and security baselines.

## 3. Media for the site
- Images: subscription/cloud image models you are already licensed for first, local models for variations; record the actual
  provider in the receipt. Paid per-call APIs only on the operator's request with a cost estimate.
- Video, music and voice come from their own pipelines. Icons, fonts, textures from your asset library; source and licence go
  in the record.

## 4. Attention first
- Language and search engine of the audience (e.g. RU audience: Yandex first, Metrica/Webmaster, `llms.txt`, structured data).
- 390 px mobile width with no horizontal scroll; keyboard and focus checked by hand (axe does not see them).
- Secrets only from the environment (`.env` not in git, not in the build); analytics blocked during audits.
- Temporary dev servers are started with an owner and a TTL, hidden, and stopped when done.
- Shared kits/tools are called, not edited, without their owner.

## 5. Finish
Verify the changed behaviour and its dependencies once. Then log in the project card what changed and where (paths, commit),
keep receipts (paths + hashes, exit codes) next to the outputs. Show finished files in the current chat; send them through your
delivery channel only when the operator asks for that send. Summary: done, verified, waiting for the operator's decision.

## Acceptance checklist
- [ ] Card found and claimed; site rules read.
- [ ] Narrowest route chosen; no adjacent "while I'm here" changes.
- [ ] Changed pages checked at 390 and 1440 on the built output.
- [ ] Receipts recorded; log written in the card.
- [ ] No production deploy or send without the explicit request.
