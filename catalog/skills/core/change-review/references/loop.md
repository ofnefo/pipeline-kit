# Running the loop

The writer runs the loop. Reviewers are always fresh (a new thread, process or subagent per pass) and read-only. Each answer is
stored with `review_receipt.py add`, which checks the verdict format. Commands below run from the skill's `scripts/` folder with
`python -X utf8 -B`. Receipts and diffs go to the state dir: `--state-dir`, else env `CHANGE_REVIEW_STATE_DIR`, else `<repo>/.review/`
(add `.review/` to `.gitignore` or point the env var outside the repo).

## Common steps

1. `review_receipt.py diff --repo <repo> --slug <slug> > diff.json` (narrow with `--staged`, `--range A..B` or paths).
2. `review_receipt.py new --slug <slug> --level L1|L2 --task "<request>" --author <family>:<id> --repo <repo> --diff-json diff.json [--command "<deploy cmd>"]`.
   Agent ids are `family:name` (`claude:session-1`, `codex:gpt-x`); the family part is what the independence rule compares.
3. Fill the template from `reviewer-prompts.md`, dispatch it (routes below), save the raw answer to a file.
4. `review_receipt.py add <receipt> --pass N --role combined|acceptance|code --reviewer <family>:<id> --route cli|subagent|mcp|mailbox|other --answer <file> [--thread-id <id>] [--seconds <s>]`.
5. `review_receipt.py finalize <receipt> --status accepted|exhausted|stopped`, then `review_gate.py check --repo <repo>`.

## Writer = Claude → reviewer from another model family

Use another model family's CLI, run read-only, with the repo as working directory. Example with Codex CLI:

```
codex exec --sandbox read-only "<filled template>"
```

- A new process (or thread) for every review and every pass; never resume the previous reviewer's thread.
- L2: start the acceptance and code reviewers at the same time (two background processes or two parallel tool calls).
- Typical timeout 10–15 min. Record `--route cli` (or `mcp` if your harness wraps the CLI as a tool).
- Read-only sandboxes often cannot start every interpreter. Put checks in `{CHECKS}` that run there (git, node, shell built-ins),
  or let the reviewer report "could not run" and add your own run's output as `author-reported:` evidence.
- Reviewer answers may come in prose in any language; the helper extracts the last JSON object (also from a json fence).

## Writer = Codex (or another non-Claude agent) → Claude reviewer

| Route | When | How |
|---|---|---|
| Claude Code headless | the writer's sandbox may start processes | `claude -p "<filled template>" --permission-mode plan --allowedTools "Read,Grep,Glob,Bash(git diff:*),Bash(git show:*),Bash(git log:*)" --output-format json` with the repo as cwd. Record `--route cli` |
| Claude subagent | the writer runs inside a Claude Code session (orchestrated) | dispatch a read-only reviewer subagent (tools Read/Grep/Glob/read-only Bash); record `--route subagent` |
| Mailbox / ticket | asynchronous; commit/deploy waits | send the filled template and receipt path to a reviewer session through your team's queue; record `--route mailbox` |
| Same-family fallback | other family unavailable | a fresh thread of the same family; needs `new --same-family-reason "<why>"` and shows in the receipt |

Be honest in the report: a same-family review is weaker than a cross-model review. Say so in the final status line.

## Repair passes

- Address all blocking items from all reviewers of the pass in one repair. Rerun only invalidated checks; keep evidence for
  unchanged behaviour. Non-blocking suggestions do not start a new pass. Then run `diff` again: the new pass needs a new
  `--diff-json` and a `--repair "<one line>"`.
- Put the previous blocking list into the repair addendum (`{PREVIOUS_BLOCKING}`) of fresh reviewer prompts.
- Bound: L1 has 1+2 passes, L2 has 1+3. When the last pass is rejected: `finalize --status exhausted`, stop and report to the
  operator (what is blocked, receipt path, what you would try next).

## Receipt schema `change-review/1`

```json
{
  "schema": "change-review/1", "slug": "...", "level": "L1|L2", "max_repairs": 2, "task": "...",
  "author": "claude:<session>", "repo": "/path/to/repo", "same_family_reason": "", "commands": ["sitectl deploy *"],
  "status": "in_review|accepted|exhausted|stopped", "final_diff_sha256": "...",
  "passes": [{"n": 1, "repair": "",
              "diff": {"repo": "...", "head": "...", "mode": "worktree|staged|range|tracked", "sha256": "...",
                       "files": {"path/a.py": "<blob sha>", "old.json": "deleted"}, "patch": "...", "stat": "..."},
              "reviews": [{"role": "combined|acceptance|code", "reviewer": "codex:<model>", "route": "cli",
                           "thread_id": "...", "seconds": 85, "verdict": {"verdict": "accepted", "evidence": [], "blocking": [], "nonblocking": []}}]}]
}
```

`review_gate.py` treats a receipt as covering a file when `status` is `accepted`, `validate` reports no problems, the repo
matches, the level is at least the file's level, and the last pass's `diff.files[path]` equals the current blob sha.
A deploy or data command is covered by an accepted L2 receipt whose `commands` lists it (trailing `*` = prefix match).
Receipts are searched in: `receipt_dirs` from the config, `$CHANGE_REVIEW_STATE_DIR/receipts`, `<repo>/.review/receipts`, `<repo>/receipts`.

## Hook (gate without remembering)

`review_gate.py hook` reads a Claude Code PreToolUse JSON on stdin and acts only on `git commit` and deploy commands.
- **warn** is the default (env `CHANGE_REVIEW_GATE=warn`): prints a reminder, the command runs.
- **block** (`--mode block` or `CHANGE_REVIEW_GATE=block`): exits 2 with the reason on stderr; Claude Code cancels the call.
- Any internal error exits 0 silently, so the hook never breaks a session.

Example `.claude/settings.json` entry (start in warn mode, switch to block once receipts are routine):

```json
{"hooks": {"PreToolUse": [{"matcher": "Bash|PowerShell",
  "hooks": [{"type": "command", "command": "python -X utf8 -B /path/to/change-review/scripts/review_gate.py hook"}]}]}}
```
