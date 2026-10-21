# Triggers — deciding L0 / L1 / L2 from facts

The level comes from what the change touches and does, not from how confident the writer feels.
`scripts/review_gate.py classify` applies the path and command rules below to the real diff. You add the task facts
(type, blast radius, reversibility) that a diff cannot show. **The highest matching row wins.** Overrides only raise the level.
Classify the actual change, not the project: a project's historical "high-risk" label does not make a typo fix L2.

## 1. Touched paths (automatic)

Globs match the repo-relative path, case-insensitive. Evaluation order: agent rules / deliverables → docs → security, deploy
config, data deletes → shared code → repo default.

| Level | Path pattern | Why |
|---|---|---|
| L2 | any `AGENTS.md` / `CLAUDE.md`, `.claude/settings*.json`, `.claude/hooks/**`, `.claude/agents/**`, `.codex/**` | agent rules: every session obeys them |
| L2 | `deliver*/**` anywhere | client deliverable |
| L2 | a path segment `auth`, `oauth`, `secret(s)`, `credential(s)`, `password(s)`, `token(s)`, `security`, `permission(s)`, `firewall`, `acl`; `*.pem`, `*.key`, `*.pfx` (not under `tests/`, `fixtures/`, `skill_evals/`) | secrets / auth / security code |
| L2 | `*deploy*.{ps1,sh,py,yml,yaml,json,toml}`, `.github/workflows/**`, `*nginx*.conf`, `*.service`, `docker-compose*`, `Dockerfile*` | deploy configuration |
| L2 | a deleted data file (`.json .jsonl .csv .db .sqlite .parquet .yaml .xlsx`) | data deletion |
| L2 | config `l2_paths` globs | your own high-stakes paths (payments, migrations…) |
| L1 | `tools/**` | shared tools |
| L1 | `agents/**`, `skills/**` (including `SKILL.md` and skill `references/`), `.claude/**` | agent config and skills |
| L1 | `scripts/**` | scripts that pipelines and other agents run |
| L1 | `lib/**`, `shared/**`, `common/**`, config `l1_paths` globs | shared libraries |
| L1 | any other code in a repo listed in config `l1_repos` | other agents run it |
| L0 | `*.md`, `*.txt`, `*.rst`, `docs/`, `notes/`, `plans/`, `receipts/`, `*.log` (except the L2 rule files and skill instructions above) | documentation |
| L0 | anything else that is project-local | routine |

## 2. Commands (automatic with `--command`, and in the hook)

| Level | Command | Notes |
|---|---|---|
| L2 deploy | `scp/rsync/sftp … <prod host>:path` (upload); `ssh <prod host> "… git pull / systemctl restart / docker up / pm2 restart / nginx -s / npm ci / rm / mv / cp / deploy …"`; a configured deploy CLI (`deploy_commands`, also run as a script); `deploy*.ps1/sh/py … prod/live`; writes to a configured production mount | reading logs over ssh is not a deploy |
| L2 data-op | `Remove-Item -Recurse`, `rm -r…`, `rmdir /s`, `del /s`, `Move-Item`, `robocopy /MOV /MOVE /MIR /PURGE`, `[IO.Directory]::Move`, `git push --force` | only via `check --command`; the hook does not gate these (too frequent on temp dirs) |
| gate point | `git commit` (also `git -C <repo> commit`) | the level comes from the staged files (`-a`: all tracked files) |

Default production hosts: names matching `prod*`. Everything else site-specific comes from the config below.

## 3. Site config (`gate.json`)

Looked up as `--config`, else env `CHANGE_REVIEW_CONFIG`, else `<repo or cwd>/.review/gate.json`. Missing keys keep defaults.

```json
{
  "prod_hosts": ["prod-web", "prod-db\\d*", "shop-live"],
  "deploy_commands": ["sitectl deploy", "deploy.py --env prod"],
  "prod_mounts": ["/mnt/prod", "Y:\\"],
  "network_drives": ["N"],
  "l1_repos": ["platform-tools"],
  "l2_paths": ["infra/payments*", "migrations/*"],
  "l1_paths": ["packages/ui/*"],
  "receipt_dirs": ["/srv/review-receipts"]
}
```

- `prod_hosts` are regex fragments matched against ssh/scp/rsync host names (with optional `user@`).
- `network_drives`: drive letters where git must never run; the hook then checks the session repo instead. For the receipt
  helper set env `CHANGE_REVIEW_REFUSE_PATHS` (e.g. `N,unc`) so `diff` refuses those paths.

## 4. Task facts (the writer decides; take the higher level)

- **Task type.** Production deploy or rollback, a client handover, a data migration/move/delete, a change to credentials, auth,
  permissions or tool-access policy, or a change to agent rules → **L2**. A new or changed shared tool, skill or pipeline step → **L1**.
- **Blast radius.** Other agents, pipelines or scheduled jobs consume it → at least **L1**. Clients, live users or money → **L2**.
- **Reversibility.** It cannot be undone by `git revert` plus a redeploy (deleted data, sent messages, external state, a
  migration without a down step) → **L2**.
- **Not raised:** the size of the diff alone, and the writer's own doubt (re-check once instead).

## 5. Floors and overrides

- A project-level `review_level` (e.g. in a project manifest) is advisory context; `classify` reports it separately and it
  does not raise every change automatically.
- Use `--floor L1|L2` for an explicit task requirement or a concrete risk that path rules cannot see; record the reason in the
  receipt. Never use a lower floor to bypass a high-risk path or command.
- Routine documentation stays L0; shared UI behaviour is L1; agent rules, auth, destructive operations and production deploys stay L2.
- The requester's explicit words ("no review needed", "double-check this") override the table for that task. Quote them in the receipt `task`.

## 6. When it runs (lifecycle)

| Moment | Action | Trace |
|---|---|---|
| **Start** | `review_gate.py classify --repo <repo>` on the planned paths (or judge from the tables) plus task facts; put the level at the start of your task note, e.g. `[L2] deploy shop menu fix`. L0 needs no tag | task note / tracker |
| **Before commit / deploy** | `review_gate.py check --repo <repo> [--command "<deploy cmd>"] [--floor L2]`. Exit 0 → go ahead. Exit 2 → run the review loop (SKILL.md), then check again. The PreToolUse hook runs the same check on `git commit` and deploy commands (warn first, block later) | gate output |
| **Done** | the final status line carries the receipt path and verdict, e.g. `L1 accepted .review/receipts/2026-01-15-x.json` | status line |

- Reconcile the initial classification with the final diff and operation. Explain any change in level from concrete scope/risk
  facts, never from a wish to pass review.
- An `exhausted` receipt never passes the gate. Stop and report to the operator.
- Changes outside git (data moves, shared asset folders, rule files outside a repo): there is no diff for the gate. Classify by
  the tables, run the review with an exact path/size/hash list, and record the receipt path the same way.
