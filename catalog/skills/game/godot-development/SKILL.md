---
name: godot-development
description: Use when building or changing a Godot 4 game: scenes, typed GDScript, signals, Resources, input, save data, UI wiring, debugging or smoke tests ("Godot", "GDScript", "сцена", "сигнал", "баг в игре"). Inspects the project, implements the smallest complete change, runs headless and in-window checks and fixes what they show. Not for engine choice, asset intake or builds (game-pipeline) or art production (game-art-production).
---

# Godot development

Purpose: change a Godot 4 project so that it still imports, runs and plays, with the change visible in a real window.

## Inputs

- `<PROJECT_ROOT>/game` (the engine project), the project's own rules/README and the exact Godot version it pins.
- The requested behaviour, plus the current slice or system doc it belongs to.

## Workflow

1. **Inspect:** read `project.godot`, the main scene, autoloads, Input Map and the scripts the change touches. Note the
   engine version and existing conventions before writing code.
2. **Plan:** the smallest complete change; list the scenes/scripts it touches and how you will test it.
3. **Implement** following the conventions below.
4. **Test headless:** import and run the smoke scene / tests with `--headless`; scan the full log.
5. **Run in a window:** play the affected path; capture a frame or short clip for any visual change.
6. **Fix** what the checks showed, then repeat only the invalidated checks.
7. **Document** the change in the project's notes (what, where, how it was tested).

## Conventions

- Typed GDScript (`var speed: float`, typed function signatures and return types).
- Composition over inheritance; communicate with signals; data in `Resource` files.
- Keep persistent state (save data), encounter/level state and presentation state (animations, UI) separate.
- UI is never authoritative: it displays and requests; game state decides.
- Input through Input Map actions, never hard-coded keys.
- Save identifiers and plain data, never `Node` references.
- No god objects or giant autoloads; one clear owner per system.
- Build one complete instance (one enemy, one room, one item) before generalising.
- Every new scene gets a smoke path (a test or a debug scene that instantiates and exercises it).

## Gotchas

- **Godot can exit 0 with script errors.** Scan the log for `ERROR:`, `SCRIPT ERROR` and `Parse Error`; a clean exit
  code alone is not a pass.
- **Headless success is not visual proof.** Layout, animation, shaders and feel need a real window.
- Pin the editor binary to the project's exact version; opening a project in a newer editor can rewrite resources.
- Scene files (`.tscn`) are text: review diffs of scene edits made by tools or MCP servers before keeping them.
- Stop any game or editor window you started.

## Acceptance checklist

1. Headless import and smoke tests pass, and the log scan finds no new `ERROR:` lines.
2. The changed path was played in a window; a frame or clip was inspected for visual changes.
3. Conventions above respected (typed code, Input Map, no Node refs in saves, UI not authoritative).
4. A smoke path exists for every new scene; notes updated.

## Boundaries

Godot code and scenes only. Engine choice, asset packages and exports are `game-pipeline`; UI design rules are
`game-ui-ux`; art is `game-art-production`; structured playtesting is `playtest-qa`.
