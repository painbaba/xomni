# AI Video Generation Landscape 2026 — Verified Knowledge Bank (Aug 9, 2026)

Full vendor-by-vendor research for DOCUMENTARY-QUALITY AI video (photoreal b-roll, archival-style footage, animated maps/charts), every number read live during the session. Companion to `video-gen-api-pricing-2026.md` (Kling/Runway API deep dive, earlier session — this file supersedes its Kling 3.0 rows where they conflict, since Kling moved from 2.x to 3.0 pricing).

## TL;DR status board
| Vendor/model | Status Aug 2026 | Max res | Max dur | Native audio | API? |
|---|---|---|---|---|---|
| Veo 3.1 (Google) | current, **preview** tier | 4K (8s only) | 8s (extend +7s → 148s) | Yes | Yes (paid tier only) |
| Gemini Omni Flash | preview, Google's recommended default | 720p | ~10s | Yes | Yes (token-based) |
| **Sora 2 (OpenAI)** | **DEAD — app Apr 26, API Sep 24, 2026** | (was 1280x720/720x1280; pro 1792x1024) | (was 12s) | — | shutting down |
| Kling 3.0 / 3.0 Omni / Turbo | current (launched Feb 5, 2026) | 4K | multi-clip/extend | Yes (3.0/Turbo) | Yes (API 2.0) |
| Runway Gen-4.5 (+ Aleph 2.0) | current | 4K upscale (API 720p) | 10s (API; Aleph 30s) | No (add audio) | Yes ($0.12/s) |
| Pika 2.5 | current (pivot: API Club aggregator) | 1080p | 25s (Pikaframes) | Pikaformance (audio) | Yes (Club) |
| Luma Ray 3.2 (Dream Machine rebranded "Luma Agents") | current | 1080p | 10s | No | Yes |
| Seedance 2.5 (ByteDance) | launched ~Jul 2026 | 720p (API) | **30s** | Yes | via Runway/Pika/fal |
| ComfyUI (open-source) | 125,308 stars, GPL-3.0, active | local models 720p-1080p | varies | LTX-Video yes | Cloud API + local |

## Pricing per second (API, USD/s, live-verified)
| Model | 720p | 1080p | 4K | Notes |
|---|---|---|---|---|
| Veo 3.1 Standard | $0.40 | $0.40 | $0.60 | 8s clips only for 1080p/4K |
| Veo 3.1 Fast | $0.10 | $0.12 | $0.30 | |
| Veo 3.1 Lite | $0.05 | $0.08 | — | released ~Apr 1, 2026 |
| Gemini Omni Flash | ~$0.10 | — | — | 5,792 tok/s video @ $17.50/1M; $1.50/1M in, $9/1M text out |
| Kling 3.0 Turbo (audio) | $0.112 | $0.14 | — | |
| Kling 3.0 (no audio) | $0.084 | $0.112 | $0.42 | |
| Kling 3.0 (audio) | $0.126 | $0.168 | $0.42 | |
| Kling 3.0 Omni (audio) | $0.112 | $0.14 | $0.42 | |
| Kling Motion Control | $0.126 | $0.168 | — | Avatar $0.056/0.112 |
| Runway Gen-4.5 (API) | $0.12 | — | — | ≤10s, text+image; credits: 12 cr/s, plan-credit math: Standard $12=52s, Max $76=791s (~$0.096/s) |
| Aleph 2.0 (Runway) | $0.28 | — | — | ≤30s video editing |
| Seedance 2.5 (Runway) | from $0.20 | — | — | ≤30s, 480p/720p |
| Luma Ray 3.2 | $0.06 | $0.24 | — | 5s $0.30 / 10s $0.90 @720p; HDR 5s-only; edit $1.08/5s; reframe $0.12/s; 360p draft $0.012/s |
| Pika API Club Kling 3.0 1080p | — | **$0.09** | — | wholesale; Seedance 2.0 R2V ~$0.0903/s; MiniMax H3 2K $0.13/s (prices as of 8.6.26) |

## Vendor notes (what matters for documentary work)
- **Veo 3.1**: image-to-video + up to 3 reference images (character/object consistency across shots — the key b-roll tool), first/last-frame interpolation (archival stills → moving shots), video extension (+7s, input ≤141s → 148s out, 720p only, 16:9/9:16). SynthID watermark. Latency 11s–6min. **Veo 3 GA and Veo 2 shut down Jun 30, 2026 — API keys only reach Veo 3.1 Preview.** No free tier.
- **Gemini Omni Flash**: multimodal in (text/image/audio/video), multi-turn conversational video EDITING (element replacement, perspective changes) via Interactions API; editing NOT available in EEA/CH/UK; negative prompts unsupported (put "Do not X" in prompt).
- **Sora 2**: `openai.com/sora` redirects → help.openai.com "What to know about the Sora discontinuation". Announced Mar 24, 2026 (TechCrunch: "OpenAI's Sora was the creepiest app on your phone — now it's shutting down"); Disney deal canceled; export via sora.chatgpt.com/sunset; unused credits → Codex. ComfyUI's OpenAIVideoSora2 node carries a deprecation notice and will be removed Sept 2026.
- **Kling 3.0**: "dual binding of visual identity and vocal tone", storyboarding, element reference; consumer app has 4K, Shorts, Motion Control, Avatar 2.0, Image 3.0 (2K/4K). API 2.0 endpoints: T2V, I2V, multi-image-I2V, multi-element editing, extension, avatar, lip sync, effects, T2A/V2A. Prepaid only: $700 min (5,000 units @ $0.14, 180-day validity, 20 concurrency). Consumer subscription prices = UNVERIFIED (login-gated; pricing page 500'd).
- **Runway**: Creative plans bundle Veo 3.1 + Kling 3.0 + Nano Banana Pro + Seedance 2.0 (Max adds Seedance 2.5 unlimited offer until Aug 14, 2026). Dev API: Model Router (cost/latency/quality routing), Workflows/Recipes/Characters, Node/Python/cURL SDKs, **MCP integration**, SOC 2 Type II, IP indemnity (enterprise). Digit (Dec 2025) same-prompt test: Gen-4.5 beat Veo 3.1 on realism/motion.
- **Pika API Club** (pika.art/api — the sleeper for agent pipelines): $10/mo membership + usage at wholesale; 100+ models through ONE key (Veo 3.1 std/fast/lite, Gemini Omni Flash, Kling 3.0 4K/Turbo/Motion Control, Seedance 2.0/2.5, MiniMax H3, FLUX 3, Grok Imagine Video, Pika 2.5, image/audio/LLM models); "agent-native" — copy one onboarding prompt into Claude Code/Codex/Cursor/Lovable/Replit; llms.txt published; enterprise volume discounts to 70%; commercial use; prices include 5% platform fee. Consumer Pika 2.5 = stylized/social-first, not top photorealism.
- **Luma**: docs.lumalabs.ai now points to docs.agents.lumalabs.ai ("Luma Agents API"); models ray-3.2 (video), uni-1/uni-1-max (images, 2K, from $0.0404/img). Async REST: POST /v1/generations → poll → presigned URLs; SDKs Py/TS/Go/CLI (`pip install luma-agents`). Provisioned Throughput $3,800/unit/mo+ with no-train guarantee. Consumer Plus $30/Pro $90/Ultra $300; Luma Agents = creative agent doing plan/generate/iterate.
- **ComfyUI**: built-in nodes for local Wan 2.1 (1.3B/14B), LTX-Video (audio VAE + reference audio), HunyuanVideo 1.5, Mochi, NVIDIA Cosmos; API nodes for Kling 3.0, Luma Ray 3.2, Runway Gen-4/Aleph 2, ByteDance/Seedance, Gemini Omni, Grok, MiniMax Hailuo, Pixverse, Pika 2.2, Vidu, HeyGen. Comfy Cloud: Standard $16/4,200cr (~380 5s videos), Creator $28/7,400cr (import own models), Pro $80/21,100cr (~1,915 5s, 1-hr runtimes), Team $630. Cloud API: submit workflow → job status → SSE live events. Comfy MCP ("turn your agent into a creative technologist").
- **Seedance 2.5**: 30s clips — longest continuous gen on the market; 480p/720p via Runway API (from $0.20/s); WION (Aug 8, 2026) frames it as the OpenAI/Google/Kling challenger.

## 2026 review verdicts (live)
- **CNET (Jul 17, 2026)**: picks = Adobe Firefly 8.0 (only commercial-safe guarantee; no native audio), Google Veo/Omni 7.5 (**best cinematic**; first major-tool native audio; no free option), Runway 7.0 (extremely creative), Midjourney 6.0. Sora removed with editor's note ("no longer generally available"). Verdict: "The best paid AI video generator for cinematic videos is Veo 3 by Google."
- **Digit (Dec 2, 2025)**: Gen-4.5 vs Veo 3.1 same-prompt — Gen-4.5 "more polished, more stable, more emotionally expressive"; Veo "more literal"; caveat: curated demo prompts.
- **CIOL (Apr 22, 2026)**: market splits cinematic/business/social; real differentiators = motion control, frame consistency, workflow integration.

## Ranked documentary stack (from the report)
1. Runway Gen-4.5 (primary workhorse — cinematic realism, $0.12/s API or Max $76/mo bundling Veo 3.1 + Kling 3.0).
2. Pika API Club ($10/mo) — cheap multi-model overflow lane, one key, agent-native.
3. Veo 3.1 — hero photoreal b-roll + archival image-to-video + native audio.
4. Kling 3.0 — budget 4K audio-native fill.
5. HyperFrames (HTML/GSAP) kept for maps/charts/typography — AI video models are wrong for text/data fidelity.
6. ComfyUI as orchestrator + local Wan/HunyuanVideo/LTX for free archival/stylized looks.

## Camofox REST innerText fetch recipe (validated this session)
```python
import json, time, urllib.request
BASE, USER = "http://localhost:9377", "docresearch"
def api(method, path, body=None, timeout=120):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())
def fetch(url, name):
    tab = api("POST", "/tabs", {"url": url, "userId": USER, "listItemId": name}).get("tabId")
    for _ in range(5):                       # poll every ~10s
        time.sleep(10)
        r = api("POST", f"/tabs/{tab}/evaluate", {"userId": USER,
                 "expression": "document.body ? document.body.innerText.slice(0, 90000) : ''"})
        txt = r.get("result") or r.get("value") or ""
        if len(txt) > 120:
            return txt
    return None
# ... save text, then: api("DELETE", f"/tabs/{tab}", {"userId": USER})
```
Start server first: `cd C:\Users\HP\camofox && npx camofox-browser` (health: `curl localhost:9377/health` → engine=camoufox). If C: drive is 100%, the server's Firefox-profile writes fail — `df -h /c`, clean `AppData/Local/Temp` + npm/pip caches. Alternative extraction via browser tools: `browser_navigate` + `browser_console` `document.body.innerText` (needs CAMOFOX_URL + Hermes restart; the REST path above needs neither).

## URL map (where each fact was fetched)
- ai.google.dev/gemini-api/docs/video | /docs/veo | /docs/omni | /docs/pricing (Veo 3.1 specs, Omni Flash, prices, deprecation warnings)
- help.openai.com/en/articles/20001152-what-to-know-about-the-sora-discontinuation (Sora sunset; reached via openai.com/sora redirect)
- klingai.com (3.0 series) · kling.ai/dev/pricing (API units) · kling.ai/document-api/quickStart/productIntroduction/overview (API 2.0, models)
- runwayml.com/pricing (plans, credits, bundled models) · dev.runwayml.com (API models/pricing, router, MCP)
- pika.art/pricing (Pika 2.5 plans + per-feature credits) · pika.art/api (API Club pricing/FAQ)
- lumalabs.ai/pricing (consumer) · docs.lumalabs.ai (points to agents docs) · docs.agents.lumalabs.ai/ + /guides/pricing (ray-3.2, uni-1, API + prices)
- docs.comfy.org/llms.txt (node index) · docs.comfy.org/built-in-nodes/OpenAIVideoSora2.md (Sora 2 params + deprecation) · comfy.org/pricing (Cloud plans) · api.github.com/repos/comfyanonymous/ComfyUI (stars/license)
- Reviews: cnet.com/tech/services-and-software/best-ai-video-generators/ (Jul 17 2026) · ciol.com/generative-ai/best-ai-video-generators-in-2026-what-actually-works-11754296 (Apr 2026) · digit.in/features/general/runway-gen-4-5-explained-creates-ai-video-better-than-veo-3-1.html (Dec 2025)
- News timeline: Bing News RSS queries (Veo 3.1 launch Oct 15 2025; vertical video Jan 2026; Veo 3.1 Lite Apr 1 2026; Kling 3.0 launch Feb 5 2026; Sora shutdown Mar 24 2026; Seedance 2.5 Jul 2026)
- Blocked/failed: openai.com via plain browser + r.jina.ai (Cloudflare/"Uh oh"); app.klingai.com/global/subscribe (500); klingai.com consumer pricing (login-gated); docs.agents.lumalabs.ai/guides/models (404); docs.agents.lumalabs.ai/llms.txt (JS shell)

Full deliverable on disk: `C:\Users\HP\ai_video_tools_2026_report.md`.
