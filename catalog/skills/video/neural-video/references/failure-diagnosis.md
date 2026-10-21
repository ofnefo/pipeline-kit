# Diagnosing a failed clip, before you repair it

Read this when a take fails review. It tells you **what** failed and **how much** effort it is worth. How to do the
actual repair is in [segment-repair.md](segment-repair.md): finding the bad stretch, the filmstrip, repair-prepare,
FLF / VACE / inpaint and seams.

## 1. Triage first

1. Play the clip at 1x, then at 0.25x. Write down every symptom, then count them.
2. Turn vague notes into failure codes:
   - "Looks fake" is usually weight (F14), speed (F13) or light (F12).
   - "AI look" is usually melting (F3), hands (F10) or speed (F13).
   - "Boring" is not a generation failure. Re-plan the shot (video-direction).
3. A clip with two or more codes skips the cheap fixes (section 3).

## 2. Failure codes

| Code | Symptom | Most likely cause |
|---|---|---|
| F1 | The face or identity drifts | The identity string is missing or changed; a weak reference; too many references |
| F2 | Little or no motion | The motion is not stated, or it is buried late in the prompt; the CFG is too low |
| F3 | Melting or morphing | Too much motion for the budget; the keyframes are too far apart (FLF) |
| F4 | The asked-for action is ignored | Too many verbs; the action comes after the camera and style words |
| F5 | No end state, the action stalls | The end state is not described; the take is too long for the action |
| F6 | The camera moves when it was not asked to | No "static camera"; motion words the model reads as camera moves |
| F7 | Breaks continuity with the previous shot | Not built from the clean last frame; the ledger was not used |
| F8 | Something from the wrong era or place | Era words instead of concrete objects |
| F9 | An extra person or object appears | A crowd or the plural in the prompt; a background prop that was mentioned |
| F10 | Hands, eyes or teeth are wrong | Precise hand work; a face too large in frame for the budget |
| F11 | Text or logos are garbled | Readable text was asked for (this cannot be fixed in generation) |
| F12 | The light drifts | The light source and side are missing from the prompt or keyframe |
| F13 | Wrong speed (too fast, slow-motion, jerky) | No speed words; frame count or fps mismatch; motion too big for the length |
| F14 | No weight or contact (floating, sliding feet) | No physical-weight cue; contact that lasts too long |
| F15 | Lip-sync is off | Wrong route; it needs the audio-driven route, not prompt text |
| F16 | Look or grade differs from the neighbours | The keyframes were made in different sessions; style words in the video prompt |
| F17 | Wrong framing or crop | The keyframe aspect differs from the graph size; the graph stretched it |
| F18 | Seam at an extension | Extended from a frame with blur or high motion |
| F19 | An object vanishes or doubles | Kept over 8 s, or through an occlusion |

## 3. Cost ladder: take the cheapest step that can work

| Level | Step | Local meaning |
|---|---|---|
| L1 | Edit the prompt | Reorder it (camera and action first); remove contradictions; add the end state |
| L2 | Change parameters | Fewer frames; less motion; keep the seed; a one-variable `cfg_high` A/B test |
| L3 | Re-roll seeds | At most 2 new seeds at draft size, with everything else fixed |
| L4 | Rebuild the keyframe | A new first or last frame (any still-image tool); add a middle keyframe for FLF |
| L4.5 | Surface pass | VACE v2v or segment inpaint over the bad stretch (segment-repair) |
| L5 | Re-plan the shot | Split it, simplify it, change the angle (video-direction) |
| L6 | Fix it in the edit | Trim it, cut away, cover it with an insert or a J/L-cut |
| L7 | Drop the shot | When it has cost more than ~8 % of the job's generation budget |

Skip straight to **L5** when:

- the clip has two or more failure codes;
- precise contact lasts longer than 1.5 s;
- the take is longer than 8 s and the action starts after 5 s;
- three generations have already been spent on this shot.

**Three-strike rule.** After three failures, change the shot, not the prompt:

- shorten the take by 40–50 %;
- push in to a closer size;
- simplify the action;
- split it at the pivot;
- switch to first and last frames;
- swap in a stand-in object or action;
- or move the action off screen and show only the reaction.

## 4. Finding the root cause

Check these in order, and stop at the first one that explains the failure:

1. Was an intended last frame or end state defined?
2. Which input mode was used, and how good is the keyframe (sharpness, aspect, a pose the model can continue)?
3. How long is the take, and when does the failure start? Failing at 60–70 % of the length means the budget ran out.
4. How many verbs and moves are in the prompt?
5. How many generations have been spent so far?
6. Is it the same failure every time (the plan is wrong), or a different one each time (it is noise, so try seeds or
   shorten)?

## 5. What generation cannot fix

Plan around these from the start; each has a workaround:

| Weak spot | Workaround |
|---|---|
| Precise hand work | At most 1.5 s of contact; start with the hand already in position |
| A hand holding a branded product | Move the light, not the product; composite the real pack shot |
| Readable text or a logo | Add it in post (motion-graphics) |
| Several people touching | Split by person; make the contact happen on the cut |
| An object kept over 8 s or behind something | Cut before it is hidden; re-anchor it with a keyframe |
| Reflections and mirrors | Avoid them, or composite them |
| Faces in a crowd | Silhouettes or soft focus; at most 2 readable faces |
| An exact count of objects | Composite, or avoid showing the count |

## 6. Trial log and acceptance

- Change **one** variable per trial. Log `shot | trial | changed variable | seed | graph/params hash | failure codes |
  verdict` in the job's `review/` notes.
- Trim 0.5–1 s from the head and the tail of every take before judging it. Those frames are often the weakest.
- Judge from a contact sheet (6–12 frames) together with real-time playback. A good still can hide motion failures.
- Every rejected take keeps its codes, so the next prompt is built from the evidence (see
  [prompt-structure.md](prompt-structure.md)).

---
Idea sources (paraphrased, see ../NOTICE.md): DirectorSKILL failure codes, cost ladder and triage (MIT, wangzhang-wu); smixs/visual-skills `fixes-and-skeletons.md` (CC BY 4.0, Serge Shima); 0xhughs/director-skills `prompt-iteration-and-diagnostics` (MIT); jacob-ye-seedance-prompt repair and QC notes (CC BY 4.0, Jacob Ye). Adapted to local open models.
