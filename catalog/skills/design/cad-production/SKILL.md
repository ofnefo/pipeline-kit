---
name: cad-production
description: Use when dimensional parametric CAD must be created, revised, inspected or handed off - product parts, fabrication parts, assemblies, profiles, fixtures - or a task mentions STEP/STP, STL, 3MF, DXF, FreeCAD, build123d, tolerances or manufacturing validation. Treats editable parameters and numeric checks as the source of truth. Not for presentation scenes and spatial rendering (blender-production) and not a substitute for engineer or vendor approval.
---

# CAD Production

Editable parameters and dimensional evidence are the source of truth. A visually plausible mesh is not a fabrication model.

## Inputs

- The active project file, the exact object brief or drawing, relevant production/vendor rules, and only sources for the requested part or assembly.
- Units, datum, confirmed dimensions, tolerances, material and process assumptions, interfaces, quantities and the approval owner.

Mark unknowns `TBD`. Never borrow dimensions from another project.

## Choose the operation

| Task | Read |
|---|---|
| Parametric solids, features, constraints, assemblies, revisions | `references/parametric-modeling.md` |
| STEP/STL/3MF/DXF handoff and fabrication checks | `references/fabrication-and-export.md` |
| build123d vs FreeCAD vs an MCP bridge | `references/tool-routing.md` |

## Workflow

1. Choose datums and named parameters before detailed features. Keep a readable parameter/source table (parameter, value, unit, source, status).
2. Model nominal geometry from confirmed dimensions. Isolate assumptions so they can change without rebuilding the part.
3. Build in feature groups: envelope, primary interfaces, cuts and openings, repeated features, rounds and chamfers, patterns. Recompute after each group and inspect solid validity, bounding box, volume, interfaces, clearances and feature references.
4. For assemblies: fixed components, constraints, degrees of freedom, clearance states, service and removal paths, bill of materials. Separate purchased from fabricated parts; use the supplier's official STEP or datasheet instead of an approximate mesh.
5. Export the requested exchange files, re-import each in a clean document and compare units, orientation, extents, part count and geometry.
6. Render a preview or screenshot and verify critical dimensions numerically before delivery.

## Techniques and gotchas

- build123d (code-first) suits parts that are clean parameters and features; FreeCAD GUI suits live inspection, mixed workbenches, TechDraw and hand edits. Keep a reviewed script route for complex parametric logic even when a typed MCP exists.
- STEP for exact solids, DXF for 2D profiles and cutting, STL/3MF for additive with explicit units and tessellation, PDF/SVG only for human-readable drawings.
- Additive: check manifoldness, normals, wall thickness, overhangs, build orientation, shrinkage/tolerance policy and slicer profile separately.
- Cutting: closed profiles, no duplicate paths, kerf/offset owner, bend allowance owner, layer naming.
- Mesh repair is an explicit, versioned operation; never silently mutate the source geometry.
- Do not claim tolerances, load capacity, fire compliance, machining strategy, printability or fit without process and specialist evidence.

## Acceptance checklist

- [ ] Parameter table exists and every critical dimension has a source or `TBD`.
- [ ] Model recomputes without errors; solids are valid and closed.
- [ ] Exchange files were re-imported and match the source (units, extents, part count).
- [ ] Critical dimensions verified numerically, plus a visual preview.
- [ ] Editable source kept; STL is never the master when STEP or the parametric source exists.

## Deliver

Return the editable source, the requested exchange files, the parameter/dimension table, validation evidence, the revision, unresolved `TBD`s and manufacturing assumptions.

## Boundaries

- Scene context and presentation renders go to `blender-production`.
- Final production release goes to `design-production-preflight` and the responsible engineer or vendor.
- A printable part verified against a measured contract can use a dedicated 3D-print workflow if your kit has one.
