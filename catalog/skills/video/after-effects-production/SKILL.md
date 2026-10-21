---
name: after-effects-production
description: Use when an existing .aep project, AE plugin or template, compositing, expressions or keyframed motion has to be built, revised, checked or rendered in After Effects ("Афтер Эффектс", "AE", "композиция", "MOGRT"). Drives AE through a local MCP bridge (AE open, bridge panel connected) or GUI-run JSX, with versioned renders and frame checks. Not for new headless motion pieces without AE (motion-graphics) or primary editorial timelines (resolve-production).
---

# After Effects production

Purpose: change and render After Effects compositions without damaging the operator's projects, and hand versioned
renders to the edit.

## Inputs

- The `.aep` (work on a copy or a saved version), the comp name, size, fps, duration, alpha requirement and the
  intended NLE handoff.
- Fonts, footage and plugins the project references (check for missing items before editing).

## Routes

| Route | Use for | Notes |
|---|---|---|
| AE via an MCP bridge | revisions of existing `.aep`, AE plugins, Adobe templates | needs AE running and the bridge panel connected; run the bridge's health call first |
| AE via GUI JSX (File > Scripts > Run Script File) | batch builds when the bridge is not connected | reliable; log what the script built and rendered |
| `aerender` (headless) | render-only batches | verify on a one-frame test first (see gotchas) |
| Headless HTML/canvas renderer | new titles and lower thirds without an `.aep` | see `motion-graphics` |

## One-time bridge gate (the operator does this in AE)

1. Edit > Preferences > Scripting & Expressions > **Allow Scripts to Write Files and Access Network** = on.
2. Restart AE fully.
3. Open the bridge's status panel from the Window menu and connect it.
4. The agent then runs the health call, then project info or a frame capture.

If the bridge is not connected, stop and report these exact clicks. Do not script around the gate. Keep any startup
script inert; connecting is an explicit panel action.

## Composition loop

1. Confirm comp, dimensions, frame rate, duration, colour/alpha requirement and the handoff format.
2. Save a version before mutation. Inspect existing layers and naming instead of assuming a blank comp.
3. Build with named comps and layers, explicit timing and reusable controls (expression controls, essential
   properties). Keep expressions readable; avoid hidden dependencies on layer index.
4. Capture representative frames after each material change and inspect them visually.
5. Render a versioned component to `60-motion/<piece>/v00N/`, record a receipt (source `.aep` hash, comp, version,
   render settings, output path and hash), and verify the returned file before NLE import.

Ask before deleting comps or layers, replacing render-queue items or applying a project-wide change.

## Techniques and gotchas

- AE is a heavy GUI app: snapshot CPU/GPU, RAM/VRAM and running jobs before launching it, and take the GPU lock (one
  heavy GPU job at a time) for long renders. Never close or save the operator's own AE session.
- Bridge installers often hard-code a list of AE versions; on a newer AE the engine is "not found". Make the host
  script check the running `app.version` first, then fall back to the known list.
- `aerender` can hang with no output and no frames on a hidden first-run, licence or modal prompt. Test with a
  one-frame render and a timeout; if it hangs, do one attended run to clear the prompt, and use GUI JSX or the render
  queue through the bridge meanwhile.
- Output-module template names are localised (a non-English AE uses translated names); read the available template
  names instead of assuming English ones.
- Alpha deliveries: ProRes 4444 or PNG/TIFF sequences with alpha; check `pix_fmt` with `ffprobe` after render.

## Acceptance checklist

1. Health check or GUI evidence recorded before any edit; a saved version exists from before the change.
2. Rendered file matches comp size, fps, duration and alpha requirement (`ffprobe`).
3. Representative frames inspected (first, last, each transition), no missing fonts or footage.
4. Receipt present; the render imports cleanly into the NLE.

## Boundaries

After Effects work only. New headless motion pieces are `motion-graphics`; editorial timelines and delivery are
`resolve-production`; generated footage is `neural-video`.
