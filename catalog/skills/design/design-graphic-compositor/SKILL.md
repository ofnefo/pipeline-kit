---
name: design-graphic-compositor
description: Use when branded raster or print graphics must be planned or assembled from logos, typography, patterns, photos, renders and cutouts - banners, key visuals, wide-format graphics, brandbook analysis, asset inspection, contact sheets, transparent cutouts, deterministic layer assembly or composition review. Uses Pillow scripts for inventory, contact sheets and reproducible JSON-spec layer composites. Not for exact vector masters (illustrator-production), non-destructive retouching (photoshop-production) or choosing a direction (design-style-director).
---

# Design Graphic Compositor

Build project graphics from approved assets and rules. Read the active project file and its rules; never invent a client identity or import another project's palette.

## Inputs

- Brandbook and project rules: logo variants, clear space, colours, typography, prohibited treatments.
- Exact copy, output size, bleed, safe areas and viewing distance.
- Source assets: logos, fonts, photos, renders, cutouts, patterns, icons.

## Asset sourcing

- Fonts: check the studio's existing font library (with Cyrillic or other script coverage and preview sheets) before downloading anything.
- Icons: prefer the project's existing icon family; otherwise pick one coherent open set (for example Lucide or Iconify). Use a dedicated brand-logo source for third-party logos and keep them unmodified.
- Store selected assets and their provenance (source, licence) inside the project.
- Generative tools may supply non-authoritative imagery only; access to a model is not a tested automation route.

## Workflow

1. Inventory the inputs:

   ```bash
   python scripts/inspect_assets.py <files or folders> --recursive --output assets.json --relative-to <project root>
   python scripts/make_contact_sheet.py <folder> --recursive --output contact.png [--checkerboard] [--columns 6]
   ```

   `--relative-to` keeps paths in the report portable when the workspace moves. `--checkerboard` shows transparency.
2. Read the brandbook and record the brand constraints listed under Inputs.
3. Define hierarchy before decoration: focal element, text blocks, supporting imagery, calm field, alignment grid, cropping behaviour.
4. Use deterministic composition for final logos, QR codes, legal text, maps and exact typography. AI may generate supporting imagery, never authoritative marks or final copy.
5. Assemble reproducible variants from a JSON layer spec (canvas, gradient, rectangle, image, text layers; schema and example in `references/layer-spec.md`):

   ```bash
   python scripts/compose_layers.py --spec layout.json --output out.png --proof proof.png --thumbnail thumb.png --grayscale-proof gray.png
   ```

   Keep source, intermediate and output files in separate folders. Outputs are not overwritten without `--overwrite`.
6. Review at full view, at the intended viewing distance (thumbnail), in greyscale and at 100% crop. Confirm contrast, edges, masks, spelling, dimensions and project restrictions.

## References

Read only what the task needs: `brandbook-workflow.md` (documenting vs proposing an identity), `layout-principles.md`, `image-workflow.md` (choosing the image method), `layer-spec.md`, `banner-composition.md`.

## Gotchas

- A flat PNG or a recipe is not an editable PSD master; never label it as one.
- Distinguish documenting an approved identity from proposing a new one, and conceptual merch mockups from exact product artwork.
- Do not install another background-removal stack when an approved route (Photoshop, a local ComfyUI cutout) already works.
- Do not hard-code interpreter, workspace or user paths in specs; use project-relative paths.

## Acceptance checklist

- [ ] Asset inventory and provenance recorded.
- [ ] Logos, QR and exact copy placed from source files, not generated.
- [ ] Proof, thumbnail and greyscale proof reviewed; 100% crops checked.
- [ ] Output dimensions, bleed and safe areas match the brief.
- [ ] Unresolved font, logo, colour-profile, scale or rights issues listed.

## Deliver

The composition, an editable or layered source when requested, a preview and a short production note.

## Boundaries

- Non-destructive masks, retouching and locked-pixel merges go to `photoshop-production`.
- Exact vector masters, artboards, signage and PDF/SVG export go to `illustrator-production`.
- Print-bound outputs go to `design-production-preflight`.
