# Vector cleanup

Prefer original AI/EPS/SVG/PDF assets. Treat Image Trace as reconstruction, never as the original vector.

After tracing or importing:

- compare silhouette and negative spaces with the approved source;
- remove background fragments, tiny noise, duplicate points, and hidden objects;
- reduce anchors only when shape fidelity survives;
- verify compound paths, holes, winding, clipping masks, open paths, and stray points;
- normalize transforms and inspect strokes at final scale;
- keep a reference layer with the approved raster or source vector.

For cutting, routing, or plotter contours, use closed paths on a dedicated named layer, confirm units and scale, remove fills when required, and never infer kerf, tool diameter, or offset without vendor confirmation.
