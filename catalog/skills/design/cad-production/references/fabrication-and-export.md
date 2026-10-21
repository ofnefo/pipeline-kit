# Fabrication and export

Choose the output by downstream need:

- STEP/STP for exact solid exchange and downstream CAD;
- DXF for 2D profiles, cutting, templates, and documented drawings;
- STL/3MF for mesh-based additive workflows, with explicit units and tessellation;
- PDF/SVG only for human-readable drawings or vector profiles, not as the parametric source.

Validate the editable model before export: recompute status, solid validity, closed shells, bounding box, mass/volume when material is known, interface dimensions, minimum feature/wall size, clearances, and process-specific limits. Then re-import the exchange file in a clean document and compare units, orientation, extents, part count, and geometry.

For additive work, verify manifoldness, normals, wall thickness, unsupported overhangs, build orientation, shrinkage/tolerance policy, and slicer profile separately. For cutting, confirm closed profiles, duplicate paths, kerf/offset owner, bend allowance owner, and layer naming. These checks do not replace vendor or engineering approval.
