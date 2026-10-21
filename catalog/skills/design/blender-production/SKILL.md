---
name: blender-production
description: Use when Blender models or scenes must be built, revised, inspected or handed off from plans, elevations, schemes, briefs, reference images or existing .blend files - spatial blockouts, exhibition, interior and show scenes, object modeling, materials, cameras, lighting, rendering, optimization, scene export. Works in small inspect-change-render-measure loops with dimension provenance and SHIP / NO-SHIP verdicts. Not for parametric fabrication parts or engineering exchange (cad-production).
---

# Blender Production

Use Blender for spatial truth, scene assembly, presentation geometry, materials, cameras and renderable context. Do not use it to impersonate engineering CAD.

## Inputs

- The active project file, selected discipline profile, current gate and the exact geometry sources.
- Only the project rules that affect the requested zone or object.
- Every critical dimension tagged `MEASURED`, `CLIENT_PROVIDED`, `ASSUMED` or `TBD`, with its source.

Do not ingest unrelated project documents, archived renders or every reference board.

## Choose the operation

| Task | Read |
|---|---|
| Venue or scene from plans, elevations, sections | `references/plans-to-scene.md` |
| Modeling, hierarchy, modifiers, object IDs, reusable assemblies | `references/modeling.md` |
| Materials, cameras, lighting, render states, sample counts | `references/materials-and-rendering.md` |
| Matching an approved reference, propagating a look, multi-view checks | `references/reference-validation.md` |
| Performance, linked data, packaging, GLB/FBX/USD export | `references/optimization-and-export.md` |
| GUI vs Python vs MCP bridge | `references/tool-routing.md` |

For photo-to-3D, reconstruction, retexturing or rigging, keep a short capabilities note of which local routes have actually produced a verified result (with a receipt) and pick by that evidence. A smoke test of one route proves that input and workflow only, not arbitrary assets. Do not install another stack to satisfy a single task. A one-photo scene blockout is covered by `image-to-scene`.

## Production contract

1. Inspect before mutating: units, scale, collections, linked libraries, transforms, modifiers, cameras, render engine, missing dependencies.
2. Save a new version before broad changes. Never silently overwrite an approved `.blend`.
3. Build a low-detail dimensional blockout before materials and detail. Keep assumptions visually and structurally distinct from confirmed geometry.
4. Give production-relevant objects stable `OBJECT_ID`s and keep `DESIGN`, `VISIBLE` and `PRODUCTION` dimensions separate when they differ.
5. Keep real openings, access, circulation, equipment, service zones, supports and obstructions. Do not solve missing dimensions by inventing precise geometry.
6. Render or screenshot after each meaningful batch. Tool success, object count or valid Python is not visual QA. For scene families, check the same client view class in every scene and record exceptions.
7. Geometry approval precedes final material and render work. AI imagery never closes engineering or fabrication gates.

## Execution loop

Small cycles: inspect, change, screenshot or render, measure and compare. With MCP or Python, batch only changes that share one reversible intention; keep live-bridge calls sequential and start read-only. Stop and report when source drawings conflict, scale is unknown, an operation changes protected geometry, or a production dimension needs an owner.

## Key parameters

- Render states: `CLAY`, `SEAMS_ON`, `MEDIA_OFF`, `WORKING_LIGHT`, `CLIENT`. A presentation render must not erase supports, service access, seams, safety elements or unresolved geometry.
- Cycles with adaptive sampling and denoising: QA 24-128 samples at 40-60% resolution; typical final 256-1024; glass, deep interiors or hard indirect light 1024-2048 only after a sample test proves the need. Apply draft settings in a separate process; never save them into the final preset.
- 16-bit PNG or OpenEXR when compositing follows; 8-bit PNG for review only.
- Camera roles `CLIENT`, `SERVICE`, `DETAIL`, `ORTHO`; assert an active camera of the intended role before every render. A bounding-box camera fit is a starting point, not approval.
- Look calibration order: camera and crop, world, base materials, emissive/practicals, key/fill balance, colour management.
- Look propagation: copy engine, samples, denoising, colour management, world and output exactly; scale light positions, sizes and energy from each scene's visible bounds.

## Acceptance checklist

- [ ] Versioned `.blend` saved; approved files untouched.
- [ ] Critical dimensions tagged with provenance; numeric checks of known distances and levels done.
- [ ] Geometry fingerprint (object names/types, vertex and polygon totals, transforms, bounds) unchanged for protected geometry.
- [ ] Review images: client view, side/profile when depth matters, material close-up when finish matters, service view when production is in scope.
- [ ] Verdict stated: `SHIP`, `SHIP WITH NOTES` or `NO-SHIP`, with render defects separated from source/model blockers.

## Deliver

Return the versioned `.blend`, requested renders and exports, source-to-dimension notes, unresolved `TBD`s, missing dependencies and the current geometry/render gate.

## Boundaries

- Fabrication solids and drawings go to `cad-production`.
- Locked render finishing goes to `design-render-refiner`.
- Production readiness goes to `design-production-preflight`.
- Method credits for ideas adapted from public Blender skill repositories are in `NOTICE.md`.
