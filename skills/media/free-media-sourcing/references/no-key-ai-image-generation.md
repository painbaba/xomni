# No-key AI image generation — verified endpoints (2026-08)

Everything below was curl/urllib-verified on 2026-08-10 from a Windows host (git-bash). All FREE, no API keys.
State of the world changes fast — re-probe before relying on any endpoint.

## 1. Pollinations.ai — URL API, zero setup (reliable, but low-res)

- Pattern: `https://image.pollinations.ai/prompt/<URL-encoded prompt>?width=W&height=H&seed=S&nologo=true&model=<m>&private=true`
- Params that matter: `nologo=true` (removes watermark), `private=true` (skip cache), `seed` (reproducibility).
- **All models hard-cap at 768×768** (flux, flux-realism, turbo, sdxl, kandinsky, sana — requested 1024/1536 silently returns 768). `/models` endpoint currently returns `["sana"]` only.
- Returns native JPEG. Generation takes ~15–45 s. `turbo` (SDXL-turbo) gave best face coverage for portraits in tests; `flux` most consistent.
- Reproducible — same prompt+seed+model = same image. Good for regeneration recipes in reports.

## 2. Hugging Face Spaces Gradio API — the high-quality no-key route (official model spaces)

Official model Spaces expose an open, unauthenticated Gradio API. Best find: **`black-forest-labs/FLUX.1-schnell`** — true 1024–2048 px output (UI slider allows up to 2048), photoreal portraits, 4-step schnell.

### Host discovery (critical)
- Naive hostname guesses 404. Real hosts:
  - `https://black-forest-labs-flux-1-schnell.hf.space` (note hyphenation: flux-**1**-schnell)
  - `https://stabilityai-stable-diffusion-3-5-large.hf.space`
- Discover: `https://huggingface.co/api/spaces/<owner>/<name>` → runtime stage; or load the space page and read the app iframe src (`document.querySelector('iframe').src`).
- Check `GET <host>/gradio_api/info` → `named_endpoints` gives exact parameter order/types/defaults.

### Call flow
1. `POST <host>/gradio_api/call/infer` with `{"data": [<params in /info order>]}` → `{"event_id": "..."}`
2. `GET <host>/gradio_api/call/infer/<event_id>` → SSE text; the **last** `"url"` value is the output file (WEBP/PNG, NOT necessarily JPEG).
3. Download the file URL (absolute, on same host).

Sample payloads:
- FLUX.1-schnell: `{"data": ["<prompt>", 777, false, 1536, 1536, 4]}` → prompt, seed, randomize_seed, width, height, num_inference_steps
- SD3.5-Large: `{"data": ["<prompt>", "<neg_prompt>", 1111, false, 1024, 1024, 4.5, 40]}` → prompt, negative_prompt, seed, randomize, width, height, guidance, steps (max 1024)

### ZeroGPU anonymous quota — the #1 gotcha
- HF Spaces run on ZeroGPU; anonymous callers get a small GPU quota (~1–2 min per IP). After exhaustion:
  - SD3.5-style spaces: `event: error` / `data: {"error": "You have exceeded your ZeroGPU quota (65s requested vs. 0s left). Try again in 0:00:00. Authenticate with a Hugging Face token..."}`
  - Some spaces (BFL flux): bare `event: error` / `data: null` — same cause, no message.
- Reset timing is not documented; plan ~1–2 min of generations per IP, or run a retry loop (`sleep 240; retry` up to N cycles — worked pattern: got 3×1536px images in first burst, then blocked).
- A free HF token removes the cap (only needed if user allows accounts).
- Browser sessions ride a different IP/quota pool than local curl — worth trying when API is blocked.

### File URL expiry
Gradio file URLs (`/gradio_api/file=/tmp/gradio/<hash>`) are session-scoped — they die on space restart. For durable deliverables, re-upload to catbox.moe:
`curl -F "reqtype=fileupload" -F "fileToUpload=@img.jpg" https://catbox.moe/user/api.php` → returns `https://files.catbox.moe/<hash>.jpg` (anonymous, no account, verified working).

## 3. this-person-does-not-exist.com — random synthetic faces (TPDNE alternative)

- `thispersondoesnotexist.com` is DEAD (domain for sale, 2026-08). This domain works.
- Has Gender / Age / Ethnicity selectors **including `indian`** — set via JS in the browser:
  `document.querySelector('select[name="gender"]').value='male'` (also `age`, `etnic`), dispatch `change`, click Refresh.
- Generated face URL pattern: `https://this-person-does-not-exist.com/img/avatar-gen<hash>.jpg` — 1024×1024 JPEG, no watermark on the preview image (the site's *free download* button serves a watermarked 512 px version; the direct img URL is the clean preview).
- curl needs flags or it returns 200/0B: `curl -L --http1.1 -A "Mozilla/5.0..." -e "https://this-person-does-not-exist.com/en" <img-url>` (referer + UA + HTTP/1.1). urllib with UA+Referer also works.
- Random faces only — no prompt control (no "news anchor in suit"), so it ranks below prompt-controlled generators for professional avatars.

## 4. Dead ends (verified 2026-08, do not re-test)
- **thispersondoesnotexist.com** — domain for sale.
- **Perchance AI (perchance.org/ai-text-to-image-generator)** — Cloudflare Turnstile challenge, not passable from automation (checkbox click doesn't clear).
- **Craiyon v3 API** (`api.craiyon.com/v3`) — 403, needs token now.
- **Stable Horde anonymous** (aihorde.net, `apikey: 0000000000`) — accepts jobs but "No available workers" for anonymous (queue pos 300+, `is_possible: false`). Effectively dead.
- **HF Inference API** (`api-inference.huggingface.co` / router) — requires token since 2024.
- **NVIDIA NIM / Prodia / getimg / DeepAI etc.** — all need (free) API keys; out of scope for "no API keys".

## 5. Example verified output (may expire — pattern proof, not durable URLs)
- FLUX.1-schnell 1536×1536 seed 777 → catbox mirror `https://files.catbox.moe/n6g1s7.jpg` (325 KB, sharpness 283, face detected)
- FLUX.1-schnell 1344×1536 seed 999 → `https://files.catbox.moe/rjxd9b.jpg` (sharpest, 564)
- this-person-does-not-exist indian/male/35-50 → `https://files.catbox.moe/gknet9.jpg` (1024², face cov 0.49)
- Pollinations turbo seed 505 (768²) → `https://files.catbox.moe/xzeqtc.jpg`
