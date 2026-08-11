# Feature Matrix — every feature of every source repo, tracked

The unified agent's contract: NOTHING from the six sources is dropped by
decision — every feature is listed here with a status. Status legend:

- `HOST` — already part of the Hermes host core (the unified agent IS Hermes)
- `SHIPPED` — ported as a module/plugin/skill in this repo, tested, installed
- `VENDORED` — source vendored for reference/attribution (read, not merged)
- `WIRED` — usable through the host (config/plumbing, e.g. providers)
- `QUEUED` — accepted into the build queue (see PORT-PLAN.md / build order below)
- `PARKED` — tracked, consciously deferred with a reason

---

## 1. HERMES (host, Python — MIT, ~228k★) — `C:\Users\HP\AppData\Local\hermes\hermes-agent`

All host features are the unified agent by construction:

| Feature | Status |
|---|---|
| Agent loop (CLI + gateway, same core) | HOST |
| Skills system (procedural memory, skill_view/manage) | HOST |
| Persistent memory + user profile | HOST |
| Cron / scheduled jobs | HOST |
| Plugin system (ctx API: commands, tools, hooks, middleware) | HOST |
| Subagent delegation (parallel batches, orchestrator nesting) | HOST |
| Kanban multi-agent board | HOST |
| Gateway: ~20 messaging platforms (Telegram, Discord, WhatsApp, Slack…) | HOST |
| Terminal + browser drivers (CDP) | HOST |
| MCP servers wiring (ffmpeg, youtube-transcript live) | HOST |
| TUI + Electron desktop app | HOST |
| Provider abstraction + automatic failover chains | HOST |
| Prompt-enhancer plugin (manual + auto pre_llm_call mode) | HOST |
| Session store (SQLite, session_search) | HOST |
| Profiles (multi-profile isolation) | HOST |
| Auth/credential pool (`hermes auth`) | HOST |
| AGENTS.md contribution rubric | HOST |

## 2. OPENCODE (Go — MIT, ~13.6k★) — `vendor/opencode/`

| Feature | Status |
|---|---|
| Terminal TUI (chat, sessions, themes, keybinds) | VENDORED (reference for P4 TUI statusline) |
| Go CLI + Web IDE + Zen + Share surfaces | VENDORED |
| 75+ LLM providers via Models.dev registry + AI SDK | WIRED through the opencode-go gateway (25 models verified live) |
| `/models`, `/connect`, model variants + cycling | QUEUED (provider-pool plugin ships /models) |
| LSP servers integration | QUEUED |
| MCP servers | HOST (native) |
| Agents (multi-agent modes), Agent Skills | QUEUED (agents → Hermes subagents already cover) |
| Rules files, formatters, commands, permissions/policies | QUEUED (permissions → sandbox-gate plugin, in swarm) |
| Custom tools (SDK), Plugins, Server (headless API) | HOST plugin system covers |
| GitHub / GitLab integration | SHIPPED (`plugins/gh-ops` — gh/glab wrappers, strict table parsers, live: auth painbaba) |
| ACP (Agent Client Protocol) support | QUEUED |
| Local models (LM Studio / Ollama endpoints) | SHIPPED (`plugins/local-models` — probe :11434/:1234, config gen; 0 servers running on this machine) |
| Free models: opencode Zen gateway — deepseek-v4-flash/pro, qwen3.8-max, glm-5.2/5.1/5, kimi-k3/k2.7-code/k2.6/k2.5, minimax-m3/m2.7/m2.5, gpt-5.6-luna, grok-4.5, hy3/hy3-preview, mimo-v2* — VERIFIED LIVE (HTTP 200, 25 models, 2026-08-10) | WIRED (provider-pool) |
| Provider pool: /models live health, /provider config gen for ALL agents (same gateway, one key) | SHIPPED (plugins/provider-pool) |

## 3. JCODE (Rust — MIT, ~16.7k★) — the RAM-efficient harness

| Feature | Status |
|---|---|
| RAM-efficient harness (minimal footprint, fast first frame) | QUEUED → P1 context-compact plugin (in swarm) |
| Agent memory | QUEUED (Hermes memory is the host equivalent; P1 summary adds session-level) |
| UI: side panels, diagrams, info widgets | PARKED (Hermes TUI differs; port-plan P4) |
| Swarm (multi-agent) | HOST (delegation) |
| OAuth + provider login flows (Copilot device flow, Google OAuth, Gmail) | QUEUED |
| Config-file providers (OpenAI-compatible, Ollama, LM Studio) | WIRED (provider-pool config gen) |
| Self-dev / customizability | HOST (plugins/skills) |
| iOS application / native OpenClaw | PARKED (out of scope for CLI product) |

## 4. CODEX (Rust — Apache-2.0, ~105k★)

| Feature | Status |
|---|---|
| Sandboxed execution (container/seatbelt) | QUEUED → P2 sandbox-gate plugin (in swarm) |
| Plan mode (plan → act) | QUEUED (todo/plan skill exists in Hermes) |
| Approval modes (read-only / auto / full) | QUEUED (sandbox-gate extends) |
| ChatGPT plan sign-in | PARKED (proprietary backend) |
| Sessions, resume, aliases, config | HOST |
| MCP support | HOST |
| Agents (multi-agent coding) | HOST (delegation) |
| OSS first / open codebase | VENDORED attribution |

## 5. AIDER (Python — Apache-2.0, ~48k★)

| Feature | Status |
|---|---|
| Repo map (tree-sitter symbol maps) | SHIPPED → repomap plugin (regex v1 SHIPPED, tree-sitter upgrade PARKED P3b) |
| 100+ code languages | SHIPPED v1 (13 lang families) + swarm v2 adds kotlin/swift/dart/scala/lua/r/tf/vue |
| Git integration (auto-commit, surgical diffs) | QUEUED → P5 git-diff-discipline skill (in swarm) |
| Cloud + local LLMs | WIRED (provider-pool) |
| IDE (watch mode) | PARKED (host has no IDE bridge; desktop app covers) |
| Images & web pages as context | SHIPPED (`plugins/context-loader` — fetch_page clean-text + describe_image via verified minimax-m3 vision; live: example.com + gateway both OK) |
| Voice-to-code | PARKED (TTS exists; STT local whisper configured) |
| Lint & test automation | SHIPPED (`plugins/verify-runner` — /verify runs tests + lint, verdict; live: PASS on the unified-agent repo) |
| Copy/paste to web chat | PARKED |

## 6. GOOSE (Rust — Apache-2.0, ~52.6k★)

| Feature | Status |
|---|---|
| MCP-native extensibility | QUEUED → P3a mcp-catalog plugin (in swarm) |
| Extensions (recipes, toolkits) | HOST (plugins/skills) |
| Install / execute / edit beyond code suggestions | HOST (terminal + file tools) |
| Sessions / resume / checkpoints | HOST |
| Benchmarks (GAIA, etc.) | PARKED |

## 7. WAITPERK / sponsorship fundamental

| Feature | Status |
|---|---|
| Status-line sponsor message while agent works | SHIPPED (waitperk + perkline plugins) |
| 50/50 impression-share payout, capped by construction | SHIPPED (waitperk) |
| Tiered pricing cpm/cpc/cpa + relevance match + receipts + escrow + auction | SHIPPED (perkline v2) |
| Real sync server / sponsor network | PARKED (productization, needs business decision) |

---

## Build order (after the current swarm batch)

1. QA gate on swarm output (verify, audit, fix, install, e2e) — orchestrator
2. provider-pool plugin (free-model registry + /models + per-agent config gen) — IN PROGRESS
3. P4: TUI statusline surface (closes the sponsorship loop)
4. LSP servers integration (opencode)
5. Local models (Ollama/LM Studio) wiring
6. GitHub/GitLab integration (opencode)
7. Aider images/webpages context, lint-test automation
8. jcode provider OAuth flows (Copilot device flow, Google OAuth)

Every row above is either shipped, being built, or has a named reason for
parking. Nothing is dropped by silence.
