# Comparative review rubric (generated or edited video)

Use this rubric for each candidate clip or cut. Compare it against the reference: a preset sample clip, an approved
clip, or the keyframes and brief. Keep three verdicts apart: **technical pass**, **creative assessment** and **owner
decision** (the operator's or client's). An agent can give the first two, never the third.

## 0. Material to have open

- The candidate, plus the reference shown side by side, or a contact sheet of both.
- Filmstrips of the start, every join or seam, and the last 1–2 s:
  `ffmpeg -ss S -to E -i clip.mp4 -vf "fps=N,scale=320:-1,tile=6x4" -frames:v 1 strip.png` (pick N so the span gives 24 frames).
- The run receipt (inputs, model, seed, output path, hash), with the prompt, seed, mode and frame count.

## 1. Technical pass (yes / no, with evidence)

| Check | How |
|---|---|
| Frame count, fps and size match the request | `ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames,r_frame_rate,width,height -of csv=p=0 clip.mp4` |
| Frame rule of the mode | Wan family `4n+1` @16, LTX-2.5 `8n+1` @24, H3 `17n+5` @24, InfiniteTalk `4n+1` @25 |
| Audio as intended | Present and in sync, or absent on purpose. After SeedVR2, the remux was done and durations match within one frame |
| First frame = start keyframe | Identity, framing, colour |
| Last frames | No decay: detail, colour and identity hold in the last 8–12 frames. An FLF end matches the end keyframe without a pop |
| Anatomy and mechanics | Hands, limbs, faces, wheels, text and logos do not melt, multiply or spin wrongly |
| Background | Neither frozen nor boiling. No texture crawl |
| Camera | Does what the prompt said: one move, no unmotivated orbit, no added shake |
| No accidental artefacts | No repeated footage, accidental speed-up or slow-down, gibberish speech or text, or unrelated overlays |
| Preset reject list | None of its items are visible (e.g. `anchored_reveal`: identity drift, topology morph, unmotivated orbit, adjective pile) |

Any "no" means the clip fails the technical pass. State the failure, where it is (timecode or frame), and the cheapest
fix: seed, prompt line, end frame, control, or segment repair.

## 2. Creative assessment (score 1–3 against the reference; write one line of evidence per axis)

| Axis | Question |
|---|---|
| Readable action | Is it clear within the planned duration what happens and to whom? |
| Shot function | Does it do the job named in the shot list (reveal, bridge, beat, emphasis)? |
| Identity and spatial specificity | Is it this person, this object, this place, rather than a generic one? |
| Temporal coherence | Do motion, physics and light behave consistently from the start to the end? |
| Rhythm | Does the length and pace suit the cut position and the sound? |
| Emotional cost | Does the shot keep its vulnerability, physicality and narrative evidence, or does polish erase them? |
| Sound relationship | Does the image sit with the voice, the music hit or the silence? |

Technical novelty is not a creative score. A take that is 2 on every axis beats one that is 3 on spectacle and 1 on
function.

## 3. Verdict format

```text
clip: <path>   reference: <path or preset>   receipt: <receipt path>
technical: pass | fail (<item>, <timecode>)
creative: action 2 · function 3 · identity 2 · coherence 2 · rhythm 3 · cost 2 · sound 2 — <one-line summary>
recommendation: use | retry <single change> | repair segment <range> | drop
owner decision: pending (operator)
filmstrips: <start> <joins> <end>
```

When several versions exist, rank them, and give one reason per place in the ranking. Prefer the smallest intervention
that makes the dramatic intention more exact.
