# Free Footage & Visuals Playbook 2026 — verified knowledge bank (2026-08-09)

Purpose: $0/month documentary-quality footage sourcing — stock APIs with exact limits, free AI-video tiers, local ComfyUI video, archival/public-domain sources, free image gen for Ken-Burns. Every fact fetched live 2026-08-09 (curl / Camoufox REST / live API calls). Full playbook on disk: `C:\Users\HP\free_footage_playbook_2026.md`.

## Stock footage APIs (exact limits, primary-source verified)
| Source | API | Limits (verified) | Attribution | Commercial |
|---|---|---|---|---|
| Pexels | ✅ free key, `api.pexels.com/v1/videos/search` | **200 req/hr + 20,000 req/mo**; "unlimited requests for free" if attribution terms met (docs quote) | link-back | ✅ |
| Pixabay | ✅ free key, `pixabay.com/api/videos/` | **100 req/60s per key**; **24h result caching REQUIRED**; "Systematic mass downloads are not allowed" | requested | ✅ |
| Coverr | ⚠️ public OpenAPI spec at `coverr.co/api` (paths: /videos, /videos?query=, /videos/{id}, /storage/videos/{filename}; **no securitySchemes declared**) — **live calls return HTTP 401 without a key** (tested) | downloads: none documented, no signup, no attribution | none | ✅ |
| Mixkit | ❌ no API | free downloads | not required (Free License tier) | ✅ |
| Videvo / Mazwai | ❌ | free accounts daily-download-capped | yes (free tier) | ✅ |
| Wikimedia Commons | ✅ MediaWiki API, keyless | generous | per-item | per file |
| archive.org | ✅ full REST + advancedsearch | no hard cap; direct `archive.org/download/<id>/<file>` | PD/CC0 = none | ✅ |

**KEY 2026 market change — Videvo AND Mazwai now live under Magnific (ex-Freepik):** both `videvo.net` and `mazwai.com` serve the same "Freepik is now Magnific" Creative Suite experience (Freepik owned Mazwai since 2021, Videvo since 2022; rebranded 2026). Free stock video library persists ("All videos can be used for both personal and commercial purposes"), free accounts download-capped/day, paid plans remove caps (magnific.com/pricing). Any 2025-era reference treating Videvo/Mazwai as standalone sites is stale.

**Coverr specifics:** homepage FAQ (live): "no sign-up needed, no attribution required or hidden tricks" + "Of course you can, please do!" (commercial) + "Do you have an API? Yes, we do!" — the OpenAPI spec is served raw at coverr.co/api (2.7KB JSON, loadable via curl), but `https://api.coverr.co/videos` → **401 Unauthorized** without a key: docs public, key issuance account/contact-gated. Don't plan a keyless Coverr API pipeline; do use Coverr downloads (they're the easiest no-account free 4K b-roll).

**Mixkit:** license page (mixkit.co/license/) lists tiers live: Stock Video **Free License** + **Restricted License** (people/brand footage), plus Free Licenses for music/SFX/templates/art. Modal text is JS-loaded — curl and innerText can't capture it; review the per-item modal before monetizing identifiable-people footage.

## Cloud AI video — free tiers (verified 2026-08-09)
| Service | Free tier | Realistic output | Commercial on free |
|---|---|---|---|
| Veo (Gemini API) | **NO free tier** — pricing page: "available to developers on the paid tier", Free Tier column "Not available"; $0.40/s 720p/1080p, $0.60/s 4K | — | — |
| Veo (AI Studio consumer) | ~**50 credits/day** reported by Ventureburn listicle ONLY; login-gated, exact quota UNVERIFIED | ~50×8s/mo if real | ⚠️ |
| Kling 3.0 | **Official blog (Jul 28 2026): Basic "$0; free forever" — no monthly video credits, 30 element creations, "generated content is not for commercial use"**; app daily free credits ~66/day ≈ 6 videos (listicle) | ~6 clips/day | ❌ (official) |
| Runway | **125 one-time credits, "doesn't expire"**; Gen-4.5 = 12 cr/s → ~10s total | ~10s ever | ⚠️ |
| Pika | **80 credits/mo**, Pika 2.5 480p-only, I2V-only (Pikascenes 5s = 20 free credits → ~4 clips/mo); watermark-free + commercial = paid tiers | ~4×5s/mo | ❌ |
| Hailuo (MiniMax) | 100 daily credits (listicle) | ~10/day | ❌ |
| PixVerse | 50 daily credits (listicle) | ~5/day | ❌ |
| Vidu Q3 | 40 credits/day (listicle) | ~4/day | ❌ |
| LTX Studio | 800 one-time credits (listicle) | one session | ❌ |
| **Bing Video Creator** | **free with Microsoft sign-in**, 8s clips, Fast (~min)/Standard (~hrs) priority | unlimited-ish, queued | ✅ typically |

**Kling official credit guide facts** (klingai.com/blog/kling-video-3-0-credit-cost-guide): Video 3.0 supports **3–15s** generation; **4K = 30 credits/second**; 720p ≈ 20 cr/video (660 cr = 33 videos on Standard $6.99/mo). Paid: Standard $6.99→660cr, Pro $25.99→3000cr, Premier $64.99→8000cr, Ultra $127.99→26000cr.
**Cross-ref table source:** ventureburn.com/best-free-ai-video-generators/ (its Pika 80/mo + Runway 125 one-time matched my direct primary-source verification — table is reliable; its "Sora 30 clips/day" row is STALE, Sora app died Apr 2026).

## Archival / public domain (proven live this session)
- archive.org `collection:prelinger` → **10,467 items** (advancedsearch.php JSON). Direct MP4: `archive.org/download/<id>/`.
- **NASA Image & Video Library: keyless** — `GET https://images-api.nasa.gov/search?q=earth&media_type=video` returned 2,578 hits, no key, no auth (live test).
- LOC Free to Use and Reuse: loc.gov/free-to-use/ live.
- Bonus: archive.org CC0 audio for beds — `licenseurl:"http://creativecommons.org/publicdomain/zero/1.0/"` query (75,512 items, prior session).

## Free image gen → Ken-Burns stills
- **Bing Image Creator** (bing.com/images/create, live): "10 free creations in Fast mode. **Unlimited creations in Standard mode**", free upgrades w/ Microsoft Rewards; sign-in required.
- Local: SDXL (Open RAIL++-M, permissive) + **FLUX.1-schnell (Apache 2.0)** via ComfyUI = $0 unlimited; ⚠️ FLUX.1-dev is non-commercial. Feed stills into Wan 2.2 I2V or ffmpeg zoompan.
- DreamStudio: JS shell at fetch, credits UNVERIFIED — don't build on it.

## Local video (ComfyUI) — re-confirmed alive 2026-08-09
`Comfy-Org/Wan_2.2_ComfyUI_Repackaged` = **5,494,798 downloads** (HF API). Wan 2.2 Apache 2.0 (commercial-clean); TI2V-5B ~8GB VRAM w/ offload; HunyuanVideo 1.5 (24GB, 5–10s, community license); LTX-2 native audio+video. Agent automation: local REST POST /prompt or Comfy MCP. See `local-ai-video-generation` skill for full model landscape.

## $0/month ranked playbook (deliverable shape that worked)
Tier 1 backbone: Pexels API + archive.org(Prelinger)/NASA/LOC + local Wan 2.2 + Coverr + Bing Image Creator. Tier 2 harvest: Kling 66/day (non-commercial, test only), Pika 80/mo, Runway 125 one-time. Tier 3 skip: Hailuo/PixVerse/Vidu watermark churn, Sora dead. **Monetization rule:** YouTube-safe = stock/public-domain/local-Apache only; Kling free + Pika free explicitly non-commercial.

## Verification notes from the run
- Blocked: Pexels/Pixabay/Videvo/Mazwai via curl (403/timeout) → recovered via Camoufox REST; r.jina.ai → **403 from this host** (previous sessions used it as fallback — when jina 403s, go straight to Camoufox); Google per-model rate-limit table login-gated (Veo 50/day marked UNVERIFIED); DreamStudio JS shell.
- Google docs pages: `document.body.innerText` returns nav-only (~7KB); content tables need `window.scrollTo(0, document.body.scrollHeight); (document.querySelector('main')||document.body).innerText.slice(0,160000)`.
- All URLs fetched this session: pexels.com/api/documentation · pixabay.com/api/docs · coverr.co (+/api) · api.coverr.co/videos (401) · mixkit.co/license · videvo.net · mazwai.com · magnific.com/pricing · runwayml.com/pricing · pika.art/pricing · ai.google.dev/gemini-api/docs/{pricing,rate-limits,video,veo} · klingai.com/blog/kling-video-3-0-credit-cost-guide · ventureburn.com/best-free-ai-video-generators · bing.com/images/create · archive.org/advancedsearch.php · images-api.nasa.gov/search · loc.gov/free-to-use · huggingface.co/api/models/{Wan-AI/Wan2.2-TI2V-5B,Comfy-Org/Wan_2.2_ComfyUI_Repackaged}
