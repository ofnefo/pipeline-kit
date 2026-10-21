# Storage inventory template

Root: `<PROJECT_ROOT>`  Date: YYYY-MM-DD  Free space before: N GB  Goal: N GB

| Path (relative) | Size | sha256 | Category | Read by | Canonical copy | Reproducible | Reclaimable | Risk | Rollback | Group |
|---|---|---|---|---|---|---|---|---|---|---|
| cache/thumbs/ | 1.2 GB | - (dir) | cache | app UI | - | yes (regenerated) | 1.2 GB | low | regenerate | 1 |
| exports/2025-01/ | 3.4 GB | per-file list | export | none | archive/2025-01.tar | no | 3.4 GB | medium | restore from quarantine | 2 |

Categories: cache, build, log, export, archive, duplicate, model, database, session, user-file, unknown.
Groups: 1 reproducible caches, 2 verified duplicates, 3 quarantined exports, 4 active archive dependencies,
5 models pending hash parity, 6 unknowns (no action).

## Receipt
| Path | Bytes | sha256 before | Quarantine path | sha256 after | Result |
|---|---|---|---|---|---|

Free space after: N GB. Smoke test: command, exit code.
