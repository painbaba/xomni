---
name: local-ai-video-generation
description: Pick local AI video models (Wan, Hunyuan, LTX) in ComfyUI.
version: 1.0.0
author: [hermes-curator]
license: MIT
metadata:
  hermes:
    tags: [ai-video, comfyui, wan, hunyuanvideo, ltx-video, video-generation, vram, licensing, documentary-broll]
    category: media
---

# Local AI Video Generation (open-source, ComfyUI-native)

Covers the class of task: "which local model stack for video X" (b-roll, documentary, social clips) + running it in ComfyUI + automating it. Complements the `comfyui` skill (that one = ComfyUI tooling/API mechanics; this one = model landscape, VRAM planning, licensing, live-docs research technique).

## When to Use
- User asks to compare/choose local video models (Wan, HunyuanVideo, LTX, AnimateDiff, SVD) for a use case.
- VRAM planning ("what can I run on my GPU?").
- Checking whether a model is commercially usable (documentary/production).
- Research deep-dives into the local video landscape that must quote live URLs.

## Model Landscape Quick Reference (live-verified Aug 2026 — full fact sheet with URLs/files in `references/2026-model-landscape.md`)

| Model | License | Res / fps | Clip len | VRAM (vendor claims) | Notes |
|---|---|---|---|---|---|
| **Wan 2.2 TI2V-5B** ⭐ | Apache 2.0 | 720p @ 24fps | ~5 s | 8 GB w/ ComfyUI offload; 24 GB for 720p w/o offload | Hybrid T2V+I2V in ONE 5B model; <9 min per 5 s 720p clip on 4090-class; best documentary b-roll default |
| Wan 2.2 T2V/I2V-A14B | Apache 2.0 | 480p + 720p | ~5 s | 24 GB+ (fp8/GGUF lowers) | MoE: 27B total / 14B active per step; TWO checkpoints (high-noise + low-noise) per direction |
| Wan 2.1 1.3B / 14B | Apache 2.0 | 480p / 720p | ~5 s | 1.3B: 8 GB | Superseded by 2.2; keep 1.3B only for ≤8 GB cards |
| HunyuanVideo 1.5 | tencent-hunyuan-community | 720p → 1080p SR | **5–10 s** | 24 GB | 8.3B; longest native clips; strong camera-motion control |
| HunyuanVideo 1.0 | tencent-hunyuan-community | 720p | 5 s | 60 GB min (vendor) | Skip on mid GPUs |
| LTX-Video 1.x (2B/13B) | LTX-Video Open Weights | ≤720×1280; realtime claim | ≤~10 s (257 fr) | low | Fastest iteration; distilled = 15× faster, no CFG/STG; long English prompts |
| LTX-2 / 2.3 (19B) | ltx-2-community-license | — | 121 fr default | — | Native audio+video in one pass; canny/depth/pose IC-LoRAs; 2× spatial+temporal upscalers |
| AnimateDiff / SVD | — | 512 px / 576×1024 | 2–4 s | ~13 GB (hi-res AD) | LEGACY — removed from official ComfyUI examples; SVD is I2V-only + non-commercial license; skip |

## Licensing Quick-Check (documentary / commercial use)
- Only **Wan 2.2 and Wan 2.1 are Apache 2.0** — clean commercial use, per official docs.
- HunyuanVideo (`tencent-hunyuan-community`) and LTX (`ltx-2-community-license-agreement`) are custom community licenses with revenue-threshold terms — always open the LICENSE link on the HF model card before paid use.
- SVD = Stability AI Community License (non-commercial).

## ComfyUI Docs Research Technique (docs restructured 2025–26)
- Old tutorial URLs (e.g. `/tutorials/video/wan/wan_2_2`, `wan_2_1`) 404. Current base: `https://docs.comfy.org/tutorials/video/<model>/...` (e.g. `/tutorials/video/wan/wan2_2`, `/tutorials/video/hunyuan/hunyuan-video-1-5`, `/tutorials/video/ltxv`, `/tutorials/video/ltx/ltx-2-3`).
- **Mintlify `.md` trick:** append `.md` to ANY docs.comfy.org page → raw markdown, perfect for `curl` + grep (e.g. `curl -sL https://docs.comfy.org/tutorials/video/wan/wan2_2.md`).
- **Discover pages via `https://docs.comfy.org/sitemap.xml`** (grep `tutorials/video`). NOTE: `llms.txt` indexes ONLY built-in-nodes/api-reference/agent-tools/account — tutorials are NOT in it.
- API docs moved: local server API examples → `/development/comfyui-server/api-examples`; agent tools → `/agent-tools/mcp`, `/agent-tools/skills`, `/agent-tools/cli`.
- `blog.comfy.org` is now a Substack newsletter ("ComfyUI Newsletter"); old blog post slugs 404 there — go to HF model cards + docs instead.

## Agent Automation (yes — agents can queue generations programmatically)
- **Local REST:** `POST /prompt` (API-format workflow JSON) + `GET /history/<id>` + `GET /view?filename=` + WebSocket `ws://127.0.0.1:8188/ws?clientId=...`. Official example scripts in `Comfy-Org/ComfyUI` `script_examples/` (basic_api_example.py, websockets_api_example.py, websockets_api_example_ws_images.py).
- **Comfy MCP (first-party, public beta):** `pip install comfy-mcp` drives a LOCAL ComfyUI (needs `comfy-cli>=1.14.0` + running server); cloud connection at `https://cloud.comfy.org/mcp`. Tools: `search_templates`, `submit_workflow`, `run_template`, `upload_file`, `wait_for_job`, `get_output`, `submit_batch`, `share_workflow`. Docs: `/agent-tools/mcp`; repo `Comfy-Org/comfy-mcp`.
- Comfy Skills repo (`Comfy-Org/comfy-skills`) = Claude Code plugin marketplace; Comfy In-App Agent exists.

## Ecosystem & Sharing
- Official hub: https://comfy.org/workflows (share IDs `<slug>-<hex>`, importable via MCP).
- Template Library in the UI = `Comfy-Org/workflow_templates` repo. Known IDs: Wan 2.2 → `video_wan2_2_5B_ti2v`, `video_wan2_2_14B_t2v`, `video_wan2_2_14B_i2v`, `video_wan2_2_14B_flf2v`; Hunyuan 1.5 → `video_hunyuan_video_1.5_720p_t2v` / `_i2v`.
- **Civitai API for gauging ecosystem:** `https://civitai.com/api/v1/models?query=wan%202.2` → JSON with `downloadCount` per item. Caveat: `types=Workflow` filter 400s — drop it, filter client-side.
- Key custom nodes: `Kijai/ComfyUI-WanVideoWrapper`, `City96/ComfyUI-GGUF` (14B GGUFs: bullerwins, QuantStack collection).

## Desktop / Browser
- ComfyUI Desktop v0.9.4 (May 2026) bundles ComfyUI v0.22.3; **Windows + macOS ARM only, still Beta, no Linux prebuild** — https://github.com/Comfy-Org/desktop/releases/latest
- The whole UI runs in a browser tab (localhost:8188, or cloud.comfy.org); Desktop wraps it with one-click model management and drag-in workflows.

## Pitfalls
1. **Vendor VRAM/speed claims need their qualifier.** Wan 2.2 5B "8 GB" relies on ComfyUI native offloading (slower); "24 GB" is without offload; Hunyuan 1.0's 60 GB is its own official minimum. Quote the qualifier, never the bare number.
2. **Windows git-bash hosts:** files written to MSYS `/tmp` are NOT readable by Windows-path tools (read_file fails) and can vanish between calls — write research artifacts into `~/<workdir>` (e.g. `~/comfy_research/`) and grep them via terminal.
3. AnimateDiff/SVD were removed from the official ComfyUI examples repo — treat as legacy; don't recommend for realistic b-roll.
4. Docs URL 404s → re-discover via sitemap.xml; don't conclude the model/topic is gone.
5. HunyuanVideo 1.0 officially needs 60 GB+ — never recommend it for mid-range GPUs; point to 1.5.
6. For per-shot consistency across b-roll clips: reuse the same seed, a style LoRA, or drive I2V from style-matched stills — models have no built-in character/location consistency across generations.

## Verification Checklist
- [ ] License verified on the HF model card (Apache vs custom community license) before claiming commercial usability
- [ ] Every VRAM/speed claim carries its qualifier (offload? fp8? resolution? which GPU?)
- [ ] Docs URLs discovered via sitemap.xml, not guessed
- [ ] Workflow template IDs confirmed against `Comfy-Org/workflow_templates`
- [ ] Every quoted fact in a research report carries its URL

## Support files
- `references/2026-model-landscape.md` — full live-verified fact sheet: exact model filenames, HF repos, VRAM numbers, workflow IDs, Civitai download counts, all source URLs.
