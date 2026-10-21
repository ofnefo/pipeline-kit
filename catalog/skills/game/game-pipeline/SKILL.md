---
name: game-pipeline
description: Use when asked for "new game", "game prototype", "Godot/Unreal/Babylon project", "game assets", "accept asset package", "check the game", "build/export the game", "gameplay capture", "игра", "прототип игры", "ассеты для игры", "сборка игры". Routes game work: picks the engine (Godot, Babylon.js, Unreal), sets up a project from a template, orders and accepts asset packages with a manifest, runs headless and visual checks, and exports builds and captures. Not for producing the art, music or video itself (owning pipeline) or for game-design rules (project canon).
---

# Game pipeline

Purpose: one route for game projects from brief to a verified build, with assets coming in as validated packages from
the art, audio and video pipelines. Companion skills: `godot-development`, `game-ui-ux`, `game-art-production`,
`playtest-qa`.

## Inputs

- The project's own rules first: `<PROJECT_ROOT>/AGENTS.md` (or README), the project metadata file (id, engine, engine
  version, status) and the docs it routes to (current slice, systems, canon, playtest). Never pick the active game from
  a random open file.
- The brief: platform(s), session length, core mechanic, target audience, deadline.

## Layout

- The pipeline root holds only tools, templates, config, docs and runtime. Game projects live under a separate projects
  root (`<PROJECT_ROOT>` = one game): `game/` (engine project), `design/`, `art/`, `audio/`, `qa/`, `releases/`,
  `asset-intake/`, `exchange/`.
- Shared config, tools and templates: one writer at a time.

## 1. Engine choice

| Need | Engine | Notes |
|---|---|---|
| Small 2D/3D desktop or mobile game | **Godot 4** | template project, typed GDScript, headless import and smoke scene |
| Browser, shareable by link | **Babylon.js** (WebGL2, Vite + TypeScript) | `tsc --noEmit` as the static check; commit the lock file |
| High-fidelity 3D | **Unreal Engine 5** | heaviest: one editor at a time, take the GPU lock (one heavy GPU job at a time) |

An installed path or a config entry is not proof that an engine works: run a smoke check before calling it ready.
Record the exact engine version per project; a project may pin an older version than the pipeline default.

Install engines from official downloads and verify them against the published checksums (Godot publishes SHA-512
SUMS for editors and export templates); keep an install receipt.

## 2. Stages

brief -> mechanic proof -> playable slice -> integration -> playtest -> candidate -> delivery.

Each stage ends with evidence: a playable build or capture for mechanic proof and slice, a QA report for playtest,
version + SHA-256 + run instructions + known issues for a candidate.

## 3. New project

Copy the engine template into `<PROJECT_ROOT>/game`, write the project metadata, README and AGENTS, create the folders
above. Project ids: uppercase, `[A-Z][A-Z0-9-]{1,39}`. Never overwrite an existing project. Babylon: install
dependencies inside `game/` and commit the lock file.

## 4. Assets from other pipelines

Order by writing `<PROJECT_ROOT>/exchange/<JOB>/request.json`: brief, deliverables with exact technical specs, canon
references, output folder (`.../returned/v001`) and acceptance. Writing the request sends nothing; the job runs in the
owning pipeline, local models first.

- **Art:** sprites, textures, icons, concept, 3D. Local image models (e.g. Z-Image Turbo for t2i, Qwen-Image-Edit for
  edits, BiRefNet for cut-out to RGBA). 3D from Blender: GLB for Godot/Babylon, FBX for Unreal, metres; import a 1 m
  test cube first.
- **Audio:** music loops/stems (e.g. ACE-Step), WAV 48 kHz / 24-bit with loop points and BPM; SFX; voice with a TTS
  model whose licence allows release.
- **Video:** trailers and cutscenes from real gameplay captures; the master stays in the video project, the engine
  delivery and a poster frame come back.

Every returned folder needs a `manifest.json`:

| Field | Meaning |
|---|---|
| `id`, `project`, `version` | asset id, owning game, package version (`v001`...) |
| `producer` | pipeline/tool/model that made it |
| `license`, `commercial_use` | licence text or id; true/false |
| `files[]` | `path`, `sha256`, `role` = `runtime` \| `source` \| `preview` \| `license` |

Validate it against a JSON Schema, check every hash, and with a commercial flag refuse packages whose
`commercial_use` is false. Accept into an immutable `<PROJECT_ROOT>/asset-intake/<ASSET>/v001`. Import only `runtime`
files into the engine, then check the real frame or sound in-game. Record licence facts; do not block work on them.

## 5. Checks

- Per engine: Godot headless import plus a smoke scene; Babylon `tsc --noEmit` plus a browser run; Unreal needs a
  live editor probe (e.g. Remote Control API on localhost) or a packaged build run.
- **Headless success is not visual proof.** Capture and inspect a real frame or a short gameplay capture for any visual
  change.
- **Godot can exit 0 with script errors:** scan the full log for `ERROR:` (and `SCRIPT ERROR`, `Parse Error`) and fail
  the check on any hit that is not on a known-harmless list.
- Keep a finite verification suite (template checks, project checks, asset manifests) writing a JSON report.

## 6. Build and export

- **Babylon:** `npm run build` inside `game/` -> `game/dist`.
- **Godot:** `godot --headless --path <PROJECT_ROOT>/game --export-release "<preset>" <absolute output path>`. Needs
  `export_presets.cfg` and the export templates of the exact engine version. Test that the exported executable runs.
- **Godot 4.7 headless export gotcha:** any key under `[preset.N.options]` in `export_presets.cfg` made the headless
  editor quit right after theme generation and then hang with no export. Keep `[preset.N.options]` empty (defaults
  apply; one harmless `ERROR: Cannot get keys from nonexistent section` line appears), or set the options in the GUI
  editor and re-test headless.
- **Unreal:** package from the editor or UAT under the GPU lock; register long processes with an owner and a finite
  timeout.
- Builds go to `<PROJECT_ROOT>/releases/<version>/`, captures and screenshots to `qa/<date>/`. Record version, SHA-256,
  run instructions and known issues. A delivery copy excludes sources and dev files (`.gd`, `.tscn`, `.uasset`, `.ts`,
  `.map`, `.blend`, `.psd`, `project.godot`, `package.json`, `tests/`, `node_modules/`, `.godot/`, `Saved/`,
  `asset-intake/`, `exchange/`).

## 7. Engine MCP servers (optional)

- Godot: the community `@coding-solo/godot-mcp` (MIT) exposes run/stop project, debug output, scene and node edits,
  UID updates. Pin its version and set `GODOT_PATH` to the exact editor binary. `run_project` / `launch_editor` open
  windows: always stop what you started. Scene edits change project files: review the diff.
- Keep pipeline MCP tools read-only and bounded (status, project info, run a named check); they never start editors.

## 8. Modding existing games

For modding, reverse-engineering and mash-ups of existing games, use Universal Modder
(https://github.com/rehan-remade/universal-modder, MIT): install it yourself pinned to a commit and follow its own
skills and docs. Make mod assets locally first; publishing a mod or contributing notes upstream needs the operator's yes.

## Acceptance checklist

1. Engine choice and exact version recorded; engine smoke check passed (not just a path).
2. Every imported asset came through a validated manifest with hashes and licence facts.
3. Headless checks pass **and** a real frame or capture was inspected; logs scanned for `ERROR:`.
4. Build exported, launched once, and recorded with version, SHA-256, run instructions and known issues.
5. Processes you started (editors, game windows, dev servers) are stopped.

## Boundaries

Routing, project setup, asset intake, checks and builds. Producing art, music or video happens in their own
pipelines; game-design rules live in the project's canon; Godot code work is `godot-development`.
