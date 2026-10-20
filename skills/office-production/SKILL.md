---
name: office-production
description: Use when building or checking a local Office project, incoming document inventory, estimate, proposal draft, registers or reconciled delivery package.
---

# Office production

Read `docs/MODULES.md` and resolve the project's `OFFICE_PROJECT.json` using `modules/office/scripts/office_project.py resolve`. For a new project, use its `init` command; retain the template registers and schemas. Install only the required optional office/PDF dependencies explicitly. Original incoming files remain unchanged.

Inventory sources with `document_inventory.py` and extract selected content with `extract_source.py`; record source hashes and distinguish supplied facts from assumptions. Keep financial inputs in the estimate JSON. Calculate with `estimate_engine.py calculate <input> --as-of <date> --output <new-result>`. Reconcile line quantities × days × unit prices, explicit amount differences, tax basis, credit period, payment status and net result. Never silently choose tax/credit rates.

Proposal generation uses `prepare_proposal.py` with explicit context. Inspect its `--help` and required fields; missing commercial facts block an approved document. Draft DOCX and workbook input JSON are intermediate deliverables. Recalculate an authored workbook separately and inspect rendered PDF pages, including tables, totals, page breaks and signatures.

Run `office_project.py doctor --project <path> --json` once after changes. Fix reported inconsistencies or state the exact remaining blockers. Technical schema validation does not imply commercial approval. Use `deliver --local-only` only after document selection/version checks; there is no messaging adapter. Acceptance: financial totals reconcile, source provenance is retained, every final file has a version and approval state, and a human has checked the final rendering.
