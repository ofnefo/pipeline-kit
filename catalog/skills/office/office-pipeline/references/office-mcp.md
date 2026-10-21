# Office MCP servers: when they help and where they stop

Optional MCP servers give an agent direct read/edit access to Office files. Useful public options:

| Server | Licence | Good for | Limits |
|---|---|---|---|
| `haris-musa/excel-mcp-server` (openpyxl) | MIT | reading sheets, small cell/formula edits, inspecting formats | no recalculation engine; formula results need a headless recalculation |
| `GongRzhe/Office-Word-MCP-Server` (python-docx) | MIT | reading paragraphs/tables, small text edits, simple formatting | cannot accept/reject tracked changes or write real comments; no path guard of its own |

## Rules

- Restrict each server to the project directory (allow-dir / path guard or a wrapper). A server without a guard must
  only be pointed at a versioned working copy.
- Edit copies, never originals in the incoming folder, and never an approved version in place.
- MCP edits leave no receipt. Documents of record are built by repeatable scripts that validate input against a
  schema, refuse to overwrite an existing output and print path + sha256.
- An MCP "read" is not visual QA: render pages/sheets to images and inspect them.
- Tracked changes and comments need a Word-capable route (a docx skill working on OOXML, or Word itself).
