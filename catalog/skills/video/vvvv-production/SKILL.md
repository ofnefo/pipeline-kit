---
name: vvvv-production
description: Use when the request names vvvv or an existing .vl/.v4p project ("вввв", "патч vvvv", "VJ-луп", "аудиореактив в vvvv", "интерактивная инсталляция"). Builds, revises and diagnoses vvvv gamma VL patches for realtime visuals, audio-reactive motion, VJ loops and installations, and exports deterministic masters or standalone apps via the vvvvc CLI. Not for legacy beta .v4p migration without a request, TouchDesigner work (touchdesigner-production) or editing timelines.
---

# vvvv production

Purpose: a vvvv patch as a production source (for a live show, an installation or an offline master), never as a
replacement for the project's edit timeline. Work in `<PROJECT_ROOT>/60-motion/vvvv/`.

## Inputs

- Dimensions, FPS, duration or live mode, audio source/BPM, input controller, output (file, local texture sharing,
  projector/window). Use project defaults when known; ask only for a choice that changes the result.
- The existing project, if any, and which vvvv it was made with.

## Establish the executor

- Identify gamma vs beta from the actual project and runtime. Do not translate beta nodes, packs or `.v4p` examples
  into gamma `.vl` by renaming files. Keep the engine of an existing project unless migration was requested.
- Record the executable and actual version, package versions, render backend and output target. A version-named folder
  is not proof of an installed executable (old folders may hold only caches and logs).
- vvvv gamma ships `vvvvc.exe`, a CLI compiler/exporter: `vvvvc <file.vl> --output-directory <dir>` builds a standalone
  executable (via `dotnet publish`). Smoke-test it on a help example (e.g. a VL.Skia example) before relying on it.
- Start from the installed Help Browser's matching example (`<install>/packs/<pack>/help/`) and the Gray Book
  (https://thegraybook.vvvv.org/). Verify exact node and pin names against the installed pack. Prefer the existing
  graphics library (VL.Stride for 3D, VL.Skia for 2D); do not add packs only because a tutorial uses them.
- Use an existing supported application interface when available; otherwise the interactive desktop. Do not fabricate
  `.vl` serialization or undocumented headless flags. If only a graph plan can be produced, label it a plan until the
  application opens and evaluates it.

## Build the smallest useful patch

- Separate input -> normalised controls -> scene -> output. Name meaningful controls (speed, intensity, palette, seed),
  expose a small control surface and keep technical settings in a secondary group. Keep media paths project-relative
  and pin package versions in the handoff.
- Audio-reactive: use an approved audio copy, check channel routing, normalise/clamp the envelope, smooth it, expose
  gain. Test silence and a loud passage: silence must not explode a division or stall the scene.
- Loops: drive phase by the intended duration/BPM; check the last-to-first transition. Feedback needs an intentional
  delay, a reset and bounded gain.
- Deterministic export uses timeline/frame time, not wall-clock time. A live preview running below target FPS is not a
  valid offline master. Build a short representative segment before the full export.
- Take the GPU lock (one heavy GPU job at a time) for renders; never start a competing render during another job.

## Acceptance checklist

1. The saved native patch opens in its recorded runtime with no missing nodes or assets.
2. Rendered output inspected: duration, dimensions, FPS, loop seam, alpha/colour contract and audio sync as applicable.
3. Live work: sustained frame time measured at target output size after warm-up; input disconnect/reconnect tested
   only when that input is part of the job.
4. Status recorded separately as `prepared`, `opened`, `exported`; a screenshot or a code-only check does not verify all
   three.

## Handoff

The native patch with dependencies, approved assets, a preview and a short recipe: runtime and packages,
start/stop/reset, exposed controls, output route and the measured result. Approved media go to the NLE/FFmpeg stage.

## Sources and licensing

- https://vvvv.org/ and the Gray Book for current gamma guidance and examples.
- Licensing: https://store.vvvv.org/ ; check the edition and terms for the actual (commercial) use. Free evaluation is
  not an open-source licence.
- Do not replace the operator's chosen vvvv workflow just because an alternative exists.

## Boundaries

vvvv patches only. TouchDesigner is `touchdesigner-production`; graphic layers are `motion-graphics`; cutting is
editing work.
