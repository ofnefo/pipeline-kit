---
name: illustrator-production
description: Use when production vector artwork must be built or revised in Adobe Illustrator - layouts, signage, banners, packaging, artboards, dielines, print masters, SVG or PDF export - and exact paths, typography, logos, dimensions, layers, bleed or separations matter. Treats Illustrator as the deterministic master and verifies every structural pass visually. Not for raster retouching (photoshop-production) or final production sign-off (design-production-preflight).
---

# Illustrator Production

Treat Illustrator as the deterministic master for vector geometry, official marks, exact copy and print contours. Generated imagery may feed a layout; it never replaces a supplied logo, exact text, QR code or cutting contour.

## Inputs

- The active project file (for example `PROJECT.yaml`) and the project rules that constrain this layout.
- The exact source file or asset manifest, the current approval record and the output dimensions.
- Official copy and marks as supplied files, not retyped or redrawn.
- Vendor requirements when the output is printed or cut (profile, bleed, spot names, contour layer names).

Load only what this layout needs. Do not read every brand or production document by default.

## Choose the operation

| Task | Read |
|---|---|
| Composition, series, artboards, layers, exact copy | `references/layout-and-artboards.md` |
| Path repair, tracing, compound paths, clipping masks, SVG cleanup | `references/vector-cleanup.md` |
| CMYK, bleed, spot colours, dielines, PDF/SVG export, vendor handoff | `references/print-and-export.md` |
| MCP, ExtendScript or GUI execution choice | `references/tool-routing.md` |

## Workflow

1. Inspect the document before editing: units, artboards, colour mode, layers, swatches, linked assets, fonts and the current selection.
2. Save a new version before broad structural changes. Never overwrite an approved master silently.
3. Build the shared grid, spacing, logo zone and type hierarchy before duplicating artboards.
4. Place official logos and exact copy from the supplied assets. Do not redraw, generate, stretch or casually recolour marks.
5. Name layers and objects so changes can be audited and repeated. Keep technical contours (cut, crease, white ink, varnish) on their own named layers, separate from artwork.
6. Keep live text until the handoff policy requires outlines. When outlines are delivered, keep an editable text master too.
7. After every structural pass, take a canvas screenshot or export a preview and look at it. A successful script call or correct coordinates are not evidence of a good composition.
8. Export the requested formats and inspect the exported files independently (bounds, separations, fonts, trim and bleed boxes).

## Automation boundary

Prefer typed MCP operations when a trusted bridge is installed. Use arbitrary ExtendScript only for an operation the bridge lacks, and only after naming the exact document, layers, objects and expected result. Keep the script bounded: no global deletion or flattening, save a version first, then verify visually. One automation bridge at a time is easier to audit.

## Gotchas

- Image Trace output is a reconstruction, never the original vector; compare silhouette and negative space with the source.
- Never invent a spot colour name, a kerf, a tool diameter or a production offset. Ask the vendor.
- Review a series of artboards as a strip, not one at a time.
- An Illustrator preflight result is evidence, not vendor approval.

## Acceptance checklist

- [ ] Document inspected and a new version saved before structural edits.
- [ ] Official marks and exact copy come from supplied files and match them.
- [ ] Layers and artboards are named; technical contours sit on dedicated layers.
- [ ] A preview or screenshot was inspected after each structural pass.
- [ ] Exports were reopened and checked against size, bleed, fonts, links, profile and separations.
- [ ] Open vendor questions are listed, not guessed.

## Deliver

Return the editable AI master, the requested PDF/SVG/EPS exports, a raster proof and a short note covering fonts, links, profiles, spots, overprint, bleed, contours and unresolved vendor requirements.

## Boundaries

- Raster masks, retouching and photo integration go to `photoshop-production`.
- Final production checks go to `design-production-preflight`.
- Choosing a visual direction goes to `design-style-director`.
