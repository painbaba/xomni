# XOMNI BACKLOG — continuous improvement program

Owned by the improvement workforce (cron: xomni-improvement-workforce, every 3h)
+ coordinator waves. Rule: one item = one leaf = self-contained brief. Mark
status: `[ ]` open · `[~]` in progress (date) · `[x]` done (date). Keep this
file current — it is the workforce's queue.

## P0 — next wave (highest value, build now)

- [ ] 01. omni-registry: models.dev live-refresh + pinned snapshot + CI conflict check (data/models.snapshot.json, /models2 refresh, ci_gate extension)
- [ ] 02. codebase-index: optional embeddings layer (Ollama/local-models) with RRF fusion + /cindex hybrid flag
- [ ] 03. omni-skills: marketplace installer from git URL (anthropics/skills-style) — /skills-marketplace <url>
- [ ] 04. omni-tools: recall benchmark harness + /tools-stats metrics surface
- [ ] 05. bharat-pack: expand to 5 more languages (mr/ta/te/kn/gu minimal UI strings + greet)
- [ ] 06. bench: extend .bench/ci_gate.py import gate to all 22 plugins (<90ms each) + .bench/bench2.py for new plugins
- [ ] 07. website: FEATURES v3 page (22 plugins, capabilities registry section, new-wave highlights)
- [ ] 08. docs/PROVIDERS.md: India section — Sarvam/Bhashini/Krutrim real endpoints, env vars, INR pricing
- [ ] 09. cost-tracker: CSV export + weekly digest text (/cost export, /cost digest)
- [ ] 10. repo hygiene: README plugin table re-sync (22), sitemap update, count sweep verify 763
- [ ] 11. TEST-MATRIX.md: add per-plugin runtime column (suite seconds) for the 5 new plugins

## P1 — next-next

- [ ] 12. WhatsApp B2B agent mode: docs + provider snippet (Meta WABA per-message pricing; consumer bots barred — B2B only)
- [ ] 13. UPI rails spec: docs/UPI.md (Razorpay UPI Intent/Autopay, 0% MDR, DPDP notes)
- [ ] 14. omni-memory: MCP adapter (memory tools over JSON-RPC for any MCP client)
- [ ] 15. gh-ops: PR-review enhancement (draft comment batch + review summary tool)
- [ ] 16. codebase-index: query CLI polish (/cindex query --json, top-N, symbols-only)
- [ ] 17. sandbox-gate: Windows-specific rule pack (powershell/cmd destructive verbs)
- [ ] 18. verify-runner: coverage summary mode (--coverage with stdlib trace)
- [ ] 19. website: client-side search for docs (tiny JS index, zero network)
- [ ] 20. bharat-pack: TTS preview via Sarvam free tier (text_to_speech-compatible snippet)
- [ ] 21. omni-registry: /models2 diff view (what changed vs last refresh)
- [ ] 22. homepage perf audit: lighthouse-style checklist + results in docs

## P2 — scale

- [ ] 23. Plugin marketplace rails: 15% take-rate spec + receipts (docs/MARKETPLACE.md)
- [ ] 24. Lightning micro-payouts pilot (global payouts; India stays UPI — 30%+1% TDS)
- [ ] 25. Enterprise tier: audit log + SSO-ready docs
- [ ] 26. Desktop GUI skin sync: xomni skin in the desktop app (dark/light pairing)
- [ ] 27. Gateway proxy mode docs: expose XOMNI as an OpenAI-compatible endpoint
- [ ] 28. Release automation: tag script (v1.x.y) + changelog generator + PyPI publish dry-run
- [ ] 29. omni-tools: cross-surface recall eval (plugin+MCP+skill mixed queries, 50-case set)
- [ ] 30. cost-tracker: model-cost table sync with omni-registry (single source of truth)

## Never (do not build)

- Consumer WhatsApp assistant (Meta ToS bars it in India since 2026-01-15)
- Anything touching DeepSeek's servers or third-party sessions (impossible)
- Hooks with LLM/network/subprocess calls (speed rule)
