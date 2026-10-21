---
name: music-vocal-production
description: Use when producing sung or rap vocals ("запиши вокал", "почисти вокал", "тюнинг", "дабл", "эдлибы", "вокальная цепочка"): recording plan, comping, cleanup, de-essing, pitch/time, character effects, space, doubles, ad-libs, export and vocal A/B diagnosis in a DAW or audio editor. Not for spoken voice-over or TTS jobs (voiceover-dubbing).
---

# Vocal Production

Preserve the original dry takes and consent/ownership metadata for every voice.

- Synthetic voice in anything that may be released must come from a model licensed for commercial use (e.g.
  Qwen3-TTS) with an owned or licensed reference, or a designed voice; non-commercial models (e.g. XTTS-v2) are
  drafts only. Cloning a real person's voice requires that person's documented consent.
- For a reverberant or bled vocal, try neural de-reverb / karaoke separation first (see `audio-production`) and keep
  the untouched export.

## Order of work

1. **Recording:** room/noise check, stable distance, conservative gain, several complete takes plus targeted pickups.
2. **Edit:** comp for meaning and timing before processing. Remove only distracting clicks/breaths; do not erase the
   body.
3. **Cleanup:** clip gain, high-pass only if needed, resonance control, optional RNNoise / DeepFilterNet A/B.
4. **Control:** compression and de-essing in modest stages. Level-match every bypass comparison.
5. **Pitch/time:** repair the smallest audible problem. Preserve deliberate slides, consonant placement and rap
   pocket.
6. **Character:** saturation, distortion, doubles, formant or band-limiting on parallel buses where possible.
7. **Space:** automate delay/reverb by section and line function; keep an intelligibility bus separate.

## Editor and bridge boundary

If an audio editor or DAW bridge is untested, write an exact action list or work in its UI with user-visible
checkpoints. Never claim an edit happened without readback or an exported file.

## Deliverables

Dry comp, cleaned comp, tuned comp (if used), lead print, doubles, ad-libs, FX returns and a vocal reference mix.
Identical start time and sample rate for every stem.

## Acceptance

- [ ] Dry takes preserved; voice consent/ownership recorded.
- [ ] Every processing step A/B'd at matched level.
- [ ] Stems aligned (same start, same sample rate); reference mix exported.
