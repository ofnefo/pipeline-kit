---
name: osint-case
description: "Use when running an OSINT self-audit or an authorised open-source investigation of your own assets, an organisation that authorised it in writing, or a public entity: own-domain recon, exposure checks, file metadata, evidence reports. Opens a case with scope and authorisation, collects passively, records evidence with receipts and builds an offline report. Not for researching private individuals, active attacks, account-recovery enumeration, leaked credentials or hidden tracking."
---

# osint-case

## Purpose
Answer a bounded question from open sources with a case file where every statement has a source, a time, a tool, a hash for files
and an honest confidence level.

## Who may be a target
- **own:** your own domains, accounts, devices, published files, your own identity's exposure (self-audit).
- **authorized-org:** an organisation that gave written authorisation naming the scope (record who and their exact words).
- **public-entity:** a company or public body, researched from public records only.
- **Never:** private individuals (including partners, employees, neighbours, people met online), people's locations, home
  addresses, family members or contacts. If a question drifts toward a person, stop and narrow the scope.

## Inputs
- The question, the scope (concrete targets + allowed checks), the target class, the authorisation (who, their words, date).

## Workflow
1. **Case first.** No case = no collection.
   ```
   python -X utf8 scripts/case.py --root <cases> --case-id own-domain-001 --target-class own \
     --scope "Domain example.org; passive sources only" --authorized-by "<who>" --authorization "<their words, date>"
   ```
   Creates `<cases>/<id>/case.json`, `raw/`, `reports/`; no network; never overwrites a case. An `authorized-org` case without an
   authorisation record is refused. Scope changes = a new case or an explicit, quoted scope update in `case.json`.
2. **Passive by default.** Allowed: public pages, documented public records, passive sources for your own domain (certificate
   transparency logs, passive DNS), metadata of files you were given, offline processing.
   Needs explicit authorisation per case: anything that touches the target's infrastructure (port/vulnerability scans, crawlers,
   non-passive modules of recon frameworks), account-existence probes, paid data APIs (estimate cost first).
   Never: active attacks, password or account-recovery enumeration, importing leaked credentials or breach dumps, hidden tracking,
   "all modules" scans.
3. **Tools:** pinned versions, a reviewed module list, run locally with an owner and time limit; record tool + version per item.
4. **Evidence** in `<case>/evidence.jsonl`, one JSON object per line (see contract below). Record failures as `error` items.
5. **Raw data** (HTML, screenshots, exports, tool logs) stays in `<case>/raw/`; the cases folder is never committed or shared.
6. **Report** (offline):
   ```
   python -X utf8 scripts/report.py --case-dir <cases>/own-domain-001 --check-only
   python -X utf8 scripts/report.py --case-dir <cases>/own-domain-001
   ```
   Any invalid evidence line -> no report, exit 2. Writes a new `reports/report-<UTC>.md` (never overwritten) with scope, target
   class, authorisation, facts, hypotheses marked `[HYPOTHESIS]`, contradicted items, collection errors and limitations.
7. **Sharing** the report is a separate action after the authoriser approves that exact report; share the `.md` only, never raw
   data, evidence files or screenshots with personal data.

## Evidence contract
Required: `id` (unique), `kind` (`claim` | `hypothesis`), `statement`, `source_url_or_file` (http(s) URL or a path relative to the
case dir, e.g. `raw/page.html`), `retrieved_at` (ISO 8601 UTC), `tool`, `tool_version`, `confidence` (`high|medium|low|unknown`),
`verification_status` (`verified|unverified|contradicted|error`).
Optional: `source_sha256` (required for file sources; checked against the file), `limitations`, `related`, `notes`.
A verified item is a `claim`; anything inferred is a `hypothesis`. Sample: `references/evidence-sample.jsonl.txt`.

## Gotchas
- A matching username or photo is not identity; Wi-Fi/cell geolocation is not a person's location; a number lookup is not GPS.
- Certificate and DNS names reveal hosts, not whether they are reachable or vulnerable; do not "just check".
- Archived pages can be stale; record the capture date, not only the retrieval date.

## Legal and ethical boundaries
Follow the law where you and the target are (computer misuse, data protection, privacy rules). Collect the minimum needed for the
question; delete raw data when the case closes unless retention was agreed. Authorisation must come from someone entitled to give
it for that target; a request from a third party about someone else is not authorisation.

## Acceptance checklist
- [ ] Case exists with scope, target class and (where needed) quoted authorisation before any collection.
- [ ] Only passive methods, or each non-passive method has its own authorisation.
- [ ] Every evidence line validates; files have sha256; failures recorded.
- [ ] Report separates facts, hypotheses, contradictions and errors; limitations stated.
- [ ] No private individual researched; raw data not shared.

## Boundaries
Own or explicitly authorised targets and public entities only; passive by default; no attacks, enumeration, leaked data or
tracking; report sharing only after approval of that exact report.
