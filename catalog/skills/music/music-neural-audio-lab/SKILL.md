---
name: music-neural-audio-lab
description: Use when music must be generated, remixed, continued, repainted, separated, transcribed to MIDI or derived from an image or audio reference with local neural tools ("сгенерируй трек", "кавер в другом стиле", "продли концовку", "перепой строчку", "разбери на стемы"). Routes to ACE-Step via ComfyUI, stem separation, Basic Pitch and local TTS with a render contract and a controlled variant matrix. Not for client voice-over jobs (voiceover-dubbing) or plain loudness/cleanup (audio-production).
---

# Neural Audio Lab

Local-first routing for neural music tools. Every render is source material until a human promotes it.

## Route by objective

- **New song or lyric demo** - ACE-Step 1.5 (XL SFT) text-to-music in ComfyUI: style tags + lyrics + seconds, seed,
  BPM, key, language; lossless FLAC out. Reference cost on a 16 GB card: about 55 s per 45 s of audio, peak about
  15.4 GB VRAM, i.e. the whole card.
- **Restyle an existing song (cover/remix)** - ACE-Step audio-to-audio with the source as input, new style tags and
  the source lyrics; cover strength 1.0 and denoise 0.7 keep structure and sung words, denoise 1.0 is a freer
  re-imagination (words may be lost). Remix rights follow the source recording.
- **Extend an ending** - extend mode: N new seconds with about 2 s overlap; pass the whole extended song's lyrics
  (source lines + new lines). Splice the render back so the original stays bit-exact up to the overlap (a raw render
  is a VAE round trip and differs from the source by about -15 dB there); crossfade inside the overlap.
- **Fix one section or one sung line** - repaint a time range (start/end seconds) with an edited lyric sheet. Take
  the range from word timestamps of a local ASR, then verify the new words with ASR again. Splice as above.
  In ComfyUI this is latent inpainting and needs a time-mask node for 1-D audio latents (a generic latent noise mask
  does not work on audio latents); the model's official repaint is a different implementation.
- **Preserve a vocal, change the arrangement** - BS-RoFormer vocals/instrumental -> remix or rebuild the instrumental
  -> level/time align -> rejoin.
- **Rebuild editable material** - HTDemucs 6-stem -> Basic Pitch per melodic stem -> onset-based drums -> MIDI cleanup
  (see `music-midi-composition`).
- **Reverberant vocal** - MelBand RoFormer de-reverb on an isolated vocal; lead vs backing - karaoke model on the
  vocal stem (see `audio-production` tooling).
- **Spoken voice** - Qwen3-TTS (Apache-2.0) for anything releasable; XTTS-v2 only as a non-commercial draft. Cloning a
  real person's voice requires that person's documented consent. Client VO jobs go to `voiceover-dubbing`.
- **Image -> music** - describe the image, write a sonic brief, merge with the project's style brief, render a few
  ACE candidates, then stems/MIDI and a human rebuild.

## Prompting music models

- Tags: genre, era, tempo feel, instrumentation, vocal type, mix character, mood; avoid artist names (translate a
  reference into attributes: structure, energy, texture, technique).
- Lyrics with section labels (`[verse]`, `[chorus]`, `[bridge]`); one line per sung phrase; keep line lengths
  singable at the chosen BPM (run `music-songwriting`'s preflight first).
- Fix BPM, key and duration explicitly when you need parts to line up later.

## Render contract

Before a render record: objective, input hashes, model and version, prompt/tags, negative constraints, seed,
duration, BPM/key if known, ownership/rights status. Audio modes also record mode, source path + sha256 (and of the
normalised 48 kHz copy) and the mask/cover settings. After the render record: output path and hash, measurements
(LUFS, true peak, duration), what survived, what failed, and whether it is source material or a release candidate.

Generate a small controlled matrix, not random abundance: vary seed first, then one axis (density, timbre or
structure). Judge at matched loudness, never louder than the references. A plausible WAV is not finished
authorship.

## Resource policy

- ACE/ComfyUI, stem separation, TTS and local LLMs are mutually exclusive heavy GPU jobs: take the project's GPU lock,
  run one at a time, unload models afterwards.
- Reachability of a worker or server is not inference readiness: check the runtime registry and a smoke receipt.
- Add a new model family only to fill a named gap; check licence/provenance, disk, CUDA compatibility and whether an
  existing runtime can be reused; do not install a second Torch stack into an unrelated environment. Gated models
  (e.g. ones needing accepted terms) stay unused until the operator accepts them.
- Pay-per-use voice/music services only on the operator's explicit request for that job.
- Send only task-selected inputs to any worker; never upload private notes or unpublished lyrics to external services
  without permission.

## Acceptance

- [ ] Render contract written before and after each render.
- [ ] Extend/repaint outputs spliced; original material outside the range bit-exact.
- [ ] Lyric edits verified by ASR; rights status recorded (source recording, voices).
- [ ] GPU lock taken and released; models unloaded.
