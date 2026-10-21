---
name: playtest-qa
description: Use when a game build must be tested, played, or checked before a candidate ("плейтест", "протестируй игру", "проверь сборку", "баги", "playtest"). Runs build -> automated tests -> launch -> play -> observe -> reproduce -> fix -> replay, covering happy path, invalid actions, boundaries, pause, restart and persistence, and writes a dated QA report with repro paths. Not for writing game code (godot-development) or UI design (game-ui-ux).
---

# Playtest QA

Purpose: find what breaks or confuses players, with reproducible evidence, before a build becomes a candidate.

## Inputs

- The build (commit or version) and what changed since the last playtest.
- The mechanic or slice under test and its intended player experience.

## Workflow

build -> automated tests -> launch -> play -> observe -> reproduce -> fix -> replay.

Headless and automated tests cover rules and logic; a real window covers feel, readability and pacing. Both are needed.

## Minimum coverage

- Happy path through the slice.
- An invalid action, with the reason shown to the player.
- Boundaries (zero/maximum resources, edges of the map, last enemy, empty inventory).
- Pause and resume.
- Restart and reload.
- Persistence: save, quit, load, and compare state.
- No new `ERROR:` lines in the log.

## What to look for

Soft locks, impossible states, unclear feedback, broken action dependencies, pacing stalls, unreadable enemy intents,
overlap and clipping, player confusion, save/load drift.

## Report

Write a dated report in `<PROJECT_ROOT>/qa/<date>/` with, per finding:

- repro path (exact steps from launch);
- expected vs observed;
- build version or commit;
- severity and result after the fix (replayed: pass/fail);
- capture (frame or clip) attached.

A screenshot alone is not evidence: it needs the repro path and the build it came from.

## Acceptance checklist

1. Automated tests and a log scan for `ERROR:` ran on the exact build.
2. Every minimum-coverage item was played in a real window.
3. Each finding has a repro path, expected vs observed, build id and capture.
4. Fixed findings replayed on the new build and marked pass/fail.

## Boundaries

Testing and reporting. Fixes are `godot-development` (or the engine's own skill); UI redesign is `game-ui-ux`; release
packaging is `game-pipeline`.
