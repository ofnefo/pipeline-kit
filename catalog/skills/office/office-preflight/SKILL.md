---
name: office-preflight
description: Use when an office project package must be audited before approval, handoff or delivery ("проверь перед отправкой", "предполётная проверка", "всё ли сходится"). Reconciles estimate JSON with the workbook, checks document and payment registers, verifies Word/PDF/Excel/slide rendering, finds missing approvals or stale versions and produces a release-blocker report. Not for building the documents themselves or for sending them.
---

# Office Preflight

A read-only audit. It produces a verdict and evidence; it never fixes, approves or sends anything by itself.

## Inputs

- The project root and its config (paths are relative to the root).
- Active estimate JSON + calculation output, the workbook and its cell map.
- Document register, payment register, QA evidence file.
- The intended delivery target (if delivery is the next step).

## Check five layers

1. **Structure** - config present; every configured path is relative, resolves inside the project and exists;
   required folders exist; no path escapes (`..`, absolute paths, symlinks out of the root).
2. **Numbers** - the active estimate calculates without unexplained warnings
   (`estimate_engine.py calculate --strict` from the estimate-production skill); the workbook was recalculated (formula caches exist), has no error
   values and matches the oracle on every mapped cell (money to 0.01, margin to 6 decimals); tax, credit, profit
   and margin reconcile with the КП and contract totals.
3. **Registers** - every required document and payment has an owner, a real status, a version and a source link;
   duplicates and superseded rows are explicit; the payment CSV and the estimate `payments` agree by id; `PAID`
   rows have a paid date.
4. **Artifact QA** - every DOCX/PDF page and every sheet/slide was rendered and inspected after the latest change;
   each QA evidence entry's sha256 still matches the artifact (a changed hash voids the evidence).
5. **Delivery** - file names and versions are unambiguous; comments, tracked changes and metadata/privacy state are
   intentional; the package manifest is complete; the destination is known and authorised.

Structural status and delivery readiness are separate verdicts: intake can pass while delivery is blocked. Reading
cached cell values is not recalculation, and recalculation is not visual inspection - do both before recording QA.

## Blockers

Block delivery for: formula errors, unexplained total mismatches, unresolved tax assumptions, missing source files,
corrupt outputs, stale approved versions, invented requisites, unresolved tracked changes, unreadable rendering,
missing required approval.

Non-blocking warnings still name the risk, the evidence and the owner. Never downgrade a blocker to ship the package.

## Output

Report:

- gate and verdict (`pass` / `block`), separately for structure and delivery readiness;
- exact evidence checked (files, hashes, cells, pages);
- mismatches and missing approvals;
- output paths;
- the next smallest action and its owner.

Separate historical archive issues from live blockers. Write a persistent report file only when asked.

## Acceptance

- [ ] All five layers checked, each with named evidence.
- [ ] Every blocker listed with the file/cell/page that proves it.
- [ ] No file in the project was modified by the audit.
