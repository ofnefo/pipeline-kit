---
name: photoshop-production
description: Use when approved pixels must be edited non-destructively in Adobe Photoshop - background removal, masks, retouching, exact-pixel composites, colour matching, layered masters, exports - or a locked render needs deterministic overlays. Works in versioned PSD/PSB with named layers and masks and checks 100% crops on the target background. Not for vector masters (illustrator-production) or generative render enhancement (design-render-refiner).
---

# Photoshop Production

Work from the approved source, never from a flattened preview when an editable master exists.

## Inputs

- The active project file and only the project rules that constrain this asset.
- The exact source asset and the current approval record.
- Canvas dimensions, protected pixels, approved copy, official marks, colour requirements, allowed edit regions and the output purpose.

Do not load unrelated project folders or old variants.

## Choose the operation

| Task | Read |
|---|---|
| Background removal, difficult edges | `references/masking.md` |
| Retouching, multi-source integration, locked-base overlays | `references/compositing.md` |
| Delivery, profiles, transparency, print-bound raster output | `references/export-qa.md` |

## Workflow

1. Keep the original untouched. Work in a versioned PSD/PSB with named layers, masks and smart objects where practical.
2. Keep canvas size, crop, camera and protected regions unchanged unless the brief explicitly authorizes a change.
3. Put every change on its own layer above the source and limit it with an explicit mask. Prefer masks and adjustment layers over destructive erasing or baked colour corrections.
4. Never replace exact logos, text, QR codes, product geometry or approved architecture with generated approximations.
5. After each structural pass, inspect the full composition and 100% crops on the intended background. A successful command is not visual approval.
6. Export, then reopen the exported file and compare dimensions, profile, alpha, visible bounds, spelling and protected pixels.

## Local background removal script

`scripts/photoshop_remove_background.py` drives an installed Photoshop on Windows: it opens the image in a temporary document, runs Select Subject (device mode), turns the selection into a layer mask, exports a transparent PNG and closes without saving the temporary PSD.

```bash
python scripts/photoshop_remove_background.py --input photo.jpg --output cutout.png [--photoshop <path to Photoshop.exe>] [--timeout 300] [--overwrite]
```

The Photoshop path comes from `--photoshop`, the `PHOTOSHOP_EXE` environment variable, or auto-detection under Program Files. Keep the source and inspect the alpha; automation does not approve the mask.

Do not install another segmentation stack or send protected assets to an external service without the operator's authorization. A local ComfyUI cutout (see `design-comfy-generation`) is an alternative when Photoshop is not available.

## Gotchas

- Check alpha on white, black, 50% grey and the intended background: fringe colour, pinholes, missing pale regions, hair and cables, dirty RGB in transparent pixels.
- Glow is not an edge fix.
- If a correction changes camera, geometry, placement or silhouette, return it to 3D (`blender-production`, `cad-production`) instead of faking it in pixels.
- When combining AI variants, transfer only approved regions onto the original. If generation keeps drifting, stop and finish with a deterministic masked composite.
- Headless converters are fine for light jobs (convert, resize, simple layer edits); masks, retouching and approved masters stay in Photoshop.

## Acceptance checklist

- [ ] Original preserved; working file versioned with named layers and masks.
- [ ] Protected regions, crop and canvas unchanged unless authorized.
- [ ] Alpha inspected on several backgrounds at 100%.
- [ ] Exported file reopened and checked (dimensions, profile, alpha, bit depth, size limit).
- [ ] Source and output pixel dimensions recorded.

## Deliver

Return the editable master when requested, the delivery exports, a before/after proof and unresolved issues such as lost fine detail, uncertain colour profile, missing fonts or geometry drift.

## Boundaries

- Vector text, contours and master layouts go to `illustrator-production`.
- Print-bound packages go to `design-production-preflight`.
- Generative refinement of a locked render goes to `design-render-refiner`.
