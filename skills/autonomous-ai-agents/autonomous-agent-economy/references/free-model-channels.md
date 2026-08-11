# Free model channels — probe results (Aug 2026, India network)

Probe before routing agents. Only channels that answer a live probe (8s timeout, 1 attempt) belong in the pool.

## opencode-go — RELIABLE, primary
- Endpoint: https://opencode.ai/zen/go/v1/chat/completions (OpenAI-compatible)
- Model: deepseek-v4-flash (works; supports reasoning_effort param)
- Keys in Hermes .env: OPENCODE_GO_API_KEY or OPENGO_API_KEY
- REQUIRES browser User-Agent header (e.g. Mozilla/5.0 ... Chrome/126.0) or requests get rejected
- Proven: sustained real agent cycles (72-202s each) without failure
- Expect daily free-quota exhaustion → 429s. Handle with retry/backoff and low-power mode.

## Gemini AI Studio keys — DEAD (all 6, GOOGLE_AI_STUDIO_API_KEY_1..6)
Probe results (key1, key2):
- gemini-2.5-flash → 404 "This model models/gemini-2.5-flash is no longer available to new users"
- gemini-2.0-flash → 429 "You exceeded your current quota"
- gemini-2.5-pro → 429 quota
- gemini-1.5-flash → 404 not found for v1beta
- gemini-2.5-flash-lite → 404 "no longer available to new users"
- gemini-3-flash → 404 not found
Key family shares one Google account: probing key1 (2 models) tells you everything — no need to probe all 6 keys × 5 models (that was a 20-minute hang risk).

## z.ai (GLM-5.2) — key exists but out of balance
- Endpoint: https://api.z.ai/api/paas/v4/chat/completions (OpenAI-compatible)
- Models: glm-5.2, glm-4.6
- Error: HTTP 429 {"error":{"code":"1113","message":"Insufficient balance or no resource package. Please recharge."}}
- GLM-5.2 via Puter is the user's favorite model but free quota exhausts daily; Puter 2nd-account declined (solo).

## NVIDIA NIM keys (NVIDIA_NIM_API_KEY_1..6) — gateway erroring
- Earlier note: axum "Missing request extension" (their infra issue). Re-probe before trusting.

## Cache pattern
- Cache channel METADATA (name/url/model) to channels.json with 10-min TTL; NEVER write keys to the cache — reattach from .env at load.
- When the probed pool is empty → low-power mode: skip spawns, keep ledger/heartbeat, resume when a channel answers.

## Network reality (this Windows host, git-bash)
- /tmp does not exist → curl -o /tmp/x fails exit 28. Use $HOME paths.
- Bing HTML/captcha, DDG lite timeout, Mojeek captcha, Google News RSS sorry-page, Bing format=rss ignores query.
- r.jina.ai reader proxy is the reliable search/page-read path:
  - SERP: https://r.jina.ai/https://duckduckgo.com/?q=<urlencoded> → markdown with numbered results
  - Page: https://r.jina.ai/<url>
  - Google via jina is abuse-blocked for anonymous (40305) — use DuckDuckGo via jina instead.
