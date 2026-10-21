---
name: video-transcription
description: Use when a video needs transcripts, subtitles or word timings for dialogue indexing, captions, selects or text-based edits ("транскрипт", "субтитры", "расшифровка видео", "тайминги слов", "SRT"). Extracts duration-preserving 16 kHz mono audio, runs local speech-to-text, and writes TXT/SRT/VTT/JSON with word timestamps plus cleaned caption derivatives. Not for meeting minutes and speaker protocols, lyrics alignment as music work, or voice synthesis.
---

# Video transcription

Purpose: text and word timings that map exactly to the original video timeline, for captions, selects and
text-based editing.

## Inputs

- The source clip(s) or a URL, the spoken language(s), and the deliverable (verbatim index, public captions, selects).
- The project folder; outputs go to `30-transcript/`.

## Workflow

1. **Extract audio without changing duration** (no silence removal, no speed change; timestamps must map to the
   original):
   `ffmpeg -i clip.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le 30-transcript/clip-16k-mono.wav`
   Check that the WAV duration equals the video duration (`ffprobe -show_entries format=duration`).
2. **URL sources:** fetch the platform's own subtitles first (e.g. `yt-dlp --write-subs --write-auto-subs
   --sub-langs <lang> --skip-download <url>`); fall back to STT only when none exist or they are poor. Use cookies
   only from a file the operator supplied; never extract them from a browser profile.
3. **Speech-to-text, local first.** One shared STT backend for every pipeline on the machine; do not install a second
   audio runtime per project. Typical choices:
   - faster-whisper (`large-v3` / `large-v3-turbo`) for most languages, with `word_timestamps=True` and VAD on;
   - a language-specialised model where it is clearly better (e.g. GigaAM for Russian) for clips within its length
     limit, falling back to Whisper beyond it;
   - Whisper explicitly for lyrics or mixed-language material.
   CPU inference is usually fast enough for editing work; if it runs on the GPU, take the GPU lock (one heavy GPU job
   at a time).
4. **Write outputs** into `30-transcript/`: `<clip>.txt`, `<clip>.srt` (and `.vtt` if needed), `<clip>.transcript.json`
   with segments and word objects `{start, end, text}` in seconds. Record a receipt: source sha256, language, backend,
   model and version, and uncertainty notes (overlaps, inaudible spans, names you could not verify).
5. **Derivatives.** For text-based editing keep fillers, false starts and pauses (they drive cut decisions). For public
   captions make a separate cleaned file; never overwrite the verbatim transcript.
6. **Batch:** many files -> one job writing all formats per file into the output folder, with one receipt per file.

## Caption rules (public derivative)

- At most 2 lines, ~42 characters per line for 16:9 (shorter for 9:16), 1-7 s per cue, no cue under ~0.8 s.
- Break lines at phrase boundaries, not inside names or number-unit pairs.
- Reading speed about 15-17 characters per second; merge or split cues to stay under it.
- Proper names, brands and numbers checked against the brief or the client's spelling list.

## Voice handoff

Voice-over or voice cloning is a separate request to the audio/music pipeline: it needs the speaker's consent for any
cloned voice and a model whose licence allows the intended release (some popular TTS models are non-commercial:
drafts only). The video side only syncs and mixes the returned audio.

## Acceptance checklist

1. Extracted audio duration equals the source duration (within one video frame).
2. Spot-check at least 5 cues spread across the clip (start, middle, end, one fast-talking passage) against the audio;
   the last cue ends before the clip ends.
3. Word timestamps present and monotonic in the JSON.
4. Receipt has source hash, language, backend, model and uncertainty notes.
5. Verbatim and cleaned versions are separate files.

## Boundaries

Video transcripts, captions and word timings only. Meeting minutes and speaker-attributed protocols, lyrics
alignment as music work, and voice synthesis are other skills.
