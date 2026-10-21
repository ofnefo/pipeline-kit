---
name: design-pipeline
description: Use when a reusable multi-project spatial-design pipeline (exhibitions, shows, weddings, interiors, retail, museums, hybrid events) must be set up, diagnosed, migrated or explained - creating or onboarding projects, locating the active PROJECT.yaml, applying discipline profiles, auditing moved workspaces, handoff reports, wiring project rules, routing work to authoring skills. Runs a seven-gate production model scoped to the deliverables actually requested. Not for chat-led progression of one active project (design-pipeline-chat) or as a client style guide.
---

# Design Pipeline

The shared pipeline is the operating system; each project is its configuration. Keep reusable process knowledge global. Keep client, brand, venue, palette, copy and project exceptions inside the project folder.

## Expected layout (adapt names to your workspace)

```text
<PIPELINE_ROOT>/
  config/paths.json              # projects_root (absolute or relative)
  config/profiles/profiles.json  # discipline profiles
  docs/method/                   # process handbook (onboarding, routes, prompts, review, estimates)
  docs/styles/                   # style catalogue
  docs/production-knowledge/     # vendor and fabrication notes
  templates/project/             # template, never a live project
<PROJECT_ROOT>/                  # under projects_root
  PROJECT.yaml                   # type, profile_file, routes, rules, vendor_profile, rate card
  DOCS/START_SCOPE.json          # selected / excluded work
  DOCS/AI_RULES.md               # project-only constraints
```

## Locate context

1. Resolve the projects root: environment variable (for example `DESIGN_PROJECTS_ROOT`), else `projects_root` in `config/paths.json`, else a default folder inside the workspace. It may live outside the workspace.
2. The active project is the nearest directory with `PROJECT.yaml` inside the projects root. Never treat the template as a live project.
3. The workspace is the nearest ancestor with the method handbook. When working inside an external projects root, locate it from a marker file in that root (for example `.pipeline-root.json` with `{"pipeline_root": "..."}`).
4. If no project is found, list the projects root and ask only when the task cannot identify the project.
5. Never assume a fixed drive, username, workspace path or project code.

## Load only what the task needs

Always read `PROJECT.yaml` and, when `pipeline.profile_file` is set, that profile before evaluating gates. Do not infer a profile from a client name. Then read only the handbook part for the task: onboarding, discipline routing, style catalogue, portfolio research (date every claim), folder structure, prerender review and prompts, estimates and rate card, production knowledge and vendor profile, tool/MCP routing (only when the task enters an application), and every path under `pipeline.rules`.

Explicit operator instructions outrank project documents; project documents outrank reusable examples.

## Scope first, then gates

Run a scope survey before assuming work: generation only, editable layouts, 3D, engineering, prepress, estimate, or a combination. Store the decision in `DOCS/START_SCOPE.json`. Standalone generation and layouts do not need engineering, production budgeting or fabrication approval. `unknown` is unresolved, not approval.

The full spatial route has seven gates; apply only those relevant to the selected deliverables and never skip one silently:

1. Brief lock: objective, deliverables, venue, dates, budget, decision owners.
2. Style approval: one style code, creative level, hero element, references, stop-list.
3. Geometry approval: dimensions, aisles, equipment, supports, camera, service access.
4. Prerender approval: composition and function reviewed before AI finishing.
5. Visual approval: approved material, graphic and lighting enhancement only.
6. DFM and engineering: vendor constraints, joints, mounts, loads, fire and evacuation.
7. Production approval: print files, drawings, bill of materials, estimate, deadlines, owners.

A discipline profile may add evidence or hold points; it never weakens a gate. Mark inapplicable gates `not_required` with a reference to the scope decision. Report the current gate, profile gaps, missing evidence, next smallest action and responsible role. An AI image is never engineering approval.

## Diagnose migration and report

Provide (or port) a read-only `doctor` that checks project links after a move, an optional deep mode that inspects dependencies inside binary files, and a `report` that writes a Markdown handoff with overwrite protection.

- Classify historical references in archives, caches and generated folders separately from live blockers.
- A shared dependency outside the workspace is not stale by location; verify the target exists and document it.
- Never auto-relink, pack, resave or otherwise mutate `.blend` or OOXML files (`.xlsx`, `.docx`, `.pptx`) from heuristic matches. Report the stored path, resolved state and candidate mappings; change a binary only with explicit authorization and an exact mapping.

## Route work

- Images: curate the brief first, use a subscription or cloud image model only if the operator approved it for the job, then local ComfyUI chains for variations and production (`design-comfy-generation`). Everything else (video, 3D, upscale, cutout) is local-first. Paid per-call APIs need the operator's explicit go-ahead and a cost note.
- Active project progression, briefs, estimates, next steps: `design-pipeline-chat`.
- Directions, moodboards, hero/buildable/value-engineered variants: `design-style-director`.
- Locked-render enhancement: `design-render-refiner`.
- Banners, layouts, contact sheets, raster assembly: `design-graphic-compositor`.
- Masks, retouching, raster masters: `photoshop-production`. Vector layouts, signage, dielines, SVG/PDF: `illustrator-production`.
- Spatial blockouts and scenes: `blender-production`. One photo to a 3D blockout: `image-to-scene`. Parametric parts and STEP/DXF: `cad-production`.
- Print and production readiness: `design-production-preflight`. Rate cards and estimates: a spreadsheet skill that preserves formulas.

Reuse existing ComfyUI and model libraries; do not duplicate them for this pipeline.

## Create or onboard a project

Ask only missing project-type, work-selection and source questions in plain language. Resolve the profile, create the minimal core, then add only the folders for selected work. Do not copy the full template tree or default to full production. Never copy rules from another client. Project-only constraints go to `DOCS/AI_RULES.md`, listed under `pipeline.rules`.

## Acceptance checklist

- [ ] Active project and profile resolved from files, not guessed.
- [ ] Scope decision recorded; gates limited to selected deliverables.
- [ ] No binary file mutated from heuristic matches.
- [ ] Handoff gives the active project, gate status, what changed, unresolved items, next action and exact output paths.

## Finish each turn

Leave the compact handoff above when changes were made. For review or diagnosis requests, report findings without creating files. Deliver final files to the client only through your delivery channel, after `design-production-preflight` and the operator's explicit approval; never send incoming client files, drafts, variants or intermediate renders.
