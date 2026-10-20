---
name: audio-finishing
description: Use when mastering local audio loudness/true peak or checking Russian lyric timing and pronunciation with the bundled CPU/text tools.
---

# Audio and text finishing

Resolve the project and establish delivery format, reference level and whether the work is music, speech or broadcast. Inspect `modules/music/scripts/master_audio.py --help`. Confirm operator-installed FFmpeg/ffprobe on PATH; preserve the input and select a fresh output path. This tool handles technical loudness and peaks, not creative mix decisions.

Render with the explicitly selected profile. Read the before/after JSON measurements, limiter and loudnorm mode, integrated loudness and true peak. Check those values against the delivery brief, then listen for clipping, pumping, excessive dynamics changes and cut-off starts/tails. Record actual output and receipt paths. Do not call a technically passing master creatively approved.

For Russian text, run `lyric_preflight.py <source> --mode <song|rap|spoken>` with known BPM/bar allocation where applicable. Use `ru_pronunciation.py --help` for pronunciation preparation. Treat syllable/rhyme/phonetic findings as evidence for an editor, not automatic approval. Preserve meaning and record uncertain names or stress marks for confirmation.

Acceptance: source preserved, output verified by listening and measurements, text changes checked in context, and all unresolved issues stated. No speech cloning, TTS model, music generator or paid service is bundled or started by these commands.
