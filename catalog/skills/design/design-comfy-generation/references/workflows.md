# Design ComfyUI workflows: models, licences, timings

Model files live under `<COMFY_ROOT>/models/<type>/`. The sidecar `*.params.json` next to each workflow is authoritative for parameter names and defaults. Verify every licence at the source before commercial release.

| Workflow | Models (under `<COMFY_ROOT>/models/`) | Defaults | Licence |
|---|---|---|---|
| t2i Z-Image Turbo | `diffusion_models/z_image_turbo_bf16.safetensors` (loaded as FP8), `text_encoders/qwen_3_4b_fp8_mixed.safetensors`, `vae/ae.safetensors` | 1024x1024, steps 8, shift 3.0, `weight_dtype=fp8_e4m3fn` (bf16 needs about 12 GB for weights) | Apache-2.0 |
| Edit Qwen-Image-Edit-2511 | `diffusion_models/qwen-image-edit-2511-Q4_K_M.gguf`, `loras/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`, `text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`, `vae/qwen_image_vae.safetensors`; custom node ComfyUI-GGUF | steps 4, cfg 1.0, Lightning strength 1.0. Strength 0 disables Lightning: then steps 40, cfg 4 | Apache-2.0 |
| Edit + extra LoRA | as above + one file from `loras/` | `extra_lora_strength` 1.0 | Apache-2.0; each LoRA has its own licence |
| Cutout BiRefNet | `background_removal/birefnet.safetensors` (native background-removal node) | outputs RGBA PNG + mask | MIT. RMBG-2.0 avoided: non-commercial |
| Face restore CodeFormer | `facerestore_models/codeformer.pth`, `facedetection/detection_Resnet50_Final.pth` + `parsing_parsenet.pth`; custom node facerestore_cf | `fidelity` 0.5, detector `retinaface_resnet50` (other detectors try to download weights at run time) | NTU S-Lab 1.0, non-commercial |
| Upscale SeedVR2 | `SEEDVR2/` 7B sharp FP8 (default) or 3B FP8 + `ema_vae_fp16` | `resolution` 2160 (short side), `color_correction=lab`, `decode_tile_size` 512, `blocks_to_swap` 0 | Apache-2.0 |

## Measured timings (16 GB consumer GPU, RTX 5060 Ti class)

- Z-Image Turbo 1024x1024: about 12 s (first run about 30 s), VRAM peak 13.6 GB.
- Qwen-Edit 2511 + Lightning: 38-48 s, peak 14.6 GB. Without Lightning (40 steps, cfg 4): about 7.5 min. With an extra LoRA: 75-89 s, peak 15.6 GB.
- BiRefNet: about 2 s. CodeFormer 512x512: about 6 s, peak 3.9 GB. SeedVR2 (resolution 1440): about 37 s, peak about 10.8 GB.

## Known limits

- Qwen-Edit keeps the scene and writes legible Cyrillic, but tests produced about one wrong letter per run. Model-rendered text is a sketch only; rebuild exact text in a vector tool.
- An extra LoRA on top of Qwen-Edit leaves almost no VRAM headroom on 16 GB; close other GPU apps first.
- SeedVR2 drops alpha. Cut out after upscaling, or upscale the RGB and the mask separately.
- Image-to-3D models (TRELLIS.2, Hunyuan3D and similar) are separate routes; record their licences and verify with a smoke test before relying on them.
