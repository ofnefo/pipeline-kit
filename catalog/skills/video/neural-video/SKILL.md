---
name: neural-video
description: Use when a frame must be animated or a video generated, regenerated or repaired with local open models ("оживи кадр", "сгенерь видео", "переход между кадрами", "почини стык", "апскейл", "интерполяция", "липсинк", "убери логотип"). Runs local ComfyUI video graphs (Wan 2.2 I2V/FLF, VACE, LTX-2.5, MiniMax H3, SVI, Wan Animate, InfiniteTalk, Uni3C), segment repair, SeedVR2/RIFE, masks and depth with pilot-first QC. Not for cuts/captions/mix (editing) or ComfyUI node debugging.
---

# Neural video

Purpose: get a usable shot (or a repaired span of a shot) out of local open video models with the fewest GPU runs, and
prove it with a receipt and a filmstrip, not with a claim.

Order of work: curator brief -> keyframes/references (any still-image tool you are licensed to use) -> local chains of
small models -> review. Pay-per-use cloud only when the operator asked for cloud for this specific job.

## Inputs

- Shot id, its function in the edit, duration, aspect/delivery size.
- Start keyframe (and end keyframe for FLF), or a source clip for v2v/inpaint/repair.
- What is **locked** (identity, camera, action) and what **may change** (atmosphere, surface).
- The project's continuity notes (identity string, palette, light) if it has more than one shot.

## Process

1. **Brief** - write the shot as: function, duration, inputs, locked vs may-change. Treat camera/lens words from the
   client ("35mm", "как в кино", "handheld") as *intent*: translate them into one plain camera verb plus framing (see
   video-direction `camera-moves.md`) and show the 1-3 resulting prompt lines before rendering.
2. **Reference** - pick the comparison before rendering: an approved earlier clip, the keyframe pair itself, or 1-2
   named real shots. Write down 3-5 rejection signals for this shot (e.g. identity drift, topology morph, unmotivated
   orbit, frozen background).
3. **Pilot** - validate the graph and inputs first (no GPU), then one short draft: 832x480 (or 480x832 vertical),
   3-4 seeds, everything else fixed.
4. **Self-critique** - filmstrip/contact sheet of every candidate against the reference and the acceptance list.
5. **Fix** - change one variable per retry (prompt, seed, end frame, control). Diagnose with
   [failure-diagnosis.md](references/failure-diagnosis.md) before spending another run.
6. **Verify with a receipt** - run receipt (inputs + hashes, graph, model files, prompt/negative, seed, size, frames,
   fps, steps/CFG, output path + hash), frame-count/fps probe, filmstrip path. The verdict stays `review-required`
   until a human watched it.

## Routes

| Need | Route |
|---|---|
| Bad frames, seam, drift, morph or flicker inside an edit | [segment-repair.md](references/segment-repair.md) - read first |
| One keyframe -> shot | Wan 2.2 I2V 14B, MiniMax H3 I2V, LTX-2.5 I2V |
| Keyframe pair -> shot / bridge | Wan 2.2 FLF (first-last frame), H3 FLF (optionally a depth video as control), LTX-2.5 FLF |
| Last frame only, or text only | H3 / LTX-2.5 last-frame and T2V modes |
| Restyle keeping motion / regenerate a region | Wan VACE v2v (depth/pose control) / VACE inpaint (mask WHITE = replace, BLACK = keep) |
| Camera must follow geometry | Wan 2.1 Uni3C (camera from a render video of a blockout or point-cloud warp) or Wan 2.2 Fun Camera (preset poses; slow, ~19 min per 5 s on a 16 GB card) |
| Long take | SVI latent continuation (identity stable, motion weak) instead of repeated last-frame hops |
| Motion transfer / talking head | Wan Animate (the drive video **needs an audio track**; add silence) / InfiniteTalk, H3 Ref2VA (ref image + ref audio) |
| Upscale / restore | SeedVR2 (does **not** mux audio: remux the source audio after), fast 2x ESRGAN (may flicker) |
| Masks, depth, interpolation | SAM-family tracker / BiRefNet, Depth Anything v2, RIFE or GIMM-VFI |
| Lip-sync existing footage | LatentSync, or InfiniteTalk on the whole shot |
| Logo / watermark | detect, then FFmpeg `delogo`/crop, or tracked mask + VACE inpaint |
| Prompt shape, motion budget, take length | [prompt-structure.md](references/prompt-structure.md), then [wan22-local-prompting.md](references/wan22-local-prompting.md) |
| Shot list, blockout passes, keyframe plan | `video-direction` |
| Cloud video (paid) | only on explicit request: [cloud-video.md](references/cloud-video.md) |

Modes, frame rules, graph facts and post-processing: [workflows.md](references/workflows.md).

## Hard numbers

- Frame counts: Wan/VACE/Uni3C/SVI/Animate `4n+1` @16 fps; LTX-2.5 `8n+1` @24; H3 `17n+5` @24; InfiniteTalk `4n+1` @25
  (conform the audio copy to `length/25` s). Conform a **copy** of the candidate, never the master.
- Keyframes: sides multiples of 16, each side <= 1280, area <= 921,600 px. Crop or pad to the target aspect first;
  never let the graph stretch.
- Wan 2.2 A14B I2V/FLF with the lightx2v 4-step LoRA: fp8 high/low-noise experts, three `KSamplerAdvanced` passes over
  8 steps (0-2-4-8), `shift=8`. Only the first sampler uses CFG (`cfg_high` ~3.5); the others run CFG 1, so **the
  negative prompt acts only in the first `split_a` steps**. Fix motion with the prompt, end frame or control, not with
  a longer negative.
- Measured on a 16 GB card: Wan FLF 832x480, 49 frames = ~166 s, ~14.3 GB peak (~3.4 s/frame plus model load).
  81 frames or native 1280x720 is a separate pilot that records time and VRAM. Default: 832x480 draft -> SeedVR2 for
  finals.

## Run (generic ComfyUI)

1. Export the graph in API format (`*.api.json`). Keep a small params map of which node inputs are settable (prompt,
   negative, seed, width, height, length, cfg, images).
2. Validate: load the JSON, patch the inputs, check that every referenced model file and input image exists, check the
   frame rule and size rule. No GPU yet.
3. Snapshot GPU/RAM and running jobs, then **take the GPU lock** (one heavy GPU job at a time; never stop another
   owner's job).
4. Upload inputs to ComfyUI (`POST /upload/image`), queue (`POST /prompt`), poll `/history/<prompt_id>`, copy outputs
   into a new versioned folder; never overwrite. Free models after the job (`POST /free`).
5. Release the lock; write the run receipt.

Chains that worked:
- Keyframe pair -> Wan FLF or H3 FLF(+depth) -> SeedVR2 upscale -> remux source audio (if any) -> RIFE 16->24 fps
  (x3 for 48 fps) -> edit.
- Text-only camera moves are the weakest: drive the camera with geometry (Uni3C, blockout depth, H3 FLF depth).

## Acceptance checklist (every clip, before "ready for review")

1. Probe matches the request: frame count = `length`, fps, size, audio present or absent as intended.
2. Frame 0 matches the start keyframe (identity, framing); an FLF end matches the end keyframe without a pop in the
   last frames.
3. No end-of-clip decay: the last 8-12 frames keep detail, colour and identity (filmstrip of the tail).
4. Anatomy and mechanics hold: hands, limbs, faces, wheels, text and logos do not melt, multiply or rotate wrongly.
5. Motion is plausible: the subject moves, the background is neither frozen nor boiling, the camera does what the
   prompt said, and no unmotivated orbit or second move appeared.
6. None of the shot's rejection signals is visible.
7. Side by side with the reference the candidate is at least as readable and serves the shot function; otherwise it is
   a failed take with a reason (failure code).
8. Receipt chain complete: run receipt, filmstrip path, chosen seed and rejected seeds with reasons.

## Anti-patterns

- Describing the keyframe in an I2V prompt instead of motion and camera; piling cinematic adjectives.
- Two camera moves in one Wan prompt (does not work); lens/film-stock brands, "anamorphic" or "grain" words in Wan
  prompts (no measurable effect).
- Rendering a batch before one pilot passed review; changing seed, prompt and size in the same retry.
- Fighting artefacts with longer negatives; covering flicker with grain or blur.
- Calling a mode "verified" without a GPU run receipt for it.
- Downloading extra weights, starting a parallel GPU stack, or going to cloud because "local is busy".

## Finish

Report: route and mode, inputs (hashes), run receipt paths, filmstrip paths, checklist result per item, verdict
(`review-required` until a human watched it), next smallest step. Keep failed outputs with their reason until the
decision is recorded. Never claim a render without a receipt path.

## Boundaries

Generation and repair only. Cutting, captions and mixing belong to editing; shot planning to `video-direction`;
titles to `motion-graphics`; ComfyUI installation and node errors to a ComfyUI debugging skill.

Idea sources and credits: [NOTICE.md](NOTICE.md).
