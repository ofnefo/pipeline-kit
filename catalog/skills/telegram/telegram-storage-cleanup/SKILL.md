---
name: telegram-storage-cleanup
description: "Use when auditing or reclaiming disk space used by a Telegram assistant: exports, archives, media caches, logs, build caches, duplicated models (RU: \"почисти место\", \"что занимает диск\"). Builds an inventory and grouped manifest, quarantines before purge, verifies hashes and smoke tests. Not for reading message bodies or deleting active databases, sessions, secrets, user files or models without verification."
---

# telegram-storage-cleanup

## Purpose
Reclaim space safely: know what each large item is, whether it can be rebuilt, and how to undo the move.

## Inputs
- The assistant's root (`<PROJECT_ROOT>`), its data and cache folders, the quarantine location, the operator's goal (bytes to free).

## Inventory (read-only)
For each candidate record: path, size, sha256 (for files to move), category, dependency (what reads it), canonical copy,
reproducibility, reclaimable bytes, risk, rollback. Use `references/inventory-template.md`. Never open message bodies; sizes and
metadata are enough.

## Protected (never in a cleanup group without separate, explicit instruction)
Active databases, Telegram sessions, secrets/config, user files, models, the notes vault, original exports, backups, quarantine.

## Manifest groups
A cleanup request authorises a **manifest only**. Group candidates:
1. Reproducible caches (build, package, thumbnail caches)
2. Verified duplicates (same sha256, canonical copy known)
3. Quarantined exports past their keep date
4. Active archive dependencies (need replacement first)
5. Models pending hash parity with their owning pipeline
6. Unknowns (left alone, reported)

## Execute
1. Resolve absolute paths and confirm each lies under the allowed root; never follow junctions/symlinks out of it.
2. Re-hash just before acting.
3. **Move** to a dated quarantine (`<quarantine>/<YYYY-MM-DD>/`) with a manifest; no direct delete.
4. Purge from quarantine only after a confirmation that names the group.
5. Receipt: before/after hashes and bytes, moved paths, free space before/after; then smoke-test the assistant.
6. An active archive is removed only after its replacement passes tests and the app starts without it.
7. Models only after hash verification in the pipeline that owns them.

## Acceptance checklist
- [ ] Inventory complete; no message bodies read.
- [ ] Protected items untouched.
- [ ] Manifest confirmed per group; moves went to quarantine with a manifest.
- [ ] Receipt with hashes and bytes; smoke test passed.

## Boundaries
No deletes outside quarantine purge; no touching protected items; no cleanup of another application's data.
