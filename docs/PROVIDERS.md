# XOMNI Providers — connect ANY provider Hermes supports

XOMNI runs on the Hermes host, so every provider Hermes supports is a provider
XOMNI supports. Two layers:

1. **The 25 verified free models** (opencode.ai Zen gateway, one key:
   `OPENCODE_GO_API_KEY`) — the zero-cost default, verified to actually work.
2. **Bring-your-own provider** — every Hermes channel below, via `config.yaml`
   (`providers.<id>` block) + `.env` (the API key). `xomni providers` prints
   this table from the terminal.

## The provider catalog

| Provider | Env var | base_url | Notes |
|---|---|---|---|
| Zen gateway (opencode.ai) | `OPENCODE_GO_API_KEY` | `https://opencode.ai/zen/go/v1` | 25 verified free models — the XOMNI default |
| OpenRouter | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` | all models incl. `:free` tier |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | `https://api.anthropic.com` | claude-*; `ANTHROPIC_BASE_URL` override |
| OpenAI | `OPENAI_API_KEY` | `https://api.openai.com/v1` | gpt-*; `OPENAI_BASE_URL` override |
| Google AI Studio (Gemini) | `GOOGLE_API_KEY` | `https://generativelanguage.googleapis.com/v1beta` | gemini-3.6-flash family, vision |
| DeepSeek | `DEEPSEEK_API_KEY` | `https://api.deepseek.com/v1` | deepseek-chat / reasoner |
| xAI (Grok) | `XAI_API_KEY` | `https://api.x.ai/v1` | grok-* |
| Groq | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` | fast open-weights: llama-*, qwen-* |
| Mistral | `MISTRAL_API_KEY` | `https://api.mistral.ai/v1` | mistral-* |
| Together AI | `TOGETHER_API_KEY` | `https://api.together.xyz/v1` | open-weights hosting |
| Fireworks AI | `FIREWORKS_API_KEY` | `https://api.fireworks.ai/inference/v1` | open-weights hosting |
| Cerebras | `CEREBRAS_API_KEY` | `https://api.cerebras.ai/v1` | fast inference |
| Azure OpenAI | `AZURE_OPENAI_API_KEY` | `https://<res>.openai.azure.com/` | enterprise; + `AZURE_OPENAI_ENDPOINT` |
| Nous Portal | `NOUS_PORTAL_API_KEY` | `https://portal.nousresearch.com/v1` | Nous models; OAuth alternative |
| Ollama (local) | — (auto) | `http://127.0.0.1:11434/v1` | zero-install `ollama/start-ollama.ps1`, qwen2.5:3b |
| LM Studio (local) | — (auto) | `http://127.0.0.1:1234/v1` | any GGUF |
| Custom OpenAI-compatible | `CUSTOM_API_KEY` | any https URL | BYO-provider escape hatch |

## How to connect (any provider)

1. Put the key in `~/AppData/Local/hermes/.env` (secrets live only in `.env`):
   ```
   OPENROUTER_API_KEY=sk-or-...
   ```
2. Add the provider block in `config.yaml` (never hand-edit — `hermes config set`):
   ```
   hermes config set providers.openrouter.request_timeout_seconds 120
   ```
   or write the block per `hermes setup` / the BYO-provider docs page
   (`website/docs/byo-provider.html`).
3. Verify: `/models` in chat, or `xomni doctor` in a terminal.

## provider-pool coverage

The `provider-pool` plugin generates ready-made config snippets for **5 agent
formats** (Hermes, opencode, aider, codex, goose) for any model you name, with
live health checks on the 25-model default pool. The catalog above is the
superset: every channel, one env var, one config block.

## Agents & surfaces

Because XOMNI is host-first, the same provider config powers **every chat
surface**: terminal, WhatsApp, Telegram, Discord, Slack, any API connected to
the Hermes gateway — the model behind any of them can use all plugins, skills,
and MCP servers (`/plugins-list`, `/skills-search`, `/skills-install`,
`/mcp list`), plus the terminal CLI (`xomni skill search|install`, `xomni
plugins install`).
