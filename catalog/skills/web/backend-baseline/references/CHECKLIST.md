# Backend baseline review — <project> @ <commit> (<date>)

Reviewer: `<reviewer>`. Rules: `BASELINE.md` (§ numbers below). Mark **pass / fail / n.a.**; evidence = file:line, query output,
test name or receipt path. Read-only against a dev copy; no production connection.

| § | Check | Result | Evidence | Follow-up |
|---|---|---|---|---|
| 1.1 | FK columns have a leading index (exceptions recorded) | | | |
| 1.2 | Hot list filters covered by composite/partial indexes (EXPLAIN) | | | |
| 1.3 | No N+1 on list pages | | | |
| 1.4 | Lists have an upper `take`; cursor pagination for large feeds | | | |
| 1.5 | No network calls inside transactions; minimal row locks | | | |
| 1.6 | Business keys enforced by UNIQUE/CHECK in the DB | | | |
| 1.7 | Connection pool sized and shared | | | |
| 1.8 | Raw SQL parameterised; no `Unsafe` with input | | | |
| 2.1 | Object-level authz before every read/write by id | | | |
| 2.2 | Tenant scope in one helper; cross-tenant test exists | | | |
| 2.3 | Unauthenticated API → 401/403 JSON (not login redirect) | | | |
| 2.4 | Role matrix documented; bulk/export use same rules | | | |
| 2.5 | Telegram Mini App identity via server-side `initData` check | | | |
| 3.1 | Webhook secret/HMAC verified in constant time → 401 | | | |
| 3.2 | Idempotency key per external event with UNIQUE | | | |
| 3.3 | Store-then-process with retry; failed events visible | | | |
| 3.4 | Malformed payload handling logged with event id | | | |
| 3.5 | Double click / resubmit / repeated QR = one effect | | | |
| 3.6 | Limits enforced atomically (lock or conditional update) | | | |
| 4.1 | Migrations reviewed as SQL | | | |
| 4.2 | Expand → migrate → contract for destructive changes | | | |
| 4.3 | Rollback or forward-fix note per migration; big-table locks | | | |
| 4.4 | Production only `migrate deploy`, on explicit request, after backup | | | |
| 5.1 | Single structured JSON logger | | | |
| 5.2 | Request id propagated to logs, response header, UI errors | | | |
| 5.3 | No secrets/PII in logs | | | |
| 5.4 | Event ids in webhook/job logs; AI cost in logs | | | |
| 5.5 | Health endpoint checks DB, exposes no internals | | | |
| 6.1 | Schema validation at boundary; stable error shape (UI-language message) | | | |
| 6.2 | Contract smoke per endpoint group | | | |
| 6.3 | Timeouts on outbound calls; graceful degradation | | | |
| 6.4 | Field work: form state kept, retry-safe submit | | | |
| 6.5 | Manager output: search, bulk, CSV/XLSX, error history | | | |
| 7.1 | Event time zone; `timestamptz` | | | |
| 7.2 | Roles and service lifetime configurable | | | |
| 7.3 | Long names fit; human-readable errors | | | |
| 7.4 | AI: cost, limits, timeout, outage behaviour, manual stop | | | |
| 8 | Secrets only in env / untracked files | | | |

## Summary
- Fails that block release: …
- Follow-ups (owner, card): …
