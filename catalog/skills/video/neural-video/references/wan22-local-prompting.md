# Wan 2.2 prompts for local I2V / FLF graphs

Applies to Wan 2.2 A14B I2V and FLF graphs (high/low-noise experts with a 4-step distill LoRA) and, for the motion
part, to VACE / SVI / Uni3C. Where a generic Wan guide disagrees with what your own A/B tests measured, your tests win.

## 1. Start from intent, not from vocabulary

- Camera or lens words from the client ("35mm", "like Fincher", "ручная камера") express intent. Translate them into
  one plain camera verb, a shot size and a framing line, capped at ~120 words in total, and show the client the
  1-3 resulting lines.
- A two-seed A/B on these graphs found:
  - **Work:** push-in, pan, and an identity-hold line for I2V.
  - **Do not work:** two camera moves combined in one prompt.
  - **No effect:** "anamorphic", film grain, a 2.39 aspect in the prompt, and an anti-wax negative.
  - Lens or film-stock brand names had no verified effect; leave them out.
  - The look comes from the keyframe, the grade and post, not from prompt words.

## 2. I2V / FLF prompt shape

The image already fixes subject, wardrobe, set and light. The prompt only has to say what changes.

1. **Motion of the subject.** Step by step, in time order, with plausible physics: "she turns her head to the window,
   then exhales". If the brief has no motion, add one small, plausible movement.
2. **One camera instruction**, or "static camera". Use plain verbs: push-in / pull-back / pan left / tilt up / tracking.
3. **Secondary motion** that sells life: fog drifting, cloth moving, light flicker. One or two items.
4. **Constraint line** when identity matters, e.g. "the face and outfit stay the same as the first frame".

Rules, paraphrased from the official Wan 2.2 prompt-rewriter system prompts:

- Write in English, at most ~100 words for I2V.
- Do not re-describe what is visible in the start frame. Delete details the image already shows.
- Keep the camera moves the user asked for. Condense an over-long prompt; enrich a too-short prompt with motion, not
  adjectives.
- Add style words only if the user asked for a style, and put them first. Never add cinematic or film language to 2D
  or illustration styles.
- No literary mood writing ("an atmosphere of quiet longing"). Describe what is seen.
- For FLF, describe the path from the first frame to the last frame, not either frame. Large topology changes between
  the keyframes (pose flips, a different set) produce morphs: bridge them with an extra keyframe instead.

T2V (LTX or H3 text modes), from the same source:

- Add at most four cinematic settings: time of day, light source and direction, shot size and angle, composition.
- Defaults: daytime, medium or wide shot, centred composition.
- The light must fit the place. Do not add subjects the user did not mention. Keep it to 60-200 words.

## 3. Negative prompt on these graphs

- Only the first sampler runs CFG (`cfg_high`, default 3.5, steps `0..split_a` = 0-2). Samplers 2-3 run CFG 1, so the
  negative stops acting after step 2.
- Keep a short default (blur, flicker, warped geometry, broken, extra or fused limbs, melting, text and watermark,
  oversaturation, static frame, cartoon). Add at most 1-3 items aimed at the failure you actually saw.
- Long, generic negative lists add nothing. Fix motion problems with the prompt, an end frame, control (depth or pose)
  or a seed change.
- Raising `cfg_high` strengthens prompt adherence in the layout steps but can burn contrast. Change it only as a
  single-variable A/B against a fixed seed.

## 4. Size, length and seeds

- Start and end frames: sides multiples of 16, each side at most 1280, area at most 921,600 px, 8-bit PNG/JPEG. Crop
  to the target aspect before the run; do not let the graph stretch.
- `length` must be `4n+1`, range 5-81 at 16 fps. 49 frames is about 3 s, 81 about 5 s.
- Measured on a 16 GB card: 832x480 with 49 frames, ~166 s, ~14.3 GB peak (~3.4 s per frame plus model load). For
  finals, upscale the 832x480 draft with SeedVR2. Native 1280x720 or 81 frames: run a separate pilot that records time
  and VRAM before relying on it. Out of memory: lower `length` first (65, then 49), then the size (768x432, 704x400).
- Text-only camera: push-in and pan have A/B evidence; tracking, orbit and crane do not. Treat them as a risk in the
  brief and plan the fallback (FLF with an end keyframe, or Uni3C with a render video).
- Vertical delivery: render 480x832 from a vertical keyframe; never cut 9:16 out of an 832x480 render.
- Seeds: try 3-4 seeds at draft size with everything else fixed. Record the chosen seed and the reasons for rejecting
  the others. Re-use the chosen seed when you change only the prompt.

## 5. Worked example (FLF)

Brief: a monolith in fog. Keyframe A is a wide shot; keyframe B is closer and the monolith is lit. Function: a reveal
before the title.

```text
Slow push-in toward the monolith. Fog drifts left to right across the ground, a cold light behind the monolith
flickers twice and then holds steady. The monolith shape and position stay the same as the first frame. The horizon
stays level and the camera keeps a straight path.
```

An earlier variant also asked for "subtle camera shake"; that is a second camera behaviour and fails. Reject the take
if any of these appear: identity drift, a large topology morph, an unmotivated orbit, or a pile of generic cinematic
adjectives.

## Sources

- Wan-Video/Wan2.2 (https://github.com/Wan-Video/Wan2.2, Apache-2.0): README (A14B MoE high-noise and low-noise
  experts) and `wan/utils/system_prompt.py` (T2V and I2V rewrite rules), paraphrased.
