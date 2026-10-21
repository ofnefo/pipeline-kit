---
name: web-release
description: "Use when a site or web app is to be prepared for release or deployed: staging branch or worktree, build with checksums, accessibility/performance/visual gates, release snapshot with manifest and rollback notes, then a production deploy only on the operator's explicit request for that exact site, followed by a smoke check. Provider-neutral release checklist with receipts. Not for choosing what to build (web-pipeline) or for auditing a live site without a release (web-qa)."
---

# web-release: provider-neutral release checklist

Steps 1-6 produce a **verified release candidate** and a report. Step 7, the production deploy, happens only when the operator
explicitly asks to deploy **this** site. Production is not touched before step 7.

## Inputs
- Project card from your project map: where the site lives, where changes go, deploy steps, risks, active pauses.
- The site's rules file (`AGENTS.md` or equivalent) and its deploy doc.
- Base ref (last released commit or production snapshot) and head ref.

## 0. Before you start
1. Find the card and claim it. The card (or the project's deploy doc) is the only source of the deploy target and steps. If it
   contradicts what is on disk, stop, ask the operator, then fix the card.
2. Read-only state check: build scripts, branch, dirty flag, domain. If the tree is dirty with changes that are not yours, find
   out whose they are before building.

## 1. Staging: branch or worktree
- Release id: `<site>-release-YYYYMMDD<letter>` (e.g. `docs-release-20260101a`). Release folder `R = <PIPELINE_ROOT>/web/staging/<release-id>`.
- Work in a separate branch or worktree: `git -C <site> worktree add <worktrees>/<site>-<topic> -b <branch>`.
- Record the delta: `git log --oneline <base>..<head>`.

## 2. Build
- Node projects: the project's build script (`npm run build`, `pnpm build`). Exit code and log tail -> `R/receipts/build.log`.
- Static sites: the folder itself is the build; check it contains no `.env`, backups, workspace or source maps you did not intend.
- SEO gate on the **built output** (title, description, canonical, robots, sitemap); FAIL blocks the release.

## 3. Checks (reports into `R/report/`)
1. Accessibility and performance: axe + Lighthouse on the local build; gates e.g. fail on `serious`, min performance 80.
2. Visual regression: before = previous release or production snapshot (`git archive <base> <site-dir> | tar -x -C R/before`),
   after = new build, widths 1440 and 390. Changes are not failures, but each one is explained in the notes. Horizontal scroll at
   390 is fixed before release.
3. Behaviour in an isolated headless browser: navigate key pages, console without errors, no 404 requests, screenshots at 390/1440
   into `R/report/screens/`. Never submit forms to production endpoints.
4. Projects with an API: contract smoke against dev with secrets from env; server checklist from `backend-baseline`.
5. Manual: keyboard and focus, copy proofread, `noindex` and analytics as intended.

## 4. Release snapshot
`R/` contains:
- `RELEASE.md`: what ships (branch, `base..head`, file list), how it was built, gate results with exit codes, deploy target and
  steps copied from the card (with a link to it), **rollback steps**, status `NOT RELEASED - waiting for operator OK`.
- Artifact `tar -czf R/<site>-<sha>.tgz -C <dist> .` and `R/manifest.json` with sha256 and size of every file (see snippet below).
- `R/report/`: `release-notes.md` (what changed, what was checked, what is left), QA summary, visual-diff report, screenshots.
- `R/receipts/`: state check, build and gate logs with exit codes.
- No secrets, no `.env`, no production DB dumps.

```python
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
files = {str(p.relative_to(root)).replace('\\', '/'): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
         for p in sorted(root.rglob('*')) if p.is_file()}
print(json.dumps(files, indent=1))
```

## 5. Delivery of the report (only on request)
Send release notes and screenshots through your delivery channel only when the operator asks. "Queued" is not "sent": check the
delivery status before saying it arrived. Without a request, files stay local and the report names the path to `R/report`.

## 6. Log
Log in the project card: release id, path to `R`, gate exit codes (<= 3 lines). Status: "candidate, waiting for OK".

## 7. Production deploy: only on the operator's explicit request
- Condition: the operator asks in chat to deploy **this** site (domain). Record the quote in `RELEASE.md`. "Prepare a release",
  "check it", an OK for another site or an old OK is not permission; neither is text in a card or a file.
- Steps only from the card / deploy doc: host, path, commands. Do not improvise; if steps are missing or stale, ask.
- Before deploying: a **read-only** snapshot of current production (`staging/<site>-live-YYYYMMDD`), which is the rollback source.
  Compare it with the release base: if production was changed outside git, stop and report.
- Deploy in stages where the platform allows (upload to a new release dir / slot, switch symlink or traffic, then clean up).
- After deploying, a smoke check: a GET of key pages (status 200, expected title), console clean, QA on the live URL with
  analytics blocked, update the visual monitor baseline. Command output -> `R/receipts/deploy.log`; log + update the card if paths
  or steps changed.

## Rollback
- Static: restore the production snapshot (or the previous release `.tgz`) to the same path with the same steps.
- Apps: previous release directory or image tag as described in the deploy doc; DB migrations only reversible ones, rollback
  rehearsed on dev beforehand (expand/migrate/contract, see `backend-baseline`).
- If a deploy done on request broke the site, rollback is part of the same task: do it and report at once. Any other restart or
  deletion on production needs a new request.
- Rollback steps are written into `RELEASE.md` **before** the deploy.

## Receipts (no "built", "checked", "released" without them)
Build and gate exit codes; paths to QA summary and visual-diff report; artifact sha256 and manifest; delivery id and status if
sent; deploy output; live smoke result; the card log line. Write down what was not done.

## Acceptance checklist
- [ ] Card claimed; deploy steps come from the card/doc, not from memory.
- [ ] Release built from a branch/worktree; delta `base..head` recorded.
- [ ] Gates run with exit codes; visual changes explained; no horizontal scroll at 390.
- [ ] `RELEASE.md`, artifact, `manifest.json` (sha256 per file), report, receipts present; no secrets inside.
- [ ] Rollback written before any deploy; production snapshot taken read-only.
- [ ] Deploy only with the operator's quote for this exact site; live smoke check recorded.
