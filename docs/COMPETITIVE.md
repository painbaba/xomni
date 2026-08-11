# XOMNI Competitive Research — Consolidated Shortlist

**Source:** 5 track reports (KIMICODE.md, ZAICODE.md, CLAUDE.md, CURSOR.md, BROAD-SCAN.md) + live-verified stars.json (46 repos, GitHub API 2026-08-12).
**Compiled by the coordinator from all five reports — ranked by impact for XOMNI.**

---

## A. Merge / Borrow candidates (ranked)

| # | Repo | ★ (verified) | What it gives XOMNI | Merge vs Build | Effort | Track |
|---|---|---|---|---|---|---|
| 1 | `anthropics/skills` | 168k | The SKILL.md standard + hundreds of reference skills — ecosystem interop (XOMNI's 170 skills become cross-harness installable) | Merge (adopt the format; write a SKILL.md loader for the Hermes skills surface) | M | CLAUDE |
| 2 | `MoonshotAI/kimi-cli` → `packages/kosong` | 11.2k (repo) | Capability-declared model registry: providers-as-protocols, per-model ctx/thinking/image/tool_use, models.dev import + offline snapshot — exactly the design provider-pool needs | Merge (MIT, directly portable Python) | M | KIMI |
| 3 | `colbymchenry/codegraph` | 66k | Persistent pre-indexed code knowledge graph — repomap upgrade from on-demand scan to incremental index | Merge-as-reference (adopt the index design; keep repomap's zero-hook profile) | L | CLAUDE+CURSOR |
| 4 | `anthropics/claude-code-action` | 8.6k | Package verify-runner + gh-ops as a drop-in GitHub Action (CI surface) | Merge (MIT) | S | CLAUDE |
| 5 | `PatrickJS/awesome-cursorrules` | 40.5k | 40k+ rules seed content for an AGENTS.md/rules marketplace | Merge (content import, Apache-2.0) | S | CURSOR |
| 6 | `getagentseal/codeburn` | 9.2k | Usage/cost tracking UI — feeds the honest-latency + budget story | Borrow (design reference) | S | CURSOR |
| 7 | `kenryu42/cc-safety-net` | 1.5k | Guardrail hook — but Kimi's ecosystem is fail-OPEN; we build fail-CLOSED (sandbox-gate is already stricter) | Borrow (concept only) | S | KIMI |
| 8 | `obra/superpowers` | MIT | Curated skills collection (Kimi's own plugin) — harvest for skills DB | Merge (harvest into skills.db) | S | KIMI |
| 9 | `jlowin/fastmcp` | 27.2k | Python MCP server framework — for mcp-catalog validation + shipping XOMNI's own MCP server | Merge (MIT) | S | BROAD |
| 10 | `mem0ai/mem0` / `getzep/graphiti` | 63k / 29.8k | Memory backends — omni-memory upgrade paths (watch; SQLite is right for v1) | Watch | — | BROAD |

## B. Build recommendations (prioritized)

| Priority | Feature | Why | Where it lands |
|---|---|---|---|
| P0 | **Capability-declared model registry** (kosong design) | 25-model pool becomes self-describing: per-model ctx/thinking/vision/tool-use; models.dev sync; honest capability display on the site | provider-pool upgrade |
| P0 | **SKILL.md interop loader + marketplace installer** | Ecosystem unlock — install anthropics/skills + wshobson/agents + claude-plugins content into the Hermes skills surface; XOMNI content becomes portable | new plugin (omni-skills) |
| P0 | **Hybrid codebase index** (BM25 + embeddings, incremental) | The core moat both Cursor (2026 indexing) and Claude (codegraph) converge on; repomap on-demand → persistent index | repomap upgrade |
| P1 | **Tool-search pattern** (on-demand tool loading) | 16 plugins + 311 MCP servers will blow the 30-50-tool accuracy ceiling; catalog-in-context, load-on-use | host-level pattern + mcp-catalog |
| P1 | **Sandbox abstraction** (LocalKaos/E2B-style) | sandbox-gate grows from classifier to execution sandbox (win/lateral move vs Codex) | sandbox-gate v2 |
| P1 | **Model routing with budget alerts** (Cursor Router style) | cost-aware Auto mode over the 25-model pool; budget caps per session | provider-pool |
| P1 | **Fail-closed hooks/guardrails** | Kimi's are fail-open (documented weakness) — our posture is already stricter; formalize the hook bus + blocking semantics | sandbox-gate + docs |
| P2 | Structured outputs (schema-validated JSON), repo-native memory files (CLAUDE.md-style), AGENTS.md rules + rules marketplace, headless stream-json wire surface, claude-code-action-style CI | Incremental moat | various |

## C. Risks / disconfirmations

- **kimi-cli is officially winding down** (Moonshot) — kosong/pykaos are still MIT + the reference design; port, don't depend on upstream.
- **devin-sdk + q-developer-cli**: 404 on GitHub (private/closed) — excluded; concept notes only.
- **ZaiCode (ZCode)**: closed-source Electron app, no repo to merge — its value is the GLM-5.2 model (already in the 25-model pool) + devpack docs.
- **codegraph is heavy (L)**: adopt the DESIGN (incremental index), not the dependency — repomap stays zero-hook.
- **Search engines bot-gated** for most tracks — all claims are primary-source; star counts cross-checked via shields.io + the 45-repo API run.

## D. Immediate next steps (coordinator's call)

1. Build wave: **omni-skills interop plugin** (SKILL.md loader + marketplace installer) — P0, ecosystem unlock, clean scope.
2. **provider-pool upgrade** (capability registry per kosong design) — P0, but needs a design pass first (docs/ provider architecture).
3. **repomap incremental index design doc** — P0/P1 hybrid; design before code.
4. Harvest obra/superpowers + awesome-cursorrules content into skills.db (S, cheap).
5. Ship SHORTLIST.md to the repo (docs/COMPETITIVE.md) so it survives .tmp cleanup.
