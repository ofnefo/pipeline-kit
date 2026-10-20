# Pipeline Kit

A portable distribution of the existing Control panel and selected reusable production tools. The panel keeps its original interface, project file browser, task board, NameNode cards, Studio chats, montage workspace, converters and SMM editorial planning. It runs against one empty local workspace.

## Install

Use Python **3.12**. From the extracted distribution:

```sh
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe pipeline_kit.py --workspace workspace init
.venv/Scripts/python.exe pipeline_kit.py --workspace workspace serve
```

macOS / Linux:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python pipeline_kit.py --workspace workspace init
.venv/bin/python pipeline_kit.py --workspace workspace serve
```

Open **http://127.0.0.1:8770**. Stop with Ctrl+C. The server binds to loopback only; there is no login or multi-user network deployment mode. Keep it local. Python dependencies install from your selected package index; the app does not install tools or models.

Create a folder from **Projects → New project folder**, open its files, add a task in **Tasks**, or start a saved conversation in **Studio**. The interface is primarily Russian with English capability explanations. An empty workspace contains no personal cards, brand history, contacts or model presets.

## Included workflows

| Area | Included | Additional dependency |
|---|---|---|
| Control | Tasks with optimistic version checks, claims and journals, file upload/preview/quarantine/restore | Runtime requirements |
| Studio | Project chats, local chat streaming, saved messages | Explicit loopback model configuration for inference |
| Video | Timeline editing, annotations and decisions; editorial and montage CLIs | FFmpeg/FFprobe for media processing; OpenTimelineIO for OTIO export |
| Design | Layer compositor, contact sheets, asset inspection, physical-size print preflight | Pillow |
| Office | Project templates, source inventory, decimal estimates, document registers and QA | Office/PDF authoring needs optional libraries/tools |
| Music | Lyric preflight and pronunciation helpers; audio mastering CLI | FFmpeg/FFprobe for mastering |
| Web | Offline HTML SEO audit and UTM builder | Standard library |
| SMM | Local content plans, revisions and JSON export | No remote publication |

See [module recipes](docs/MODULES.md), [optional components](docs/CONFIGURATION.md), [agent setup](docs/AGENTS.md), and [release checks](docs/RELEASE.md).

## Boundaries

GPU workers, weights, paid/cloud inference, personal assistants, remote SSH hosts, secrets managers, download queues, automatic publishing, installed creative applications and production sites are **not bundled**. Their original navigation entries explain the missing capability. There is no background host scan, alert sender, scheduler, implicit Git commit or remote startup command.

Source provenance and bundled third-party notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and `provenance.json`. No client project or private core/site repository is included. [Validation status](VALIDATION.md) records the checks actually performed and the remaining release gates.
