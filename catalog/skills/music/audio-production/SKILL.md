---
name: audio-production
description: Use when audio must be analysed, repaired, transformed, separated, transcribed, normalised, looped, catalogued or quality-checked ("BPM и тональность", "раздели на стемы", "сведи громкость", "LUFS", "почисти вокал", "сделай мастер под стриминг"). Runs a measure, transform, re-measure loop with immutable sources, versioned outputs and JSON before/after reports. Not for live DAW editing (flstudio-production) or for writing music.
---

# Audio Production

DAW-independent audio work: FFmpeg for deterministic transforms, local models for stems/transcription/MIDI, and
measured QA for every derived file. Tool notes: [references/tooling.md](references/tooling.md).

## Inputs

- Source audio (never modified) and the project stage folder for outputs (e.g. `60-mix/`, `70-master/`).
- The question to answer or the deliverable: analysis, stems, loudness target, loop, transcript, cleaned vocal.

## Protocol

1. **Probe and hash.** `sha256` + `ffprobe`: codec, duration, sample rate, channels, bit depth.
2. **Measure only what answers the task** - tempo/onsets, key estimate, integrated LUFS, sample/true peak, silence,
   spectrum, loop seam, intelligibility:

   ```bash
   python scripts/analyze_audio.py SRC.wav --output SRC.analysis.json
   ```

   BPM, key, beat grid and cue points are hypotheses (halftime, modal, detuned and noisy material fool detectors).
   Report confidence and alternatives; never quantise expressive vocals or guitars just because a grid was found.
3. **Choose the smallest tool.**
   - FFmpeg: trim, fade, resample, channel ops, concat, silence detect, speed, mixing.
   - Stems: python-audio-separator with BS-RoFormer (vocals/instrumental), HTDemucs 6-stem, MelBand RoFormer
     de-reverb and karaoke (lead vs rest) models - see tooling.md.
   - Transcription with word timestamps: a local ASR (GigaAM-v3 for Russian, faster-whisper otherwise).
   - Audio-to-MIDI: Basic Pitch (separate stems first for dense mixes).
   - Technical master: `scripts/master_audio.py` (below).
4. **Render a new version** into the project stage; never overwrite the source. Record command, parameters, source
   sha256 and tool version beside the output (JSON sidecar or a `renders.jsonl` ledger).
5. **Re-measure the output.** Reject clipping, unexpected duration/channel changes, phase problems, audible seams,
   cut tails or loudness drift.

## Loudness master (technical)

```bash
python scripts/master_audio.py MIX.wav --output 70-master/song-master-v001.wav --profile streaming --ledger renders.jsonl
```

| Profile | LUFS | True peak | LRA |
|---|---|---|---|
| streaming | -14 | -1.0 dBTP | 11 |
| apple | -16 | -1.0 | 11 |
| video | -16 | -1.0 | 11 |
| speech | -16 | -1.5 | 9 |
| broadcast (EBU R128) | -23 | -1.0 | 15 |
| club | -9 | -0.3 | 8 |

Two-pass loudnorm in linear mode; when the gain would push peaks over the ceiling, a drive + look-ahead limiter goes
before loudnorm, and a final 4x-oversampled true-peak limiter ends the chain. 16-bit output gets TPDF dither. The
sidecar JSON reports before/after LUFS/TP/LRA and checks (±0.5 LU, TP under ceiling, linear mode, duration kept);
exit 2 means "check". This is not creative mastering (no EQ, multiband or reference matching). Optimise for the real
delivery context instead of one universal LUFS number.

## Stems, loops, libraries

- Keep an untouched separation export; label bleed and artifact risk per stem.
- Loops: inspect the waveform discontinuity *and* listen to a repeated render.
- Draft continuous mixes (album/DJ preview): order by key/BPM, match loudness, beat-snapped crossfades, write a JSON
  timeline. A release mix is still done by ear.
- Sound libraries: catalogue with hashes; filename roles/BPM/key are hypotheses; licence files found in a pack are
  candidates, not clearance. Hash verification does not replace decoding and listening.

## Resources and rights

- Separation, TTS and other neural models are heavy GPU jobs: take the project's GPU lock (one heavy GPU job at a time)
  and unload models afterwards.
- Local-first; a cloud or paid audio API only when the operator asked for it for this job.
- Voice synthesis or cloning of a real person needs that person's documented consent (see `voiceover-dubbing`).

## Delivery

Nothing here publishes by itself. Deliver exact approved files through your delivery channel only when the operator
asks, dry run first, with a receipt (path + sha256). Never ship raw/incoming folders, intermediate segment files or
unapproved previews.

## Acceptance

- [ ] Source hash and probe recorded; source untouched.
- [ ] Every output is a new version with a provenance record.
- [ ] Output re-measured; duration, channels and sample rate as intended; no clipping; true peak under the ceiling.
- [ ] Musical estimates reported as hypotheses with alternatives.
- [ ] Final listen on the delivered file (start, joins, end/tail).
