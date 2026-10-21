---
name: image-to-scene
description: Use when one photo or render must become a rough 3D blockout scene - separate objects, a clean background plate, per-object meshes, depth and camera, Blender assembly ("photo to 3D scene", "split this image into objects", "blockout from a reference", "clean plate"). Runs a staged local chain (object list, SAM masks, Qwen-Edit clean plate, SF3D meshes, MoGe-2 geometry, Blender assembly) with a receipt and status per stage. Not for production modelling (blender-production), parametric parts (cad-production) or photoreal relighting of a locked render (design-render-refiner).
---

# Image to Scene

Turn a single image into an editable, approximate 3D blockout: a backdrop plane with the clean plate, separate object meshes placed by depth, and a camera that matches the photo. The result is a starting point for layout and previz, not a measured model.

## Inputs

- One photo or render. Treat it as read-only: copy it into the job folder with the long edge capped at 2048 px.
- Optional: the operator's object list, target units or a known dimension for scale.
- Output folder inside the project, for example `<PROJECT_ROOT>/scenes/<job>/`, one new folder per run.

## Stages

Each stage writes its outputs plus a `stage-<name>.json` receipt (inputs, parameters, model, SHA-256 of outputs, duration, VRAM peak, status). A stage reruns only when its inputs changed; otherwise it is reused.

1. **Object list** - propose 2-6 salient, separable objects in `objects.json` (name, short prompt, rough bbox, keep/skip). The operator confirms or edits the list before any GPU stage. Skip tiny, thin or heavily occluded items.
2. **Masks** - segment each object with a text- or box-prompted segmenter (SAM 3.x class). Save one PNG mask per object and an overlay preview. Check that masks do not overlap and cover the whole object.
3. **Clean plate** - remove the confirmed objects from the photo with an instruction-edit model (Qwen-Image-Edit class) using the union mask, then verify: compare the masked areas against the original and re-run with a stricter prompt when an object survived. Record each verify pass.
4. **Object crops and meshes** - crop each object with its mask on a neutral background and run a single-image-to-3D model (SF3D class) to a GLB. Optionally complete occluded parts with an edit pass before meshing. Rotate fronts by 180 degrees around the vertical axis when the model outputs them facing away.
5. **Scene geometry** - run a monocular geometry model (MoGe-2 class) on the original to get depth, normals and the camera field of view. Use the depth at each mask centroid to place and scale objects.
6. **Sound and assets (optional)** - search the local asset library for matching ambience or props and record licences; never download automatically.
7. **Blender assembly** - build `scene.blend` with the camera from stage 5, a backdrop plane carrying the clean plate, the object GLBs placed by depth, then export `scene.glb`, render `preview.png` and write `assemble.json` (object transforms, scale source, `scale_fallback` flag when depth was unreliable).

Run GPU stages one at a time under the GPU lock; check resources before Blender and defer when the lock is held, CPU load is at or above 90% or free RAM is below 4 GB.

## Statuses

Use one status per stage and for the whole job: `ok`, `traces` (worked with visible leftovers), `partial` (some objects failed), `failed`, `verify_failed` (clean plate still shows objects), `deferred` (resources busy), `stale` (inputs changed since the run), `running`.

## Typical cost (3 objects, 800x600, 16 GB GPU)

Masks about 13 s, clean plate about 150 s with verify passes, meshes about 80 s, geometry about 7 s, Blender about 50 s.

## Gotchas

- Reflections and shadows of removed objects stay on the plate; fix them in Photoshop if they matter.
- One view only: hidden sides are invented by the mesh model. Do not present the result as measured geometry.
- Single-image-to-3D models are weak on people, hair, foliage and thin objects (chairs, railings, cables); mark them as `partial` or leave them on the plate.
- The edit model may skip an object; the verify step exists for that. Never mark the plate `ok` without it.
- Scale is relative unless a known dimension is given; record which object set the scale.

## Acceptance checklist

- [ ] Source photo untouched; working copy capped at 2048 px.
- [ ] Object list confirmed by the operator before GPU stages.
- [ ] Every stage has a receipt and a status; failures are reported, not hidden.
- [ ] Clean plate verified; leftovers reported as `traces`.
- [ ] `scene.blend`, `scene.glb`, `preview.png` and `assemble.json` exist; preview matches the photo framing.
- [ ] GPU lock released; limits stated in the handoff.

## Boundaries

- Clean modelling, materials, lighting and production renders: `blender-production`.
- Parametric or manufacturable parts: `cad-production`.
- Enhancing an approved render: `design-render-refiner`. Single image edits or cutouts: `design-comfy-generation`.
