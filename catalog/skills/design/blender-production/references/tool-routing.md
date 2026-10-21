# Blender execution routes

This skill does not bundle a Blender MCP.

- [`ahujasid/blender-mcp`](https://github.com/ahujasid/blender-mcp) (`MCPBlender/blender-mcp` redirects here): mature community bridge with a simple Blender addon and Python execution. It is the preferred first pilot; disable its opt-in-by-default telemetry for protected client work.
- [`RFingAdam/mcp-blender`](https://github.com/RFingAdam/mcp-blender): much broader typed surface, including measurement, validation, multi-angle render, and refinement tools. Treat it as an advanced evaluation candidate; review its AGPL-3.0-or-later license and smaller adoption before standardizing.
- [`Vedmani/blender-lab-codex-skill`](https://github.com/Vedmani/blender-lab-codex-skill): a Codex wrapper for the official Blender Lab bridge on loopback (`localhost:9874/uv`). Use only when the official bridge is already installed and its built-in inspect/render/docs commands fit the task. Start read-only, keep live calls sequential, and do not vendor its GPL-3.0 implementation into this skill.

Do not install any bridge automatically. Use one bridge at a time, bind local services to loopback, review arbitrary Python capability, and keep source-control/cache paths outside client deliverables. Prefer built-in read/inspect/render commands over arbitrary code when the bridge exposes them. If no MCP is available, use Blender GUI, Computer Use, or reviewed `bpy` scripts. Every route must support visual inspection and save-as versioning.
