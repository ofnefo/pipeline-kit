# Sequence dramaturgy: from the idea to timed shots

Use this before the shot list, when a brief has more than about three shots. The aim is a sequence that builds. A string
of pretty clips does not.

## 1. Scene formula

Write one line per scene:

**desire + obstacle + the shape of the space + where the gaze goes + the rhythm**

Example: "She wants the letter (desire); he stands between her and the desk (obstacle); a narrow hallway, the desk at the
far end (space); we look past his shoulder at the letter (gaze); slow, slow, then one fast cut (rhythm)."

If you cannot fill in the desire or the obstacle, you have a mood, not a scene. That is fine for a sizzle reel, but then
plan it by the rhythm ladder alone (section 5).

## 2. Five anchors per piece

Fix these before any shot exists. Every shot should serve at least one of them:

1. **Emotion:** the one feeling the viewer leaves with.
2. **Motif:** a visual or sound element that comes back and changes (light through blinds, a ticking sound).
3. **Object:** the one thing the story turns on.
4. **Break:** the moment the pattern breaks (the twist, the silence, the change of colour).
5. **Final image:** the last frame, designed first. Generate it early. All other keyframes lead toward it.

## 3. Pressure from the environment

Each scene needs one thing in the place that pushes on the people: rain, heat, noise, a crowd, a closing door, a clock,
failing light. Write it in the scene line. It gives the model believable motion that is not a camera move.

**Three details per shot.** Each shot gets one environmental pressure, one micro-action (a hand tightening, a swallow)
and one motif (a sound or a visual). A shot with none of these is filler.

Emotions you name have to become visible signs. "Anxious" becomes two to four cues: "she rubs her thumb on the cup, looks
at the door twice, does not drink".

## 4. Beat map

Lay out the sequence in these beats. Short pieces merge some of them, but keep the order:

| Beat | Job | Typical shot functions (see shot-grammar.md) |
|---|---|---|
| Hook | One striking image or question in the first 1–2 s | Detail, Impact |
| Context | Where, who, what they want | Establish, Power |
| Pressure | The obstacle tightens | Pressure, Reaction |
| Crack | The first sign that something will give | Detail, Shift |
| Acceleration | Shorter shots, more movement | Pressure, Reaction, Shift |
| Impact | The turn, reveal or hit | Impact |
| Aftermath | What is left | Aftermath, Exit |

The storyboard has three layers: beats → shot functions → rhythm. Write it in that order. Do not start from a list of cool
images.

## 5. Rhythm ladders

The shot lengths in seconds set the pulse. Ready-made ladders:

| Feel | Ladder (s) |
|---|---|
| Slow burn | 4 · 4 · 3 · 2 · 1 · pause · 2 |
| Product reveal | 3 · 2 · 1.5 · 1 · 0.5 · 2 (hero hold) |
| Anxiety | 2 · 2 · 1 · 2 · 0.5 · 0.5 · 3 |
| Impact | 3 · 3 · pause (black or silence) · 0.5 · 4 |

- Always put a pause (a held frame, black, or silence) before the biggest cut. The contrast is what makes the hit land.
- The "staircase" pattern is long, shorter, pause, impact.
- One local take is 2–5 s. Shots under 2 s are cut from a longer take in the edit, not generated at that length. Plan the
  take so the useful part sits in its first 60–70 %.

## 6. Shot duration and where to split

| Content | Safe take length |
|---|---|
| A face carrying the emotion | 3–5 s |
| Hands doing something precise | 3–4 s (or ≤1.5 s of the actual contact) |
| Environment, with no faces | up to 8–12 s across a chain; each local take still 2–5 s |

- Split a long action at its **pivot**, the instant the person commits (the hand closes, the foot leaves the ground). The
  cut on that pivot hides the join.
- At the split, change the angle by at least 30° or the size by at least two steps. If the angle must stay the same, make
  shot B's first keyframe from shot A's clean last frame (crop or re-render it).
- Extend a clip only when its last frame is clean and the motion at that point is low. Otherwise generate a new take.

## 7. Shot card (14 fields)

For shots that matter (Hook, Impact, Final image), fill the full card. For the others, the shot-list row is enough:

1. id and beat
2. function
3. duration (from the ladder)
4. size, angle, camera height
5. lens intent (see camera-moves.md)
6. camera move and the moment it starts
7. blocking: start and end positions
8. action: one verb, from the start state to the end state
9. environmental pressure
10. micro-action
11. motif
12. light: source, side and time of day
13. sound cue (with a J-cut or L-cut, if any)
14. first and last frame description, and the continuity ledger ids

## 8. Hand-off

- The beat map and the rhythm become `00-brief/shotlist.md`. The cards for key shots live next to it.
- Keyframes are ~70 % of the final quality. Make the final image and the hook keyframes first, then the rest.
- The previz chain ([previz.md](previz.md)) checks the rhythm on an animatic before any video is generated.
- Review the whole sequence for its rhythm, not only each clip ([review-rubric.md](review-rubric.md)).

---
Idea sources (paraphrased, see ../NOTICE.md): smixs/visual-skills `dramaturgy.md`, `universal-rules.md` (CC BY 4.0, Serge Shima); DirectorSKILL duration and split rules (MIT, wangzhang-wu); 0xhughs/director-skills `audio_motion_timing.md` (MIT). Living directors' names removed.
