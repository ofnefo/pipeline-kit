# Camera moves and lenses: choose by purpose

A camera move has to answer the question **"what changed?"**. If nothing in the story changes during the shot, lock the
camera. The local video models follow camera text worst of everything they are given. When the move is the point of the
shot, drive it with geometry (see the last section), not with adjectives.

## 1. Moves by purpose

| Purpose (what changed) | Move | Notes |
|---|---|---|
| A decision is being made, the pressure grows | Slow push-in | The most reliable move on Wan; start it on the beat that matters |
| A reveal: new information or the space opens up | Pull-back, or crane / pedestal up | End the move on the thing that was revealed |
| We follow a desire or a chase | Tracking or dolly alongside | Keep the screen direction (see shot-grammar.md) |
| We connect two things in the same space | Pan or tilt | One axis only; it should not drift |
| Attention moves from one person or object to another | Rack focus | Name the plane it starts on and the plane it ends on |
| We are lost, in a panic, or subjective | Handheld | Use a small amplitude; heavy shake reads as an AI artefact |
| Inspecting an object, or a product hero shot | Slow orbit, less than 90° | Lock the subject to the centre; geometry drives it better than text |
| An observing distance, inevitability | Static, long lens | Often the best choice for close character work |

Rules:

- **One main move, plus at most one subtle one** (for example a push-in plus a slight drift). Two main moves in one
  prompt failed in a two-seed A/B test on local Wan graphs. If you need a second move, split the shot or cut.
- Start and stop the move on story beats ("the push-in starts when she sees the letter"). Do not run it through the whole
  shot.
- Give the speed and the direction in plain words: "slow", "steady", "quick". Give the amount ("a short push-in, about one
  shot size").
- Use the plain verbs: push-in, pull-back, pan left/right, tilt up/down, tracking left/right, crane up, orbit left, static.
  Put the camera instruction near the start of the prompt. When it comes last, it is the part that gets ignored.

## 2. Lenses: the intent, then the visible effect

Client lens words ("35mm", "telephoto", «как у ...») express **intent**. Translate them into one camera verb, a
lens band and a framing line. Do not paste the lens name into the prompt. Write the value **and** what it does to the
picture:

| Lens band | Visible effect to write instead of the number |
|---|---|
| Ultra-wide (14–20 mm) | The space stretches, lines bend toward the edges, the person is small inside the place |
| Wide (24–35 mm) | Environment and person together, natural depth, the "you are there" feel |
| Normal (40–55 mm) | Close to how the eye sees, little distortion, an honest look |
| Short tele (75–105 mm) | Flattering faces, a soft background, the person separated from the place |
| Long tele (135 mm and up) | Compressed depth, the background stacked behind the subject, an observed or surveillance feel |

- A shallow depth of field has to name what is sharp and what falls off ("eyes sharp, the room behind dissolves into soft
  shapes").
- Lens and film-stock brand names have no verified effect on the local models (`brands_verified` is empty). Leave them
  out.
- The look comes from the keyframe, the grade and post, not from lens words in the video prompt.

## 3. Rare or technical terms

When a term is rare (dolly zoom, snorricam, whip pan, Dutch roll), the model may not know it. Spell it out in five parts:

1. the term;
2. the target (which subject the move centres on);
3. the visible change (for example "the background expands while the face keeps its size");
4. how the foreground and background relate;
5. the direction and speed.

## 4. Transitions between shots

Name the transition in the shot list, and say the moment it happens. Use one type per cut.

| Transition | When it works |
|---|---|
| Straight cut | The default; cut on action or on a look |
| Match cut (shape, motion or colour) | Linking two places or two times; plan both keyframes together |
| Whip-pan hand-off | Energy, a change of place; generate the blur in both shots, then join them in the edit |
| Push-in through an object | The camera passes through a doorway or a dark foreground; the next shot starts from the dark |
| Smash cut | From quiet to loud or the other way round; no in-between frames |
| J-cut / L-cut | The sound of the next shot arrives early, or the sound of the last one carries over; this is done in the edit, not in generation |
| Dissolve | Time passing or a memory; use rarely |

Transitions that need a camera move in both shots belong in the previz chain ([previz.md](previz.md)), so their speed and
direction match.

## 5. When the move matters: geometry, not words

Text-only camera control is the weakest route on the local stack. When the move is the reason the shot exists:

- Block the move in 3D or in a depth blockout, then drive the generation with the camera path through a camera-control graph (Wan 2.1
  Uni3C), or through a depth-controlled FLF route (see neural-video `workflows.md`). For a standard move with no
  blockout, the Wan 2.2 Fun Camera graph has preset camera poses (it is slow: about 19 min per 5 s).
- For FLF, the first and last keyframes already set the start and end of the move. The prompt only names the path and the
  easing ("slow push-in, easing out at the end").
- Check the move at 1x and at 0.25x speed. Look for drift, a horizon that wobbles, or a second move the model added on
  its own (see neural-video `failure-diagnosis.md`, F6).

---
Idea sources (paraphrased, see ../NOTICE.md): smixs/visual-skills `camera-lighting-vocabulary.md`, `universal-rules.md`, `dramaturgy.md` (CC BY 4.0, Serge Shima); 0xhughs/director-skills `camera_lens_movement.md` (MIT); jacob-ye-seedance-prompt (CC BY 4.0, Jacob Ye); fal-ai-community/skills `cinematography` (MIT).
