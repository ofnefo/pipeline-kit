---
name: comfy-motion-recipes
description: Use when the operator shows a trending AI-video reference reel and wants the same technique ("хочу так же", "как в этом ролике", "HUD-разметка", "морф", "глитч", "шторка до/после"): HUD tracking labels and cursors, 3D-scan island orbits, morph chains, style before/after wipes, datamosh/CRT/dither glitch, strip transitions, fake 2000s game cutscenes, kinetic captions. Maps each technique to a local ComfyUI chain plus After Effects, Blender or TouchDesigner finishing. Not for single-shot generation (neural-video) or editing.
---

# Comfy motion recipes: reference techniques -> local chains

Purpose: break a viral reference reel into layers (generation, 3D, tracking, overlay, captions) and rebuild each
layer with local open models and standard finishing tools.

Generation runs locally: run ComfyUI workflows, take the GPU lock (one heavy GPU job at a time) and record a run
receipt (inputs, model, seed, output path, hash) per `neural-video`. Editing is editing work; compositing goes to
`after-effects-production`; real-time shaders to `touchdesigner-production`. Keyframe images: a curated still-image
model you are licensed to use, then local Qwen-Image / Z-Image for variations. Nothing is downloaded or installed
without the operator's go-ahead; cloud only when the operator asked for it for this job.

## Typical local toolkit (check what is actually installed)

- Video graphs: Wan 2.2 I2V 14B and first/last-frame (FLF), LTX-2.5 FLF and I2V, depth-controlled FLF, Wan 2.2 VACE
  v2v / inpaint, Wan 2.2 Fun Camera, Wan 2.1 Uni3C, Wan Animate, SVI long takes, InfiniteTalk, SeedVR2 video upscale.
- Images: Qwen-Image, Qwen-Image-Edit (with Lightning 4-step, multiple-angle and relight LoRAs), Z-Image Turbo (+
  ControlNet Union), FLUX.2 Klein, Qwen-Image-Layered (layers).
- Masks and geometry: SAM 3, BiRefNet, MoGe-2 (depth + normals), Depth Anything v2, Hunyuan3D 2.1, TRELLIS.2,
  Stable Fast 3D, UniRig.
- Frames: frame interpolation (RIFE, GIMM-VFI); upscale: SeedVR2, FlashVSR, 4x ESRGAN-family models. Sound: ACE-Step,
  Stable Audio Open, Qwen3-TTS (voice by description and clone). Lip-sync: LatentSync, InfiniteTalk.

## Recipes

| Technique | Chain | Finish | Gotcha |
|---|---|---|---|
| **HUD labels: boxes, captions, cursors** | clip from any chain -> part masks with SAM -> point tracks in AE (or Mocha) | precomp boxes parented to track nulls, small monospace labels, cursor as its own layer lagging 2-4 frames | commercial HUD packs cost money; build one reusable HUD template once and keep it in the shared asset library |
| **Morph chain** (head: normal -> cube -> melts) | first key from a curated still model; next states with Qwen-Image-Edit from it (keeps composition) or Z-Image + ControlNet -> pairs of neighbouring keys through Wan 2.2 FLF / LTX FLF -> join, smooth with GIMM-VFI | BiRefNet cut-out, HUD on top | make each key from the previous one, otherwise the face drifts |
| **"3D-scan islands" with an orbit** | key image -> MoGe-2 -> displaced mesh in Blender, torn edge = SAM mask + noise -> orbit, EEVEE -> Uni3C on that render (camera) or VACE v2v (animate the figure) | single objects: Hunyuan3D / TRELLIS.2; flying paper and debris: cell fracture in Blender | MoGe sees one side only: keep the orbit within 35-40 degrees or holes appear; this is not photogrammetry or splats |
| **Orbit without Blender** | key -> Wan 2.2 Fun Camera (`camera_pose`) or Uni3C on a zoompan render | - | slow (~19 min per 5 s on a 16 GB card); test at 480p first |
| **Style before/after wipe** (cyanotype, pixel sort, voxels, glass, 256 colours...) | one source -> Qwen-Image-Edit with a style prompt (hero frames from the curated still model) -> optionally animate 3-5 s with LTX I2V | AE: vertical wipe line + style label | there is no pixel-sort node: use a TouchDesigner shader or a small script |
| **Glitch set: datamosh, CRT, 1-bit dither, halftone, scanlines, blob tracking** | datamosh: ffmpeg with keyframes removed + AE; CRT/dither/halftone: TouchDesigner GLSL (the same GLSL works in three.js); blob tracking: TD Blob Track | - | no ready pack: build a small own set and keep it in the asset library |
| **Strip transition, subject stays on top** | subject matte with SAM / BiRefNet on every frame | NLE/AE: next shot slides in as horizontal strips under the subject; colour edge, flash, light blur-shake, film grade (LUT) | light-leak / film-burn overlays need a licensed source |
| **Fake 2000s game cutscene** | keys from a still model: "PS2-era low-poly, flat light, wooden faces, static camera, NOT photoreal"; variations with Qwen-Image-Edit / Z-Image; or a Hunyuan3D mesh in Blender with nearest-neighbour textures -> LTX I2V / Wan FLF with a static camera -> voice with local TTS -> talking via InfiniteTalk | music with ACE-Step; game-style subtitles | cloning a real actor's voice is a rights question for the operator |
| **Camera-move library** | move -> a `camera_pose` preset in Fun Camera or a Uni3C trajectory, plus a tested camera phrase from your prompt vocabulary | - | add a newly verified move to the vocabulary only with a receipt |
| **Kinetic captions** (words pop one at a time) | word timings from local STT (`video-transcription`) | AE text animators or NLE titles; in code: Remotion or canvas lower thirds (`motion-graphics`) | the font must cover the script (e.g. Cyrillic) |
| **Finish** | SeedVR2 or FlashVSR upscale; smoothness with GIMM-VFI / RIFE | - | upscale last, after the edit |

## Workflow

1. Break down the reference: which layers (generation / 3D / tracking / overlay / captions), duration, format (9:16
   for vertical social).
2. Keyframes first: show 2-4 stills to the operator for approval before any video (video is the expensive GPU step).
3. Video steps one GPU job at a time, 480p test -> final; each generation with a run receipt in
   `<PROJECT_ROOT>/60-motion/`.
4. Composite in AE or the NLE, sound, upscale. Deliver the MP4 plus the list of receipts.

## Acceptance checklist

1. Every layer of the reference is mapped to a chain or listed as a gap.
2. Keyframes approved before video runs; a receipt for every generation.
3. Final checked in motion at delivery size: seams, masks edges, morph identity, caption timing against the audio.
4. Licences of packs, overlays, fonts and voices recorded; no uncleared real-person voice clone.

## Typical gaps (decide with the operator; download nothing by default)

Commercial HUD/time-slice packs (buy or build your own template); photogrammetry / Gaussian splats; light-leak and
film-burn overlays; cloud-only image models.

## Boundaries

Technique breakdown and chaining only. Single-shot generation and repair are `neural-video`; cutting is editing work.
