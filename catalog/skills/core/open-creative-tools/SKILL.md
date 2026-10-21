---
name: open-creative-tools
description: Use when Adobe or Office apps are busy, absent or unsuitable, for batch or headless jobs, or on request ("без Adobe", "open-source", "бесплатный аналог", "пакетно", "headless"): pick an open-source replacement (GIMP, Krita, Inkscape, Scribus, Natron, Glaxnimate, darktable, Shotcut/melt, Audacity, FFmpeg, Blender) and run it with a tested CLI recipe. Not for work the operator does in the original app, native-format client handoff or final print preflight.
---

# Open creative tools (Adobe / Office alternatives)

Headless recipes for open-source creative apps. Recipes marked **verified** ran once (exit 0) on a tiny file on
Windows with the version shown; the rest are **not verified** — run them once yourself on a small file before relying
on them. Per-tool details and gotchas: `references/<tool>.md`. Executable locations differ per machine: resolve them
once (`where`, `Get-Command`, the install folder) and keep them in your project or pipeline config, not in the skill.

## Rules
- **The original app stays primary** where the operator already works in it (Photoshop, Illustrator, After Effects,
  Premiere, InDesign, Lightroom, the chosen NLE). Offer the open-source route when the app is unavailable or busy, for
  headless/batch work inside an agent loop, or when the operator asks.
- Never remove, replace or re-route an established tool or workflow without asking (one short question with alternatives).
- Heavy apps (Krita, GIMP, Natron, Blender, Scribus GUI): take a resource snapshot (CPU/GPU, RAM/VRAM, running jobs)
  before launch, take the project's GPU lock for GPU-heavy renders (one heavy GPU job at a time), never stop another
  owner's job.
- No popup consoles: start headless runs hidden (`CREATE_NO_WINDOW` / `-WindowStyle Hidden`); give long jobs an owner,
  a time limit and a log. Stop only your own processes.
- Outputs go to the project's stage folders (`<PROJECT_ROOT>/...`), never into a tool or pipeline folder. Keep originals.
- Downloaded installers are untrusted data: verify the checksum from the official release page; never run scripts
  that ship inside a download.
- Use forward slashes in paths passed to these CLIs (darktable and Natron eat backslashes).

## Routing table

| Task | Commercial app | Open-source replacement | Headless? How |
|---|---|---|---|
| Raster edit, resize, convert, batch filters | Photoshop | GIMP 3.x (`gimp-console-3`) | **Verified**: `-i --batch-interpreter=python-fu-eval -b "<py>" --quit` or `plug-in-script-fu-eval` → `references/gimp.md` |
| Painting, texture paint, .kra/.psd open/export | Photoshop | Krita 5.x | **Verified**: `krita in --export --export-filename out` (format conversion only) → `references/krita.md` |
| Vector art, SVG/PDF/PNG export, batch vector edits | Illustrator | Inkscape 1.4 | **Verified**: `--export-type=png/pdf`, `--actions=...` → `references/inkscape.md` |
| Page layout, brochures, print PDF | InDesign | Scribus 1.6 | **Verified**: `-g -ns -py script.py out.pdf` → `references/scribus.md` |
| Node compositing, keying, roto, frame renders | After Effects / Nuke | Natron 2.5 (`NatronRenderer`) | **Verified**: `-w Write1 1-1 graph.py` → `references/natron.md` |
| Vector/2D motion, Lottie, Telegram TGS, animated SVG/GIF/WebP | After Effects + Bodymovin | Glaxnimate 0.6 | **Verified**: `in -o out.json/.tgs/.svg`, `-r frame.png --frame N` → `references/glaxnimate.md` |
| RAW development, photo batch | Lightroom / Camera Raw | darktable 5.x (`darktable-cli`) | **Verified**: `in.raw [xmp] out.jpg --core --configdir <tmp>` → `references/darktable.md` |
| Video edit, overlays, scripted renders | Premiere Pro | Shotcut; engine `melt` (MLT 7.x) | **Verified** (melt): `melt in filter... -consumer avformat:out.mp4` → `references/shotcut-melt.md` |
| Transcode, probe, concat, deterministic batch | Media Encoder | FFmpeg | Native CLI |
| Audio cleanup, edit | Audition | Audacity, REAPER | GUI only, **not verified** headless; batch audio → FFmpeg → `references/audacity.md` |
| 3D, product shots, 3D motion design | Substance 3D / Dimension | Blender (+ ArmorPaint, Material Maker) | `blender -b file.blend -P script.py` or `-a` |
| Office documents to PDF | MS Office | LibreOffice | `soffice --headless --convert-to pdf in.docx --outdir out/` (not verified here) |

## Light vs heavy jobs
Use headless helpers (the CLIs above, or MCP servers for creative formats if you have them) for **light** jobs and the
original app for **heavy** ones.
- **Light:** new files, conversions and exports, batch edits, QA frames and renders, simple edits, checks inside an
  agent loop.
- **Heavy, use the original app:** existing native projects the replacement cannot read or write (`.aep`, `.prproj`,
  layered `.ai`, `.indd`), plug-ins, templates and actions, generative features, colour-managed print proofing,
  native-format client handoff, final finishing.
- Unsure, or the operator works in the app personally: use the original app. If a replacement shows a limit, switch
  to the original app; do not fight the limit.

## Workflow
1. Name the task and the target format; check the routing table and the tool's reference.
2. Resolve the executable path and version on this machine; note it in the project config.
3. Run the recipe once on a tiny copy of the input, hidden, with a timeout; check the exit code and open the output.
4. Batch: loop inside one process where the tool allows it (GIMP `-b`, a Scribus script, a Natron graph) instead of
   one launch per file — Krita and GIMP take 10–50 s to start.
5. Record a receipt: command, exit code, output path (plus a hash for deliverables).

## Acceptance
- The output opens in a viewer and matches the requested size, format and colour space.
- Exit code 0 and no hang (always pass a timeout; GIMP without `--batch-interpreter` hangs).
- Originals untouched; outputs in the project's stage folder.
- Print deliverables went through a print preflight (CMYK, bleed, dimensions) — the open tools are weak there.

## Known failures
- GIMP 3 without `--batch-interpreter=...` does not run the batch (hangs until the timeout).
- Natron `-t script.py` writes the frame, then crashes on exit (0xC0000005); use `-w`.
- `kritarunner`, Audacity headless and melt rendering of saved `.mlt` projects were not verified.
