---
name: video-direction
description: Use when deciding what to show and why before video is generated, or when judging versions ("раскадровка", "шот-лист", "превиз", "аниматик", "режиссура", "какой вариант лучше", "разбор версий", "референсы по свету/камере"). Writes treatments and shot lists with shot functions and rhythm, translates references into observable decisions, plans Blender blockout passes and keyframe pairs, and runs a comparative creative review. Not for running generation or repair (neural-video) or cutting and rendering (editing).
---

# Video direction

Purpose: decide what each shot is *for* before any GPU time is spent, and judge finished versions against stated
intentions instead of taste or technical novelty.

## Inputs

- The project brief (`00-brief/`): purpose, viewer, where it plays, duration, what must be understood or felt at the end.
- The project's canon: for a client, the brief and the client references; for an own project, its style bible. Never
  carry one project's aesthetic into another.
- Candidate references (works, frames, timecodes) and, for reviews, the clips with their receipts.

## Process

1. **Brief.** Purpose, viewer, where it plays, duration, end state for the viewer. Ask for anything missing in one list.
2. **Reference.** Choose 2-4 concrete works or frames (approved earlier project clips, the client's examples, film or
   animation libraries). For each, record the source and a frame or timecode, then write what you take from it in
   observable terms.
3. **Draft.** Write the treatment and the shot list (format below). Each shot must pass the direction test.
4. **Self-critique.** Check the shot list against the acceptance list and the references. Name the two weakest shots and
   say why.
5. **Fix.** Rework only those shots. Prefer cutting a shot to decorating it.
6. **Verify.** Run a blockout or animatic for timing. Review generated clips with
   [review-rubric.md](references/review-rubric.md); every verdict comes with a receipt (filmstrip or contact-sheet path,
   clip paths).

## Direction test (every shot or effect)

- What changes in the viewer's understanding or bodily state?
- What must stay readable (the action, the face, the product, the text)?
- Why are this duration and this cut position necessary?
- What does the image gain that is specific to this project? For a client, their product truth rather than a stock
  mood; for an own project, its specific contradiction rather than generic gloom.
- How does the shot relate to voice, rhythm, silence or a physical detail of the text?

Translate references into observable decisions: framing, lens and camera behaviour, blocking, duration, cut logic,
light, material, temporal artefacts, typography, relationship to sound. Never use a living artist's name as the
instruction. Camera or lens words from the client express intent: translate them into one camera verb, a lens band and
a framing line ([camera-moves.md](references/camera-moves.md)) before they become prompt text.

Useful public reference sources: Cinematique (terms), FilmGrab and similar still archives (candidate works),
Motionographer and Blender Studio (animation), type specimen sites for typography. Inspect only the works you choose;
do not adopt a site's own cloud generator.

For neural prompts, separate what is **locked** (identity, camera, action) from what **may transform** (atmosphere,
surface). Reject polish that erases vulnerability, physicality or narrative evidence.

## Shot list format

`00-brief/shotlist.md`, one row per shot:

`id · function in the sequence · duration (2-5 s per local take) · camera (one move or static) · action · first frame / last frame · sound cue · reference (source + frame/timecode) · locked / may change`

## Previz / animatic

Shot list -> Blender blockout -> passes (beauty, depth, normal, line) -> keyframe pair -> local video -> review. Full
chain, blockout rules, Blender CLI and keyframe prompts: [previz.md](references/previz.md).

More: [shot-grammar.md](references/shot-grammar.md), [camera-moves.md](references/camera-moves.md),
[continuity-bible.md](references/continuity-bible.md), [sequence-dramaturgy.md](references/sequence-dramaturgy.md).

Timing check of a clip: a 24-frame filmstrip of the span
(`ffmpeg -ss S -to E -i clip.mp4 -vf "fps=N,scale=320:-1,tile=6x4" -frames:v 1 strip.png`).

## Acceptance checklist (treatment / shot list / chosen version)

1. Every shot has a stated function, and removing any one shot would lose something named.
2. Every shot has a reference with its source and frame or timecode, translated into observable decisions (no artist's
   name used as the instruction).
3. Each shot has one camera behaviour. Durations fit the chosen model's take length, or the shot is planned as a bridge
   or a continuation.
4. Locked and transformable elements are written down for every generated shot.
5. The sequence reads with the sound off: action and key information stay legible at the planned durations.
6. The sound relationship (voice, music hit, silence) is stated for every cut that depends on it.
7. For a chosen version, the review rubric is filled in, with filmstrip paths for the beginning, the joins and the end,
   and the technical pass, creative assessment and owner decision kept separate.

## Anti-patterns

- Generic mood words ("cinematic", "epic", "moody") instead of observable choices.
- Imposing an own project's aesthetic on client work, or making client work look like stock.
- Planning a shot local models cannot hold (two camera moves, more than 5 s of continuous action, big pose changes
  between keyframes) without a bridge plan.
- Judging versions by technical novelty, or picking the most polished take over the most truthful one.
- Rating a clip without watching its beginning, joins and end, or without the reference next to it.
- Calling a clip "approved" because it passed technical checks. Approval is the operator's or client's decision.

## Finish

Deliver the treatment and shot-list paths, the reference list with sources, open questions, and the next step
(blockout, keyframes or `neural-video`). For reviews: the filled rubric, receipts, a recommended version, and the
smallest change that would make the dramatic intention more exact.

## Boundaries

Planning and judging only; generation and repair are `neural-video`, cutting and rendering are editing work.
Idea sources and credits: [NOTICE.md](NOTICE.md).
