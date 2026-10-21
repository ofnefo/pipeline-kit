# CAD execution routes

[flowful-ai/cad-skill](https://github.com/flowful-ai/cad-skill) describes a CadQuery method (PolyForm Noncommercial; idea source only, nothing copied): parameterized dimensions, STEP plus mesh exports, six-view checks, finite coordinates and degeneracy checks. Treat mesh repair as an explicit versioned operation; never silently mutate source geometry. Keep a short capabilities note that separates tools actually installed on your machine (for example a specific FreeCAD version) from candidates. A viewer/annotation tool that also runs code is a candidate, not permission to expose a code-execution server to a network.

This skill does not bundle a CAD MCP or third-party skill library.

- [`earthtojake/text-to-cad`](https://github.com/earthtojake/text-to-cad): strong external skills library for CAD/CAE/CAM with STEP-first output, build123d, STL/3MF/DXF, viewer, DfAM, and fabrication workflows. Use as a reference or optional separately reviewed plugin; do not copy its files into this plugin.
- build123d: preferred deterministic code-first route when a part can be expressed cleanly as parameters and features.
- FreeCAD GUI: preferred when live inspection, mixed workbenches, TechDraw, or hand editing matters.
- [`ahelja/FreeCAD-MCP`](https://github.com/ahelja/FreeCAD-MCP): compact live-session bridge with screenshots and exports, but currently very new and verified by its author on macOS; pilot before Windows production use.
- [`sergiudanstan/freecad-mcp`](https://github.com/sergiudanstan/freecad-mcp): broader 165-tool surface including Part Design, TechDraw, BIM, FEM, and assemblies; review maturity and visually verify through FreeCAD because the documented tool list does not provide a screenshot tool.

Do not install tools automatically. Bind bridges to loopback, review arbitrary Python execution, use a dedicated workspace, and preserve versioned source files. Prefer typed operations, but keep a reviewed script route for complex parametric logic.
