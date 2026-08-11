# XOMNI — one agent. every feature. every free model.

**XOMNI** (X + Omni = everything, in one) is a single terminal agent that
composes the signature strengths of the six best open-source coding agents —
**Hermes, OpenCode, jcode, Codex, Aider, Goose** — on one host, with a built-in
**sponsorship engine** that pays you for your installs.

- **Free forever.** MIT sources, no license key, no "pro" wall. The agent is
  the free bait; the sponsorship network is the product.
- **One command to install.** Windows + POSIX launchers, all 12 plugins loaded
  automatically.
- **25 verified free models** — every one tested to actually work (deepseek-v4-*,
  qwen3.8-max, glm-5.2, kimi-k3, minimax-m3 vision, and more) via the provider
  pool with live health checks.
- **329 passing tests** across the plugin suite.
- **Earn while you work**: 50/50 impression-share sponsorship payouts, receipts,
  escrow caps, second-price auctions.

> Design rule: **compose, don't merge.** A literal merge of six codebases in
> Python + Go + Rust would produce a broken monolith. XOMNI is one host
> (Hermes — the richest framework of the six, MIT, and the only one with
> skills/memory/cron/plugins/gateway) with the other agents' signature
> strengths ported in as edge modules.

---

## The six agents, one host

| Tool | Language | Signature strength | Where it lands in XOMNI | Status |
|---|---|---|---|---|
| Hermes | Python | Full agent framework: skills, memory, cron, plugins, gateway, multi-platform | The host core — session loop, persistence, extensibility | host |
| OpenCode | Go | Terminal TUI, fast provider-agnostic loop | Status-line/TUI rendering pattern | SHIPPED (`plugins/title-statusline`, `plugins/local-models`) |
| jcode | Rust | Most RAM-efficient harness | Context/memory-compaction discipline for long sessions | SHIPPED (`plugins/context-compact`) |
| Codex | Rust | Sandboxed execution, plan+act loop | Sandbox gate for risky tool calls | SHIPPED (`plugins/sandbox-gate`) |
| Aider | Python | Repo map (tree-sitter), surgical git diffs | Symbol-level repo map for the model | SHIPPED (`plugins/repomap`) |
| Goose | Rust | MCP-native extensibility | MCP-server catalog conventions | SHIPPED (`plugins/mcp-catalog`) |

## The 12 plugins

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

## Install (one command)

```bash
# Windows
run.cmd

# POSIX / git-bash
./run.sh
```

The launcher starts the Hermes host with all 12 plugins loaded — interactive
chat, `-q` one-shots, `--continue` resume. Plugins are also drop-in installable:

```bash
cp -r plugins/* ~/AppData/Local/hermes/plugins/
hermes plugins enable waitperk perkline repomap
```

## Verify

```bash
cd plugins/waitperk && python -m unittest tests.test_core -v
cd plugins/repomap  && python -m unittest tests.test_core -v
# ... 329 tests total across the suite
```

Verified live (2026-08-11): **329/329 tests pass, 0 failures.**

| Plugin | Tests | Plugin | Tests |
|---|---|---|---|
| gh-ops | 60 | verify-runner | 38 |
| context-loader | 34 | context-compact | 30 |
| local-models | 29 | sandbox-gate | 29 |
| title-statusline | 27 | mcp-catalog | 26 |
| provider-pool | 16 | repomap | 15 |
| waitperk | 14 | perkline | 11 |

## Verified free-model routing (live-tested)

| Role | Model | Live TTFB |
|---|---|---|
| Default | `deepseek-v4-flash` | ~12s |
| Deep reasoning | `deepseek-v4-pro` | ~2s |
| Frontier | `gpt-5.6-luna` | ~1.4s |
| Coding | `kimi-k2.7-code` / `qwen3.7-plus` | ~12s / ~5s |
| Vision | `minimax-m3` (only verified vision) | ~6s |

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
