---
name: music-track-director
description: Use when starting, planning, resuming or auditing a whole song project, or deciding which specialist workflow runs next ("веди трек", "что дальше по песне", "статус трека"). Orchestrates a track from brief through lyrics, MIDI, neural renders, DAW production, vocals, mix, master and release artifacts with stage gates and a project card. Not for doing one specialist step itself (use that step's skill).
---

# Track Director

## Project layout

One project folder per track with numbered stages:
`00-brief -> 10-lyrics -> 20-midi -> 30-sound -> 40-vocals -> 50-arrangement -> 60-mix -> 70-master -> 80-release`,
a project card (`PROJECT.md` + `project.json`: stage, decisions, artifacts, risks, next action) and a `renders.jsonl`
ledger for every AI render (model, prompt, seed, source hashes, output path).

## Direct the work

1. Locate or create one active project card. Do not scatter outputs outside it.
2. State the current stage, the decision blocking progress and the smallest useful deliverable.
3. Route specialist work: `music-songwriting`, `music-midi-composition`, `music-neural-audio-lab`,
   `flstudio-production`, `music-vocal-production`, `audio-production`, `music-track-editor`.
4. Require each stage gate before promoting the project (e.g. lyric preflight reviewed before vocals; routing and tails
   checked before stems; master QA `pass` and a full listen before release).
5. Record variants and rejection reasons. Preserve source material and dry recordings; never overwrite a source
   recording, project file, MIDI, lyric draft or master.

## Decision hierarchy

When layers conflict, prefer: emotional truth -> hook/song -> performance -> arrangement -> sound design -> polish ->
loudness.

Do not solve a weak song by adding tools. Do not imitate a living artist's exact style; translate references into
musical attributes. Do not send private context, recordings or unpublished lyrics to external services without
explicit permission.

## Deliverable

Update the project card with: current stage, decisions made, artifacts created, unresolved risks and one concrete
next action. A full-track request is incomplete if the next specialist cannot tell what to do from the files alone.

## Release

Nothing is released automatically. Deliver only an exact approved final master that passed technical master QA,
only when the operator asks, once, through your delivery channel with a receipt. Never deliver drafts, stems,
previews or unpublished private material. "Queued" is not "sent".

## Acceptance

- [ ] One project card, current and actionable.
- [ ] Stage gates met before promotion; variants and rejections logged.
- [ ] Sources preserved; renders in the ledger.
