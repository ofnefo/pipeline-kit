# Local configuration

`--workspace` selects all mutable state. It is resolved once at startup; restart after changing it. Use a dedicated directory owned by your local account. Do not put it inside the distribution when building a release archive.

Use ordinary local directories: symlinks, junctions and other reparse points are refused, including cloud-backed folders that use them. A new project text file may be created beneath checked ordinary directories. Browser uploads reserve 64 MiB of free space beyond the declared upload size.

Copy `config/workspace.example.json` to `<workspace>/config.json` only when enabling an optional feature. The default config is absent and therefore all integrations are off. `watch_project_files` is opt-in and observes only configured project folders; it never scans disks. Leaving it false gives on-demand file browsing.

For local chat, run your own OpenAI-compatible server separately, set `local_chat.enabled` to true, and supply its exact model identifier and HTTP loopback `base_url` ending in `/v1`. The kit does not start the server, download weights, read API credentials or discover models. Requests are made only when you send a Studio message. Redirects and non-loopback addresses are rejected. A configured model is not proof that the server is online; connection errors are shown at send time.

Optional executable lookup uses PATH. Run `python pipeline_kit.py doctor` to check availability. Install FFmpeg and FFprobe for montage/audio; LibreOffice for Office-to-PDF; Pandoc for document transformations. The upstream references in `config/optional-components.json` are informational and do not execute anything. Install optional Python production libraries in an environment you manage; they are excluded from the core dependency set.

The panel exposes a local API schema at `/docs` and `/openapi.json`. Unknown production adapters return HTTP 501. No remote MCP servers or global agent settings are installed. Use the CLI or documented HTTP endpoints for your own integrations.

Back up the selected workspace while the panel is stopped. Preserve its SQLite databases, project folders and NameNode directory together. Updating the distribution must not overwrite the workspace. To remove the application, stop it and remove the extracted program/venv; retaining or deleting your workspace is a separate operator decision.
