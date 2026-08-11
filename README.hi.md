# XOMNI — एक एजेंट। हर फीचर। हर फ्री मॉडल।

**XOMNI** (X + Omni = सब कुछ, एक में) एक सिंगल टर्मिनल एजेंट है — सात सबसे अच्छे open-source coding agents **Hermes, OpenCode, jcode, Codex, Aider, Goose, OpenClaw** की सिग्नेचर ताकतें एक ही host पर, साथ में बिल्ट-इन **sponsorship engine** जो आपको आपके installs के लिए पैसे देता है।

- **हमेशा फ्री।** MIT sources, कोई license key नहीं, कोई "pro" wall नहीं। एजेंट फ्री bait है; sponsorship network ही असली product है।
- **एक command में install।** Windows + POSIX launchers, सभी 16 plugins अपने आप load।
- **25 verified free models** — हर एक को test करके देखा गया कि वाकई चलता है (deepseek-v4-*, qwen3.8-max, glm-5.2, kimi-k3, minimax-m3 vision, और भी), provider pool + live health checks के साथ।
- **635 passing tests** पूरे plugin suite में।
- **कमाते हुए काम करें**: 50/50 impression-share sponsorship payouts, receipts, escrow caps, second-price auctions।

> Design rule: **compose करो, merge मत करो।** सात codebases का literal merge (Python + Go + Rust) एक टूटा हुआ monolith बनाएगा। XOMNI एक host है (Hermes — सातों में सबसे rich framework, MIT, और इकलौता जिसमें skills/memory/cron/plugins/gateway हैं) और बाकी agents की सिग्नेचर ताकतें edge modules के रूप में port की गई हैं।

---

## सात agents, एक host

| Tool | भाषा | सिग्नेचर ताकत | XOMNI में कहाँ | Status |
|---|---|---|---|---|
| Hermes | Python | पूरा agent framework: skills, memory, cron, plugins, gateway, multi-platform | Host core — session loop, persistence, extensibility | host |
| OpenCode | Go | Terminal TUI, तेज़ provider-agnostic loop | Status-line/TUI rendering pattern | SHIPPED (`plugins/title-statusline`, `plugins/local-models`) |
| jcode | Rust | सबसे RAM-efficient harness | लंबे sessions के लिए context/memory-compaction discipline | SHIPPED (`plugins/context-compact`) |
| Codex | Rust | Sandboxed execution, plan+act loop | जोखिम भरे tool calls के लिए sandbox gate | SHIPPED (`plugins/sandbox-gate`) |
| Aider | Python | Repo map (tree-sitter), surgical git diffs | Model के लिए symbol-level repo map | SHIPPED (`plugins/repomap`) |
| Goose | Rust | MCP-native extensibility | MCP-server catalog conventions | SHIPPED (`plugins/mcp-catalog`) |
| OpenClaw | TypeScript | Personal assistant: persistent semantic memory, media understanding (OCR/vision), platform-native automation | Local memory + media pipeline | SHIPPED (`plugins/omni-memory`, `plugins/omni-media`) |

## 16 plugins

| Plugin | क्या करता है | Origin strength |
|---|---|---|
| `waitperk` | WaitPerk-model sponsorship: sponsor line, impression ledger, 50/50 payout math | sponsorship |
| `perkline` | PerkLine v2: CPM/CPC/CPA pricing tiers, relevance match, signed receipts, escrow caps, second-price auction | sponsorship |
| `provider-pool` | 25 verified free models, live health checks, हर agent के लिए config generation | free models |
| `context-compact` | लंबे session का compaction, cache-safe context injection | jcode |
| `sandbox-gate` | Pre-tool risk gate (block/warn/allow) + allowlist | Codex |
| `mcp-catalog` | MCP server catalog, validation, JSON-RPC shapes | Goose |
| `repomap` | 13+ languages, rank_files relevance scoring, stack tags | Aider |
| `context-loader` | `fetch_page` + `describe_image` (vision) tools | Aider |
| `verify-runner` | Projects पर `/verify` tests+lint verdict | Aider |
| `gh-ops` | gh/glab wrappers सख्त parsers के साथ | OpenCode |
| `local-models` | Ollama/LM Studio probe + config generation | OpenCode |
| `title-statusline` | Terminal title bar में sponsor line | OpenCode |
| `omni-memory` | OpenClaw-style personal memory: local SQLite facts, /remember /recall, LLM consolidation | OpenClaw |
| `omni-media` | OpenClaw-style media understanding: /ocr /caption /mediascan verified vision model के ज़रिए | OpenClaw |
| `omni-design` | Omni Design: एक brief से premium self-contained HTML artifacts generate करें (/design), 10-tell slop audit (/design-audit) — zero hooks | Claude Design / Stitch |
| `omni-parallel` | Parallel-task layer: /swarm task queue + context packs + multi-agent judging + PR-split merge plans | Kimi / Cursor / Claude |

## Install (एक command)

```bash
# Windows
run.cmd

# POSIX / git-bash
./run.sh
```

Launcher सभी 16 plugins के साथ Hermes host शुरू करता है — interactive chat, `-q` one-shots, `--continue` resume। Plugins drop-in install भी हो सकती हैं:

```bash
cp -r plugins/* ~/AppData/Local/hermes/plugins/
hermes plugins enable waitperk perkline repomap
```

## Verify

```bash
cd plugins/waitperk && python -m unittest tests.test_core -v
cd plugins/repomap  && python -m unittest tests.test_core -v
# ... पूरे suite में 635 tests
```

Live verified (2026-08-12): **635/635 tests pass, 0 failures.**

| Plugin | Tests | Plugin | Tests |
|---|---|---|---|
| gh-ops | 60 | verify-runner | 38 |
| context-loader | 34 | context-compact | 30 |
| local-models | 40 | sandbox-gate | 29 |
| title-statusline | 27 | mcp-catalog | 26 |
| provider-pool | 16 | repomap | 15 |
| waitperk | 14 | perkline | 11 |
| omni-media | 9 | omni-memory | 8 |
| omni-design | 8 | omni-parallel | 20 |

## Verified free-model routing (live-tested)

| Role | Model | Live TTFB |
|---|---|---|
| Default | `deepseek-v4-flash` | ~12s |
| Deep reasoning | `deepseek-v4-pro` | ~2s |
| Frontier | `gpt-5.6-luna` | ~1.4s |
| Coding | `kimi-k2.7-code` / `qwen3.7-plus` | ~12s / ~5s |
| Vision | `minimax-m3` (इकलौता verified vision) | ~6s |

## अपना provider लाओ — built in

आप XOMNI की routing पर lock नहीं हैं। Hermes native तौर पर **किसी भी OpenAI-compatible endpoint** से जुड़ता है — आपकी अपनी OpenAI/Anthropic/Groq/Azure/OpenRouter key, कोई corporate gateway, या LAN पर कोई vLLM/LM-Studio box:

```yaml
# config.yaml (Hermes install dir)
model:
  provider: custom          # या 32 built-in profiles में से कोई (anthropic,
                            # gemini, openrouter, deepseek, xai, nvidia, ...)
  model: gpt-4o             # या जो भी आपका endpoint serve करे
  base_url: https://api.openai.com/v1   # direct endpoint; precedence लेता है
  api_key: YOUR_KEY         # नहीं हो तो .env में OPENAI_API_KEY से fallback

# optional failover chain
fallback_providers:
  - provider: openrouter
    model: deepseek/deepseek-chat
```

Keys `.env` में रहती हैं, हर provider के लिए एक (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, ...), और `/provider` stack के हर agent (Hermes/OpenCode/Codex/Aider/Goose) के लिए ready-to-paste snippet छापता है।

## Local models, zero install — Ollama bundled

XOMNI **Ollama runtime** के साथ आता है ताकि local models अलग से download किए बिना चलें। Launcher पहली run में सब कुछ कर देता है:

1. Official portable Ollama build **एक बार** download (~130 MB) → `ollama/runtime/` (official source, MIT-licensed)।
2. `ollama serve` अपने आप `127.0.0.1:11434` पर शुरू।
3. पहली run में default local model `qwen2.5:3b` (~1.9 GB) pull — उसके बाद local inference **offline, हमेशा फ्री, बिना account**।

फिर `/ollama` command इसे manage करती है (`status | start | install | pull`), और `/localmodels scan` इसे live OpenAI-compatible server की तरह detect करता है — Hermes/OpenCode/Codex/Aider/Goose को `http://127.0.0.1:11434/v1` पर `/localmodels config ollama` से route करें।

## जो skills आपको पहले से मिलती हैं

XOMNI **Hermes पर** चलता है — same host, same install — इसलिए Hermes जो भी skill load करता है, वह बिना किसी extra setup के आपकी है। पूरा catalog repo में ship होता है:

- **`skills/` — 42 domains में 170 procedural skills**, in-tree committed: cloudflare (workers, durable objects, wrangler), hyperframes (video/motion graphics), media-use (audio/video pipelines), research (papers, scraping), productivity (docx, powerpoint, obsidian, note-taking), devops, data science, mlops (vllm, lm-evaluation-harness), mobile, github, security, web-perf, sandbox-sdk, turnstile, और भी।
- साथ ही memory, cron, और gateway multi-platform support — host features लाता है, आपको install नहीं करना पड़ता।

## Sponsorship model (कैसे कमाता है)

```
Sponsor (pays) ──► XOMNI sponsor marketplace ◄── Dev (installs + earns 50%)
                        │
                        └── XOMNI keeps 50% (network fee)
```

- **एक sponsor line**, जो agent के काम करते समय render होती है।
- **Impressions हर agent work event पर गिनी जाती हैं** (LLM calls + tool calls) — "line screen पर कितनी देर रही" का ईमानदार proxy।
- **Dev earnings**: `0.5 × P × (आपके impressions / कुल network impressions)`, cap `0.5 × P` पर — receipts, escrow, और auctions XOMNI की rails पर चलते हैं।
- **Moat ही network है**: ज़्यादा installs → sponsors ज़्यादा pay → ज़्यादा devs कमाने के लिए install। Rails (counting, receipts, escrow, auction) sponsor और dev के बीच trust layer हैं — जो rails चलाता है, fee उसी को मिलती है।

पूरा go-to-market plan [`docs/SELLING.md`](docs/SELLING.md) में है।

## License

Agent और modules MIT; per-tool attribution [`LICENSE-ATTRIBUTION.md`](LICENSE-ATTRIBUTION.md) में। Sponsorship modules public WaitPerk *concept* की independent reimplementations हैं — कोई WaitPerk client code vendored या derived नहीं है।
