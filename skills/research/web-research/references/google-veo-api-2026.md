# Google Veo 3 / Veo 3.1 API — verified knowledge bank (Aug 9, 2026)

All numbers live-verified from Google's official pages on 2026-08-09. Full audit-trail report (every URL + what it confirmed, local copies of all fetched pages): `C:\Users\HP\veo_research\VEO_API_DEEP_DIVE.md`.

## Pricing (USD, per SECOND of generated video)

### Gemini API (AI Studio paid tier) — https://ai.google.dev/gemini-api/docs/pricing
Veo is **NOT on the free tier** ("Not available") — Cloud billing required. One price line per model (video WITH audio, default):

| Model (Gemini API ID) | 720p | 1080p | 4k |
|---|---|---|---|
| Veo 3.1 `veo-3.1-generate-preview` | $0.40 | $0.40 | $0.60 |
| Veo 3.1 Fast `veo-3.1-fast-generate-preview` | $0.10 | $0.12 | $0.30 |
| Veo 3.1 Lite `veo-3.1-lite-generate-preview` | $0.05 | $0.08 | — |
| Veo 3 `veo-3.0-generate-001` (deprecated) | $0.40 | | |
| Veo 3 Fast `veo-3.0-fast-generate-001` (deprecated) | $0.10 | $0.12 | $0.30 |
| Veo 2 `veo-2.0-generate-001` (deprecated) | $0.35 | | |

### Vertex AI (Gemini Enterprise Agent Platform) — https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing
Audio and silent are priced separately on Vertex:

| Model (Vertex ID) | Feature | Res | $/s |
|---|---|---|---|
| Veo 3.1 `veo-3.1-generate-001` (GA) | +Audio | 720p/1080p | $0.40 |
| | | 4k | $0.60 |
| | Video only | 720p/1080p | $0.20 |
| | | 4k | $0.40 |
| Veo 3.1 Fast `veo-3.1-fast-generate-001` (GA) | +Audio | 720p / 1080p / 4k | $0.10 / $0.12 / $0.30 |
| | Video only | 720p / 1080p / 4k | $0.08 / $0.10 / $0.25 |
| Veo 3.1 Lite `veo-3.1-lite-generate-001` (Preview) | +Audio | 720p / 1080p | $0.05 / $0.08 |
| | Video only | 720p / 1080p | $0.03 / $0.05 |
| Veo 3 `veo-3.0-generate-001` | +Audio / silent | 720p,1080p | $0.40 / $0.20 |
| Veo 2 `veo-2.0-generate-001` | Video | 720p | $0.50 (advanced controls also $0.50) |

Cost example: 8 s clip @1080p with audio = $3.20 on both platforms; silent on Vertex = $1.60; Lite = $0.64 (Gemini) / $0.40 (Vertex audio).

## Model IDs & lifecycle
- Gemini API: all Veo 3.1 = `-preview` IDs (Preview status; Veo 3/2 marked Deprecated). Docs updated Jan/Mar 2026.
- Vertex: `veo-3.1-generate-001` + `veo-3.1-fast-generate-001` **GA** (released Nov 17 2025, retirement Nov 17 2026 or later); `veo-3.1-lite-generate-001` Preview (Apr 2 2026). Vertex `*-generate-preview` endpoints deprecated/removed **Apr 2, 2026** → migrate to `*-001`.
- CONFLICT FLAG: `references/ai-video-gen-2026.md` claims "Veo 3 GA + Veo 2 shut down Jun 30 2026" — as of Aug 9, 2026 the Gemini API pricing page still lists veo-3.0-generate-001/veo-2.0-generate-001 (deprecated but present) and Vertex still serves `veo-2.0-generate-001`. Verify against https://ai.google.dev/gemini-api/docs/deprecations before asserting shutdown dates.

## Clip specs (Gemini API docs — https://ai.google.dev/gemini-api/docs/veo)
- Duration: `4`, `6`, `8` s (`durationSeconds`); **8 s mandatory for 1080p, 4k, reference images, and video extension**. Veo 2: 5–8 s.
- Resolution: 720p default; 1080p & 4k (8 s only) on Veo 3.1 Standard; Fast/Lite max 1080p; 24 fps; `video/mp4`.
- Aspect: `16:9` default / `9:16`.
- **Audio: natively generated, always on** for all Veo 3.x (dialogue in quotes, SFX, ambient cues; blocked-by-safety audio = NOT charged). Veo 2 was silent-only.
- Outputs per request: **1** on Gemini API, **1–4** on Vertex (`sampleCount` / Media Studio slider).
- Inputs: text, start-frame image, first+last frames, ≤3 reference images (not Lite), video extension (not Lite). Text input ≤1,024 tokens; input image ≤20 MB (Vertex spec).
- Latency 11 s–6 min; **videos deleted after 2 days** (download within 2 days); `personGeneration` EU/UK/CH/MENA = `allow_adult` only.

## Endpoints
- **Gemini API:** `POST https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:predictLongRunning` (`x-goog-api-key` header; body `{"instances":[{"prompt":"..."}],"parameters":{...}}`) → poll the returned operation until `done` → download `response.generateVideoResponse.generatedSamples[0].video.uri`. Request body also accepts `webhookConfig.uris[]` (per-request webhooks).
- **Vertex:** `POST https://us-central1-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/us-central1/publishers/google/models/{MODEL_ID}:predictLongRunning` (Bearer `gcloud auth print-access-token`); params: `aspectRatio`, `negativePrompt`, `personGeneration`, `resolution`, `sampleCount` (1–4), `seed` (0–4294967295), `storageUri` (optional GCS output; omit → bytes in response). Poll via `POST ...:fetchPredictOperation` with `{"operationName": "..."}` → `done:true`, `response.videos[0].gcsUri`.
- **OpenAI/Sora-compatible (Gemini API):** `POST https://generativelanguage.googleapis.com/v1beta/openai/videos` (multipart `model` + `prompt`; extra params like `duration_seconds`, `image`, `aspect_ratio` via `extra_body`) → poll `GET /v1/videos/{id}` → `status: completed` + `video.url`. Works with the standard `openai` Python package (`base_url="https://generativelanguage.googleapis.com/v1beta/openai/"`).

## Python (google-genai SDK — `pip install --upgrade google-genai`)
```python
operation = client.models.generate_videos(
    model="veo-3.1-generate-preview", prompt="...",
    config=types.GenerateVideosConfig(resolution="1080p", aspect_ratio="16:9", duration_seconds=8))
while not operation.done:
    time.sleep(10); operation = client.operations.get(operation)
video = operation.response.generated_videos[0]
client.files.download(file=video.video); video.video.save("clip.mp4")
```
Vertex mode: `GOOGLE_GENAI_USE_ENTERPRISE=True` + `GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION=global`. SDK ref: https://googleapis.github.io/python-genai/.

## Watermark & commercial
- All Veo videos carry invisible **SynthID** watermark (embedded at creation; survives crop/filter/framerate change/lossy compression) — verify via SynthID Detector portal or Gemini chat. Vertex GA models also support **C2PA** content credentials.
- Terms (https://ai.google.dev/gemini-api/terms): "Google won't claim ownership over that content"; paid tier = no training on your data; free tier = data used + human review; **EU/EEA/CH/UK: only Paid Services may be used when making API clients available to users**; Vertex Preview models explicitly allowed for production/commercial use.

## Rate limits
- Gemini API: per-model RPM/RPD live only at `aistudio.google.com/rate-limit` — **behind Google sign-in (verified)** → treat any specific Gemini-API Veo RPM as UNVERIFIED. Documented mechanics: RPM+TPM+RPD per project (not key); RPD resets midnight Pacific; spend caps per rolling 10 min: Tier 1 $10 / Tier 2 $200 / Tier 3 $200 (exceed → `429 RESOURCE_EXHAUSTED`); tiers: Free / T1 ($250 cap) / T2 (paid $100+3d, $2k cap) / T3 (paid $1k+30d, $20k–$100k+); preview models more restrictive.
- Vertex: per-model quota "Regional online prediction requests per base model per minute: **50 tokens/min**" (GA + fast/lite models), **10/min** for `veo-3.1-generate-preview`; `us-central1` only. Batch inference NOT supported; Provisioned Throughput + fixed quota supported.

## Automation (documented)
- Webhook event **`video.generated`** ("Video generation LRO completed"; payload `id`, `output_file_uri`, `file_name`) — https://ai.google.dev/gemini-api/docs/webhooks; ack 2xx fast, validate `webhook-timestamp` (reject >5 min old), dedupe via `webhook-id` (at-least-once).
- Vertex: deterministic `seed` + `storageUri` → GCS + `fetchPredictOperation` polling = pipeline-friendly.
- Interactions API (GA, recommended for agentic Gemini) does NOT cover video generation — Veo stays on `predictLongRunning`.

## Docs caveats hit this session
- Vertex model page says "Sound generation: Not supported" for `veo-3.1-generate-001`/`-fast-001` while Vertex pricing bills "Video + Audio generation" for those models (and Gemini docs say audio always-on) — billing page is authoritative; test audio before committing.
- Vertex prompt-guide page still references `veo-3.0-generate-001` "Preview" for audio — stale.
- `ai.google.dev/api/videos` 404s — Veo method docs live at `ai.google.dev/api/models` (`models.predictLongRunning`).
