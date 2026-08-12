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
| Sarvam AI (India) | `SARVAM_API_KEY` | `https://api.sarvam.ai` | 100 free credits on signup; Sarvam-105B/30B chat (₹4–16 /1M tok), TTS `bulbul:v3` (11 Indic langs), ASR |
| Bhashini (MeitY, India) | `BHASHINI_API_KEY` | `https://api.bhashini.gov.in` | gov ASR/TTS/MT, 22+ languages; registration-gated (userid + subscription-id), pricing not published |
| Krutrim Cloud (Ola, India) | `KRUTRIM_API_KEY` | `https://cloud.olakrutrim.com/v1` | OpenAI-compatible; INR billing, India data residency, free start no card; token pricing `[UNVERIFIED]` |

## India channels (backlog 08)

Three India-resident channels round out the catalog (research:
`.tmp/research-next/INDIA-FEATURES.md`, fetched 2026-08-12):

- **Sarvam AI** — 100 free API credits on signup; chat at ₹4–16 per 1M tokens
  (Sarvam-105B ₹4 in / ₹16 out; Sarvam-30B ₹2.5 / ₹10), TTS `bulbul:v3` in 11
  Indic languages (₹30 / ₹15 per char by tier), per-second ASR. ISO 27001 +
  SOC 2 Type II. Python SDK: `pip install sarvamai`.
- **Bhashini (MeitY)** — the National Language Translation Mission's free
  (approval-gated) ASR / TTS / MT APIs for 22+ languages; billion+ inferences
  shipped (Sansad Bhashini runs Parliament). **Registration gate:** register at
  bhashini.gov.in → apply for API access → on approval you receive a `userID` +
  `apiKey` (plus a per-pipeline `subscriptionId`); all three go in the request
  headers. Pricing is not published (historically government-funded). API base:
  `https://api.bhashini.gov.in`.
- **Krutrim Cloud (Ola)** — OpenAI-compatible (`/v1`), free start with no
  credit card; bills in INR and keeps data in India (ISO 27001/27017/27018,
  SOC I/II). Per-token pricing is account-gated — verify on signup.

**Payment/distribution constraints (from the research):**

- **WhatsApp (Meta):** India is **not** on the list of markets where third-party
  "AI Providers" (general-purpose AI assistants) may operate under Meta's
  Jan 15, 2026 ToS — a consumer "chat with an AI" bot on WhatsApp is
  non-compliant. The compliant play is a **business-owned WABA running its own
  service agent** (free 24h customer-service-window replies; utility templates
  ₹0.115/msg). All WABAs must migrate to INR billing by Dec 31, 2026 (non-INR
  WABAs stop delivering Jan 1, 2027). Full runbook — WABA setup, INR pricing,
  template approval, `hermes whatsapp-cloud` gateway bridge:
  [`WHATSAPP-B2B.md`](WHATSAPP-B2B.md).
- **UPI (RBI):** UPI payments carry **zero merchant MDR** — but recurring
  subscriptions must target **UPI Autopay/Intent** (UPI Collect is being
  deprecated). Payment data must stay localized in India (RBI).

## How to connect (any provider)

One-command connect (XOMNI CLI):

```
xomni providers add my-provider https://api.example.com/v1 \
    --key-env MY_PROVIDER_API_KEY --api-type openai --models m1,m2 --yes
```

Writes the `providers.<id>` block into config.yaml (YAML-validated, idempotent,
preserves the rest of the file) and adds the `KEY=` placeholder line to `.env`
(never overwrites an existing key, never writes a value — you paste the secret
in). `--dry-run` previews; failures are loud (bad name/URL/env-var, read-only
config, missing config). Then: paste the key into `.env` and run `xomni doctor`
or `/models` to verify.

Manual path (equivalent):

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
