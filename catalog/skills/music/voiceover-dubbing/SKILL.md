---
name: voiceover-dubbing
description: Use when a job needs voice-over, narration, announcer reads, client TTS, dubbing or re-voicing a video, subtitle-timed VO ("озвучка", "закадр", "дубляж", "переозвучка", "диктор"). Script prep, local TTS batch synthesis (cloned or designed voice), cue-slot fitting, speech-to-text back-check, loudness master, mixing a new voice under the original music and effects, remux onto the picture. Not for singing or rap vocals (music-vocal-production), songs (music-songwriting) or plain transcription (audio-production).
---

# Voice-over and dubbing

Keep every source immutable; write versioned files (`-v001`, `-v002`) and a JSON sidecar next to each output
(engine, model revision, seed, reference hash, voice rights, script hash, QA). Typical stage folders:
`00-brief/` (brief, client sources under `incoming/`), `10-lyrics/` (script, stress dictionary), `40-vocals/` (TTS
renders), `60-mix/` (dub mixes), `70-master/`, `80-release/`.

## Engine and rights rules

- Anything that may be released (client work, videos, ads, events) uses a TTS model whose licence allows commercial
  use, e.g. **Qwen3-TTS** (Apache-2.0). XTTS-v2 is under the Coqui Public Model License (non-commercial): internal
  drafts and timing guides only, never in a client file.
- **Cloning a real person's voice requires that person's documented consent** (or a written licence from the rights
  holder). Record `voice_rights: owned | licensed | synthetic` in the sidecar. Cloning the original speaker of a
  client video counts as `licensed` only with that permission on file; otherwise use a designed (described) voice or
  another owned reference. Never clone public figures, colleagues or callers from recordings without consent.

## 1. Script

- Russian: numbers and abbreviations written out as words, `ё`, stress marks on ambiguous words, breath-sized
  phrases, a per-project stress dictionary (`stress-dictionary.json`). Other languages: same discipline.
- Script formats worth supporting in your TTS wrapper:
  - `.srt` - timed cues (dubbing, subtitle-timed VO);
  - `.json` - `{"segments":[{"id","text","start"?,"end"?,"pause_after"?}]}`;
  - `.txt` - one segment per line, optional `[mm:ss.s]` or `[mm:ss.s-mm:ss.s]` prefix, `#` comments.
- Untimed segments follow each other with a fixed gap (about 0.35 s).

## 2. Synthesis (GPU)

- Take the project's GPU lock; one heavy GPU job at a time; load the model once per batch.
- Clone mode: 3-10 s clean reference WAV plus its exact transcript. Design mode: a short voice description
  ("calm warm male announcer, close-mic, medium pace").
- Reproducibility: fixed seed, temperature, top-p stored in the sidecar.
- Keep per-segment WAVs as intermediates (never delivered) and render the timeline file from them.

### Fitting speech to cue slots

- **push** (default for VO): place each timed segment at its cue start; if the previous segment is still speaking,
  push later ones and report the drift.
- **stretch** (dubbing): slot = cue start to max(cue end, next cue start - 0.05 s guard). A segment longer than its
  slot is sped up with pitch preserved (rubberband, or FFmpeg `atempo`) up to **1.25x**; the remainder is
  overflow and gets pushed. Overflow after 1.25x means the line is too long: shorten the text, do not raise the rate.
- Keep the raw take beside the stretched one.

## 3. QA

1. Back-transcribe every segment with a local ASR (GigaAM-v3 for Russian, faster-whisper otherwise) and compute
   WER against the script. Flag `wer-high` (above ~0.15), `stt-failed`, `longer-than-slot`, `longer-than-cue`,
   `pushed-late`. Fix flagged lines (stress, spelled-out numbers, shorter phrasing) and re-render as the next version.
2. Transcribe the final file once more to produce client subtitles (json/srt/txt) as an independent check.
3. Loudness master (see `audio-production`, `master_audio.py`): speech -16 LUFS / -1.5 dBTP; video -16 / -1.0;
   broadcast -23 / -1.0. The report must say `pass`.
4. Listen to the master. A passing report is not an approval.

## 4. Dubbing a video

1. Extract the original audio: `ffmpeg -n -i clip.mp4 -vn -ac 2 -ar 48000 60-mix/clip-orig.wav`.
2. Transcribe with timings (video input works) into `clip.srt`.
3. Translate/edit into `10-lyrics/dub-v001.srt`, keeping cue numbers and timings. A local LLM may draft; a human or
   the agent edits.
4. Separate speech from music and effects (two-stem BS-RoFormer, see `audio-production`); the instrumental stem is
   the M&E bed.
5. Synthesize the dub against the cue grid in stretch mode; fix flagged and overflow lines first.
6. Mix the voice over the bed, ducking the bed under speech:

   ```bash
   ffmpeg -n -i 60-mix/clip-orig.stems/instrumental.wav -i 40-vocals/dub-v001.wav -filter_complex \
     "[0:a]aresample=48000[bed0];[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,asplit=2[vo][sc];[bed0][sc]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[bed];[bed][vo]amix=inputs=2:duration=first:normalize=0[mix]" \
     -map "[mix]" -c:a pcm_s24le 60-mix/dub-mix-v001.wav
   ```

   Then master with the `video` profile.
7. Put the audio back on the picture without re-encoding video:
   `ffmpeg -n -i clip.mp4 -i 70-master/dub-master-v001.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest 80-release/clip-dub-v001.mp4`.
   Picture edits (cuts, titles, burnt-in subtitles) belong to a video workflow.
8. QA: transcribe the final MP4, watch the whole clip, check sync at the first, middle and last cue.

## 5. Delivery

Stop at local files unless the operator asks to send approved files. Then deliver exact files from the release
folder through your delivery channel (dry run first), never raw/incoming files, stems or per-segment WAVs. Oversized
files get a compact copy (e.g. 720p MP4 `-vf scale=-2:720 -crf 26`, MP3 for audio). "Queued" is not "sent": confirm
the delivery status before reporting it as delivered.

## Report back

Version paths, QA status, mean WER and flagged segment ids, master LUFS/TP, voice rights, and the delivery receipt.
If something was only planned, say so.

## Acceptance

- [ ] Voice rights recorded; documented consent on file for any cloned real voice.
- [ ] Release files contain no non-commercial-model output.
- [ ] All segments pass WER/timing QA or are explicitly accepted by the operator.
- [ ] Master report `pass`; full listen done; video sync checked at three points.
