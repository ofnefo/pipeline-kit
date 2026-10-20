---
name: pipeline-control
description: Use when starting or maintaining a local Pipeline Kit project, task board, NameNode card, Studio chat, project files or optional model configuration.
---

# Local Control workflow

Resolve the kit root and `PIPELINE_KIT_WORKSPACE` first. Read `docs/CONFIGURATION.md` and the project's rules. Never infer a remote host or search unrelated disks. Use `python pipeline_kit.py namenode search '{"query":"sample"}'`, then `card` with the exact id. Claim the card under a stable agent id before edits; an occupied card requires coordination with its owner. The last argument is JSON; use your shell's literal-string quoting rules.

Define the result and sufficient checks. For substantial production, record brief → references → sample → production → technical and user acceptance → delivery. Keep the task board version from each read; a 409 means reread before editing, not force the write. Preserve source files and use new result versions. Use the local quarantine/restore flow for file removal.

Start Control with `python pipeline_kit.py --workspace <absolute-path> serve`. Create a project in Projects and open Studio. Local chat is optional and disabled until the operator configures an exact loopback endpoint/model. Do not invent model availability or enable a paid route. Generation and external delivery are separate adapters and unavailable in this distribution.

Record actual paths, outputs and check results in the project; log the meaningful change in NameNode and release the claim at handoff. Acceptance: the intended user journey works, persisted data survives a reload, and no unsupported external action is represented as completed. Use the relevant production skill for domain checks. Read `docs/AGENTS.md` for agent integration without rewriting global settings.
