# Brandbook and asset workflow

## Contents

1. Evidence-first extraction
2. Brand manifest
3. Asset hierarchy
4. Pattern and imagery interpretation
5. Conflict handling
6. Brand QA

## 1. Evidence-first extraction

Treat the brandbook as a specification, not a mood board.

1. Preserve the original PDF and note its version/date.
2. Render page thumbnails to locate identity, palette, typography, pattern, imagery, layout, and forbidden-use sections.
3. Re-open relevant pages at high resolution before recording a rule. Do not infer small color values or clearspace from thumbnails.
4. Extract original embedded/vector assets when possible. Do not use a raster screenshot of a logo when an AI/EPS/SVG/PDF asset exists.
5. Record the page number or source filename behind every consequential rule.

Use the PDF skill or Poppler for inspection and rendering. Use Acrobat/Illustrator for embedded vector artwork and separations when required.

## 2. Brand manifest

Create a compact project manifest before composition:

```yaml
brand:
  source: brandbook.pdf
  version: "date or revision"
logos:
  primary: assets/logo-primary.svg
  reversed: assets/logo-white.svg
  minimum_size: "from page N"
  clearspace: "from page N"
palette:
  primary:
    - {name: brand-blue, hex: "#...", cmyk: "...", source_page: N}
type:
  display: {family: "...", weights: ["..."], source_page: N}
  text: {family: "...", weights: ["..."], source_page: N}
patterns:
  allowed: ["..."]
  restrictions: ["..."]
imagery:
  traits: ["..."]
forbidden:
  - "..."
open_questions:
  - "printer profile not supplied"
```

Do not invent missing CMYK values, clearspace, font weights, or co-branding rules. Flag them as open questions and use a reversible working assumption only when work can safely continue.

## 3. Asset hierarchy

Prefer sources in this order:

1. Approved project-native vector asset.
2. Approved brandbook package/export.
3. Exact supplied high-resolution raster.
4. Faithful local reconstruction of simple geometry only when authorized and verified.
5. Generated material only for non-official decorative imagery.

Classify files as `official`, `approved supporting`, `generated`, `reference-only`, or `unverified`. Keep the classes separate in the layer structure.

## 4. Pattern and imagery interpretation

Distinguish a repeatable pattern from a one-off key visual. Record:

- tile or placement behavior;
- allowed rotation, cropping, scale, and density;
- foreground/background color combinations;
- interaction with logos and copy;
- whether the motif can cross trim or seams;
- whether it is decorative or carries meaning/direction.

For imagery, extract operational traits rather than vague adjectives: subject scale, camera height, contrast, background complexity, color temperature, edge softness, grain, material palette, and human presence.

## 5. Conflict handling

When the brief conflicts with the brandbook:

- preserve official mark geometry and mandatory exclusions;
- identify the exact conflict and supporting page;
- propose the least disruptive compliant interpretation;
- create a clearly labeled exception proof only when the user wants to evaluate a deviation.

Never silently modify the brand to make a composition easier.

## 6. Brand QA

Verify against the manifest, not memory:

- correct logo version and contrast;
- clearspace and minimum size;
- exact palette values in the intended color space;
- available font family and actual weight files;
- approved pattern behavior;
- co-brand order and relative scale;
- no forbidden effects or pseudo-brand generated material;
- source page/asset recorded for every official element.
