# TTS providers for documentary narration — live-verified Aug 2026

All figures fetched live 2026-08-09 from official pages. Re-verify before spending money (prices move).

## ElevenLabs creative plans — elevenlabs.io/pricing

| Tier | $/mo | Credits/mo | ≈ TTS min | Notes |
|---|---|---|---|---|
| Free | $0 | 10,000 | ~10 | no commercial license, 3 projects |
| Starter | $6 | 30,000 | ~30 | +Commercial License, Instant Voice Cloning; extra ~$0.20/min |
| Creator | $22 ($11 1st mo) | 121,000 | ~121 | +Professional Voice Cloning; annual ≈ $18.33/mo |
| Pro | $99 | 600,000 | ~600 | +44.1kHz PCM via API, 192kbps; annual ≈ $82.50/mo |
| Scale / Business | $299 / $990 | 1.8M / 6M | ~1,800 / ~6,000 | 3 / 10 PVC slots, seats |

- 1 char = 1 credit (Multilingual v2 + v3 on website); Flash/Turbo API = 0.5–1 credit/char.
- Rollover: unused credits up to 2 months, max 3× quota; not on Free. Regenerations charged per request.
- Audio quality: Free–Creator 128kbps 44.1kHz; Pro+ adds 192kbps.

## ElevenLabs API pricing — elevenlabs.io/pricing/api (billed in USD, not credits)

- TTS **Multilingual v2/v3: $0.10 per 1K chars** (~$0.10/min; ~250–300 ms latency; "32 languages" per this page).
- TTS **Flash/Turbo: $0.05 per 1K chars** (~75 ms; real-time grade — not for cinematic VO).
- **Per-request cap: 40,000 characters** → a 60-min doc needs 2+ requests.
- API-track monthly char inclusions (Multilingual): Free 10k · Starter 60k · Creator 220k · Pro 990k · Scale 2.99M · Business 9.9M. ⚠️ These differ from creative-plan credit volumes (Starter 60k vs 30k, Creator 220k vs 121k) — both quoted as displayed on their live pages.

## ElevenLabs long-form stitching — docs/api-reference/text-to-speech/convert

- `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}` · header `xi-api-key` · body `text` (req), `model_id` (default `eleven_multilingual_v2`), `voice_settings`, `seed`, `apply_text_normalization` auto/on/off.
- Continuity across split requests: `previous_request_ids` / `next_request_ids` (≤3 each) + `previous_text` / `next_text`; `seed` for deterministic re-runs. Stitching needs history logging (off in zero-retention mode).
- `output_format` default `mp3_44100_128`; 192kbps MP3 = Creator+ (API doc; pricing page lists it Pro+ — conflict, verify); PCM/WAV 44.1kHz = **Pro+**.
- Streaming: `POST .../text-to-speech/{voice_id}/stream` + WebSocket (WSS) endpoints. `GET /v1/models` returns per-model char limits / cost multipliers — needs auth (404 without key).

## ElevenLabs models for narration

- **`eleven_v3`**: latest, "most expressive"; audio tags (`[sad] [angry] [whispers] [shouts] [laughs] [clears throat]`), dialogue mode, "70+ languages" (per v3 help page — API page says 32, conflict). 1 credit/char website; API discounted to $0.10/1K. Official caveat: "more variable consistency and higher latency… not suitable for real-time" — fine for offline narration. Pace via speed setting; punctuation/ellipses/caps shape delivery.
- **`eleven_multilingual_v2`**: still the default `model_id` on the endpoint; 32 languages; the proven narration workhorse.

## Voice cloning (docs/eleven-creative/voices/voice-cloning)

- **IVC** (Starter+): 1–2 min audio, near-instant, no training; weak on unique voices/accents; >2–3 min can hurt stability.
- **PVC** (Creator+, 1 slot; Scale 3; Business 10): 30–180 min audio, fine-tune ~2–6 h (up to 24 h), **own voice only + verification**; "virtually indistinguishable". Voices not exportable; downgrading below Creator locks the PVC.
- OpenAI custom voices: ≤30 s sample + consent recording, ≤20/org, sales-gated.

## OpenAI gpt-4o-mini-tts (developers.openai.com)

- **$0.60/1M input text tokens · $12.00/1M audio output tokens** (model page; max 2,000 input tokens). Snapshots: `gpt-4o-mini-tts-2025-03-20`, `-2025-12-15` (default).
- Audio conversion (realtime managing-costs guide): assistant audio = **1 token per 50 ms** → 1,200 tok/min → 60 min ≈ 72k tokens ≈ **$0.86** + trivial input. Community-cited 1,800 tok/min → $1.30. Budget ~$1 per 60 min.
- `POST /audio/speech`: `input` ≤ **4096 chars** (~15 requests/60 min), model `gpt-4o-mini-tts`, voice = 13 built-ins (`alloy ash ballad coral echo fable onyx nova sage shimmer verse marin cedar`; **`marin`/`cedar` recommended**), `instructions` (accent/tone/speed/emotion — not for tts-1/tts-1-hd), `response_format` mp3/opus/aac/flac/wav/pcm, `speed` 0.25–4.0, `stream_format` sse/audio. AI-disclosure to end users required by usage policies.
- Rate limits (Tier 1): 500 RPM / 50k TPM.
- `openai.com/api/pricing` and `help.openai.com` are Cloudflare-walled for bots; **developers.openai.com `.md` export works fine**.

## edge-tts (current default — free)

- Microsoft Edge online service via `pip install edge-tts`; `--rate/--volume/--pitch` (negative values need `--rate=-50%` form); unofficial → no commercial guarantee, throttling risk. Our default documentary voice: `en-US-ChristopherNeural`.
- **License = LGPLv3** (only `src/edge_tts/srt_composer.py` is MIT — verified in repo LICENSE, Aug 2026). OK as a CLI pipeline tool (output audio isn't a derivative work); don't embed the library in a closed-source product without thinking. For monetized-at-scale narration, keep a license-clean fallback: free tiers in `free-media-stack-2026.md` (Kokoro = best local, Apache-2.0).
- edge-tts voices are Microsoft Azure neural voices (e.g. ChristopherNeural) exposed via the Edge endpoint — same voice names are available through paid Azure Speech (F0 free tier = 0.5M chars/mo) if you ever need a licensed path with the identical voice.

## Cost model: 60 min narration ≈ 60k chars (~150 wpm ≈ 1,000 chars/min)

- edge-tts $0 · OpenAI ~$0.86–1.30 · ElevenLabs API $6.00 (Multilingual v2/v3) / $3.00 (Flash) · ElevenLabs Creator $22/mo covers ~220 min incl. PVC.
- Verdict: monetized → paid is worth it (commercial license + quality); cheapest serious upgrade = OpenAI ~$1/60 min; best quality + cloning = ElevenLabs Creator; Pro only if 44.1kHz PCM/192kbps output needed.

## Docs-fetch technique (reusable for research passes)

- ElevenLabs docs: append `.md` to any docs URL (`.../docs/api-reference/text-to-speech/convert.md`); `https://elevenlabs.io/docs/llms.txt` = full page index; `llms-full.txt` = whole docs in one file. Stub pages (404) list "Similar pages" with the current correct URLs (e.g. voice cloning moved to `/docs/eleven-creative/voices/`).
- OpenAI: same `.md` pattern on developers.openai.com (`/api/docs/pricing.md`, `/api/docs/models/gpt-4o-mini-tts.md`, API-reference method pages).
- Marketing/pricing pages (`elevenlabs.io/pricing`) are Next.js but server-render their FAQ content — plain curl + HTML-strip works; only interactive calculators need a browser.
