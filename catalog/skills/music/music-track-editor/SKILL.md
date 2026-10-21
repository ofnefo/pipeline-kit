---
name: music-track-editor
description: Use when reviewing a track, choosing between variants, diagnosing why a song feels generic, preparing a final mix/master or deciding release readiness ("послушай трек", "какой вариант лучше", "готово к релизу?"). Runs eight audit passes (identity, structure, lyrics, performance, arrangement, mix, master, product) and labels each candidate advance / salvage / archive / reject. Not for writing new material (music-songwriting) or technical loudness processing (audio-production).
---

# Track Editor

Read the active project, its artifacts and rejection log. Judge at matched loudness. The task is not to reward
effort; it is to protect the song.

## Audit passes

1. **Identity** - can the conflict, hook and sonic thesis be stated without artist-name references?
2. **Structure** - does each section change pressure, evidence or consequence?
3. **Lyrics** - remove generic abstraction, accidental comedy, forced rhyme and paper-only syntax.
4. **Performance** - choose takes by belief and timing before cleanliness.
5. **Arrangement** - mute-test every layer; name the owner of pulse, harmony, hook and rupture.
6. **Mix** - vocal/bass/kick hierarchy; check mono, low volume, phone, headphones, harshness and tails.
7. **Master** - headroom/source quality, true peak, dynamics and a level-matched reference, not a target number
   alone.
8. **Product** - title, metadata, cover, credits, rights (samples, voices, remix sources), source hashes, stems, MIDI,
   lyrics and reproducibility.

## Decision labels

One label per candidate: `advance`, `salvage element`, `archive` or `reject`. State why in one sentence and name the
next test that could change the decision.

Reject polish that makes the track interchangeable. Keep damage only when it carries meaning or structure.

## Output

A short review file in the project (`review-vNNN.md`): candidates compared (paths + hashes), pass-by-pass notes,
labels, the next test, and what blocks release.
