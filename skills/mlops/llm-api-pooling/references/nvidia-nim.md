# NVIDIA NIM (build.nvidia.com) free-tier specifics

Base URL (OpenAI-compatible): https://integrate.api.nvidia.com/v1
Auth: `Authorization: Bearer nvapi-...`

## Verified behavior (Aug 2026 session)

### Error semantics
- `404 {"status":404,"title":"Not Found","detail":"Function '<uuid>': Not
  found for account '<account>'"}` — the model is NOT provisioned for that
  key's account, even though `/v1/models` lists it. PERMANENT for the
  account. Drop the model; do not retry.
- `503 {"error":{"message":"ResourceExhausted: Worker local total request
  limit reached (33/32)",...}}` — shared-worker rate limit. RETRYABLE with
  backoff. Caused by too many concurrent requests to one model's worker
  (e.g. round-robinning 6 keys against the same model). Fix: pin one key per
  model so 6 keys drive 6 different models.
- 429 — per-key rate limit (stated ~40 RPM/key on free tier). Hermes
  credential pool auto-rotates on 429.

### Per-account model access
- `/v1/models` returns the platform-wide catalog (102 models in Aug 2026)
  for every key, regardless of that account's actual provisioning. Always
  probe a specific model with a tiny completion before trusting it.
- Model availability differs per account — a key that works for model A
  tells you nothing about model B.

### Known-good / known-dead on the user's accounts (Aug 2026)
- DEAD: `nvidia/llama-3.1-nemotron-ultra-253b-v1` (404 on all tasks)
- WORKS (but slow, ~2-4 min/call, easy to 503): `nvidia/nemotron-3-ultra-550b-a55b`
- Catalog highlights worth benchmarking: deepseek-ai/deepseek-v4-pro,
  deepseek-ai/deepseek-v4-flash, z-ai/glm-5.2, moonshotai/kimi-k2.6,
  openai/gpt-oss-120b, nvidia/nemotron-3-super-120b-a12b,
  nvidia/llama-3.3-nemotron-super-49b-v1.5, mistralai/mistral-large-2-instruct,
  meta/llama-3.3-70b-instruct, nvidia/llama-3.1-nemotron-70b-instruct
- Non-chat models in catalog: embeddings (nvidia/nv-embedqa-*, baai/bge-m3),
  vision (meta/llama-3.2-11b-vision, microsoft/phi-3-vision-128k),
  translation (nvidia/riva-translate-4b), guard/safety models, OCR
  (nvidia/nemoretriever-parse), reward models (nvidia/nemotron-4-340b-reward)

## User's accounts / config
- 6 keys: .env `NVIDIA_NIM_API_KEY_1..6`, temp copy at
  `~/AppData/Local/hermes/tmp_nvidia_keys.txt`
- Hermes credential pool: provider `nvidia`, labels `nim-1..6` (seed via
  `hermes auth add nvidia --type api-key --label nim-N --api-key <key>`)
- Hermes provider plugin: `plugins/model-providers/nvidia/` expects env var
  `NVIDIA_API_KEY`; base_url `https://integrate.api.nvidia.com/v1`;
  fallback models `nvidia/llama-3.1-nemotron-70b-instruct`,
  `nvidia/llama-3.3-70b-instruct`
- Benchmark outputs live at `C:\Users\HP\decentral-ai-research\bench\`

## Free-tier usage notes
- Free tier is heavily contended during the day; night runs get better
  throughput and fewer 503s. Long benchmark runs → background +
  notify_on_complete, revisit at night.
- Reasoning models (DeepSeek V4 Pro, GLM-5.2, Kimi K2.6, Nemotron Ultra)
  emit long thinking traces; allow 240s+ timeouts and expect multi-minute
  drains per call.
