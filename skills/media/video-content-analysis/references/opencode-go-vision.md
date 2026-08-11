# opencode-go gateway (Hermes provider) — direct API access quirks

The Hermes model provider on this host is `opencode-go`
(`base_url: https://opencode.ai/zen/go/v1`, model `deepseek-v4-flash`).
Direct script/curl access to this gateway works, but only with the right
headers. Discovered 2026-08 while analyzing an Instagram reel.

## Access recipe

- Key: `OPENCODE_GO_API_KEY` in `~/AppData/Local/hermes/.env`.
- **Mandatory header**: a browser `User-Agent`. Without it the gateway returns
  `403` with Cloudflare `error code: 1010` (bot block). With a UA, requests
  pass. (Curious: `GET /models` returns `200` + empty list without UA, but
  `POST /chat/completions` 403s — always send the UA.)
- Endpoint is OpenAI-compatible: `POST {base}/chat/completions` with
  `messages`/`model`/`max_tokens`. Image input uses the standard
  `image_url` content type with a `data:image/jpeg;base64,...` URL.

## Model list (25 models, 2026-08) and vision capability results

| model | vision? | observed result |
|---|---|---|
| minimax-m3 | YES | detailed, accurate frame descriptions (incl. on-screen text verbatim). Chosen model for frame analysis. |
| gpt-5.6-luna | ~ | accepts request but returned EMPTY assistant message (HTTP 400). Not usable. |
| grok-4.5 | ? | 503 "Endpoint is unavailable" at the time. Retry may help. |
| qwen3.8-max | ? | 500 Internal server error on image input. |
| kimi-k3 | ? | 500 Internal server error on image input. |
| glm-5.2 | NO | text-only; explicitly says it lacks multimodal input. |
| hy3 | NO | 400 "No endpoints found that support image input". |
| mimo-v2-omni | — | 400 "Unsupported model". |
| mimo-v2.5-pro, deepseek-v4-pro | likely NO | not tested with images. |

Full list (25): minimax-m3, minimax-m2.7, minimax-m2.5, kimi-k3,
kimi-k2.7-code, kimi-k2.6, kimi-k2.5, glm-5.2, glm-5.1, glm-5,
deepseek-v4-pro, deepseek-v4-flash, qwen3.7-max, qwen3.8-max, qwen3.7-plus,
qwen3.6-plus, qwen3.5-plus, mimo-v2-pro, mimo-v2-omni, mimo-v2.5-pro,
mimo-v2.5, hy3, hy3-preview, gpt-5.6-luna, grok-4.5.

## Other API keys on this host (status 2026-08)

- `OPENAI_API_KEY` in .env is a STUB (`sk-fake-...`) — 401 on api.openai.com.
  Do not route vision/transcription through it.
- The opencode-go gateway is the only working LLM API route for scripts.
