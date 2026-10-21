---
name: comfy
description: Use when an agent must run, inspect or debug a local ComfyUI server - submit an API-format workflow, check which nodes and models exist, track a queued prompt, collect outputs, free VRAM or place new model weights ("run this ComfyUI workflow", "queue the graph", "which models are installed", "ComfyUI error", "where does this checkpoint go"). Drives the ComfyUI HTTP API with validation, one GPU job at a time and a receipt per run. Not for choosing design models or prompts (design-comfy-generation) or installing a second ComfyUI.
---

# ComfyUI operator

Run workflows on an existing local ComfyUI server through its HTTP API, safely and reproducibly. The server address is configuration (for example `COMFY_URL=http://127.0.0.1:8188`); the install folder is `<COMFY_ROOT>`.

## Inputs

- A workflow in API format (node id -> `{class_type, inputs}`), exported with "Save (API)". UI-format files (with `nodes`/`links` arrays) must be converted or re-exported first.
- A sidecar `<workflow>.params.json` mapping friendly parameter names to `node_id.input` slots, with defaults.
- Input images and the output folder in the project.

## Workflow

1. **Discover.** `GET /system_stats` (server up, GPU, VRAM) and `GET /queue` (running and pending jobs). Read `GET /object_info` once per session and cache it: it lists every node class with its inputs, and the allowed values of model selectors are exactly the files ComfyUI sees. Take model names from there, never from memory.
2. **Prepare.** Start from a known-good graph. Change only the slots named in the sidecar, addressed by node id. Upload inputs with `POST /upload/image` (multipart, `overwrite=false`) and reference the returned name. Set the seed explicitly; for variants change only the seed.
3. **Validate locally.** Every `class_type` exists in `object_info`; every required input is present; enums (models, samplers, schedulers) are allowed values; links point to existing node ids and output indices. Fail before submitting.
4. **Lock and submit.** Check resources, take the GPU lock (one heavy job at a time, owner = your agent id), then `POST /prompt` with `{"prompt": <graph>, "client_id": <uuid>}`. A 400 response carries `node_errors`; read them and fix the graph rather than retrying unchanged.
5. **Wait.** Prefer the websocket `/ws?clientId=<uuid>` for progress and the `executing` message with `node: null` for completion; otherwise poll `GET /history/<prompt_id>` with a backoff of a few seconds and an overall timeout. No tight loops.
6. **Collect.** Read output file names from the history entry and download them with `GET /view?filename=...&subfolder=...&type=output`. Copy them into the project folder under new names; ComfyUI's own output folder is a scratch area.
7. **Receipt.** Write `run-<prompt_id>.json`: server, workflow hash, changed parameters, seed, model names, input and output SHA-256, duration, VRAM peak (from `system_stats` before and after or a GPU monitor), status.
8. **Release.** `POST /free` with `{"unload_models": true, "free_memory": true}` unless the next job reuses the models; release the lock.

To stop a job, `POST /interrupt` only when it is your own running prompt; remove your own pending prompts with `POST /queue` and `{"delete": [ids]}`. Never interrupt or delete another owner's job.

## Model placement

- Weights live once, under `<COMFY_ROOT>/models/<type>/`: `checkpoints`, `diffusion_models`, `text_encoders`, `vae`, `loras`, `controlnet`, `upscale_models`, `clip_vision` and folders created by custom nodes. Extra shared libraries go through `extra_model_paths.yaml`, not copies.
- Before adding a weight, search the existing folders by name and size. Never download a duplicate, and never let a custom node auto-download weights during a production run.
- New weights go to a staging folder first, get a hash, licence and source note, then move into place. Refresh `object_info` afterwards.
- Custom nodes are code: install only from a reviewed source and record the commit.

## Gotchas

- Model selector values include subfolders (`sub/name.safetensors`) and use the server's path separator.
- A missing custom node shows up as an unknown `class_type`, not a model error.
- Out-of-memory errors: lower resolution or batch, use an FP8/GGUF variant, enable tiling, or free other GPU users. Do not retry the same graph unchanged.
- Long or non-Latin prompts belong in a UTF-8 file that the client reads, not in shell arguments.
- The first run after loading a model is slower; time the second run when you report speed.

## Acceptance checklist

- [ ] Graph validated against live `object_info` before submission.
- [ ] Only sidecar slots changed; seed recorded.
- [ ] GPU lock taken and released; no other owner's job touched.
- [ ] Outputs copied into the project; receipt with hashes and VRAM peak written.
- [ ] No duplicate weights or unreviewed downloads added.

## Boundaries

- Picking models, prompts and design QA: `design-comfy-generation`.
- Installing or upgrading ComfyUI itself, drivers or CUDA: out of scope; ask the operator.
