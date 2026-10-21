# Print and export

Before print export confirm final size/scale, bleed or wrap, safe area, seams, substrate, finishing, color mode/profile, ink limit, spot colors, overprint, transparency handling, fonts, links, and required PDF standard.

Keep technical colors and layers explicit: cut, crease, white ink, varnish, registration, and notes must use vendor-approved names and values. Never invent a spot name or production offset.

For SVG, define the intended consumer. Preserve viewBox, dimensions, groups, IDs, fills/strokes, and live text only when fonts are guaranteed; otherwise provide a documented outlined copy plus an editable source. For PDF, inspect the exported file independently and compare artboard bounds, separations, transparency, fonts, images, and trim/bleed boxes.

An Illustrator preflight result is evidence, not vendor approval. Use `$design-production-preflight` for the final package.
