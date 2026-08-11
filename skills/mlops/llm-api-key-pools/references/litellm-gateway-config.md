# LiteLLM Gateway for Pooled Free Keys (verified 2026-08-07)

All repo statuses verified via GitHub API; all config keys verified against
live docs.litellm.ai pages on 2026-08-07. Re-verify before trusting long-term.

## Repo / ecosystem status (Aug 2026)

| Repo | Status | Notes |
|---|---|---|
| BerriAI/litellm | ALIVE, 55.8k★, pushed 2026-08-07, releases v1.95-1.97 | GitHub tagline: "Rust core with Python SDK" — rewrite in progress, but current releases + docs still use classic Python `model_list`/`litellm_params` config |
| songquanpeng/one-api | ALIVE, 36.3k★, pushed 2026-01 | Multi-user key reselling/quotas (channels/tokens); Chinese-first; no clean per-model key pinning; heavier than needed for a workforce |
| Calcium-Ion/new-api | MOVED → QuantumNous/new-api (44.6k★, pushed 2026-08-07) | Same class as one-api. Old URL 301s; use the new org |
| xtekky/gpt4free | ALIVE, 66.5k★, pushed 2026-08-07, GPLv3 | Uses unofficial/free endpoints — ToS-gray, historically takedown-targeted; no legal disclaimer in README; UNRELIABLE for production. Skip |

## Verified provider prefixes (LiteLLM, Aug 2026)

| Provider | model string | Env vars | Docs |
|---|---|---|---|
| NVIDIA NIM | `nvidia_nim/<catalog-name>` (catalog names keep their `nvidia/` or `z-ai/` prefix) | `NVIDIA_NIM_API_KEY` (+ optional `NVIDIA_NIM_API_BASE`) | https://docs.litellm.ai/docs/providers/nvidia_nim |
| Google AI Studio | `gemini/<model>` | `GEMINI_API_KEY` (no-prefix models default to Vertex AI + GCP auth) | https://docs.litellm.ai/docs/providers/gemini |
| Groq | `groq/<model>` (nested ids keep slashes: `groq/meta-llama/llama-4-scout-17b-16e-instruct`) | `GROQ_API_KEY` | https://docs.litellm.ai/docs/providers/groq |
| Cloudflare Workers AI | `cloudflare/@cf/<org>/<model>` | `CLOUDFLARE_API_KEY` + `CLOUDFLARE_ACCOUNT_ID` | https://docs.litellm.ai/docs/providers/cloudflare_workers |
| HuggingFace Inference Providers | `huggingface/<provider>/<org>/<model>` | `HF_TOKEN` | https://docs.litellm.ai/docs/providers/huggingface |
| Any OpenAI-compatible | `openai/<model>` + `api_base` | any | https://docs.litellm.ai/docs/providers/openai_compatible |

- z.ai: NOT a native provider — wire via `openai/glm-5.2` + `api_base: https://api.z.ai/api/paas/v4`. Paid-only since 2026 (error 1113, zero credits on new accounts).
- Puter: NOT wireable — JS-SDK-only (puter.ai.chat), no OpenAI-compatible HTTP endpoint.

## config.yaml (verified syntax)

```yaml
model_list:
  # NVIDIA NIM: PIN one key per model (never round-robin — 503 storms)
  - model_name: nim/glm-5.2                # reasoning lead
    litellm_params:
      model: nvidia_nim/z-ai/glm-5.2
      api_key: os.environ/NVIDIA_NIM_API_KEY_1
      rpm: 40
  - model_name: nim/gpt-oss-120b           # code drafter
    litellm_params:
      model: nvidia_nim/openai/gpt-oss-120b
      api_key: os.environ/NVIDIA_NIM_API_KEY_2
      rpm: 40
  # keys 3-6: probe per-account, pin to working models (404 = provisioning gap)

  - model_name: gemini-flash
    litellm_params:
      model: gemini/gemini-2.5-flash       # check current AI Studio catalog id
      api_key: os.environ/GEMINI_API_KEY

  - model_name: groq/scout                 # bulk worker
    litellm_params:
      model: groq/meta-llama/llama-4-scout-17b-16e-instruct
      api_key: os.environ/GROQ_API_KEY
  - model_name: groq/gpt-oss-120b          # verifier
    litellm_params:
      model: groq/openai/gpt-oss-120b
      api_key: os.environ/GROQ_API_KEY

  - model_name: cf/llama-3.3-70b           # bulk worker
    litellm_params:
      model: cloudflare/@cf/meta/llama-3.3-70b-instruct  # check CF catalog
      api_key: os.environ/CLOUDFLARE_API_KEY
      # CLOUDFLARE_ACCOUNT_ID must also be in .env

  - model_name: hf/qwen3-32b               # verifier
    litellm_params:
      model: huggingface/together/qwen/Qwen3-32B  # <provider>/<org>/<model>
      api_key: os.environ/HF_TOKEN

  - model_name: zai/glm-5.2                # reasoning backup (paid-only)
    litellm_params:
      model: openai/glm-5.2
      api_base: https://api.z.ai/api/paas/v4
      api_key: os.environ/ZAI_API_KEY

router_settings:
  routing_strategy: simple-shuffle         # default; least-busy available
  num_retries: 3                           # exponential backoff on 429
  cooldown_time: 60
  allowed_fails: 2
  enable_pre_call_checks: true

general_settings:
  master_key: os.environ/PROXY_MASTER_KEY
  background_health_checks: true
  health_check_interval: 60
  enable_health_check_routing: true        # proactive removal of dead deployments
  health_check_ignore_transient_errors: true  # 429/408 never kill routing
```

Run: `pip install 'litellm[proxy]'` → `litellm --config config.yaml`.
Clients: `OpenAI(base_url="http://localhost:4000/v1", api_key=<master_key>)`, choose
role by `model=` name. Config reference: https://docs.litellm.ai/docs/proxy/configs

## Health + 429/503 semantics (verified: https://docs.litellm.ai/docs/proxy/health_check_routing)

- `background_health_checks` (default off) + `health_check_interval` (default 300s)
  + `enable_health_check_routing` (default false) = proactive: unhealthy
  deployments are excluded BEFORE user requests land on them (reactive
  cooldown is the old default).
- `health_check_ignore_transient_errors: true` → 429/408 from health checks
  never affect routing; only hard failures (401, 404, 5xx) count.
- `router_settings.allowed_fails_policy` tunes cooldown per error class:
  `AuthenticationErrorAllowedFails`, `TimeoutErrorAllowedFails`,
  `RateLimitErrorAllowedFails` (when set, the binary health filter is bypassed;
  only the cooldown system gates routing).
- Retries: `num_retries` in router_settings; RateLimitError gets exponential
  backoff, generic errors retry immediately (https://docs.litellm.ai/docs/routing).
- Weighted failover within a model group: `enable_weighted_failover=True`
  (re-picks among remaining deployments of same model_name, excludes failed id).
- NIM 503 `ResourceExhausted (32/32)` = transient congestion → retry, ignore in
  health; NIM 404 `Function not found for account` = provisioning gap → re-pin.
- Per-model cross-provider fallbacks: https://docs.litellm.ai/docs/proxy/reliability
  (exact `fallbacks:` key spelling NOT re-verified this session).
- Client timeouts: 600s for reasoning models (DeepSeek/GLM class on NIM).

## Workforce role map (free model classes)

| Role | Models | Rationale |
|---|---|---|
| Reasoning lead | NIM `z-ai/glm-5.2`; DeepSeek V4 class on NIM (slow, 600s timeouts) | verified 4/4 workhorses; depth > speed |
| Code drafter | NIM `openai/gpt-oss-120b`; Groq `gpt-oss-120b` | verified 4/4; Groq for fast iterations |
| Verifier | Groq `llama-3.3-70b-versatile` / `llama-4-scout`; HF `qwen3-32b`; NIM nemotron-3-super-120b | cheap, low-latency re-runs |
| Bulk worker | Groq `llama-4-scout`; Cloudflare Workers AI; NIM `llama-3.3-nemotron-49b` | throughput roles tolerate queues/retries; NIM night-shift (00:00-06:00 IST) |

## Docs-access technique (docs.litellm.ai)

- Provider pages 404/block plain curl (Cloudflare) — the Mintlify `.md`-suffix
  trick does NOT work on this Docusaurus site.
- `https://docs.litellm.ai/llms-full.txt` fetches fine with a browser UA
  (it's mostly overview + changelog, not full provider pages).
- Fast path: browser_navigate to the page, then browser_console with
  `document.querySelector('.theme-doc-markdown').innerText` — sidebar noise
  excluded, code blocks included.
- Windows git-bash: `curl -o /tmp/x.txt` writes where native curl's `/tmp`
  maps, which MSYS `head`/`cat` can't see — use `~/` or native paths.
