---
name: design-render-refiner
description: Use when an approved architectural, exhibition, retail, interior or product render needs controlled material, decal, lighting, atmosphere, signage-placeholder or surface-graphics enhancement while its camera, geometry, venue, equipment and composition stay locked. Runs a locked-base image edit with drift checks and one recovery retry. Not for redesigning the scene (blender-production), final logos or legal copy (illustrator-production) or choosing a style (design-style-director).
---

# Design Render Refiner

Treat the source render as a locked base, not an invitation to redesign it.

## Inputs

- The active project file, its project rules and the approved style/prerender record.
- The exact source image and its pixel dimensions.
- Approved surfaces, forbidden changes, the desired material or graphic delta and acceptance criteria.

## Before editing

1. Confirm the inputs above. If geometry or function is not approved, stop image finishing and return the issue to 3D or design.
2. Look at the source image before invoking any image-editing tool.
3. Fill the prompt template in `references/prompt-template.md`. Add palette, copy, motifs and restrictions only from current project files; never from another project.

## Edit contract

Preserve canvas, crop, camera, lens, perspective, exposure logic, venue architecture, structural elements, facade silhouettes, openings, furniture, screens, equipment, people, circulation and official marks unless the operator explicitly approves a change. Change only the named surfaces or attributes.

Use the available image-editing model with the original image as the only edit target. One request = one controlled pass.

Do not generate final logos, QR codes, legal copy, technical labels or authoritative signage. Add those later through deterministic composition (`design-graphic-compositor`, `illustrator-production`).

## Drift recovery

1. Compare result dimensions and visible anchors (edges, openings, equipment, people, protected text) with the source.
2. If anything protected drifted, retry once from the original, not from the failed result, with a shorter correction prompt (template in the reference).
3. If drift persists, deliver the cleanest controlled variant plus an explicit deterministic-overlay plan (masked composite in Photoshop) instead of hiding the failure.

## Acceptance checklist

- [ ] Output has the same pixel dimensions and crop as the source.
- [ ] Protected anchors match the source in a side-by-side or difference view.
- [ ] Only approved surfaces changed; no new objects, text, logos or light sources.
- [ ] Variant names are versioned; the original is untouched.
- [ ] The result is labelled concept, approval visual or production intent.

## Deliver

Keep the original untouched. Save variants with clear version names, state exactly what changed, list any protected element that could not be preserved, and say whether the result is a concept, an approval visual or production intent. A refined render is never engineering approval.

## Boundaries

- Geometry or camera changes go to `blender-production`.
- Pixel-exact masked composites go to `photoshop-production`.
- Exact text and marks go to `illustrator-production` or `design-graphic-compositor`.
