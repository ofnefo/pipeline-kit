# Previz and animatic chain

Project-relative paths. One folder per stage (`00-brief`, `30-keyframes`, `60-motion`, `50-edit`); every output gets
a provenance record (path, prompt, model, seed, sha256).

| Step | Tool | Output |
|---|---|---|
| 1. Shot list | `00-brief/shotlist.md`: id, duration (local Wan/LTX/HunyuanVideo 2-5 s per take), camera move, action, first/last frame description, sound cue | text |
| 2. Blockout | Blender: cubes and proxies, one camera per shot (`CAM_sh010`), frame range = shot timing, 24 fps; headless `blender -b -P make_blockout.py` or a Blender MCP bridge. Save `00-brief/previz/<shot>.blend` | .blend |
| 3. Passes | headless render script, e.g. `blender -b <shot>.blend -P render_passes.py -- --camera CAM_sh010 --passes beauty,depth,normal,line [--only-ends] [--engine eevee\|cycles\|workbench]` | `30-keyframes/blockout-<id>/`: `<pass>/####.png`, `<pass>.mp4`, `passes.json`, per-frame sha256 list |
| 4. Keyframes | any image model with the blockout frame as composition reference, or a local edit/ControlNet model with the depth/line pass as control | `30-keyframes/<id>/sh010-first.png`, `sh010-last.png`, provenance.json |
| 5. Video | local first/last-frame (FLF) or I2V graph (Wan 2.2, LTX, HunyuanVideo; depth.mp4 as control where supported), camera-control graph (e.g. Uni3C with the blockout render), VACE v2v | `60-motion/...` + run receipt |
| 6. Finals | best local take -> video upscaler (e.g. SeedVR2) -> frame interpolation (RIFE) -> NLE; sound from the music/sound pipeline | `60-motion`, `50-edit` |

Continuous shots: the accepted last frame of shot N is the first frame of shot N+1. Cloud video only when the
operator asked for it for this job (see neural-video `references/cloud-video.md`).

## Blockout rules

- Metres, real lens (focal length and sensor go into `passes.json`), one named camera per shot. Proxies carry composition,
  scale, depth order and motion, not look.
- `--only-ends` renders first and last frame only: the pair used as keyframe composition references and for FLF.
- Depth: linear view-Z normalised per shot (near = white), fixed near/far over the range, 16-bit PNG. Normal: camera-space
  OpenGL. Line: Freestyle black on white.
- EEVEE/Workbench blockouts are light (24 frames x 4 passes at 640x360 took ~14 s) and need no GPU lock. Take the GPU
  lock (one heavy GPU job at a time) for long Cycles GPU or high-resolution renders. Never save or change the source
  .blend from the render script.

## Keyframes from the blockout

1. Give the image model the blockout first frame (`30-keyframes/blockout-<id>/beauty/0001.png`, add `line/0001.png`
   when edges matter) and one style reference.
2. First frame prompt, e.g.: "Edit/reference: image 1 is a 3D blockout - keep its camera, horizon, perspective, object
   placement and scale exactly; only replace grey proxies with <materials, set, time of day, light, lens look>. Image 2 is
   the style reference (palette, grain, contrast). 16:9, 1536x864. No text, logos or watermarks. Do not add or move objects."
3. Last frame: composition from the blockout last frame, look from the first generated keyframe ("same lighting, materials
   and colour as the previous image"). Generate the pair back to back.
4. Sizes in multiples of 16 (1280x720, 1536x864).
5. Record provenance per image: path, prompt (and any revised prompt the tool reports), model, time, sha256, size.
6. Check composition drift against the blockout (contact sheet or a 50% overlay) before any video run.
