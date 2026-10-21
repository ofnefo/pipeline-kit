# Tool routing

- **FFmpeg / FFprobe** - probe, transcode, trim, fade, mix, resample, channel operations, silence detection,
  loudnorm, ebur128 true peak. Keep them on PATH (the bundled scripts also accept `FFMPEG` / `FFPROBE` env vars).
- **Analysis** - `scripts/analyze_audio.py` (numpy, librosa, soundfile, pyloudnorm): BPM/key hypotheses
  (Krumhansl-Kessler profiles over chroma), waveform envelope, LUFS, sample peak, FFmpeg true peak, silence ranges,
  beat grid, transient cue candidates, loop-seam RMS, spectral statistics.
- **Technical master** - `scripts/master_audio.py` (stdlib + FFmpeg): delivery profiles, two-pass linear loudnorm,
  limiter only when needed, 16-bit TPDF dither, before/after report.
- **Stems** - [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator) (MIT) in its own
  environment. Useful models (list current names with `audio-separator --list_models`):
  - `model_bs_roformer_ep_317_sdr_12.9755.ckpt` - BS-RoFormer vocals / instrumental (default two-stem);
  - `htdemucs_6s.yaml` - HTDemucs six stems (drums, bass, guitar, piano, vocals, other);
  - `dereverb_mel_band_roformer_anvuew_sdr_19.1729.ckpt` (and a less aggressive variant) - vocal de-reverb; it
    expects an isolated stereo vocal with decorrelated reverb, a mono reverb identical on both channels is barely
    removed;
  - `mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt` - lead vocal vs the rest.
  - Chain: isolate vocals first, then run karaoke on the vocal stem to get lead vs backing, or de-reverb from a full
    mix.
  Write a `separation-report.json` with input/output hashes and model names. Check each model's licence before
  commercial use.
- **Voice synthesis** - Qwen3-TTS (Apache-2.0) for anything that may be released; XTTS-v2 is under the Coqui Public
  Model License (non-commercial) and fits internal drafts only.
- **Audio-to-MIDI** - Spotify Basic Pitch (Apache-2.0); separate stems first for dense mixes.
- **Transcription / alignment** - a local ASR with word timestamps: GigaAM-v3 for Russian, faster-whisper
  `large-v3-turbo` for other languages and lyrics.
- **Neural generation / remix / continuation** - ACE-Step through ComfyUI; see `music-neural-audio-lab`. It occupies
  the exclusive GPU lane.

Keep heavy GPU engines in their own environments; do not install a second Torch stack into a control or web venv.

## Architectural references

- The public `ffmpeg-audio-processing` skill in
  [benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench) is a useful command-surface checklist
  (conversion, trimming, fades, channels, resampling, silence, speed, mixing, loudnorm). This skill adds
  immutable-source handling and measured before/after QA.
- [AnqiPinku/reaper-producer-skill](https://github.com/AnqiPinku/reaper-producer-skill) shows the boundary used here:
  DAW-independent audio work stays in this skill; live DAW control lives in a separate producer skill and bridge.
