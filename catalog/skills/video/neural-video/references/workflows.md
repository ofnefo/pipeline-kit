# Local ComfyUI video modes

Keep each graph as `<name>.api.json` (ComfyUI API export) plus a small `<name>.params.json` that maps friendly keys
(prompt, seed, length, images) to node inputs. Keep a machine-readable mode table (inputs, frame rule, limits,
evidence) next to the graphs, and mark each mode **verified** (a GPU run receipt exists) or **pending** (graph
configured, never run). Never advertise a pending mode as verified; pilot it first.

## Modes

| Mode | Use | Frames / fps | Notes |
|---|---|---|---|
| Wan 2.2 I2V 14B | one start frame -> video | `4n+1` @16 | same three-sampler graph as FLF |
| Wan 2.2 FLF 14B | first + last frame -> video | `4n+1` @16 | 832x480, 49 frames ~166 s, ~14.3 GB peak on 16 GB |
| LTX-2.5 FLF / I2V / T2V / last-frame | video with audio | `8n+1` @24 | |
| MiniMax H3 FLF, FLF + depth control | keyframe pair; depth video steers geometry | `17n+5` @24 | trained range ~124-362 frames |
| MiniMax H3 T2V / I2V / last-frame | text / start / end frame | `17n+5` @24 | |
| MiniMax H3 Ref2VA | ref image + ref audio + prompt -> video with audio | `17n+5` @24, canvas multiple of 32 | reference influence, not exact editing; check the model licence |
| Wan VACE A14B v2v | restyle keeping motion (depth/pose control) | `4n+1` @16 | re-measure VRAM after any quantisation switch |
| Wan VACE A14B inpaint | regenerate a region, mask WHITE = replace | `4n+1` @16 | used for logo/watermark removal too |
| Wan 2.2 SVI long take | latent continuation with blended overlaps | `4n+1` @16 | identity stable, motion weak |
| Wan Animate | motion transfer from a drive video | `4n+1` @16 | the drive video **needs an audio track** (add silence) |
| InfiniteTalk | portrait + speech -> talking head | `4n+1` @25 | `length` sets duration; conform the audio copy to `length/25` s |
| Wan 2.1 Uni3C | camera follows a render video (blockout, point-cloud warp, zoompan) | `4n+1` @16 | |
| Wan 2.2 Fun Camera | preset camera poses | `4n+1` @16 | ~19 min per 5 s on 16 GB |
| SeedVR2 video / image | restore/upscale to a target short side, keeps fps | - | video output has **no audio**: remux it |

The Wan 2.2 TI2V-5B model is not needed when the 14B FLF/I2V graphs fit; prefer those.

## Wan 2.2 I2V / FLF graph facts

- Settable: start image, end image (FLF), prompt, negative, width, height, `length` (default 81), seed, `cfg_high`
  (3.5), the step splits `split_a` (2) / `split_b`, the two LoRAs, fps, filename prefix.
- Hard-wired: 8 total steps, `ModelSamplingSD3 shift=8` on all three branches, lightx2v 4-step rank-64 LoRA at
  strength 1.
- Samplers 2 and 3 run CFG 1, so the negative prompt only influences steps `0..split_a`.
- If a graph has SageAttention patch nodes set to `disabled`, do not quote SageAttention as a speed-up.
- Default negative: blur, flicker, warped geometry, broken/extra/fused limbs, melting, text/subtitles/watermark,
  oversaturation, static frame, cartoon. Add 1-3 shot-specific items at most.
- Treat 1280x720 or 81 frames on a 16 GB card as a pilot that records time and VRAM.

## Post-processing

- **Remux source audio** after SeedVR2:
  `ffmpeg -i upscaled.mp4 -i original.mp4 -map 0:v -map 1:a? -c:v copy -c:a copy -shortest out.mp4`;
  durations must agree within one frame.
- **Interpolation** (RIFE / GIMM-VFI) 16 -> 24 fps (or x2/x3/x4) on CFR input, audio copied. Thin fast detail (rain,
  sparks, spokes) ghosts under RIFE: check the filmstrip, or deliver at 16 fps.
- **ESRGAN x2** is fast but may flicker; prefer SeedVR2 for finals.

## QC helpers (FFmpeg)

- Frame count and fps:
  `ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames,r_frame_rate,width,height -of csv=p=0 clip.mp4`.
- Filmstrip of a span (24 frames between S and E seconds):
  `ffmpeg -ss S -to E -i clip.mp4 -vf "fps=24/(E-S),scale=320:-1,tile=6x4" -frames:v 1 strip.png`
  (replace `24/(E-S)` with the computed rate). Make one for the start, every join and the tail.

All smoke tests on synthetic inputs are not acceptance on a real scene; that is a separate review.
