# Architecture

The unified host is **one host core + edge modules**. This is the only merge
strategy that produces working software from seven different codebases; a literal
source merge (Python + Go + Rust, 2.7 GB across the seven repos) would be an
unmaintainable monolith. The AGENTS.md of the host project states the rule
itself: *"the core is a narrow waist; capability lives at the edges."* We follow
it.

## 1. Host core: Hermes

The local git checkout is the host source:
`C:\Users\HP\AppData\Local\hermes\hermes-agent` (public mirror:
`NousResearch/hermes-agent`, Python, MIT, ~228k stars). It is the only one of
the seven tools with:

- skills + memory persistence across sessions
- plugin system (ctx API: commands, tools, hooks) — the sanctioned extension path
- cron/scheduling, subagent delegation, multi-platform gateway
- a real terminal + browser driver

Everything else lands as a module **on** this core, never **in** it.

## 2. Edge modules (shipped)

**16 edge modules are shipped as of 2026-08-12** — the three deep-dives below
plus: `provider-pool` (25 verified free models), `context-compact` (jcode),
`sandbox-gate` (Codex), `mcp-catalog` (Goose), `context-loader`,
`verify-runner`, `gh-ops`, `local-models`, `title-statusline` (OpenCode),
`omni-memory`, `omni-media` (OpenClaw), `omni-design`, `omni-parallel`, and
the sponsorship pair. Full per-plugin matrix, tests, and statuses:
[`docs/FEATURES.md`](FEATURES.md). The sections below detail the first three.

### 2.1 Sponsorship module (`plugins/waitperk`) — the WaitPerk fundamental

The concept, embedded as a first-class module: one sponsor message in the
agent's status area while it works; revenue split 50/50 with the developer by
impression share; payouts capped at what sponsors paid.

**Adaptation to Hermes**: Claude Code has a `statusLine` settings surface;
Hermes has no status-line plugin surface today, so the module renders the
sponsor line two ways: (a) on demand via `/sponsor`, and (b) continuously by
writing `~/.waitperk/current.txt`, which any statusline (tmux, Windows Terminal
tab title, a shell prompt snippet) can tail. The impression accounting uses
agent **work events** (each `pre_llm_call` / `post_tool_call`) as the unit of
"the line is on screen" — a principled proxy that does not require a background
timer.

**Data flow** (what happens end to end):

```
on_session_start ──► ledger: open session, pick sponsor (round-robin)
pre_llm_call / post_tool_call ──► impression += 1 (skipped while paused),
                                  active_seconds += delta, current.txt rewritten
on_session_end ──► ledger: close session, persist state.json
/sponsor          ──► status: sponsor, impressions, active time, est. earnings,
                           share %, paused flag, sync mode
/sponsor sync     ──► build sync_payload() → POST sync_url (dry-run without url)
```

**Payout math** (exact WaitPerk semantics):

- Sponsor pays `P` for a campaign.
- `your_share = your_impressions / total_network_impressions`
- `earnings = min(0.5 × P × your_share, 0.5 × P)`
- Invariant: `Σ_devs earnings_i = 0.5 × P × Σ_devs share_i = 0.5 × P ≤ P`.
  Payouts can never exceed what sponsors paid — by construction. ✓

**What leaves the machine**: only `sync_payload()` — impression IDs, surface
name, client version, device-derived session hash. Prompts, code, file paths,
conversation content: never. The render path does zero network work.

**Demo mode**: config ships a small sponsor pool and a simulated network
impression total so earnings are computable and visible before any real sponsor
exists. `sync_url` empty = dry-run sync prints the exact payload that would be
sent. No telemetry of any kind is enabled by default.

### 2.2 Repo-map module (`plugins/repomap`) — the Aider port

Aider's signature capability: give the model a compact symbol-level map of the
codebase (classes, functions, types per file) so it can navigate without
dumping whole files. Ported as a dependency-free module:

- walks a directory tree, skips `node_modules`, `.git`, `venv`, build dirs, big
  and binary files
- extracts top-level symbols with per-language regexes (py, js/ts, go, rs,
  c/h/cpp, java, rb)
- renders a depth-sorted, size-capped map (default 6000 chars) with file stats
- exposed as a model-callable tool (`repomap`) and a `/repomap` command

The regex extractor is the honest v1; the port-plan defers the tree-sitter
upgrade that Aider itself uses.

### 2.3 PerkLine v2 (`plugins/perkline`) — the researched upgrade

The user directive: if the WaitPerk model isn't impressive, deep-research and
build a better one. PerkLine v2 fixes WaitPerk's three structural flaws while
keeping its one good invariant (payouts never exceed what sponsors paid):

| WaitPerk flaw | Fix (researched) | Evidence basis |
|---|---|---|
| Glance-value pricing (CPM impressions are the weakest ad signal) | Tiered pricing: `cpm` $10-40/1k renders, `cpc` $1-8 per engagement, `cpa` $20-200 per completed action | B2B display CPM, search CPC, and SaaS-trial CPA benchmarks (order-of-magnitude industry ranges) |
| Untargeted inventory (worth ~nothing) | Local relevance matching: sponsors target stack tags; the client matches against the LOCAL repo's stack (extension scan — nothing leaves the machine) | Relevance lift 2-5x in ad markets; privacy preserved by construction |
| Unverifiable "live numbers, zeros included" | Every render/engagement carries an HMAC-SHA256 receipt signed with the install secret; sponsor networks can verify each delivery | Turns transparency from a claim into a proof |
| Opaque pricing (fixed 50/50 of an unverifiable pool) | Second-price sealed-bid auction for the slot; escrow per sponsor caps spend at budget | Honest price discovery (VCG-style); escrow generalizes WaitPerk's cap invariant |

**Flow**: work events (`pre_llm_call`/`post_tool_call`) → render (CPM charges
price/1000, receipt) → `/perkline engage` (CPC charge, receipt) →
`/perkline complete <id>` (CPA charge — explicit, user-confirmed) →
`/perkline sync` (dry-run payload with receipts, or POST to `sync_url`).
Earnings = 50% of what the sponsor actually spends, escrow-capped per sponsor.
The developer can never earn more than half the budget; the sponsor never pays
more than budget. `~/.perkline/current.txt` is the external statusline sink.

## 3. Composition invariants (from host AGENTS.md, honored by all modules)

1. **Prompt-cache safe**: modules never mutate past context or rebuild the
   system prompt. The waitperk hooks return `None` (no behavior change); the
   repomap tool is a plain read-only function.
2. **Narrow waist**: nothing was added to the core schema; both modules ship
   through the plugin API (`register_hook` / `register_tool` / `register_command`).
3. **Plugins own their directory**: state lives in `~/.waitperk/` (module) and
   plugin-local files — no core files touched.
4. **No telemetry without opt-in**: the sync endpoint is off by default.

## 4. Deferred (see FEATURES.md roadmap)

Now SHIPPED (previously deferred in this list): jcode RAM-compaction
(`plugins/context-compact`), Codex-style sandboxing (`plugins/sandbox-gate`),
Goose-style MCP catalog wiring (`plugins/mcp-catalog`), OpenCode-style
statusline surface (`plugins/title-statusline`), and OpenClaw memory/media
(`plugins/omni-memory`, `plugins/omni-media`).

Still deferred:
- Aider git-diff discipline (precise patch application) — queued
- Repo-map tree-sitter upgrade (repomap regex v1 shipped) — parked P3b
- LSP servers integration, jcode OAuth provider flows — queued
- Real sponsor sync network / productized marketplace — parked (business decision)
