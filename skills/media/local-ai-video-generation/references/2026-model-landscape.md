# 2026 Local Video Model Landscape — Live-Verified Fact Sheet (Aug 2026)

All facts below were fetched live from the cited URLs during a research deep-dive. Quotes are verbatim from those pages. Treat vendor VRAM/speed numbers as claims tied to a specific setup (offload, precision, resolution, GPU), not absolutes.

## Wan 2.2 (Alibaba) — Apache 2.0, commercial use OK
- Tutorial: https://docs.comfy.org/tutorials/video/wan/wan2_2 (raw md: append `.md`)
- "The Wan2.2 series models are based on the Apache 2.0 open source license and support commercial use."
- MoE architecture: high-noise expert (early denoising, layout) + low-noise expert (late, detail). A14B series = 27B total params, 14B active per step — https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B
- Model versions (HF): `Wan2.2-TI2V-5B` (hybrid T2V+I2V, dense 5B, Wan2.2-VAE 16×16×4 compression), `Wan2.2-T2V-A14B`, `Wan2.2-I2V-A14B` (both 480P & 720P).
- ComfyUI repackaged weights: https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged
  - 5B: `wan2.2_ti2v_5B_fp16.safetensors` (diffusion_models/) + `wan2.2_vae.safetensors` (vae/) + `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (text_encoders/, shared with 2.1)
  - 14B T2V: `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` + `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors`; uses `wan_2.1_vae.safetensors`
  - 14B I2V: `wan2.2_i2v_high_noise_14B_fp16.safetensors` + `wan2.2_i2v_low_noise_14B_fp16.safetensors`
- Resolution/fps: 720P @ 24fps; TI2V 720P = 1280×704 or 704×1280; ~5 s clips (workflow `length` param). FLF2V (first+last frame) workflow exists; Wan2.2-S2V-14B = audio-driven (image+audio→video) — https://docs.comfy.org/tutorials/video/wan/wan2-2-s2v
- VRAM: docs Tip — "The Wan2.2 5B version should fit well on 8GB vram with the ComfyUI native offloading." Official single-GPU inference for 720p TI2V: "at least 24GB VRAM (e.g., RTX 4090)".
- Speed: "TI2V-5B can generate a 5-second 720P video in under 9 minutes on a single consumer-grade GPU" (HF card, 4090-class). 4-step Lightning LoRAs: https://huggingface.co/lightx2v/Wan2.2-Lightning
- GGUF quants: https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF , QuantStack collection (https://huggingface.co/collections/QuantStack/wan22-ggufs-6887ec891bdea453a35b95f3), loader City96/ComfyUI-GGUF; wrapper Kijai/ComfyUI-WanVideoWrapper.
- Workflow template IDs: `video_wan2_2_5B_ti2v`, `video_wan2_2_14B_t2v`, `video_wan2_2_14B_i2v`, `video_wan2_2_14B_flf2v` — https://github.com/Comfy-Org/workflow_templates

## Wan 2.1
- Tutorial: https://docs.comfy.org/tutorials/video/wan/wan-video ; Apache 2.0, Feb 2025. 14B + 1.3B; T2V + I2V.
- "its lightweight version requires only 8GB of VRAM" (official docs, about 1.3B). Separate 480P and 720P I2V models (`wan2.1_i2v_480p_14B_fp16`, `wan2.1_i2v_720p_14B_fp16`).
- Components: `umt5_xxl_fp8_e4m3fn_scaled` / `umt5_xxl_fp16`, `wan_2.1_vae.safetensors`, `clip_vision_h.safetensors` (I2V) — https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged

## HunyuanVideo (Tencent)
- 1.0 tutorial: https://docs.comfy.org/tutorials/video/hunyuan/hunyuan-video — 13B DiT; T2V Dec 2024, I2V Mar 2025 (v1 "concat" = more motion / v2 "replace" = better image adherence); 720p, 5 s clips; text encoders `clip_l` + `llava_llama3_fp8_scaled`; custom 3D VAE.
- Official VRAM (vendor): "Minimum… 60GB for 720px1280px129f and 45G for 544px960px129f. Recommended… 80GB" — https://huggingface.co/tencent/HunyuanVideo (FP8 weights released to cut memory). Too heavy for mid GPUs.
- 1.5 tutorial: https://docs.comfy.org/tutorials/video/hunyuan/hunyuan-video-1-5 — 8.3B, "delivers flagship-quality video generation on consumer GPUs (24GB VRAM)" (official docs); T2V + I2V, **5–10 s clips**, native 720p upscalable to 1080p via `hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors`; encoders `qwen_2.5_vl_7b_fp8_scaled` + `byt5_small_glyphxl_fp16`; I2V vision `sigclip_vision_patch14_384`; VAE `hunyuanvideo15_vae_fp16`. Template IDs: `video_hunyuan_video_1.5_720p_t2v` / `_i2v`.
- License (1.5): `tencent-hunyuan-community` — https://huggingface.co/tencent/HunyuanVideo-1.5 (NOT Apache; verify commercial terms).

## LTX (Lightricks)
- LTX-Video 1.x: https://docs.comfy.org/tutorials/video/ltxv ; model https://huggingface.co/Lightricks/LTX-Video — 2B/13B (0.9.5 → 0.9.8). "the first DiT-based video generation model capable of generating high-quality videos in real-time", 30 FPS @ 1216×704 claim; works best <720×1280 and <257 frames (~10 s); distilled versions "15× faster, real-time capable… no STG/CFG required"; long descriptive English prompts; text encoder `t5xxl_fp16`. Official ComfyUI workflows: https://github.com/Lightricks/ComfyUI-LTXVideo
- LTX-2: https://docs.comfy.org/tutorials/video/ltx/ltx-2 ; model https://huggingface.co/Lightricks/LTX-2 — 19B DiT, synchronized audio+video in one pass; T2V/I2V/V2V; Canny/Depth/Pose IC-LoRAs; keyframe interpolation; distilled 8-step (`ltx-2-19b-distilled`); spatial(2×)+temporal(2×) upscalers; 121-frame default @ 24fps. LTX-2.3 current: https://docs.comfy.org/tutorials/video/ltx/ltx-2-3
- Licenses: LTX-Video Open Weights License / `ltx-2-community-license-agreement` (both "other" on HF; revenue-threshold terms — check before commercial use).

## Legacy (skip for production)
- AnimateDiff: https://github.com/guoyww/AnimateDiff — SD1.5 motion modules; 16 frames @ 8fps ≈ 2 s; 512px-class; "1024x1024x16 frames… requires ~13GB VRAM" (README). ComfyUI integration still maintained: https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved. **Removed from official examples** (no animatediff/ dir in https://github.com/comfyanonymous/ComfyUI_examples).
- SVD: https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt — I2V only, ~2–4 s, 576×1024, 14/25 fps; Stability AI Community License (non-commercial). Same examples repo dropped it.

## Automation (agent-drivable, no API fees locally)
- Local server API examples (3 patterns: HTTP fire-and-forget, WebSocket+History, SaveImageWebsocket): https://docs.comfy.org/development/comfyui-server/api-examples — sources in Comfy-Org/ComfyUI `script_examples/` (basic_api_example.py, websockets_api_example.py, websockets_api_example_ws_images.py). Endpoints: `POST /prompt`, `GET /history/<id>`, `GET /view?filename=…`, WS `ws://127.0.0.1:8188/ws?clientId=…`.
- Comfy MCP (first-party, public beta): https://docs.comfy.org/agent-tools/mcp — `pip install comfy-mcp` (local, open source; requires `comfy-cli>=1.14.0` + running ComfyUI; `COMFY_BIN` env for non-PATH comfy) and cloud at `https://cloud.comfy.org/mcp` (X-API-Key header or OAuth). Tools: search_templates / search_models / search_nodes / cql / get_prompting_guide; run_template / submit_workflow / partner_generate / upload_file / apply_slots; get_job_status / wait_for_job / get_output / submit_batch; save/run/share_workflow; create_app. Repo: https://github.com/Comfy-Org/comfy-mcp
- Comfy Skills (Claude Code plugins): https://github.com/Comfy-Org/comfy-skills ; in-app agent: https://docs.comfy.org/agent-tools/in-app-agent
- Desktop: v0.9.4 (2026-05-28) bundles ComfyUI v0.22.3; Windows + macOS ARM installers; Beta; no Linux prebuild — https://github.com/Comfy-Org/desktop/releases/latest ; https://docs.comfy.org/installation/system_requirements

## Ecosystem numbers (live, Aug 2026)
- Civitai search `api/v1/models?query=wan 2.2`: "WAN 2.2 Workflow T2V-I2V-T2I (Kijai Wrapper)" 63,202 dl; "Wan 2.2 14b Long video Workflow (30 sec+)" 17,707 dl; "WAN 2.2 i2v workflow for LONG videos – SVI + GGUF + UPSCALING!" 13,704 dl; "WAN 2.2 I2V GGUF COMPACT + SPEED WF (Lightning Lora 4+4 steps)" 8,411 dl.
- Official hub: https://comfy.org/workflows (share IDs `<slug>-<hex>`); templates: https://github.com/Comfy-Org/workflow_templates

## Research technique notes (from the session)
- Mintlify `.md` suffix on any docs.comfy.org URL → raw markdown for curl+grep. Page discovery: sitemap.xml. `llms.txt` does NOT include tutorials (only built-in-nodes / api-reference / agent-tools / account).
- blog.comfy.org redirected to a Substack ("ComfyUI Newsletter"); legacy blog slugs 404.
- Windows git-bash: MSYS `/tmp` files were unreadable by Windows-path read_file and vanished between terminal calls — persist research artifacts under `~/<workdir>`.
- Civitai API `types=Workflow` filter returns 400 — query without it and filter client-side.
