# Reference matching and multi-view validation

Use this procedure when matching an approved scene, reconstructing from images, or propagating one visual system across multiple Blender scenes.

## Lock the baseline

1. Save a new `.blend` version and record the source hash.
2. Identify protected geometry, cameras, materials, and output settings.
3. Capture the approved view plus at least one diagnostic view before edits.
4. Record a geometry fingerprint: object names/types, mesh vertex and polygon totals, transforms, and visible bounds.

## Match in controlled passes

Work in this order and change one major variable family per pass:

1. Camera lens, projection, crop, horizon, and target.
2. Object scale, placement, silhouette, and negative space.
3. World/background and exposure baseline.
4. Material values and texture scale.
5. Practical/emissive sources, then key/fill/rim.
6. Color management and final contrast.

For image matching, compare bounding box, centroid, silhouette, landmarks, and crop. Use overlays or difference views when possible. If two references demand incompatible geometry or camera assumptions, stop at a contradiction gate and report the conflict instead of averaging it away.

## Scene-family propagation

An approved render preset contains:

- engine, sampling, denoising, bounces, output format, and resolution;
- display device, view transform, look, exposure, gamma, and curve mapping;
- world nodes and background strength;
- camera-role policy and lens metadata;
- light roles, relative placement, shape, size, power, and collection naming.

Copy absolute settings only where scale-independent. Scale positions, sizes, and energy intentionally from each scene's visible bounds, then inspect every client frame. Keep the template scene unchanged unless the user explicitly asks to improve it.

## Evidence and verdict

Render a consistent client-view set and any necessary service/detail views. Log missing files, GPU/CPU fallback, and scene-specific deviations. Recompute the geometry fingerprint after edits. A render-system task is complete only when the protected geometry still matches and every requested scene has an active camera, valid world, active lights, and a review image.
