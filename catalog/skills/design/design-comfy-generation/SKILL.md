---
name: design-comfy-generation
description: Use when a design task needs an image generated, edited, cut out, face-restored, upscaled, vectorized or an icon found on a local GPU ("generate a concept", "moodboard", "texture", "replace the sign text", "remove background", "upscale for print", "restore face", "vectorize", "Z-Image", "Qwen-Edit"). Runs local ComfyUI chains - Z-Image Turbo, Qwen-Image-Edit-2511, BiRefNet, CodeFormer, SeedVR2 - plus CPU tools (VTracer, free-licence icon lookup) with a receipt per run. Not for locked-base render refinement (design-render-refiner), Photoshop/Illustrator masters or choosing a direction.
---

# Design Comfy Generation

Local executor for raster generation and image utilities: the production stage of the image route. Generated pixels are sketches and layers, not masters. Exact text, logos and QR codes are rebuilt deterministically afterwards.

Route order: curate the brief first; use a cloud image model for hero references only when the operator approved it; then run local chains here for variations and production. Utilities (cutout, upscale, vectorize) can start here directly. This skill calls no cloud API.

Model files, licences, defaults and measured timings: `references/workflows.md`. How to submit a workflow JSON to ComfyUI, validate it and collect outputs: the `comfy` skill.

## 1. Place the job

- Resolve the active project. One AI request = one layer or one controlled pass, with stated invariants and negative constraints.
- Output folder inside the project, for example `<PROJECT_ROOT>/generations/<deliverable>/<job>` for flat design or `<PROJECT_ROOT>/renders/<zone>/layers` for spatial work. Use a new folder per version; never overwrite outputs.
- Inputs stay where they are; upload copies to ComfyUI under a content-hash name so reruns are reproducible.

## 2. GPU discipline

- One heavy GPU job at a time. Before a run, snapshot GPU/VRAM, RAM and active jobs, then take the project's GPU lock (an exclusive lock file or queue slot with your agent id as owner). Release it after the run.
- If another owner holds the lock, wait or report. Never delete their lock or stop their job.
- Free models after the run (ComfyUI `/free` with `unload_models`) unless the next job reuses them.
- Use the existing ComfyUI install and its `<COMFY_ROOT>/models/<type>` folders. Never install a second ComfyUI or download duplicate weights.

## 3. Workflows

Keep each workflow as an API-format JSON plus a sidecar `*.params.json` that names the editable inputs and defaults. The sidecar is the source of truth for parameter names.

| Job | Model chain | Key params |
|---|---|---|
| Concept, moodboard, texture (t2i) | Z-Image Turbo | `prompt`, 1024x1024, `seed`, steps 8, `batch_size` |
| Instruction edit, replace sign text | Qwen-Image-Edit-2511 GGUF + Lightning 4-step LoRA | `input_image`, `prompt` (text to render in quotes), `seed`; steps 4, cfg 1.0 |
| Same edit + one style/content LoRA | as above + `extra_lora` | `extra_lora_strength`; VRAM headroom near zero on 16 GB |
| Background cutout to RGBA + mask | BiRefNet | `input_image` |
| Face restore | CodeFormer | `input_image`, `fidelity` 0-1 (1 = closest to source); detector `retinaface_resnet50` |
| Upscale for print and masters | SeedVR2 | `input_image` (alpha dropped), `resolution` = target short side in px |

Pass long or non-Latin prompts from a UTF-8 file rather than the command line.

Before upscaling compute the needed pixels (`px = mm / 25.4 x PPI`) and compare source, plain resize and SeedVR2 at 100% crops. Upscale before placing exact text. CodeFormer weights are under a non-commercial licence: record that in the job notes so the operator can make the release decision.

Receipt: every run writes `run-<id>.json` in the output folder with workflow, parameters, seed, input and output SHA-256, duration and VRAM peak. No "generated" claim without it.

## 4. CPU tools (no GPU lock)

- Raster to SVG with VTracer (`pip install vtracer`): presets `logo` (few colours, smooth curves), `photo`, `bw` (silhouette, plotter). Route: BiRefNet cutout PNG, then `logo` or `bw`, then an Illustrator check of nodes, colours and scale. A trace is a draft vector. Never overwrite an existing SVG.
- Icons and brand marks: search an offline icon snapshot filtered to free licences (CC0, MIT, Apache-2.0) by default; copy chosen icons into `<PROJECT_ROOT>/assets/icons` with a provenance JSON (slug, source, licence, variant). Brand logos remain their owners' trademarks; no-derivatives icons are not modified.
- Before bulk cleanup of generation folders, run a read-only inventory (path, size, hash, receipt link) and review it.

## 5. QA and hand-off

1. Layer QA: no pseudo-text, fake logos or QR codes; perspective and light match the base; protected pixels untouched; source, prompt, workflow, seed and receipt recorded in the layer passport.
2. Assemble masters with `photoshop-production`, `illustrator-production` or `design-graphic-compositor`; check exact copy against the project's text master.
3. Print or production output goes to `design-production-preflight`.
4. Deliver only final, approved files through your delivery channel when the operator asks. Never send raw inputs, drafts, variants or intermediate layers.

## Quality chain for hero images

Curated brief, then a hero reference (cloud model only if approved), then local Z-Image with structural guidance, Qwen-Edit fixes, detail pass, SeedVR2 upscale.

## Acceptance checklist

- [ ] Output in a new versioned project folder; nothing overwritten.
- [ ] GPU lock taken and released; models freed.
- [ ] Receipt with parameters, hashes and VRAM peak exists for every output.
- [ ] Model-rendered text treated as a sketch and rebuilt deterministically.
- [ ] Licence notes recorded (non-commercial weights, third-party logos).

## Boundaries

- Locked-base render refinement: `design-render-refiner`.
- Raster and vector masters: `photoshop-production`, `illustrator-production`.
- Choosing a direction: `design-style-director`.
