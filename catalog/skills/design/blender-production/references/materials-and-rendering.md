# Materials, cameras, lighting, and renders

Separate geometry validation from look development. Use clay and seam-visible states before presentation materials.

## Camera contract

Camera metadata must include lens/focal length, sensor or projection mode, height, target, output ratio, and crop. Lock camera only after composition review. Avoid extreme wide angles that conceal spatial problems. Before every render, assert that the scene has an active camera and that it belongs to the intended role (`CLIENT`, `SERVICE`, `DETAIL`, or `ORTHO`). Preserve an approved camera instead of regenerating it from a bounding box.

For a new camera, derive distance and target from the visible-geometry bounding box, then inspect the actual frame. A bounding-box fit is a starting point, not approval.

## Material contract

Materials should communicate actual families through roughness, reflectance, thickness, edge response, transparency, and scale—not only color. Keep unapproved special finishes provisional.

- Reuse named master materials instead of creating per-object duplicates.
- Use physically plausible PBR ranges and verify texel/feature scale against model units.
- Test materials under both a neutral diagnostic rig and the target presentation rig.
- Record missing textures and packed/external dependency status before handoff.

## Lighting and look propagation

Give each light one job: practical, key, fill, rim, environment, or diagnostic. Prefer area lights for spatial/product scenes. Keep lights in a dedicated named collection and preserve the approved rig as a template scene or versioned preset.

When propagating one approved scene look to differently sized scenes, copy render engine, samples, denoising, color management, world, output format, and camera policy exactly, but normalize light positions and sizes to each scene's visible bounding box. Do not copy absolute coordinates blindly. Preserve any intentional practical lights in the template scene and document replaced or disabled legacy lights.

Calibrate in this order: camera and crop → world/background → base materials → emission/practicals → key/fill balance → color management. Do not use lighting to conceal geometry or construction defects.

## Render quality

Use Cycles adaptive sampling and denoising for client/final states unless the project explicitly requires another engine. Render a sample test before the full set.

- Fast QA: 24–128 samples at 40–60% output.
- Typical product/spatial final: 256–1024 samples.
- Glass, deep interiors, or difficult indirect light: 1024–2048 samples after a sample test proves the need.
- Use 16-bit PNG or OpenEXR when downstream compositing needs latitude; 8-bit PNG is acceptable for review-only deliverables.

Do not change the saved final preset merely to accelerate QA. Apply draft settings in a separate render process or restore them before saving.

Maintain named render states such as `CLAY`, `SEAMS_ON`, `MEDIA_OFF`, `WORKING_LIGHT`, and `CLIENT`. A presentation render should not erase supports, service access, seams, safety elements, or unresolved geometry. Use masks/passes when downstream retouching is expected.

Finish with screenshot-backed QA: client view, profile/side view when spatial depth matters, material close-up when finish matters, and a service/construction view when production is in scope. State `SHIP`, `SHIP WITH NOTES`, or `NO-SHIP`, and separate render defects from source/model blockers.
