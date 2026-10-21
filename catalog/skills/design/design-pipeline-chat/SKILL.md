---
name: design-pipeline-chat
description: Use when the operator asks an agent in chat to start or continue a named design-production project - triage incoming files, build the brief, route scope, plan or estimate, find blockers, advance the next gate ("start project X", "what's next on X"). Keeps one shared project state with claims tagged confirmed / assumption / contradiction / open_question and ends every turn with a compact handoff. Not for workspace setup and migration (design-pipeline) or an isolated image or file edit without project state.
---

# Design Pipeline Chat

The workspace pipeline is the operating system and the active project is its configuration. Keep one shared project state; professional roles (designer, 3D, prepress, estimator) are views over that state, not separate chats.

## Start

1. Locate the workspace and projects root the same way `design-pipeline` does.
2. For a new project or a scope change, run the scope survey: what the project is, which outputs are wanted, which inputs exist. Skip answered questions. Distinguish generation, editable layouts, 3D, engineering, prepress and estimates. Never assume full production from the project type. Ask geometry, vendor and budget questions only when the selected outputs need them.
3. Resolve the active project from the nearest `PROJECT.yaml` or the project name in the request. Ask only when it cannot be inferred safely.
4. Read `PROJECT.yaml`, its selected profile, the chat state file (for example `DOCS/CHAT_STATE.json`) when present, and the project rules listed under `pipeline.rules`.
5. If the operator asks to start or continue and there is no chat state, initialize it. Initialization must refuse to overwrite existing state.

## Operate

- Load only sources relevant to the current phase. Exclude caches, generated previews, archives and `node_modules` unless provenance requires them.
- Before any application work, build a compact packet: deliverable, exact source paths, confirmed dimensions and copy, allowed changes, stop-list, output format and QA criteria.
- Activate one authoring skill for the current master type (raster, vector, Blender scene or parametric CAD) and open only the reference it selects. Add `design-production-preflight` at handoff, not during design.
- Record every claim as `confirmed`, `assumption`, `contradiction` or `open_question`, with source paths and confidence.
- Reuse existing answers. Ask only questions whose answers change scope, function, safety, schedule, budget or approval.
- Select one lead profile and optional routes from the profiles config; explain the evidence.
- Persist selected and excluded work in `DOCS/START_SCOPE.json` and mirror the operator's decision and concrete deliverables in the chat state. `unknown` is unresolved, not approval. The phase list is a menu: concept or layout delivery may finish without engineering. Mark inapplicable gates `not_required` with a scope-decision reference. Never automatically overwrite approved or blocked gates, and never waive checks for actual fabrication or print outputs.
- AI role outputs are proposals. The operator or a named owner closes decision gates. Engineering, prepress, vendor and budget confirmations cannot be invented.
- After a material change, update the chat state and the relevant canonical project document. Preserve history by adding or superseding entries, not erasing them.
- When the project file and chat state disagree, use the more restrictive status and report the conflict.

## Chat state shape (suggested)

```json
{
  "project": "<code>",
  "phase": "brief|style|geometry|prerender|visual|dfm|production|handoff|archive",
  "gates": {"brief": "approved|pending|blocked|not_required"},
  "claims": [{"text": "...", "status": "confirmed|assumption|contradiction|open_question", "source": "<path>", "confidence": 0.8}],
  "blockers": [{"what": "...", "owner": "..."}],
  "decisions": [{"date": "YYYY-MM-DD", "decision": "...", "by": "...", "supersedes": null}]
}
```

## Finish every project turn

Return a compact handoff: active project, current phase and gate, confirmed information, assumptions or contradictions, blockers and their owners, decisions needed, and the next smallest action.

Deliver final files only when the operator explicitly asks and the deliverable passed `design-production-preflight`: send the exact final files once through your delivery channel and report its receipt (queued is not sent). Never send incoming client files, drafts, style-frame variants or intermediate renders; make a compact delivery copy when a file exceeds the channel's size limit.

## Acceptance checklist

- [ ] Project resolved from files; scope decision recorded.
- [ ] Every new claim tagged with status and source.
- [ ] No gate closed by the agent alone; no invented confirmations.
- [ ] Chat state and canonical documents updated after material changes.
- [ ] Handoff block present at the end of the turn.

Do not continue past a required approval merely because enough material exists to speculate.

## Boundaries

- Workspace setup, migration diagnostics and pipeline maintenance go to `design-pipeline`.
- One-off image or file edits without project state go directly to the authoring skill.
