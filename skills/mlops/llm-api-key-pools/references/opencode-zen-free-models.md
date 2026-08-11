# OpenCode Zen gateway — the free model pool (verified 2026-08-10)

OpenCode's own free channel, and the one this machine is wired to. One
OpenAI-compatible endpoint serves 25 models; the same `base_url` + key works in
EVERY OpenAI-compatible agent, so the free models are available across the whole
stack without per-agent duplication.

## The channel

- Base: `https://opencode.ai/zen/go/v1` (OpenAI-compatible `/v1/models`,
  `/v1/chat/completions`). Key: `OPENCODE_GO_API_KEY` in `.env`.
- **Browser User-Agent REQUIRED** — raw clients get HTTP 403 `error code: 1010`
  (Cloudflare browser-signature block). Add
  `"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"`.
- `GET /v1/models` returns the authoritative catalog — **models.dev is NOT
  resolvable from this host** (api.models.dev DNS fail; npm `@models.dev/api`
  404), so the gateway's own endpoint is the list to trust. The vendored
  opencode Go repo has NO embedded model registry either — providers are
  anthropic/azure/bedrock/copilot/gemini/openai/vertexai and the model list is
  runtime-fetched.

## Verified catalog (25 models, HTTP 200)

deepseek-v4-flash (default/fast/reasoning), deepseek-v4-pro (heavy reasoning),
kimi-k3 (frontier reasoning), kimi-k2.7-code (coding), kimi-k2.6/k2.5,
glm-5.2/5.1/5 (reasoning), qwen3.8-max/3.7-max (frontier), qwen3.7-plus/
3.6-plus/3.5-plus (fast coding), minimax-m3 (reasoning + VISION), minimax-m2.7/
m2.5, mimo-v2-pro/v2-omni/v2.5-pro/v2.5, hy3/hy3-preview (frontier reasoning),
gpt-5.6-luna (frontier), grok-4.5 (frontier reasoning).

- **Vision: `minimax-m3` is the only model VERIFIED with image input** (base64
  frames through chat/completions). glm-5.2 = text-only; hy3 = "no endpoints
  that support image input"; gpt-5.6-luna returns an EMPTY assistant message on
  image requests; grok-4.5/qwen3.8-max/kimi-k3 errored 503/500/500 on probe.
- Model quirks: gpt-5.6-luna returns 400 with an empty `chat.completion` body
  on unsupported content — the 400 is the model refusing, not a bad request.
- deepseek-v4-flash accepts `reasoning_effort: "high"` and always returns
  `reasoning_content`; use max_tokens >= 500 or reasoning eats the budget.

## One gateway, every agent (config snippets)

Same base_url + key, per-agent surfaces (all OpenAI-compatible):

- **Hermes** (config.yaml): `provider: opencode-go`, `base_url:
  https://opencode.ai/zen/go/v1`, `key_env: OPENCODE_GO_API_KEY`; fallback chain
  via `fallback_model:` (e.g. OpenRouter `:free` models).
- **OpenCode** (opencode.json): provider `opencode-zen` with
  `@ai-sdk/openai-compatible`, options `baseURL` + `apiKey {env:...}`, models
  block listing the ids you want.
- **Codex** (~/.codex/config.toml): `model_provider = "opencode-zen"` +
  `[model_providers.opencode-zen] base_url = ... env_key = ... wire_api = "chat"`.
- **Aider**: `aider --model openai/deepseek-v4-flash --openai-api-base
  https://opencode.ai/zen/go/v1 --openai-api-key $OPENCODE_GO_API_KEY`.
- **Goose**: `goose configure --provider openai --model ... --base-url ...
  --api-key $OPENCODE_GO_API_KEY`.

## Other free channels (cataloged, need keys — NOT wired on this machine)

NVIDIA NIM (`integrate.api.nvidia.com/v1`, free keys, per-account provisioning
trap — catalog lists models the key can't call, 404); Google AI Studio
(generativelanguage.googleapis.com, card-free, keys retire Sept 2026);
OpenRouter (`openrouter.ai/api/v1`, 17 `:free` models verified 2026-08-10,
20 RPM / 50 req/day without credits, no GLM/DeepSeek/Qwen free variants).
