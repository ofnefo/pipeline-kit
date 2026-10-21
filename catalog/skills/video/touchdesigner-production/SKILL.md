---
name: touchdesigner-production
description: Use when the request names TouchDesigner or an existing .toe/.tox ("тачдизайнер", "TD", "аудиореактив", "VJ-луп", "шейдер в TouchDesigner"). Builds, edits and diagnoses TouchDesigner projects and components for audio-reactive graphics, VJ loops, procedural visuals and interactive video, using in-app Python for bounded graph operations and verifying exports. Not for vvvv (vvvv-production), After Effects compositions or editing timelines.
---

# TouchDesigner production

Purpose: native `.toe` projects and versioned `.tox` components under `<PROJECT_ROOT>/60-motion/touchdesigner/`, with
imported footage and approved masters left unchanged.

## Inputs

- Dimensions, FPS, live vs deterministic export, loop length/BPM, audio/controller input, destination (file, Spout/NDI,
  projector).
- The existing project or component, if any.

## Establish access and runtime

- Identify the installed executable, build, licence tier and Python version from the actual application before
  building. Do not present the skill as an installed application or MCP bridge.
- `op`, operator classes and `td` execute **inside** TouchDesigner; a system Python script cannot create a real `.toe`
  by importing them. Use an in-app Text DAT/script for a bounded graph operation, or desktop automation if there is no
  supported application route. Do not open a new network control server just to run a script.
- Save a new project version before altering an existing network.
- Check build-specific operator and parameter names in the official Python guide
  (https://derivative.ca/UserGuide/Python) and the operator help. Do not guess names, binary `.toe`/`.tox`
  serialization or unattended launch switches.
- Keep TouchDesigner's bundled Python packages intact; its Python ABI need not match system Python or ComfyUI.

## Construct the graph

- Separate source, controls, visual processing and output inside a named COMP; do not delete or rebuild unrelated nodes.
- Families: TOP for images/textures, CHOP for signals and audio/control channels, SOP for geometry, DAT for
  text/tables/scripts, COMP for composition and controls. Choose the smallest relevant family rather than routing
  everything through Python.
- Audio-reactive: approved audio -> envelope or selected spectrum bands -> normalise/clamp/smooth -> exposed controls.
  Test silence, peaks and stereo routing. Never route a live microphone to speakers by default.
- Loops: time/phase -> scene/shader -> output, with deterministic frame progression for recording. Keep seed, duration
  and reset explicit. Feedback needs a delay/reset and bounded gain.
- GLSL TOPs (CRT, dither, halftone, pixel sort) can usually be ported to three.js or other WebGL hosts.
- Expose readable controls (intensity, speed, palette, audio gain) for handoff, not the whole internal graph. Keep
  operator paths scoped to the owned component and media paths project-relative.

## Licence limits

Output operators, Spout/NDI, alpha, codecs and resolution are capabilities to verify in the actual edition. The
Non-Commercial licence caps output at 1280x1280: record the licence limit in the project and never label an upscaled
preview a native 4K render. Terms: https://derivative.ca/UserGuide/Licensing.

## Acceptance checklist

1. Check GPU/resource use and take the GPU lock (one heavy GPU job at a time) before starting the app for a render.
2. A short representative export: the saved project reopens, no missing assets or operator errors; actual dimensions,
   FPS, duration, audio sync and first/last frame behaviour verified on the file.
3. Live mode: frame time measured after warm-up at target resolution; only the required controller/output connection
   tested. Disable viewers or cooking only when profiling points to them.
4. Status recorded as prepared, opened in TouchDesigner, or actually exported. A Python syntax check is not runtime proof.

## Handoff

A versioned `.toe`, reusable `.tox` when needed, dependency and build notes, a preview or master and start/stop/reset
instructions. Approved media go to the NLE/FFmpeg stage.

## References

- Getting started: https://docs.derivative.ca/Getting_Started_With_TouchDesigner
- Python: https://derivative.ca/UserGuide/Python ; licensing: https://derivative.ca/UserGuide/Licensing
- TouchDesigner stays the executor when the operator selected it; alternatives are not a reason to switch.

## Boundaries

TouchDesigner work only. vvvv is `vvvv-production`; AE compositions are `after-effects-production`; cutting is editing
work.
