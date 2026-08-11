# NVIDIA NIM Free Tier — Quirks & Observed Behavior

Observed 2026-08-06 on build.nvidia.com free keys (6-key pool, provider
`nvidia` in Hermes, base URL https://integrate.api.nvidia.com/v1).
These are empirical findings from a live benchmarking session.

## Error signatures (learn to read them)

1. **404 "Function not found for account"**
   `{"status":404,"title":"Not Found","detail":"Function '...': Not found
   for account 'x95b-...'"}`
   Meaning: model IS listed in /v1/models but THIS key/account cannot call
   it. Per-account provisioning gap. NOT transient — do not retry, mark
   model DEAD for that account. Different keys (accounts) can see
   different working sets.

2. **503 ResourceExhausted (Worker local request limit)**
   `{"error":{"message":"ResourceExhausted: Worker local total request
   limit reached (33/32)",...}}`
   Meaning: NVIDIA's shared worker for that model is saturated. Transient
   — retry with backoff. Cause: hammering one model from many keys at
   once (round-robin). Fix: pin one key per model.

3. **Read timeout** (`The read operation timed out`)
   Meaning: model is alive but slow — DeepSeek V4 Pro/Flash take >240s
   per reasoning call on NIM. Raise timeout to 600s. NOT a failure.

## Catalog realities (102 models listed, 2026-08-06)

Working on the user's 6 free keys (verified via benchmark):
- openai/gpt-oss-120b — 4/4 tasks OK (reasoning, coding, domain, structured)
- nvidia/nemotron-3-super-120b-a12b — 4/4 OK
- nvidia/llama-3.3-nemotron-super-49b-v1.5 — 4/4 OK (fast)
- z-ai/glm-5.2 — 3/3 OK (structured, coding, reasoning)
- nvidia/nemotron-3-ultra-550b-a55b — 2/4 OK, 2x 503 (flaky, slow, night-shift only)
- deepseek-ai/deepseek-v4-flash — 1/4 OK, 3x timeout (slow)
- deepseek-ai/deepseek-v4-pro — 0/4, all timeout (slowest)

DEAD on these accounts (404/limit despite being listed):
- nvidia/llama-3.1-nemotron-ultra-253b-v1 (404 all 4)
- moonshotai/kimi-k2.6 (404 all 4)
- mistralai/mistral-large-2-instruct (all 4 FAIL)

Notable catalog entries: deepseek-v4-pro/flash, kimi-k2.6, glm-5.2,
gpt-oss-120b/20b, nemotron-3-ultra-550b, nemotron-3-super-120b,
llama-3.3-nemotron-super-49b-v1.5, embeddings (bge-m3, nv-embedqa-*,
arctic-embed-l), vision (llama-3.2-90b-vision, phi-3-vision, fuyu-8b),
riva-translate, nemotron-guard safety models.

## Key facts

- Free tier ~40 RPM per key; 6 keys ≈ 240 RPM aggregate
- Provider plugin expects env var `NVIDIA_API_KEY` (single), but the
  real multi-key mechanism is the Hermes credential pool (`hermes auth
  add nvidia --type api-key --label nim-N --api-key <key>`)
- `hermes model --refresh` wipes the picker cache and re-fetches every
  provider's live /v1/models
- The 550B/253B "Ultra" class are MoE behemoths — cold-start slow, heavy
  worker contention. Schedule them at night / low concurrency.

## Benchmark methodology that worked

10 models x 4 tasks (reasoning / coding / domain / structured), 6 keys as
thread workers, 240s timeout (raise to 600s for reasoning models), every
output saved to disk under `bench/<model>/<task>.txt` with a STATUS line.
Round-robin keys = 503s on shared models; one-key-per-model = clean.
See scripts/bench_models.py in this skill for the reusable harness.

## Related pools on this machine

- Gemini: 6 keys GOOGLE_AI_STUDIO_API_KEY_1..6 in .env + auth pool
  (auto-rotate on 429), gemini-3.6-flash = newest flash
- NVIDIA NIM: 6 keys NVIDIA_NIM_API_KEY_1..6 in .env + pool labels
  nim-1..6 (seeded via hermes auth add, provider `nvidia`)
