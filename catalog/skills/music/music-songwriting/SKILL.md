---
name: music-songwriting
description: Use when writing or editing song lyrics, rap verses, hooks or hybrid song structures, especially in Russian ("напиши текст песни", "куплет", "припев", "рэп-куплет", "поправь текст"). Builds from one conflict and an evidence bank, designs prosody and rhyme against a pocket, runs a three-pass editor and a heuristic lyric preflight. Not for voice-over scripts (voiceover-dubbing) or for copying existing lyrics.
---

# Songwriting

Personal emotional context may feed the song, but private facts are transformed, never quoted or exposed.

## Inputs

- The brief: theme or situation, mode (song / rap / spoken), BPM and feel if known, the artist's style brief.
- Optional source draft (preserve it; write new versions into `10-lyrics/`).

## Write from evidence

1. Reduce the song to one conflict that contains desire and resistance.
2. Build an evidence bank before lines: objects, gestures, changed routines, withheld phrases, bodily reactions,
   locations and time pressure.
3. Choose POV, tense, addressee distance and the exact event of each section.
4. Draft the hook in plain speech. Make its rhythm and vowel shape memorable before adding imagery.
5. Give verses new evidence; do not paraphrase the hook.
6. For rap, design stresses and internal rhyme against a stated pocket. Density must rise or fall for dramatic
   reasons.
7. Read aloud over a metronome. Mark forced stress, filler, tongue collisions and lines that only work on paper.

Choose the speaker's stance from the actual request: intimacy, active observation, dry satire, anger, tenderness or a
transition. Do not force passive sadness or an impossible metaphor into every song; humour is allowed.

## Line filter

- One concrete claim or image per line; earn abstraction through physical detail.
- Preserve rough or colloquial syntax when it carries the voice.
- Use the project's signature imagery sparingly and only when it is emotionally causal.
- Reject generic scale: eternity, universe, destiny, stars, wings, endless empty rooms.
- Do not name a private person unless requested.
- Do not reproduce copyrighted lyrics or mimic a living artist exactly. From a reference take one semantic mechanism
  and one technical mechanism (structure, cadence class, density, emotional mechanics), never a blended imitation.

## Russian craft notes

- Stress is lexical and mobile: mark ambiguous stresses (`замо́к` / `за́мок`) for the performer and the model.
- Rhyme by sound from the stressed vowel onward, not by spelling; voiced/unvoiced final consonants rhyme.
- Watch consonant clusters at word boundaries (`вств`, `здн`) at high tempo.
- Syllabo-tonic meter is a tool; spoken stress and performance outrank a scansion label.

## Three-pass editor

1. **Meaning** - every line changes the scene or pressure.
2. **Mouth** - stress, consonants, vowels, breath and tempo.
3. **Memory** - hook, title, one irreversible image.

## Technical preflight

For a substantial draft run the bundled stdlib script with the real mode, BPM and estimated bars per line:

```bash
python scripts/lyric_preflight.py 10-lyrics/song-v003.txt --mode rap --bpm 92 --line-bars 1 \
  --jargon "@style-jargon.txt" --json 10-lyrics/song-v003.preflight.json --markdown 10-lyrics/song-v003.preflight.md
```

- `--timing-json` gives per-section mode/BPM/beats_per_bar/line_bars; section labels come from `[Куплет]`,
  parenthetical labels or Markdown headings, repeated labels become `Припев #2` etc. Check the line map before
  assigning timing.
- `--jargon` takes the project's overused signature words (comma list or `@file`).
- Flags: long lines, syllables per second (rap above ~7.2, song above ~5.2), articulation collisions, section
  variance, cliches, repeated end words, filler/abstract words, jargon, orthographic rhyme tails.
- Reports are never overwritten; use new paths per revision. These are heuristics: they never replace stress
  marking, a metronome take or artistic judgment, and must not homogenise intentional irregularity.

## Sessions

For sustained work create a new `10-lyrics/session-NNN/` with a writing spec that separates evidence origins
(user-provided, transformed, fictional) and preserves the author's chosen phrases, plus a short workflow note for the
next session. A one-line edit needs no new session.

## Acceptance

- [ ] One conflict and an evidence bank exist before the final draft.
- [ ] Three editor passes done; preflight flags reviewed (accepted or fixed with a reason).
- [ ] Read aloud over a metronome at the target BPM.
- [ ] No private facts exposed; no copied lyrics; no exact imitation of a living artist.
