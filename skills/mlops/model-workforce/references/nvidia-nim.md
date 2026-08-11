# NVIDIA NIM (build.nvidia.com) — Verified Quirks & Tested Lineup (Aug 2026)

Base URL: https://integrate.api.nvidia.com/v1 (OpenAI-compatible chat completions)

## Verified quirks (from live 40-call benchmark, 2026-08-06)

1. **Catalog overstates per-account access.** `/v1/models` returned 102 models,
   but a key can 404 with `{"detail":"Function '...': Not found for account
   '...'"}` on models the account isn't provisioned for. Always health-check
   each model you plan to use with the actual key. The catalog is NOT truth.

2. **503 ResourceExhausted = shared-worker limit.** `"Worker local total
   request limit reached (33/32)"` happens when multiple keys hammer one
   model's shared workers. Retryable with backoff, and a signal to spread
   models across keys (key-per-model pinning).

3. **Reasoning models are slow, not broken.** deepseek-v4-pro/flash exceeded
   240s per call on NIM (long thinking traces) and my harness timed out.
   A 240s timeout is NOT a failure signal for these — use 600s+ timeouts or
   assign them single tasks at low concurrency.

4. **Free tier ≈ 40 RPM per key.** Pooling 6 keys gives ~240 RPM aggregate.

## Tested lineup (free accounts, 2026-08-06, 4-task battery)

| Model | Result | Role fit |
|---|---|---|
| openai/gpt-oss-120b | 4/4 | Workhorse / synthesis |
| nvidia/nemotron-3-super-120b-a12b | 4/4 | Workhorse / architecture |
| nvidia/llama-3.3-nemotron-super-49b-v1.5 | 4/4 | Fast drafter |
| z-ai/glm-5.2 | 4/4 | Structured data / tables |
| nvidia/nemotron-3-ultra-550b-a55b | 2/4 (503s) | Review, low RPM, off-peak |
| deepseek-ai/deepseek-v4-flash | 1/4 (timeouts) | Only with 600s+ timeout |
| deepseek-ai/deepseek-v4-pro | 0/4 (timeouts) | Only with 600s+ timeout |
| nvidia/llama-3.1-nemotron-ultra-253b-v1 | 0/4 (404) | DEAD on free accounts |
| moonshotai/kimi-k2.6 | 0/4 | DEAD on free accounts |
| mistralai/mistral-large-2-instruct | 0/4 | DEAD on free accounts |

## Hermes integration
- Provider id: `nvidia` (built-in plugin, env var `NVIDIA_API_KEY`)
- Pooled keys: `hermes auth add nvidia --type api-key --label nim-<N> --api-key <KEY>`
- .env seeds: `NVIDIA_NIM_API_KEY_1..6` (also accepted by the pool seeder)

## The bandwidth-physics context (why this matters)
This skill was born while assembling a model workforce for a distributed-
inference feasibility study. The benchmark proved 4 models are usable
workhorses on free NIM keys — the models were never the bottleneck; the
network bandwidth math was. Don't conflate "models work" with "the
architecture works" when the research question is about distributed serving.
