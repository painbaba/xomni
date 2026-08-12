# XOMNI — one agent. every feature. every free model.

> **हिंदी (Hindi):** [README.hi.md](README.hi.md) — पूरा pitch हिंदी (Devanagari) में पढ़ें।

**XOMNI** (X + Omni = everything, in one) is a single terminal agent that
composes the signature strengths of the seven best open-source coding agents —
**Hermes, OpenCode, jcode, Codex, Aider, Goose, OpenClaw** — on one host, with
a built-in **sponsorship engine** that pays you for your installs.

- **Free forever.** MIT sources, no license key, no "pro" wall. The agent is
  the free bait; the sponsorship network is the product.
- **One command to install.** Windows + POSIX launchers, all 23 plugins loaded
  automatically.
- **25 verified free models** — every one tested to actually work (deepseek-v4-*,
  qwen3.8-max, glm-5.2, kimi-k3, minimax-m3 vision, and more) via the provider
  pool with live health checks.
- **1043 passing tests** across the plugin suite (29 plugins).
- **Earn while you work**: 50/50 impression-share sponsorship payouts, receipts,
  escrow caps, second-price auctions.

> Design rule: **compose, don't merge.** A literal merge of seven codebases in
> Python + Go + Rust would produce a broken monolith. XOMNI is one host
> (Hermes — the richest framework of the seven, MIT, and the only one with
> skills/memory/cron/plugins/gateway) with the other agents' signature
> strengths ported in as edge modules.

---

## The seven agents, one host

| Tool | Language | Signature strength | Where it lands in XOMNI | Status |
|---|---|---|---|---|
| Hermes | Python | Full agent framework: skills, memory, cron, plugins, gateway, multi-platform | The host core — session loop, persistence, extensibility | host |
| OpenCode | Go | Terminal TUI, fast provider-agnostic loop | Status-line/TUI rendering pattern | SHIPPED (`plugins/title-statusline`, `plugins/local-models`) |
| jcode | Rust | Most RAM-efficient harness | Context/memory-compaction discipline for long sessions | SHIPPED (`plugins/context-compact`) |
| Codex | Rust | Sandboxed execution, plan+act loop | Sandbox gate for risky tool calls | SHIPPED (`plugins/sandbox-gate`) |
| Aider | Python | Repo map (tree-sitter), surgical git diffs | Symbol-level repo map for the model | SHIPPED (`plugins/repomap`) |
| Goose | Rust | MCP-native extensibility | MCP-server catalog conventions | SHIPPED (`plugins/mcp-catalog`) |
| OpenClaw | TypeScript | Personal assistant: persistent semantic memory, media understanding (OCR/vision), platform-native automation | Local memory + media pipeline | SHIPPED (`plugins/omni-memory`, `plugins/omni-media`) |

## The 23 plugins

| Plugin | What it does | Origin strength |
|---|---|---|
| `waitperk` | WaitPerk-model sponsorship: sponsor line, impression ledger, 50/50 payout math | sponsorship |
| `perkline` | PerkLine v2: CPM/CPC/CPA pricing tiers, relevance match, signed receipts, escrow caps, second-price auction | sponsorship |
| `provider-pool` | 25 verified free models, live health checks, per-agent config generation | free models |
| `context-compact` | Long-session compaction, cache-safe context injection | jcode |
| `sandbox-gate` | Pre-tool risk gate (block/warn/allow) + allowlist | Codex |
| `mcp-catalog` | MCP server catalog, validation, JSON-RPC shapes | Goose |
| `repomap` | 13+ languages, rank_files relevance scoring, stack tags | Aider |
| `context-loader` | `fetch_page` + `describe_image` (vision) tools | Aider |
| `verify-runner` | `/verify` tests+lint verdict on projects | Aider |
| `gh-ops` | gh/glab wrappers with strict parsers | OpenCode |
| `local-models` | Ollama/LM Studio probe + config generation | OpenCode |
| `title-statusline` | Sponsor line in the terminal title bar | OpenCode |
| `omni-memory` | OpenClaw-style personal memory: local SQLite facts, /remember /recall, LLM consolidation | OpenClaw |
| `omni-media` | OpenClaw-style media understanding: /ocr /caption /mediascan via the verified vision model | OpenClaw |
| `omni-design` | Omni Design: generate premium self-contained HTML artifacts from a brief (/design), 10-tell slop audit (/design-audit) — zero hooks | Claude Design / Stitch |
| `omni-parallel` | Parallel-task layer: /swarm task queue + context packs + multi-agent judging + PR-split merge plans | Kimi / Cursor / Claude |
| `omni-skills` | SKILL.md interop: scan/validate/install skills from any marketplace — zero hooks | Claude (SKILL.md standard) |
| `omni-registry` | Capability-declared model registry (corrected 1M-context flags) | next-feature wave |
| `codebase-index` | FTS5 codebase index (repomap v2): full-text symbol search | next-feature wave |
| `omni-tools` | Tool-search corpus + BM25 router: catalog-in-context, load-on-use | next-feature wave |
| `bharat-pack` | Hindi + Indian model pool, Devanagari prompt support | next-feature wave |
| `cost-tracker` | Per-run token/cost ledger + budget caps | next-feature wave |
| `receipts` | Receipts-by-default JSONL ledger: every side-effect issues a verifiable handle (sha256 / URL 200 / exit code) + `/receipts verify` re-checks it | U7 (owner demand) |

## Install (one command)

**A) pip (recommended — installs the `xomni` CLI):**

```bash
pip install .            # from the repo root — or: pip install git+https://github.com/painbaba/xomni
xomni doctor             # verify the environment
xomni plugins install    # load all 23 plugins into the Hermes plugins dir
xomni skill search <q>   # search skills from the terminal
xomni providers          # every provider Hermes supports, one table
xomni stacks             # list one-command vertical stacks
xomni add <stack>        # install a stack's MCPs in one command
```

**B) launcher (zero-pip, from a checkout):**

```bash
# Windows
run.cmd

# POSIX / git-bash
./run.sh
```

The launcher starts the Hermes host with all 23 plugins loaded — interactive
chat, `-q` one-shots, `--continue` resume. Plugins are also drop-in installable:

```bash
cp -r plugins/* ~/AppData/Local/hermes/plugins/
hermes plugins enable waitperk perkline repomap
```

## One-command vertical stacks — `xomni add <stack>`

Prebuilt vertical stacks install a curated set of MCP servers + skills in a
single non-interactive command. `xomni add` validates the stack def, prints the
plan, then **appends** the servers to your host's `config.yaml` `mcp_servers`
block (stdio servers → `command`/`args`, hosted servers → `url`) — it never
invokes the interactive `hermes mcp add` and never touches existing entries
(re-runs are idempotent: already-present servers are skipped).

| Stack | Skills | MCP servers | Smoke test (live) |
|---|---|---|---|
| `trading-stack` | 4 | yfinance, TradingView, CoinGecko, AlphaVantage, Polymarket | CoinGecko BTC price API → 200 |
| `data-science` | 6 | arXiv, DuckDuckGo, Fetch, chroma, time | Crossref API → 200 |
| `web-dev` | 6 | Playwright, Chrome DevTools, Cloudflare, Supabase, Neon | npm registry → 200 |
| `home-automation` | 4 | Home Assistant (ha-mcp), Windows, mobile, time, memory | PyPI ha-mcp → 200 |

```bash
xomni stacks                      # list available stacks
xomni add trading-stack           # install: appends 5 MCPs to config.yaml
xomni add trading-stack --dry-run # preview the plan, write nothing
xomni add web-dev --smoke         # install + run the stack's live smoke test
```

The write is a textual insert into the existing `mcp_servers:` block — comments,
ordering, and every other config section are preserved byte-for-byte (empty
inline forms like `mcp_servers: {}` are expanded, never corrupted). If
`config.yaml` is missing or read-only the command fails loudly with the exact
fix. Stack definitions live in `data/stacks/*.json` (skills must exist in
`data/curated-skills.json`, MCPs in `data/mcp/catalog.json`). Restart the host
(or `/reload-mcp`) after installing.

## MCP catalog — install any of 311 servers

The full marketplace (`data/mcp/catalog.json`, 311 servers, searchable at
[website/docs/mcp.html](website/docs/mcp.html) and rendered in
[docs/MCP-CATALOG.md](docs/MCP-CATALOG.md)) installs two ways:

- **In chat:** `/mcp add <name> --yes` — non-interactive install of one server
  (stdio → `command`/`args`, hosted/Smithery remote → `url`), appended to
  `config.yaml` `mcp_servers`. Idempotent; `/mcp list` to browse.
- **As a stack:** `xomni add <stack>` — a curated vertical bundle of MCPs +
  skills (see table above), optionally with a live smoke test via `--smoke`.

## Verify

```bash
cd plugins/waitperk && python -m unittest tests.test_core -v
cd plugins/repomap  && python -m unittest tests.test_core -v
# ... 1043 tests total across the suite
```

Verified live (2026-08-12): **1043/1043 tests pass, 0 failures.**

| Plugin | Tests | Plugin | Tests |
|---|---|---|---|
| gh-ops | 130 | verify-runner | 38 |
| context-loader | 69 | context-compact | 31 |
| local-models | 87 | sandbox-gate | 75 |
| title-statusline | 32 | mcp-catalog | 26 |
| provider-pool | 37 | repomap | 42 |
| waitperk | 34 | perkline | 27 |
| omni-media | 27 | omni-memory | 29 |
| omni-design | 8 | omni-parallel | 20 |
| omni-skills | 23 | omni-registry | 22 |
| codebase-index | 28 | omni-tools | 21 |
| bharat-pack | 19 | cost-tracker | 17 |

## Verified free-model routing (live-tested)

| Role | Model | Live TTFB |
|---|---|---|
| Default | `deepseek-v4-flash` | ~12s |
| Deep reasoning | `deepseek-v4-pro` | ~2s |
| Frontier | `gpt-5.6-luna` | ~1.4s |
| Coding | `kimi-k2.7-code` / `qwen3.7-plus` | ~12s / ~5s |
| Vision | `minimax-m3` (only verified vision) | ~6s |

## Bring your own provider — built in

You're never locked to XOMNI's routing. Hermes natively connects **any
OpenAI-compatible endpoint** — your own OpenAI/Anthropic/Groq/Azure/OpenRouter
key, a corporate gateway, or a vLLM/LM-Studio box on your LAN:

```yaml
# config.yaml (Hermes install dir)
model:
  provider: custom          # or any of the 32 built-in profiles (anthropic,
                            # gemini, openrouter, deepseek, xai, nvidia, ...)
  model: gpt-4o             # or whatever your endpoint serves
  base_url: https://api.openai.com/v1   # direct endpoint; takes precedence
  api_key: YOUR_KEY         # falls back to OPENAI_API_KEY in .env

# optional failover chain
fallback_providers:
  - provider: openrouter
    model: deepseek/deepseek-chat
```

Keys live in `.env`, one per provider (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
...), and `/provider` prints the ready-to-paste snippet for every agent in the
stack (Hermes/OpenCode/Codex/Aider/Goose).

**WhatsApp B2B agent mode:** run XOMNI as a *business's own* WhatsApp service
agent on its Meta WABA — per-message INR pricing (free 24h window, ₹0.115
utility), the India B2B-only rule, template approval, and the
`hermes whatsapp-cloud` gateway bridge:
[`docs/WHATSAPP-B2B.md`](docs/WHATSAPP-B2B.md).

## Local models, zero install — Ollama bundled

XOMNI ships the **Ollama runtime** so local models work without downloading
Ollama separately. The launcher does it all on first run:

1. Downloads the official portable Ollama build **once** (~130 MB) into
   `ollama/runtime/` (official source, MIT-licensed).
2. Starts `ollama serve` automatically on `127.0.0.1:11434`.
3. Pulls the default local model `qwen2.5:3b` (~1.9 GB) on first run — after
   that, local inference works **offline, forever free, no account**.

Then the `/ollama` command manages it (`status | start | install | pull`), and
`/localmodels scan` detects it as a live OpenAI-compatible server — route
Hermes/OpenCode/Codex/Aider/Goose to `http://127.0.0.1:11434/v1` with
`/localmodels config ollama`.

## The skills you already inherit

XOMNI runs **on Hermes** — same host, same install — so every skill Hermes
loads is yours with zero extra setup. The full catalog ships in the repo:

- **`skills/` — 170 procedural skills** across 42 domains, committed in-tree:
  cloudflare (workers, durable objects, wrangler), hyperframes (video/motion
  graphics), media-use (audio/video pipelines), research (papers, scraping),
  productivity (docx, powerpoint, obsidian, note-taking), devops, data
  science, mlops (vllm, lm-evaluation-harness), mobile, github, security,
  web-perf, sandbox-sdk, turnstile, and more.
- Plus memory, cron, and gateway multi-platform support — the host brings the
  features, you don't install them.

## The sponsorship model (how it earns)

```
Sponsor (pays) ──► XOMNI sponsor marketplace ◄── Dev (installs + earns 50%)
                        │
                        └── XOMNI keeps 50% (network fee)
```

- **One sponsor line**, rendered while the agent works.
- **Impressions counted per agent work event** (LLM calls + tool calls) — the
  honest proxy for "time the line is on screen".
- **Dev earnings**: `0.5 × P × (your impressions / total network impressions)`,
  capped at `0.5 × P` — receipts, escrow, and auctions run on XOMNI's rails.
- **The moat is the network**: more installs → sponsors pay more → more devs
  install to earn. The rails (counting, receipts, escrow, auction) are the
  trust layer between sponsor and dev — whoever runs the rails keeps the fee.

The full go-to-market plan lives in [`docs/SELLING.md`](docs/SELLING.md).

## License

MIT for the agent and modules; per-tool attribution in
[`LICENSE-ATTRIBUTION.md`](LICENSE-ATTRIBUTION.md). The sponsorship modules are
independent reimplementations of the public WaitPerk *concept* — no WaitPerk
client code is vendored or derived.
