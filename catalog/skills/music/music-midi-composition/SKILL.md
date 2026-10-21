---
name: music-midi-composition
description: Use when composing, extracting, transforming or validating editable MIDI ("напиши басовую партию", "MIDI барабанов", "переведи в MIDI", "гармония"): drums, bass, harmony, melody, groove, humanisation, audio-to-MIDI cleanup, arrangement markers, DAW Piano Roll preparation. Works in separate role tracks with groove first and deterministic files (Mido). Not for audio processing (audio-production) or live DAW control (flstudio-production).
---

# MIDI Composition

Use Mido (or another deterministic MIDI library) for files and Basic Pitch for audio transcription.

## Compose in roles

1. Lock the tempo interpretation: straight, half-time, double-time, swing or mixed.
2. Create separate tracks for drums, bass, harmony, lead/counterline and markers.
3. Establish the groove with kick/bass interaction before decorative percussion.
4. Limit the harmonic palette and make voice-leading audible. A bass may state the harmony; guitars or keys can
   answer rather than double it.
5. Write melody as contour, register, rhythm and target tones. Generate variants by changing one dimension at a time.
6. Humanise intentionally: timing bias, velocity ranges, note length and rare deviations. Never apply global
   randomisation blindly.
7. Export Standard MIDI with tempo, time signature, track names, channel/program intent and section markers.

## Audio to MIDI

HTDemucs 6-stem -> Basic Pitch per melodic stem -> onset-based GM drums -> quantise with configurable strength ->
assemble with Mido.

Do not transcribe a full dense mix and call the result production-ready. Keep both raw and cleaned MIDI; log
thresholds per stem. Do not extract or reconstruct copyrighted reference melodies for reuse.

## Genre lenses

- **Post-punk:** melodic bass, narrow guitar cells, motor pulse, strategic empty beats.
- **Rap:** the vocal pocket comes first; drum microtiming and bass note length are structural.
- **Techno:** controlled evolution; automation targets and timbral rhythm matter as much as notes.
- **Hybrid:** define which layer owns the downbeat and which layer creates instability.

## Acceptance

- [ ] Tempo, meter, track names and markers present; file opens in the target DAW.
- [ ] One role per track; groove checked with kick + bass alone.
- [ ] Raw and cleaned MIDI kept for transcriptions, with thresholds logged.
