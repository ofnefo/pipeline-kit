---
name: graphic-production
description: Use when composing layered raster graphics, inspecting assets, making contact sheets or checking physical print dimensions with Pipeline Kit.
---

# Raster composition and preflight

Resolve the project and read its brief. Establish audience, use, pixel or physical dimensions, colour requirements, supplied brand references and acceptance before production. Inspect source assets with `modules/design/scripts/inspect_assets.py --help`; keep originals and licence notes. Choose a representative sample before making a set.

Use a JSON layer spec and `compose_layers.py --spec <spec> --output <new.png> --proof <proof.png>`. Paths in a spec resolve relative to the spec; choose fonts explicitly. `examples/composition.json` is an executable shape example. The compositor supports images, text, shapes, lines and gradients; it is not a substitute for an editable vector/Adobe master when that is required.

Compare the result with the supplied references. Inspect readable hierarchy, alignment, crop, contrast and margins at delivery size. Produce a contact sheet for a set. Run `preflight_print.py` using explicit target physical dimensions/PPI and inspect the exit code/report; do not relax thresholds to get PASS. A proof overlay is review evidence, not a production export.

Acceptance: output size and content match the approved sample, production and proof files are distinct, assets are traceable, and technical print checks plus visual review are recorded. Do not generate images or launch external editors without an explicitly chosen provider/resource route.
