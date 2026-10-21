---
name: backend-baseline
description: "Use when building or reviewing the server side of a web project (Next.js route handlers and server actions, FastAPI, Telegram bots): Postgres indexes, N+1, pagination and locks, object-level authorization and tenant scope, idempotent webhooks and repeated user actions, safe migrations, structured logs with request id, API contract smoke. Produces a pass/fail checklist with evidence. Not for transport/headers/CSP hardening (a security baseline) or UI work."
---

# backend-baseline: acceptance of the server side of web projects

The project's own rules file and project card override this text. It complements a general security baseline (transport,
headers, CSP, secret storage) and does not repeat it. Sources credited in `NOTICE.md`.

## When
- A new endpoint, server action, webhook, job, migration or export in a web project.
- "Review the backend", "is this safe to retry", "why is this list slow", before handing a feature to the owner.

## Inputs
- Repository at a known commit; a **dev copy** of the database; the role matrix if it exists; the endpoints in scope.

## Workflow
1. Read `references/BASELINE.md` (rules §1-§8) once per task.
2. Copy `references/CHECKLIST.md` into the task's output folder and fill **pass / fail / n.a.** with evidence (file:line, query
   output, test name, receipt). Partial reviews say which sections were not checked.
3. Database checks run read-only against a dev copy (`CREATE DATABASE <copy> TEMPLATE <dev db>`), never against production, never
   `migrate dev` / `reset` / `db push` on shared data. Use the project's own client (e.g. Prisma `$queryRaw`) if `psql` is absent.
4. HTTP contracts: a collection per endpoint group (Bruno, Hurl, or a small test file): happy path, unauthenticated, wrong tenant,
   invalid body, repeated call. Run against dev and keep the JSON/text result as the receipt. Secrets only via environment
   references (e.g. `{{process.env.NAME}}`).
5. Findings that need code go to the project owner (via the project card) unless the task is to fix them.

## Techniques and gotchas
- FK without a leading index is the most common silent slowness; check it with a catalog query, not by reading the schema.
- "Read, check in JS, write" for seats/quotas is a race: use a conditional `UPDATE ... WHERE remaining > 0` or a row lock.
- Webhooks: store-then-process; a repeat delivery must be a 2xx no-op thanks to a UNIQUE idempotency key.
- Unauthenticated API calls must get 401/403 JSON, not an HTML login redirect.
- Telegram Mini Apps: identity only from server-side `initData` HMAC verification; `initDataUnsafe` proves nothing.

## Hard rules
- No production connections, deploys or migrations unless the operator asked for that exact site; then `migrate deploy` only,
  after a verified backup.
- No destructive migration without expand -> migrate -> contract and a rollback/forward-fix note.
- No new framework or auth library just because a reference mentions it.
- No secrets in code, collections, logs, project notes or command arguments.

## Acceptance checklist
- [ ] `CHECKLIST.md` filled for every section in scope; every fail has evidence and a follow-up owner.
- [ ] DB evidence came from a dev copy; no production connection was opened.
- [ ] Contract smoke result saved (exit code + file path).
- [ ] Blocking fails listed at the top of the summary.
