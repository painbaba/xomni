# Free API channels for Chinese AI models — snapshot 2026-08-07

All verified by live fetch on 2026-08-07. Terms churn monthly — re-verify
before relying on any row. "India-accessible" = signup/use without CN phone
or CN ID card.

## Channel table

| Provider | Free model(s) | Limits | Signup | India-accessible | Status |
|---|---|---|---|---|---|
| Zhipu z.ai | GLM-4.7-Flash, GLM-4.5-Flash, GLM-4.6V-Flash (all "Free"); GLM-5.2 NOT free | Flash free; flagship needs balance (new acct = error 1113) | Email; referral credits need paid subs (Stripe min $0.50) | Yes | ALIVE |
| Alibaba Model Studio (intl) | qwen3.7-max, qwen3-max, qwen-max, qwen3.6-max-preview: 1M tokens each | 90 days post-activation; Singapore scope only | Alibaba Cloud intl | Yes | ALIVE |
| Kimi/Moonshot | none for chat; file-extraction APIs limited-time free | — | CN phone | No | No free tier; Moonshot V1 dies 2026-08-31 |
| DeepSeek | none, no credits | — | Email, intl cards | Yes | Alive; price hike announced |
| MiniMax | none on LLM pricing page | — | CN phone (.cn); intl platform separate | Partial | No free tier |
| SiliconFlow | free models (¥0, fixed RPM; paid twins prefixed `Pro/`) | CN real-name ID KYC; /v1/models auth-walled | CN ID card | No | ALIVE, China-only |
| OpenRouter | 17 free variants (see SKILL.md refresh section) | standard throttling | Email | Yes | ALIVE |
| HF Inference Providers | all models w/ monthly credits: Free $0.10, PRO $2, Team $2/seat | credits auto-apply | HF account | Yes | ALIVE |
| Puter | 500+ models incl. GLM-5.2, DeepSeek, Qwen | user-pays; rate-limited per user | none | Yes | ALIVE (repo pushed 2026-08-07) |
| NVIDIA NIM | gpt-oss-120b/20b, nemotron-3-super-120b, nemotron-3-ultra-550b, llama-3.3-nemotron-super-49b-v1.5, z-ai/glm-5.2/5.1/4.7, deepseek-v4, qwen3.5-122b, qwen3-coder-480b | ~40 RPM/key; congested at IST peak | NVIDIA account | Yes | ALIVE |
| GitHub Models | — | — | — | — | DEAD (retired 2026-07-30) |

## Re-verification recipe (which URL proves what)

- **OpenRouter free list**: `curl -s https://openrouter.ai/api/v1/models` →
  filter `pricing.prompt == "0"`. 400 models total, 17 free on probe day;
  zero GLM/DeepSeek/Qwen/Kimi free variants.
- **Zhipu pricing**: `curl -sL https://docs.z.ai/guides/overview/pricing.md`
  (Mintlify raw .md). Read the column header: "Limited-time Free" sits under
  Cached Input Storage, NOT the model price. Referral rules:
  `https://docs.z.ai/devpack/credit-campaign-rules.md`.
- **Qwen quota**: `curl -sL https://www.alibabacloud.com/help/en/model-studio/billing-for-model-studio`
  — grep "Free quota"; intl page is ~1.2MB HTML, CN help.aliyun.com won't
  download from this host.
- **DeepSeek**: `curl -sL https://api-docs.deepseek.com/quick_start/pricing`
  (redirects — needs -L). No "free" anywhere; watch for price-hike notice.
- **HF credits**: `curl -sL https://huggingface.co/docs/inference-providers/en/pricing`.
- **NVIDIA NIM catalog**: `curl -sL https://docs.api.nvidia.com/nim/reference`
  → grep `apis/nvidia-nim-api-for-.*\.json` for model IDs.
- **SiliconFlow**: Mintlify `/llms.txt` index lists docs; the
  `free-inference` page 404s (`__next_error__` in shell HTML) but
  `cn/userguide/rate-limits/rate-limit-and-upgradation.md` documents the
  free-tier policy. Public `api.siliconflow.cn/v1/models` now returns
  "Invalid token" without auth.
- **GitHub Models**: docs.github.com/en/github-models/prototyping-with-ai-models
  states retirement (2026-07-30). Do not recommend it.

## Notes
- Biggest zero-budget stack for India: NVIDIA NIM (GLM-5.2, gpt-oss-120b)
  + OpenRouter free variants + Puter (GLM-5.2) + Alibaba intl 1M-token gift.
- New 2026 entrants with free frontier-class models: nemotron-3-ultra-550b
  (NIM + OpenRouter :free, 1M ctx), Ling (inclusionai/ling-3.0-tiny:free,
  Chinese 2026 startup), HF monthly credits as universal top-up.
- UNVERIFIED as of snapshot: exact SiliconFlow free-model list (API
  auth-walled), MiniMax signup bonuses, Moonshot promo credits.
