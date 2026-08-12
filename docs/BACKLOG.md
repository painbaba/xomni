# XOMNI BACKLOG — continuous improvement program
# USER-DRIVEN v1.1 (from the owner's hands-on session — highest priority)

## Quick wins (days)

- [x] U1. One-command vertical stacks: `xomni add trading-stack|data-science|web-dev|home-automation` — installs skills + MCPs + config, runs smoke tests, shows live-data proof. Stack defs in data/stacks/*.json (skills from curated DB, MCPs from catalog.json). done 2026-08-12 (4 stacks + xomni add wiring + test_stacks).
- [x] U2. Make the MCP catalog REAL: host `hermes mcp list` shows 2 (disabled) vs 311 in the catalog — gap verified 2026-08-12. Full marketplace path: search/stars/keyless badges/security scores in /mcp, one-command install that WRITES the host mcp config (not the host's interactive flow). done 2026-08-12 (311-catalog marketplace + host config.yaml writer + tests; windows_checks host_config_edit PASS).
- [x] U3. Non-interactive everything: every install command takes --yes; NO silent cancels — failed installs exit non-zero with a loud error naming the cause. done 2026-08-12 (--yes audit + fail-loud + test_noninteractive).
- [x] U4. Windows CI pass: GitHub Actions windows-latest job running the full matrix + windows-specific checks (npx .cmd shim resolution, config.yaml write-protection handling, /tmp vs Windows paths). done 2026-08-12 (windows-latest job + windows_checks.py 8 checks, 0 fail).

## Big wins (design-then-build)

- [x] U5. Automatic model routing: pick per task (fast/reasoning/vision) from the 25 free models + per-task cost/latency telemetry after every answer. done 2026-08-12 (model-router plugin: detect_task_type/route + deterministic pre_llm_call hook, ci_gate DETERMINISTIC_HOOK_PLUGINS).
- [x] U6. Auto-skill creation: after any 5+ tool-call success, auto-draft a skill and show "saved: <name>" for approval. done 2026-08-12 (skill-drafter plugin: draft_skill/parse_transcript + auto-draft bridge).
- [x] U7. Receipts by default: every external side-effect returns a verifiable handle (URL/hash/status) — proof, not claims. done 2026-08-12 (receipts plugin: sha/url/exit handles + verify).


Owned by the improvement workforce (cron: xomni-improvement-workforce, every 3h)
+ coordinator waves. Rule: one item = one leaf = self-contained brief. Mark
status: `[ ]` open · `[~]` in progress (date) · `[x]` done (date). Keep this
file current — it is the workforce's queue.

- [x] U8. Domain guardrails: per-domain approval policies (trading/money/medical/legal/crypto/code-exec) — trading stack defaults to analysis-OK, execution-requires-explicit-approval; /guardrails commands. done 2026-08-12 (domain-guardrails plugin, 16 tests).

- [x] U9. Self-healing agent: watchdog kills silent hangs (vectorbt-180s case) + postcondition checks for exit-0-nothing-happened, config-drift auto-fix with audit trail (heal.jsonl), /heal commands. done 2026-08-12 (self-healing plugin: watchdog/postcondition/heal.jsonl, /heal).

- [x] U10. Voice-first mode: optional hands-free CLI — ffmpeg/arecord capture, whisper-or-Gemini STT, edge-tts TTS, /voice test|ask|on. done 2026-08-12 (voice-first plugin, 17 tests).

- [x] U11. Cross-session skill market: publish XOMNI-created skills to the shared skills.sh registry (verified: git-repo content model, 9615 skills) with automatic credit (author/source/published_at stamping), /skills publish + receipt, docs/SKILLS-MARKET.md. done 2026-08-12 (omni-skills publish_skill + SKILLS-MARKET.md, 35 tests).

## MOONSHOTS (proposals — pick or add yours)

- [ ] M1. XOMNI as a service: OpenAI-compatible gateway mode — any app (VS Code, Excel, WhatsApp, custom) talks to XOMNI as a localhost API.
- [ ] M2. Self-hosted XOMNI Marketplace live: skills/MCPs/plugins with 15% rails + UPI payouts — the ecosystem bet (design exists in MONETIZATION-V2.md).
- [ ] M3. Voice-native Bharat agent: full-duplex Hindi/regional TTS+STT via Sarvam/Bhashini — talk to XOMNI like a phone call.
- [ ] M4. Agent-to-agent economy: XOMNI instances trading services + verification receipts (autonomous-agent-economy).
- [ ] M5. Offline-first XOMNI: full local stack (Ollama + local embeddings + local search) — works on a no-internet laptop.
- [ ] M6. Self-improving operator: XOMNI runs its own improvement + task-execution loop 24/7 with human-on-top approvals (the cron is the seed).

## P0 — next wave (highest value, build now)

- [x] 01. omni-registry: models.dev live-refresh + pinned snapshot + CI conflict check (data/models.snapshot.json, /models2 refresh, ci_gate extension) — done 2026-08-12 (refresh_from_models_dev + snapshot_load in core.py; models.snapshot.json pinned sha256 ffe72277…; ci_gate MODELS-DEV warn-only check; 25/25 matched, 1 flagged CTX conflict)
- [x] 02. codebase-index: optional embeddings layer (Ollama/local-models) with RRF fusion + /cindex hybrid flag — done 2026-08-12 (P0 workforce wave)
- [x] 03. omni-skills: marketplace installer from git URL (anthropics/skills-style) — /skills-marketplace <url> — done 2026-08-12 (P0 workforce wave)
- [x] 04. omni-tools: recall benchmark harness + /tools-stats metrics surface — done 2026-08-12 (P0 workforce wave)
- [x] 05. bharat-pack: expand to 5 more languages (mr/ta/te/kn/gu minimal UI strings + greet) — done 2026-08-12 (P0 workforce wave)
- [x] 06. bench: extend .bench/ci_gate.py import gate to all 22 plugins (<90ms each) + .bench/bench2.py for new plugins — done 2026-08-12 (P0 workforce wave)
- [x] 07. website: FEATURES v3 page (22 plugins, capabilities registry section, new-wave highlights) — done 2026-08-12 (P0 workforce wave)
- [x] 08. docs/PROVIDERS.md: India section — Sarvam/Bhashini/Krutrim real endpoints, env vars, INR pricing — done 2026-08-12 (P0 workforce wave)
- [x] 09. cost-tracker: CSV export + weekly digest text (/cost export, /cost digest) — done 2026-08-12 (P0 workforce wave)
- [x] 10. repo hygiene: README plugin table re-sync (22), sitemap update, count sweep verify 763 — done 2026-08-12 (P0 workforce wave)
- [x] 11. TEST-MATRIX.md: add per-plugin runtime column (suite seconds) for the 5 new plugins — done 2026-08-12 (P0 workforce wave)

## P1 — next-next

- [x] 12. WhatsApp B2B agent mode: docs + provider snippet (Meta WABA per-message pricing; consumer bots barred — B2B only)
- [x] 13. UPI rails spec: docs/UPI.md (Razorpay UPI Intent/Autopay, 0% MDR, DPDP notes) — done 2026-08-12 (P1 workforce wave)
- [x] 14. omni-memory: MCP adapter (memory tools over JSON-RPC for any MCP client) — done 2026-08-12 (P1 workforce wave)
- [x] 15. gh-ops: PR-review enhancement (draft comment batch + review summary tool) — done 2026-08-12 (P1 workforce wave)
- [x] 16. codebase-index: query CLI polish (/cindex query --json, top-N, symbols-only) — done 2026-08-12 (P1 workforce wave)
- [x] 17. sandbox-gate: Windows-specific rule pack (powershell/cmd destructive verbs) — done 2026-08-12 (P1 workforce wave)
- [x] 18. verify-runner: coverage summary mode (--coverage with stdlib trace) — done 2026-08-12 (P1 workforce wave)
- [x] 19. website: client-side search for docs (tiny JS index, zero network) — done 2026-08-12 (P1 workforce wave)
- [x] 20. bharat-pack: TTS preview via Sarvam free tier (text_to_speech-compatible snippet) — done 2026-08-12 (P1 workforce wave)
- [x] 21. omni-registry: /models2 diff view (what changed vs last refresh) — done 2026-08-12 (P1 workforce wave)
- [x] 22. homepage perf audit: lighthouse-style checklist + results in docs — done 2026-08-12 (P1 workforce wave)

## P2 — scale

- [x] 23. Plugin marketplace rails: 15% take-rate spec + receipts (docs/MARKETPLACE.md) — done 2026-08-12
- [x] 24. Lightning micro-payouts pilot (global payouts; India stays UPI — 30%+1% TDS) — done 2026-08-12 (docs/LIGHTNING-PAYOUTS.md)
- [x] 25. Enterprise tier: audit log + SSO-ready docs — done 2026-08-12 (audit-log plugin + docs/ENTERPRISE.md)
- [x] 26. Desktop GUI skin sync: xomni skin in the desktop app (dark/light pairing) — done 2026-08-12 (data/skins/xomni-skin.json + docs/DESKTOP-SKIN.md)
- [x] 27. Gateway proxy mode docs: expose XOMNI as an OpenAI-compatible endpoint — done 2026-08-12 (docs/GATEWAY-PROXY.md)
- [x] 28. Release automation: tag script (v1.x.y) + changelog generator + PyPI publish dry-run — done 2026-08-12 (scripts/release.sh + scripts/changelog.py + CHANGELOG.md, dry-run verified)
- [x] 29. omni-tools: cross-surface recall eval (plugin+MCP+skill mixed queries, 50-case set) — done 2026-08-12 (50 cases 15/15/10/10, recall@5 1.000, runner + report)
- [x] 30. cost-tracker: model-cost table sync with omni-registry (single source of truth) — done 2026-08-12 (sync_costs_from_snapshot + /cost sync, 25 models from snapshot)

## Never (do not build)

- Consumer WhatsApp assistant (Meta ToS bars it in India since 2026-01-15)
- Anything touching DeepSeek's servers or third-party sessions (impossible)
- Hooks with LLM/network/subprocess calls (speed rule)
