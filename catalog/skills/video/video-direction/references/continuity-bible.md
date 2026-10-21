# Continuity bible: what must not drift

Each local take is short (2–5 s) and is generated on its own. Continuity comes only from what you lock in writing and in
keyframes. Keep the bible in `00-brief/continuity.md` next to the shot list. Every prompt and keyframe brief copies from
it **word for word**.

## 1. What is locked and what may change

Split every element into two lists before you make any keyframe:

- **Locked:** face structure, hair cut, body build, wardrobe pieces, key props, the layout of the set, the side the key
  light comes from, the palette.
- **May change:** expression, pose, hair state (wet, wind), dirt or wetness, the state of a prop (full or empty, open or
  closed), the time of day, the weather.

Locked items are written once and pasted without edits. Variable items change only through the state ledger (section 3).

## 2. Identity string: one per character

Write 30–50 words in this order:

1. one or two demographic facts, with the age as a number ("woman, 34");
2. two or three structural facts (face shape, build, height relative to others);
3. exactly **one** distinctive mark (a scar, a mole, a gap in the teeth);
4. one hair spec (length, cut, colour);
5. one wardrobe anchor, last: colour, material and one detail ("rust wool coat, brass toggles").

Never put these in it:

- mood words, or camera, lens or light words;
- celebrity look-alikes or anyone's name;
- age ranges, or era words that stand in for a garment ("1970s look");
- negatives, or memory instructions like "same as the reference";
- states that change (wet, bloody);
- a second character.

Paste the identical string into every shot where the person appears. If a tool has a separate wardrobe slot, use only the
first 15–25 words (the face part). Freeze one string per language, and never translate it halfway through the project.

## 3. State ledger

For every shot, the bible has one row:

`shot id | what changes in this shot | what carries into the next shot | what to check on the generated clip`

- A state moves one band at a time: dry → damp → wet, clean → dusty → dirty, full → half → empty. If a state jumps two
  bands between shots, the viewer reads it as an error.
- The state at the end of one scene has to equal the state at the start of the next scene.
- Write the progress of an object's state in one sentence ("the candle burns from full height to half by shot 6").

## 4. Drift checklist

Check each axis on the contact sheet. [Segment repair](../../neural-video/references/segment-repair.md) covers the repair
route.

| Axis | What to lock or track |
|---|---|
| Face | The identity string; one reference image per character |
| Hair | Keep the cut (locked) apart from the state (wind, wet) |
| Wardrobe | Layers and fastenings (open or closed jacket, sleeves rolled), which side things are on |
| Props | Who holds it, in which hand, and "only one X in the scene" |
| Wet, dirt, injury | Their band in the ledger; the injury side (left or right) |
| Light | Key direction, colour and hardness, written in the keyframe prompt of every shot |
| Time of day | A clock time ("17:40, low sun"), not "evening" |
| Weather | A track per scene (rain starting, steady, stopping) |
| Geography | One locked plate or layout image of the set, made before any character shots |
| Screen direction | Who is screen left and who is screen right; the direction of travel |
| Eyeline | Its direction, from the people's heights and positions |
| Camera height | In metres, per setup |
| Palette | Make all the stills of one scene in one session, from the same palette block |

## 5. Props: three tiers

- **Hero props** are touched, used or important to the story. Each gets a reference image, a full description and a
  ledger row.
- **Set props** are visible but never touched. Lock them in the layout plate and do not mention them in motion prompts.
- **Background props** are dressing. Leave them out of prompts, so they do not start moving or multiplying.

## 6. Scene pack: reference images per scene

Before any shot of a scene is generated, make:

1. a **master** wide shot of the set with the light already in place;
2. a **layout** image (top-down or plan) for the geography;
3. a character sheet for each person (front, three-quarter, profile; expressions only if needed);
4. hero prop sheets.

Generate the keyframes from this pack. Do not invent the set again for each shot.

## 7. Binding the references

When more than one reference image goes in, give each one a role, and say what to **ignore**:

> image 1: the face and hair of the woman only (ignore its background and light);
> image 2: the room layout and the window light only (ignore any people in it);
> image 3: the coat only.

- Bind each character to their own reference. Two people described in one sentence come out as twins.
- Do not describe again in text what a reference already defines. Text and image that disagree produce drift.
- Every extra reference raises the motion-budget cost (see neural-video `prompt-structure.md`).

## 8. Where the bible plugs in

- `00-brief/shotlist.md` points to the bible's line ids; the keyframe briefs paste them in.
- Review ([review-rubric.md](review-rubric.md)) checks the drift axes above, as well as quality.
- When a clip drifts, repair it through neural-video `failure-diagnosis.md` (F1, F7, F12, F19) and then `segment-repair.md`.

---
Idea sources (paraphrased, see ../NOTICE.md): DirectorSKILL (MIT, wangzhang-wu); smixs/visual-skills `universal-rules.md`, `fixes-and-skeletons.md` (CC BY 4.0, Serge Shima); 0xhughs/director-skills `character-location-prop-bible` (MIT); jacob-ye-seedance-prompt (CC BY 4.0, Jacob Ye); fal-ai-community/skills `character-design` anchor system (MIT).
