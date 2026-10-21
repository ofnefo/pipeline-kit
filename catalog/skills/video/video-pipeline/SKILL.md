---
name: video-pipeline
description: Use when starting, continuing, diagnosing or delivering any video project, or when unsure which video skill applies ("видеопроект", "смонтируй", "ролик", "видео для клиента", "что с проектом", "сдай видео", "проверь громкость"). Entry and router for a file-based video pipeline - intake, stage gates, QC, loudness, delivery hand-off - that routes the actual work to one specialised video skill. Not for stills, music or 3D masters (use the design or music skills).
---

# Video pipeline (entry and router)

Purpose: turn any video request into a named project, a named stage and a named reference, then route the work to
the **smallest** specialised skill and verify the result before anyone calls it ready.

## Inputs

- The request: what result, by when, where it plays (social vertical, web, broadcast, screen at an event).
- The project folder `<PROJECT_ROOT>` with its manifest (`project.yaml` or similar), `00-brief/`, sources, previous
  versions and a renders log (`renders.jsonl`).
- The reference the result is judged against (approved previous version, client reference, shot list, delivery spec).

## Process (every request)

1. **Brief** - resolve the project and its stage/gate. Restate the request as *result + deadline + where it plays*.
   Never mix material between projects.
2. **Reference** - before proposing work, name what the result is judged against: the approved previous version, the
   client reference, the shot list in `00-brief/`, or the delivery spec (format, loudness preset). If there is none,
   ask once.
3. **Inspect** sources, manifests and existing outputs (`ffprobe`, contact sheets). Originals and approved masters are
   immutable; every output goes to a new versioned folder (`v001`, `v002`, ...) and one line in `renders.jsonl`.
4. **Route** to the smallest skill below and load only that one; it drafts and self-critiques.
5. **Verify** with the acceptance list, then report: stage, gate passed/failed (receipt path), blockers, next smallest
   action.

## Route

| Task | Skill |
|---|---|
| Probe, proxy, cuts, rough cut, shorts, captions burn-in, audio mix, conform | an editing skill / plain FFmpeg |
| Transcript, subtitles, word timings, URL transcript | `video-transcription` |
| Local neural generation (Wan, VACE, LTX, MiniMax H3, SVI, Wan Animate, InfiniteTalk), keyframes to video, upscale/interpolate, masks/depth, segment repair, optional cloud | `neural-video` |
| Treatment, shot functions, rhythm, references, shot list, Blender blockout/passes, creative review | `video-direction` |
| Titles, lower thirds, overlay cards, kinetic type, HyperFrames/Remotion/Lottie | `motion-graphics` |
| Ready-made ComfyUI motion looks (HUD labels, morphs, glitch, wipes, camera library) | `comfy-motion-recipes` |
| Multi-track timeline, colour, Fairlight, final NLE export | `resolve-production` |
| After Effects motion/compositing components | `after-effects-production` |
| Realtime visuals | `touchdesigner-production`, `vvvv-production` |
| Music, voice-over, SFX | music/audio skills |
| Stills, keyframe images, 3D | design/3D skills |

## Ownership of layers

- The filesystem and project manifests are the production record. Do not keep parallel project state inside an MCP
  server or a UI.
- FFmpeg is the low-level deterministic media layer (probe, cut, concat, loudness, encode).
- The NLE (DaVinci Resolve) is the canonical timeline executor.
- After Effects owns motion/VFX components and returns versioned renders.
- ComfyUI (Wan/VACE/LTX...) owns controlled neural generation and is never the only master.
- Music/audio and design/3D pipelines own their components; video imports their versioned outputs.
- Add an executor only when it contributes a distinct capability.

## QC and loudness (generic FFmpeg)

- Probe the exact file you hand over: `ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration -of json master.mp4`.
  Compare frame count, fps, size and audio presence with the target. QC findings are review candidates; QC never
  approves a master by itself.
- Loudness presets: **social -14 LUFS integrated / -1 dBTP**, **broadcast -23 LUFS** (EBU R128, true peak -1 dBTP).
- Measure: `ffmpeg -i master.mp4 -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null -`.
- Fix with **two-pass** loudnorm: feed the measured `input_i/input_tp/input_lra/input_thresh/target_offset` into the
  second pass (`loudnorm=I=-14:TP=-1:LRA=11:measured_I=...:linear=true`), copy the video stream (`-c:v copy`), then
  re-measure.
- Before calling anything done, watch the result (or a dense filmstrip of each join) and keep the receipt path.

## Always

- One heavy GPU job at a time: take the project's GPU lock before any neural render and release it after; snapshot
  GPU/RAM first.
- Local-first. Pay-per-use cloud video only when the operator explicitly asked for cloud for that job, with a cost
  estimate first and a receipt. No hidden fallback, no automatic retries.
- Record a run receipt for every render: inputs, model/graph, seed, output path, file hash.
- Delivery happens through your delivery channel only after the operator asks for it; a queued message is not proof of
  delivery and is never re-sent automatically.

## Acceptance checklist (before "ready" / delivery)

1. Project and stage named; output in a new versioned folder and appended to `renders.jsonl`.
2. QC run on the exact file being handed over (expected frames, audio present, loudness preset as the target needs);
   receipt path recorded.
3. Watched against the reference: beginning, every join and the ending (or a dense filmstrip of each seam).
4. No repeated footage, accidental speed change, gibberish speech/captions or unrelated overlays.
5. Sources, approved masters and other projects untouched.
6. Technical pass, creative assessment and the operator's decision reported separately; the agent never calls
   anything "approved".
7. Delivery only on the operator's request, with its own receipt (message id or upload id).

## Anti-patterns

- Loading every video skill "to be safe" instead of routing to one.
- Starting generation or cutting before the reference/target is named.
- Treating a passing QC as approval; re-running an unchanged expensive render to "double-check".
- Writing outputs into the pipeline/tool folder or over a previous version.

## Boundaries

Router and gatekeeper only: the actual cutting, generation, grading and motion work is done by the routed skill.
