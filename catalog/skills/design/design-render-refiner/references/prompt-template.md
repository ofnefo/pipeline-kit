# Locked-base refinement prompt

Fill every bracket from the current project. Remove unused clauses.

```text
Use case: precise-object-edit. Image 1 is the only edit target and an immutable locked base.
Goal: [APPROVED MATERIAL / GRAPHIC / LIGHTING CHANGE].
Change only: [EXPLICIT ALLOWED SURFACES OR ATTRIBUTES].
Preserve exactly: canvas dimensions, crop, camera, lens, perspective, venue architecture,
structural elements, geometry, openings, furniture, screens, equipment, people, circulation,
official marks, and all protected content listed in [PROJECT RULES].
Apply current project style [STYLE CODE / CREATIVE LEVEL] using [APPROVED PALETTE / MATERIALS]
at [APPROVED DENSITY]. Add no text, logo, QR, claim, equipment, object, person, plant,
light source, opening, support, or geometry unless explicitly listed above.
The result is [CONCEPT / APPROVAL VISUAL / PRODUCTION INTENT], not engineering approval.
```

Drift correction:

```text
Use the original again as Image 1. The prior result is reference only for [ONE APPROVED ATTRIBUTE].
Restore exactly: [ALTERED PROTECTED ELEMENTS]. Transfer only [APPROVED DELTA] onto [SURFACES].
```
