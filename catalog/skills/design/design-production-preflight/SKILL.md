---
name: design-production-preflight
description: Use when design files or a project package go to print, fabrication, procurement, installation or a vendor - artwork size, DPI/PPI, colour mode, bleed, safe areas, fonts, links, PDF/image preflight, sheet limits, mounts, loads, DFM, bill of materials or production approval. Returns PASS, PASS WITH CONDITIONS or BLOCKED with the next responsible role. Not for creating or editing the artwork itself (illustrator-production, photoshop-production) and never a substitute for vendor or engineer sign-off.
---

# Design Production Preflight

Vendor and engineer confirmation is authoritative. Reusable rules here are defaults, not promises about a specific machine, material, fire certificate, suspension point or load.

## Inputs

- The active project file, the referenced vendor profile, the relevant production notes and project-specific rules.
- The package to check: raster and vector artwork, PDFs, drawings, bill of materials, estimate.
- Output purpose, final physical size, scale, viewing distance, material, finishing, quantity and deadline.

Mark unknown values `TBD`. Never fill them from another project.

For printed artwork read `references/print-production.md` (resolution, viewing distance, bleed, seams, colour, packaging, vendor handoff).

## Workflow

1. Confirm the output purpose, final physical size, scale, bleed, safe area, viewing distance, material, finishing, quantity and deadline.
2. Check every raster file against its final placed size:

   ```bash
   python scripts/preflight_print.py --input art.tif --width-mm 3000 --height-mm 2000 --target-ppi 100 --output art.preflight.json
   ```

   It reports pixel size, effective PPI at final size, aspect mismatch and a status. It writes the JSON report first, then exits `1` on `BLOCKED` and `0` on `PASS` / `PASS_WITH_CONDITIONS`. The target PPI is a project setting (depends on viewing distance), not a universal truth. Required pixels = mm / 25.4 × PPI. In a 1:10 document the placed raster needs ten times the full-scale PPI.
3. Review vector and PDF files for layout: colour mode and profile, effective resolution of placed images, linked assets, fonts or outlines, overprint and transparency, spot colours, white ink and contour-cut layers, trim and bleed boxes, naming and versioning.
4. Check fabrication: panelization, stock sheet and print-width limits, seams, grain and direction, edge finishing, mounts, bases, access, transport, installation sequence, fire and evacuation constraints, maintenance.
5. Reconcile the package with the estimate and rate card. Flag missing rates, quantities, waste, setup, delivery, installation and reserve.
6. Keep visual approval, DFM approval, engineering approval and production approval separate. One never implies another.

Inspection never overwrites source artwork. The script's tests run with `python -m unittest test_preflight_print` from `scripts/` (needs Pillow).

## Gotchas

- A zero exit code is not production approval; read the conditions in the report.
- Keep logos, type, flat shapes and repeating patterns vector; fine high-contrast detail exposes low resolution sooner than soft atmosphere.
- Do not replace a missing printer specification with a confident guess. Label assumptions in the report.
- Loads, suspension, fire ratings and structural details need a named engineer or vendor, never an AI estimate.

## Result format

```
VERDICT: PASS | PASS WITH CONDITIONS | BLOCKED
Blocking issues: ...
Warnings: ...
Verified facts: ... (with file and evidence)
Unresolved TBD: ...
Next responsible role: ...
```

## Acceptance checklist

- [ ] Every raster checked at final placed size; JSON reports saved next to the package.
- [ ] Vector/PDF checks done on the exported files, not only the working documents.
- [ ] Fabrication constraints and estimate reconciliation covered or explicitly out of scope.
- [ ] Each approval type stated separately; vendor/engineer items have an owner.

## Boundaries

- Fixing artwork goes back to `illustrator-production`, `photoshop-production` or `design-graphic-compositor`.
- Dimensional solids and drawings go to `cad-production`.
- This skill never gives engineering, fire or load approval.
