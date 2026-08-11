# Western provider free tiers (verified 2026-08-07 — re-verify, terms churn)

All facts below were read from live pages on 2026-08-07. Every limit cites
its source URL. Anything console-gated is marked UNVERIFIED (only visible
after signup). India access could NOT be confirmed on any live page — treat
as unverified and test at signup.

## Recurring free API tiers (no card): the shortlist
Only 4 of 11 Western providers have a recurring, card-free API free tier:
**Google AI Studio, Groq, Cloudflare Workers AI, Mistral**.

## Google AI Studio (Gemini) — best overall
- Free tier: "Free input & output tokens", "limited access to certain
  models". No card required. Free-tier content IS used to improve products;
  Grounding/Google Search/Maps tools NOT available on Free.
  Source: https://ai.google.dev/gemini-api/docs/pricing
- Free on Free tier (price "Free of charge"): `gemini-3.6-flash`,
  `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`,
  `gemini-2.5-flash`, `gemini-2.5-pro` (still free!), 3.1-flash-live,
  omni-flash previews.
- **NOT free: `gemini-3.1-pro-preview`** — pricing table says "Not
  available" on Free tier (input $2.00/M, output $12.00/M paid-only).
  Same for 3-pro-image preview. Frontier Pro-class = paid.
- Rate limits (RPM/TPM/RPD) are now **auth-gated**: docs page describes
  mechanics only (per-project, RPD resets midnight Pacific, preview models
  stricter, free tier has no spend cap) and points to the AI Studio console
  for actual numbers: https://aistudio.google.com/rate-limit (login needed).
  Source: https://ai.google.dev/gemini-api/docs/rate-limits
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=KEY`

## Groq — best raw throughput
- Free plan table (live, no card): https://console.groq.com/docs/rate-limits
- `llama-3.3-70b-versatile`: 30 RPM / 1K RPD / 12K TPM / 100K TPD
- `llama-3.1-8b-instant`: 30 RPM / 14.4K RPD / 6K TPM / 500K TPD
- `openai/gpt-oss-120b`, `qwen/qwen3.6-27b`: 30 RPM / 1K RPD / 8K TPM / 200K TPD
- `groq/compound`: 30 RPM / 250 RPD / 70K TPM
- **No Llama 4 model is on the free list** (as of 2026-08-07).
- Limits are per-organization, not per-key.

## Cloudflare Workers AI — daily allowance, with a catch
- Free + Paid Workers plans: **10,000 neurons/day free**, resets 00:00 UTC,
  then $0.011 / 1,000 neurons (Paid plan only).
  Source: https://developers.cloudflare.com/workers-ai/platform/pricing/
- BIG GOTCHA: some frontier models are **excluded from the free allowance —
  they require a paid billing method even to use your 10k neurons**:
  `@cf/moonshotai/kimi-k2.6`, `@cf/moonshotai/kimi-k2.7-code`,
  `@cf/zai-org/glm-5.2`. So GLM-5.2 is NOT free on Cloudflare.
- Budget math: llama-3.3-70b = 26,668 neurons/M input tokens →
  ~350-375K input tokens/day free; small models (llama-3.2-1b =
  2,457 neurons/M) go much further.

## Mistral La Plateforme — free mode, caps hidden
- "Free mode: API access is enabled by default with no credit card
  required. Usage and rate limits apply."
  Source: https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key
- Exact RPM/TPM caps are console-only (UNVERIFIED):
  https://console.mistral.ai/limits
- Frontier-class free: Mistral Medium 3.5 (Modified MIT), Small 4
  (Apache 2.0), Magistral Medium reasoning model.
  Source: https://docs.mistral.ai/ (model cards)
- Docs restructured mid-2026: old `docs/deployment/laplateforme/tier` page
  is 404 — use llms-full.txt (https://docs.mistral.ai/llms-full.txt) or the
  new /studio-api/* paths.

## Cerebras — one-time $5, CARD REQUIRED, no permanent tier
- Free Trial = **$5 credits, expires 30 days**; requires a VERIFIED PAYMENT
  METHOD (card) at signup — without it Playground/API stay inactive.
  Explicit FAQ: "Cerebras doesn't currently offer a no-cost tier that
  renews automatically." Source: https://inference-docs.cerebras.ai/support/rate-limits
  (append `.md` for markdown; docs.cerebras.ai/cloud/* 404s — inference
  docs moved to inference-docs.cerebras.ai)
- Free Trial limits (all models): **5 RPM / 30K TPM / 1M TPH / 1M TPD**.
  Models: `gpt-oss-120b`, `zai-glm-4.7`, `gemma-4-31b`.
- Dual-bucket rate limiting: uncached TPM (primary) + total TPM = 3x
  uncached; cache hits stretch the uncached bucket.

## Cohere — trial key, tiny quota
- Trial/eval keys: **1,000 API calls per month**, 20 req/min for Command A,
  Command A+, Command A Reasoning, Command A Vision, Command R+.
  Source: https://docs.cohere.com/docs/rate-limits (`.md` suffix works)

## No recurring free API tier (verified)
- **Together AI**: no free credits/models published; rate limits are
  DYNAMIC per model (scale with sustained usage; 429/503 semantics
  documented), build tiers (1-5) retired. Source:
  https://docs.together.ai/docs/rate-limits (.md) and
  https://docs.together.ai/docs/billing-usage-limits.md
- **Azure AI Foundry** (renamed "Microsoft Foundry" — pricing page
  redirects): no recurring free inference tier; only the generic $200/30-day
  new-account credit (card required). Source:
  https://azure.microsoft.com/en-us/pricing/details/ai-foundry/
- **AWS Bedrock**: "Get started for free" banner links to signup only; NO
  free-tier token amounts anywhere on the pricing page; requires AWS
  account + card. Source: https://aws.amazon.com/bedrock/pricing/
- **GitHub Models: RETIRED 2026-07-30** — playground, catalog, inference
  API, BYOK all gone; redirects users to Azure AI Foundry.
  Source: https://docs.github.com/en/github-models/prototyping-with-ai-models

## SambaNova Cloud — UNVERIFIED (docs unreachable)
docs.sambanova.ai/cloud/* returns 404 / empty Next.js renders from this
host (tried rate-limits, getting-started, llms.txt). Free tier status
unknown — do not rely on it without a live check.

## Docs-fetching notes that generalize
- Mintlify `.md` suffix trick works for: Together (docs.together.ai/docs/<page>.md),
  Cohere (docs.cohere.com/docs/<page>.md), Cerebras inference docs
  (inference-docs.cerebras.ai/<path>.md). Fails on Docusaurus (docs.litellm.ai)
  and on Mistral (moved/JS SPA — use llms-full.txt).
- Google AI Studio docs are browser-friendly (curl hits an OAuth redirect);
  the browser works unauthenticated for pricing + rate-limits pages.
- Azure pricing page returns "Microsoft Foundry" title — the product was
  renamed; search by new name.
