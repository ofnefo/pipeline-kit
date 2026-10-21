# Illustrator execution routes

This skill does not bundle an Illustrator MCP. Use an already configured trusted route when available; otherwise operate through the local app/Computer Use or prepare an explicit execution plan.

- [`ie3jp/illustrator-mcp-server`](https://github.com/ie3jp/illustrator-mcp-server): broad typed coverage for reading, creating, editing, preflight, and export. Prefer as the first MCP pilot after local security review.
- [`ajfonthemove/illustrator-mcp`](https://github.com/ajfonthemove/illustrator-mcp): narrower and much newer, but exposes preview/screenshot plus raw ExtendScript. Treat as an experimental visual-control candidate, not the default production dependency.

Do not install either automatically. One Illustrator automation bridge at a time is easier to audit. Require a preview/screenshot after structural edits; if the chosen MCP cannot see the canvas, export PNG/PDF or use Computer Use for visual verification. Keep arbitrary-script tools limited to trusted local work and exact targets.
