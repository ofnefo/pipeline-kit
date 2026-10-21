# Large-format print production

## Contents

1. Production brief
2. Scale and resolution
3. Color and transparency
4. Bleed, seams, and safe areas
5. PDF/export
6. Packaging and final QA

## 1. Production brief

Obtain from the fabricator whenever possible:

- final physical size and permitted document scale;
- bleed, wrap, pocket, hem, or welding allowance;
- seam/panel map and hardware locations;
- preferred PDF standard and compatibility;
- required color space and ICC profile;
- minimum effective PPI by material/viewing distance;
- spot-color, rich-black, ink-limit, and overprint rules;
- naming and packaging requirements.

Do not replace a missing printer specification with confident guesses. Keep assumptions labeled in the preflight report.

## 2. Scale and resolution

Use:

`required pixels = physical inches × target PPI`

At 1:10 scale, placed raster effective PPI in the scaled document must be ten times the intended full-scale PPI. Verify the application reports effective rather than original PPI.

Keep logos, type, flat shapes, and repeating patterns vector. For raster layers, judge resolution together with viewing distance and content frequency. Fine linework and high-contrast detail reveal low resolution sooner than soft atmosphere.

Run `scripts/preflight_print.py` for single raster files, but treat its threshold as a project setting rather than universal truth. The CLI writes its JSON report before returning exit code `1` for `BLOCKED`; `PASS` and `PASS_WITH_CONDITIONS` return `0`. A zero exit code is not production approval; review the report conditions.

## 3. Color and transparency

- Work in a documented color-managed space.
- Convert with the printer profile, not an arbitrary generic CMYK profile.
- Verify brand spot/process values against the brandbook and printer workflow.
- Inspect large gradients for banding at realistic proof depth.
- Check rich black, small black type, gray balance, and total ink according to printer guidance.
- Preserve live transparency when the requested PDF workflow supports it; otherwise flatten using the fabricator's settings and inspect seams/edges.

Generic PNG/Pillow scripts do not provide reliable CMYK/spot/overprint preflight. Perform those checks in Illustrator, Acrobat, or the RIP-aware production application.

## 4. Bleed, seams, and safe areas

Distinguish:

- trim/final visible size;
- bleed or wrap outside trim;
- structural seam overlap;
- content safe area inside trim;
- obstruction zone caused by furniture, floor proximity, or installation hardware.

Do not place logos, QR codes, faces, small type, or critical vertical edges on seams. Continue non-critical backgrounds and patterns through bleed/wrap according to fabrication instructions.

## 5. PDF/export

Prefer the printer's requested preset. When none is supplied, preserve vectors and embedded profiles, avoid unnecessary downsampling, and choose a modern print PDF workflow only after confirming compatibility.

Before delivery verify:

- page/artboard physical size and scale;
- trim and bleed boxes;
- fonts embedded or outlined according to policy;
- linked images present and sufficient effective PPI;
- spot/process colors and overprints intentional;
- no hidden annotations, guides, proof overlays, or accidental white backgrounds;
- transparency and gradients render identically in an independent PDF viewer;
- no rasterized logo or tiny text unless explicitly intended.

## 6. Packaging and final QA

Package:

- editable master;
- linked images and approved logos;
- font files when licensing permits, otherwise documented font names/outlined delivery copy;
- printer PDF;
- RGB JPEG/PNG approval proof;
- series overview and seam map when relevant;
- assumptions/preflight note.

Open the exported delivery file independently. Compare it with the approved proof and inspect the most failure-prone areas at high zoom: seams, transparency, gradients, masks, small type, and logo edges.
