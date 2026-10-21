# Retouching and compositing

For a locked render, keep the approved source as the bottom immutable layer. Put every allowed change above it and limit each change with an explicit mask.

Integrate sources in this order:

1. crop, subject scale, perspective, camera height, and horizon;
2. light direction, contact, shadow softness, and reflections;
3. black/white points, local contrast, color temperature, and saturation;
4. edge sharpness, depth blur, grain, atmospheric depth, and material response.

Do not use glow as a generic edge fix. Do not paint over official text, existing people, equipment, openings, or structural edges. If a requested correction changes camera, geometry, object placement, silhouette, or service clearance, return it to `$blender-production` or `$cad-production` instead of faking it in pixels.

When combining AI variants, transfer only approved regions onto the original. If repeated generation drifts, stop regenerating and complete a deterministic masked composite.
