---
name: meeting-transcription
description: Use when a meeting, call or interview recording must become a timestamped transcript with speaker labels and a draft protocol ("расшифруй созвон", "протокол встречи", "кто что сказал", "задачи по итогам встречи"). Runs local ASR and diarisation, reviews speaker names against visible evidence and drafts decisions/tasks with a local LLM, keeping every claim tied to a transcript time. Not for voice cloning, song lyrics or video captions as a deliverable.
---

# Meeting Transcription

The recording is immutable evidence. The verbatim transcript is immutable too; cleaned minutes, captions and
protocols are derived versions that point back to transcript times.

## Inputs

- The recording (audio or video) and the project root where the package will live
  (e.g. `03_ДОКУМЕНТЫ/ВСТРЕЧИ/`).
- Language; known participant count, if any; participant names only from an authorised source (invite, agenda).

## 1. Prepare audio

Hash the source (sha256) and extract 16 kHz mono **without** trimming or silence removal - timestamps must map back to
the original:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 meeting.mp4
ffmpeg -n -i meeting.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le meeting-16khz.wav
```

## 2. Recognise speech (local)

- Russian: GigaAM-v3 (punctuation, word timestamps) in windows of up to ~10 min. GigaAM writes numbers as digits
  ("6 вечера").
- Other languages or fallback: faster-whisper `large-v3-turbo` with word timestamps.
- Run inside a local service or script; keep per-window checkpoints so an interrupted run resumes on the same source
  hash instead of starting over.
- Keep speech recognition local by default. Sending a recording to a cloud ASR needs the operator's explicit
  decision for that job.

## 3. Diarise

- Speaker embeddings (e.g. WavLM-based) clustered into acoustic speakers; pass `--speakers N` (2..12) when the count
  is known, otherwise estimate (cap around 8).
- Split segments at word timestamps before long pauses so one cluster does not swallow minutes of audio.
- `Спикер 1`, `Спикер 2`... are **unverified acoustic clusters**, not people.

## 4. Name speakers with evidence

For video calls, use the call application's active-speaker indicator and visible name labels as evidence, never
faces. Procedure and map format: [references/speaker-review.md](references/speaker-review.md). Each assignment carries
a method (`visual`, `context`, `unverified`), evidence ids and a reviewer, and is applied to a **new** reviewed
transcript version.

## 5. Package

Write a versioned package `<source>-transcript-vNNN/` (raw words, labelled segments, Markdown, plain text, SRT,
provenance, zip). Contract: [references/output-contract.md](references/output-contract.md).

## 6. Draft the protocol (local LLM)

- Feed the reviewed transcript as `[ЧЧ:ММ:СС] Speaker: text` lines in chunks of up to ~5000 characters to a
  **local** LLM endpoint; refuse non-local endpoints unless the operator chose a cloud model for this job.
- Output: summary, decisions, tasks (task, owner, due, transcript time), open questions. Flag items whose time or
  owner is not in the transcript (`time-not-in-transcript`, `owner-not-in-transcript`).
- Never invent deadlines, surnames or amounts. The draft is a draft; the working agent reviews it against the full
  transcript before delivery. A formal DOCX protocol or an action register is built only after facts and names are
  reviewed.
- Local LLM and diarisation models are heavy jobs: check resource headroom and the project's GPU lock first; never
  start a second model server or stop someone else's job.

## Privacy

- Recordings and transcripts contain personal data: keep them inside the project, never in shared caches, prompts to
  cloud models or public repos.
- Do not identify people from faces or voices against external databases.
- Creating tasks in an external tracker, sending minutes or publishing anything needs an explicit target and the
  operator's authorisation.

## Acceptance

- [ ] Source hash recorded; working audio has the full original duration.
- [ ] No omitted speech intervals; long recognition gaps inspected before being called silence.
- [ ] Original recognised words unchanged in the verbatim transcript.
- [ ] Every name has frame/context evidence or an explicit uncertainty mark; overlaps are marked.
- [ ] Every summary claim, decision and task points to a real transcript time.
- [ ] Numbers, dates, prices and decisions checked against the recording before any commercial document uses them.
- [ ] A short smoke test proves the runtime works, not that the whole meeting is accurate.
