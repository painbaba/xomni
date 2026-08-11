# Feature Matrix — every feature of every source repo, tracked

XOMNI's contract: NOTHING from the seven source agents is dropped by
decision — every feature is listed here with a status. All counts below were
**verified live against the repo on 2026-08-12** (source tree, auto-generated
test matrix, SQLite row counts, JSON array lengths, file listings) — no number
is carried over from memory.

## Verified headline numbers (2026-08-12)

| Metric | Verified value | How verified |
|---|---|---|
| Plugins shipped | **16** | `ls plugins/` = 16 dirs; README plugin table (16 rows) |
| Passing tests | **635 / 635** (0 failures) | `docs/TEST-MATRIX.md` (auto-generated 2026-08-12 00:27) |
| Skills in repo | **170** `SKILL.md` files, **42** domain folders | glob count `skills/**/SKILL.md`; `ls skills/` |
| External-skills DB | **519 rows** (skills.db), 6 sources; **180** curated shortlist (201 rows carry a rank) | SQLite `COUNT(*)`; `curated-skills.json` (180 entries) + `.stats.json` |
| MCP server catalog | **311 servers** | `data/mcps.db` (311), `data/mcp/catalog.json` (311), `website/data/mcps.json` (311) |
| Verified free models | **25** (live HTTP 200, 2026-08-10) | README + FEATURES.md provider-pool row |
| Source agents composed | **7** (Hermes, OpenCode, jcode, Codex, Aider, Goose, OpenClaw) | README §"The seven agents, one host" |
| Site assets | index (flagship) + mcp.html + skills.html + **5** docs pages + 404 + favicon + robots + css/js + 2 data JSONs | `ls website/ website/docs/` |
| Docs | **8** files in `docs/` | `ls docs/` |
| CI (.github) | **not present — PENDING** | `ls .github/` → no such directory |

> Discrepancies found vs. prior claims: (a) `website/docs/` contains **5** pages
> (byo-provider, faq, install, security, sponsorship), not 6; (b) `run.cmd` /
> `run.sh` still printed a stale plugin count — fixed to 16 with this rebuild; (c)
> `docs/ARCHITECTURE.md` said "six codebases" and enumerated only 3 shipped
> modules — updated to seven / 16 with this rebuild; (d) the 2026-08-11
> competitive-scan baseline in `.tmp/competitive-research/BROAD-SCAN.md` still
> cites stale plugin/test counts (pre-dates omni-design + omni-parallel).

Status legend:

- `HOST` — already part of the Hermes host core (XOMNI IS Hermes)
- `SHIPPED` — ported as a module/plugin in this repo, tested, installed
- `WIRED` — usable through the host (config/plumbing, e.g. providers)
- `PENDING` — accepted into the build queue / in progress (see Roadmap)
- `PARKED` — tracked, consciously deferred with a reason

---

## 1. Plugin matrix — all 16, shipped (source of truth: `docs/TEST-MATRIX.md`, README)

| # | Plugin | Theme | Tests (PASS) | Status | Origin strength |
|---|---|---|---|---|---|
| 1 | `waitperk` | WaitPerk-model sponsorship: sponsor line, impression ledger, 50/50 payout math | 34 | SHIPPED | sponsorship (WaitPerk) |
| 2 | `perkline` | PerkLine v2: CPM/CPC/CPA tiers, relevance match, HMAC receipts, escrow caps, second-price auction | 18 | SHIPPED | sponsorship (researched upgrade) |
| 3 | `provider-pool` | 25 verified free models, live health checks, per-agent config generation, `/models` `/provider` | 36 | SHIPPED | free models (OpenCode Zen gateway) |
| 4 | `context-compact` | Long-session compaction, cache-safe context injection | 31 | SHIPPED | jcode (RAM efficiency) |
| 5 | `sandbox-gate` | Pre-tool risk gate (block/warn/allow) + allowlist | 42 | SHIPPED | Codex (sandboxed execution) |
| 6 | `mcp-catalog` | MCP server catalog, validation, JSON-RPC shapes | 26 | SHIPPED | Goose (MCP-native) |
| 7 | `repomap` | Symbol-level repo map (13+ lang families), `rank_files` relevance scoring, stack tags | 42 | SHIPPED | Aider (repo map) |
| 8 | `context-loader` | `fetch_page` + `describe_image` (vision) context tools | 69 | SHIPPED | Aider (images/web context) |
| 9 | `verify-runner` | `/verify` tests+lint verdict on projects | 38 | SHIPPED | Aider (lint & test automation) |
| 10 | `gh-ops` | gh/glab wrappers with strict table parsers | 99 | SHIPPED | OpenCode (GitHub/GitLab) |
| 11 | `local-models` | Ollama / LM Studio probe (:11434/:1234) + config generation | 87 | SHIPPED | OpenCode (local endpoints) |
| 12 | `title-statusline` | Sponsor line in the terminal title bar | 32 | SHIPPED | OpenCode (TUI/statusline) |
| 13 | `omni-memory` | Personal memory: local SQLite facts, `/remember` `/recall`, LLM consolidation | 26 | SHIPPED | OpenClaw (persistent memory) |
| 14 | `omni-media` | Media understanding: `/ocr` `/caption` `/mediascan` via verified vision model | 27 | SHIPPED | OpenClaw (media pipeline) |
| 15 | `omni-design` | `/design` premium self-contained HTML artifacts from a brief, `/design-audit` 10-tell slop audit — zero hooks | 8 | SHIPPED | Claude Design / Stitch |
| 16 | `omni-parallel` | Parallel-task layer: `/swarm` task queue + context packs + multi-agent judging + PR-split merge plans | 20 | SHIPPED | Kimi / Cursor / Claude |

**Totals: 16 plugins · 635 test methods · 635 passed · 0 failed** (TEST-MATRIX.md, 2026-08-12 00:27).
Row sum check: 34+18+36+31+42+26+42+69+38+99+87+32+26+27+8+20 = 635 ✓

## 2. Heritage map — the seven source agents, one host

| Tool | Language | Signature strength | Where it lands in XOMNI | Status |
|---|---|---|---|---|
| Hermes | Python | Full agent framework: skills, memory, cron, plugins, gateway | The host core (XOMNI IS Hermes) | HOST |
| OpenCode | Go | Terminal TUI, provider-agnostic loop | `title-statusline`, `local-models`, `gh-ops` | SHIPPED |
| jcode | Rust | RAM-efficient harness | `context-compact` | SHIPPED |
| Codex | Rust | Sandboxed execution, plan+act loop | `sandbox-gate` | SHIPPED |
| Aider | Python | Repo map, surgical git diffs, images/web context, lint+test | `repomap`, `context-loader`, `verify-runner` | SHIPPED |
| Goose | Rust | MCP-native extensibility | `mcp-catalog` | SHIPPED |
| OpenClaw | TypeScript | Persistent semantic memory + media understanding | `omni-memory`, `omni-media` | SHIPPED |
| — | — | Sponsorship fundamental | `waitperk`, `perkline` | SHIPPED |
| — | — | Design + parallel-task layers | `omni-design`, `omni-parallel` | SHIPPED |

## 3. Website assets (static site, no build step — `website/`)

| Asset | Type / role | Status | Source |
|---|---|---|---|
| `index.html` | **Flagship landing page** (24.9 KB, updated 2026-08-12 00:31 — newest file in site) | SHIPPED | hand-authored + `.tmp/flagship-site/` spec (BRIEF.md, DESIGN.md, ENGINEERING.md, MOTION.md) |
| `mcp.html` | MCP catalog page (27.7 KB) — renders the 311-server catalog | SHIPPED | `data/mcps.db` → `website/data/mcps.json` (311) |
| `skills.html` | Skills catalog page (48.4 KB) — vanilla-JS search + category filter over 170 skills | SHIPPED | `website/scripts/gen_skills.py` |
| `docs/byo-provider.html` | "Bring your own provider" doc page | SHIPPED | hand-authored |
| `docs/faq.html` | FAQ doc page | SHIPPED | hand-authored |
| `docs/install.html` | Install doc page | SHIPPED | hand-authored |
| `docs/security.html` | Security doc page | SHIPPED | hand-authored |
| `docs/sponsorship.html` | Sponsorship model doc page | SHIPPED | hand-authored |
| `404.html` | 404 page | SHIPPED | hand-authored |
| `favicon.svg` | Site favicon | SHIPPED | hand-authored |
| `robots.txt` | Robots directives | SHIPPED | hand-authored |
| `css/style.css` | Site-wide stylesheet | SHIPPED | hand-authored |
| `js/site.js` | Shared scripts | SHIPPED | hand-authored |
| `data/skills.json` | Machine-readable skills catalog — **170 entries** (verified) | SHIPPED | generated by `gen_skills.py` |
| `data/mcps.json` | Machine-readable MCP catalog — **311 entries** (verified) | SHIPPED | mcp pipeline |
| `README.md` | Website layout + regeneration docs | SHIPPED | hand-authored |
| `scripts/gen_skills.py` | Regenerates `skills.html` + `data/skills.json` | SHIPPED | pipeline (see §5) |

## 4. Docs (`docs/`, 8 files)

| File | Purpose | Status |
|---|---|---|
| `FEATURES.md` | **This file** — master feature matrix, rebuilt 2026-08-12 | SHIPPED |
| `ARCHITECTURE.md` | Host-core + edge-module architecture (updated 2026-08-12: seven agents, 16 modules) | SHIPPED |
| `TEST-MATRIX.md` | Auto-generated plugin test matrix — 635/635 PASS (2026-08-12 00:27) | SHIPPED (regenerated by the test harness) |
| `PERFORMANCE.md` | Bench results (updated 2026-08-12) | SHIPPED |
| `SELLING.md` | Go-to-market / sponsorship plan (updated 2026-08-12) | SHIPPED |
| `SKILLS-SECURITY.md` | External-skills security scan report — regenerated by `data/build_db.py` | SHIPPED |
| `VALIDATION.md` | Validation record (updated 2026-08-12) | SHIPPED |
| `BRANDING.md` | Brand/identity guide | SHIPPED |

## 5. Data pipelines

| Pipeline | Input → Output | Verified counts | Status |
|---|---|---|---|
| `data/build_db.py` | `data/raw/scrape{1..6}.json` → dedupe by sha256 → `data/skills.db`; merges curated ranks; regenerates `docs/SKILLS-SECURITY.md` | 519 rows in `skills` table, 6 rows in `sources`, 6 raw scrape files, 475 unique / 467 scored / 180 curated per `.stats.json` | SHIPPED |
| `data/curated-skills.json` (+ `.stats.json`, `curated-summary.md`) | Curator-ranked top-useful shortlist, keyed by sha256 | **180 entries** (verified); 201 skills rows carry a `rank` in db | SHIPPED |
| `website/scripts/gen_skills.py` | `skills/**/SKILL.md` (YAML frontmatter) → `website/data/skills.json` + `website/skills.html` | 170 SKILL.md files → 170 JSON entries | SHIPPED |
| MCP catalog pipeline | `.tmp/mcp/` harvest scripts (`harvest_gh.py`, `build_github_json.py`) + `.tmp/build_smithery.py` + `.tmp/build_final.py` → `data/mcp/catalog.json` → `data/mcps.db` → `website/data/mcps.json` + `website/mcp.html` | **311 servers** (catalog.json = mcps.db = mcps.json = 311, verified) | SHIPPED |
| `.tmp/competitive-research/` | Track scans: `BROAD-SCAN.md` (Track 5), `CLAUDE.md` (Track 3), `CURSOR.md` (Track 4), `KIMICODE.md`, `ZAICODE.md` | Shortlist for next build phase | **PENDING** triage into roadmap |

## 6. Infra & tooling

| Asset | Role | Status |
|---|---|---|
| `run.cmd` | Windows launcher — starts Hermes host with all **16** plugins; bootstraps bundled Ollama (updated 2026-08-12: 14→16) | SHIPPED |
| `run.sh` | POSIX/git-bash launcher — all **16** plugins; ensures `ollama serve` on :11434 (updated 2026-08-12: 14→16) | SHIPPED |
| `ollama/start-ollama.ps1` | Bundled-Ollama starter: downloads official portable build once (~130 MB) into `ollama/runtime/`, serves `127.0.0.1:11434`, pulls `qwen2.5:3b` on first run; idempotent | SHIPPED |
| `.github/` | CI/workflows | **PENDING** (directory not present as of 2026-08-12) |
| `.bench/` | Benchmark harness: `bench.py`, `run_all_tests.sh`, `results[-before|-after].json` over the 635-test suite | SHIPPED |
| `.gitignore`, `LICENSE` (MIT), `LICENSE-ATTRIBUTION.md` | Repo hygiene / licensing | SHIPPED |

## 7. Skills & free models

| Asset | Verified count | Status |
|---|---|---|
| `skills/` — procedural skills committed in-tree | **170** `SKILL.md` across **42** domain folders (cloudflare, hyperframes, media-use, research, productivity, devops, mlops, github, security, web-perf, …) | SHIPPED |
| External-skills knowledge base | **519** skills in `data/skills.db` from 6 curated sources; **180**-entry ranked shortlist | SHIPPED |
| Verified free-model routing | **25 models** live-verified (HTTP 200, 2026-08-10): deepseek-v4-flash/pro, qwen3.8-max, glm-5.2/5.1/5, kimi-k3/k2.7-code/k2.6/k2.5, minimax-m3 (vision)/m2.7/m2.5, gpt-5.6-luna, grok-4.5, hy3, mimo-v2, … | WIRED via `provider-pool` |

## 8. Roadmap / next

**Pending inputs** (in build queue, awaiting triage):
- `.tmp/competitive-research/` shortlist — `BROAD-SCAN.md` (2026-08-11/12) + sibling deep-dives (`CLAUDE.md`, `CURSOR.md`, `KIMICODE.md`, `ZAICODE.md`) — **PENDING**; note its baseline cites stale plugin/test counts (pre-dates omni-design/omni-parallel).
- `.github/` CI — **PENDING**.
- Real sponsor sync network / productized marketplace — PARKED (needs business decision, see `docs/SELLING.md`).

**Queued work** (carried from this matrix's build-order history, still open):
1. Repo-map tree-sitter upgrade (repomap v2; regex v1 SHIPPED) — PARKED P3b
2. Aider git-diff discipline (precise patch application) — QUEUED
3. LSP servers integration (OpenCode line) — QUEUED
4. jcode provider OAuth flows (Copilot device flow, Google OAuth) — QUEUED
5. OpenCode ACP (Agent Client Protocol) support — QUEUED

**Shipped since the original build order** (no longer pending): provider-pool, local-models wiring, gh-ops, context-loader, verify-runner, repomap, sandbox-gate, mcp-catalog, context-compact, title-statusline, omni-memory, omni-media, omni-design, omni-parallel, waitperk, perkline.

Every row above is either shipped, pending with a named input, or has a named
reason for parking. Nothing is dropped by silence.
