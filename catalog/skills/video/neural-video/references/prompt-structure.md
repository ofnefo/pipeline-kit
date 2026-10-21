# Video prompt structure (model-agnostic)

This file covers the shape of a prompt that works on any local route (Wan 2.2 I2V/FLF, VACE, LTX-2.5, MiniMax H3). It also
covers how much motion to ask for, and how long a take should be. Model-specific facts come from
[wan22-local-prompting.md](wan22-local-prompting.md) and from each model's official prompting guide. Those facts
include negative-field behaviour, sizes, frame counts and word caps, and they win over this file.

## 1. Order and weight

The model gives the most weight to the start of the prompt. Use this order, and drop the parts the keyframe already fixes:

1. the style or medium, only if the user asked for one;
2. **the camera** (one main move, or "static camera");
3. the subject, with its start state;
4. **one** action, as a chain in time order: "then …, then …";
5. one motion in the environment;
6. the end state;
7. a lock line: what has to stay the same.

- Write what **changes**, not what things look like. The still image already sets the appearance.
- Use no filler words: cinematic, masterpiece, epic, stunning, 8k, hyperreal. They do not help and they push the look
  toward "AI".
- Turn named emotions into two to four visible cues (see video-direction `sequence-dramaturgy.md`).
- Remove contradictions ("static camera" together with "sweeping view"). The model averages them into drift.
- Never put the names of living artists or directors in the prompt. Describe the visible traits instead.

## 2. Four prompt shapes

| Shape | When | What goes in |
|---|---|---|
| S1 motion-only I2V | One keyframe in, the usual case | Camera; start state; one action; one environment motion; end state; lock line. No appearance words. |
| S2 full T2V | No keyframe (LTX or H3 text modes) | The full description: subject, place, light source and side, shot size, then the S1 motion part |
| S3 keyframe pair (FLF) | First and last frames given | One bridge sentence; **one** change (pose OR camera OR light); the path; the easing; what does not change |
| S4 timed multi-beat | A longer take, or a model that follows time cues | A global block (identity, palette, light) plus time segments; each segment holds only action, camera and one cue |

- **S3:** if the two keyframes differ in pose and camera and light at once, the result morphs. Make a middle keyframe and
  run two FLF segments.
- **S4:** write time blocks as `[0:00–0:02] …`, `[0:02–0:04] …`. A 4 s take holds one gesture. A 6–8 s take holds an
  action and its consequence. Never repeat the identity in the segments, because it is already in the global block.

## 3. Motion budget

Score every planned take before you write the prompt:

- Score the subject motion, the camera motion and the environment motion from 0 to 3 each.
- Multiply by the duration factor: ×1.0 up to 5 s, ×1.3 for 6–10 s, ×1.6 above 10 s.
- Add 1 for each of these: each extra independent person, a face filling more than a third of the frame, precise hand
  work, each extra reference image.

| Shot type | Budget ceiling |
|---|---|
| Close character work | 4 |
| Medium or wide shot with people | 6 |
| Environment or product with no people | 8 |

On open-weight models, depth or pose conditioning (Uni3C, `h3_flf_depth`, VACE control) lifts the ceiling by about 2.
Over the ceiling, simplify, split the take, or move the motion into conditioning. Do not write a longer prompt.

## 4. Action

- Give one main verb per take. Consequence prompting chains a cause to its visible effect: "she drops the glass; it
  shatters; she steps back". That chain counts as one action.
- Give physical weight early: "a heavy door, she leans her whole body into it".
- Muscle cues with an amplitude beat mood words: "jaw tightens slightly", "shoulders drop about 2 cm", "a small, slow
  breath". With no amplitude, models over-act.
- If the brief has no motion, add a breathing-level micro-motion: blinking, breath, hair or cloth moving. A dead-still
  frame reads as a freeze.
- Light must have a source in the scene ("light from the window on the left"). A light with no source drifts from shot to
  shot.

## 5. Durations and frames

- Duration = frames / fps. Frame counts follow each graph's rule (Wan/VACE `4n+1` at 16 fps, LTX `8n+1` at 24, H3
  `17n+5` at 24; check `workflows.md`).
- Quality drops past the middle of a long generation. Prefer shorter takes chained through clean last frames to one long
  take.
- If an action keeps failing late in the take (about 60–70 % of the way in), the take ran out of budget. Shorten it, or
  start the action earlier.

## 6. Negatives and the language of the text encoder

- Put negatives in the negative field or node only, never as "no X" inside the positive prompt. Add 2–4 items aimed at the
  failure you actually saw. Where a graph ignores negatives after the first steps, say the positive instead: "hands
  stay still on the table", not "no hand movement".
- The text encoder sets the language. Wan's encoder understands Chinese as well as English; for LTX and H3, use
  English. Pick one language per comparison and never switch it in the middle of an A/B test.
- Stay near the model's training resolutions and aspect ratios. Odd sizes cost more quality than any prompt can win back.

## 7. Compressing a prompt that is too long

Cut in this order, keeping the items at the top longest:

1. continuity and identity (keep);
2. the action;
3. the timecodes;
4. the light;
5. the camera;
6. the edit grammar;
7. sound (cut first).

Philosophy, stacked adjectives and director references go before any of these.

For a long piece, add a **priority line** to the brief, not to the prompt. It names what must be right (the main subject,
the key shots, the final frame) and what may be loose (the transitions). Spend the seeds on the "must" shots.

## 8. Checks before you queue

- [ ] One camera move, placed near the start.
- [ ] One action, from a start state to an end state.
- [ ] Three details: an environmental pressure, a micro-action, a motif.
- [ ] Nothing the keyframe already shows is described again.
- [ ] The motion budget is under the ceiling.
- [ ] Identity is pasted from `00-brief/continuity.md` (see video-direction `continuity-bible.md`).
- [ ] No living names, brand lenses or filler words.
- [ ] The frame count fits the graph rule; the seed is recorded.

---
Idea sources (paraphrased, see ../NOTICE.md): DirectorSKILL prompt shapes, motion budget and OSS notes (MIT, wangzhang-wu); smixs/visual-skills `universal-rules.md`, `fixes-and-skeletons.md` (CC BY 4.0, Serge Shima); 0xhughs/director-skills `video_prompt_components.md`, `negative_prompt_patterns.md` (MIT); jacob-ye-seedance-prompt (CC BY 4.0, Jacob Ye); fal-ai-community/skills SCLCAM order (MIT). Paraphrased; cloud-model syntax left out.
