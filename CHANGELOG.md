# Changelog

Generated 2026-08-12 from git log (full history, no tags found), newest first.

## other

- a8dc776 xomni providers add: one-command LLM-provider connect (writes providers.<id> block + .env placeholder, YAML-validated, idempotent, --yes/--dry-run, loud failures); 12 tests; docs/PROVIDERS.md; CLI 1.2.0
- 02b0221 quality wave A-E: skill-drafter auto-draft bridge (regex fix + in-flight skip), --yes audit + NONINTERACTIVE docs, model-router deterministic routing hook (0.056ms, ci_gate DETERMINISTIC_HOOK_PLUGINS), publish delegates to host hermes skills publish, MCP/trading-stack e2e (live CoinGecko 200); CLI 1.1.0 data resolution via direct_url; gate env-noise recheck; 1009/1009
- 18af5e5 TEST-MATRIX regen (982/982, runtime col)
- aadce98 U11 cross-session skill market: omni-skills publish_skill (author/source/published_at stamping, REJECT refusal, idempotent), /skills publish with push + npx skills add steps + receipt, docs/SKILLS-MARKET.md; 35 omni-skills tests
- e4b2228 U8 domain-guardrails (built by coordinator — leaf burned budget on reads and wrote nothing): per-domain policies (trading analysis-OK/execution-approval default), /guardrails check, 16 tests, zero hooks
- 6a56926 U10 voice-first mode: plugins/voice-first (ffmpeg/arecord capture, whisper-or-Gemini STT, edge-tts TTS, /voice test|ask|on, fail-loud, 17 tests, zero hooks)
- 338f2bf BACKLOG: U5/U6/U7 building (model router, skill drafter, receipts)
- 5b1692a BACKLOG: U11 cross-session skill market (building; skills.sh verified as git-repo directory)
- 8b3b0a6 BACKLOG: U10 voice-first mode (building)
- 3c3b2a1 BACKLOG: U9 self-healing agent (building)
- 57006c8 BACKLOG: U8 domain guardrails (building) + MOONSHOTS proposals M1-M6
- 7f680a5 BACKLOG: USER-DRIVEN v1.1 section — 4 quick wins + 3 big wins from owner's hands-on session (MCP 2-vs-311 gap verified)
- 984d145 P1 workforce wave remainder: verify-runner coverage final touches (authoritative-exit double-run + README); BACKLOG 12-22 done
- 33d76e2 P0 workforce wave (11/11 landed): models.dev refresh+snapshot+CI check, codebase-index embeddings/RRF, omni-skills git marketplace, omni-tools recall bench, bharat-pack 5 langs, bench2+22-plugin gate, features.html+nav+sitemap, 20 providers, cost export/digest, hygiene sweep, TEST-MATRIX runtime col; BACKLOG 01-11 done
- ce38c75 docs/BACKLOG.md: 30-item continuous-improvement queue (P0/P1/P2 + never-list)
- 2ecec88 next-feature wave: 5 new plugins (22 total) — omni-registry (capability registry, corrected 1M ctx), codebase-index (FTS5 repomap v2), omni-tools (tool-search corpus/BM25 router), bharat-pack (Hindi + Indian model pool), cost-tracker + perkline 2.0 deltas; 763/763 tests; docs/site/CLI cascaded
- 17c32b8 standalone XOMNI branding: xomni skin (void/emerald, ◉ XOMNI panel label, XOMNI welcome), XOMNI SOUL persona, launchers boot the standalone xomni profile (HERMES_HOME)
- 2cbb2fb STATS.md: last 647 -> 677
- 34911cb STATS.md: 647 -> 677 (post-hardening)
- 95dad0d xomni_cli: fix ROOT resolution for package layout (checkout + installed modes both list 17 plugins)
- c630789 nav race fix: gallery link in troubleshooting + roadmap pages
- 207a832 installable package + provider coverage + full skill access: pyproject (pip install ., xomni CLI), 17-channel provider catalog (docs/PROVIDERS.md), omni-skills search/list/status commands, CLI: plugins list/install, skill search/install, providers, doctor; final backlog (troubleshooting/architecture/roadmap pages, MCP export, classifier tests, verify-runner example, check_models, STATS); 677/677 tests
- aa4a359 omni-skills plugin (#17): SKILL.md interop — /skills-scan /skills-install /skills-marketplace + skills_import tool, fail-closed validation, zero hooks; 12 tests; cascade 16->17 plugins, 635->647 tests
- 8709170 P0 competitive wave: superpowers harvest (25 skills -> skills.db), awesome-cursorrules rules catalog (99), provider capability-registry proposal, RULES.md
- 5ad9ae9 plugin READMEs D (omni-design/parallel/memory/media) — 16/16 plugins documented; fix 14->16 in COMPETITIVE.md
- badf758 docs/COMPETITIVE.md: consolidated competitive shortlist (merge candidates ranked, P0-P2 build roadmap, risks)
- d02216f monetization-trio edge-case tests (task 3 completion): waitperk +7, perkline +7, title-statusline +5 -> 635/635; FEATURES.md test column synced to TEST-MATRIX; count sweep 603->635
- 7b6dcf5 omni-design: audit precision — IGNORECASE hex scan + preset token-family whitelist (gallery stays honest 1/1/1, real indigo still caught)
- 4927c82 wave2: SEO, CI workflows + gate, gallery, sponsors, hindi, ollama docs, quickstart, changelog, brand sweep; fix audit precision, 603-test cascade
- da432f3 site: 7 theme columns (auto-fit grid), heading fix
- ee24e9e XOMNI: 16 plugins, flagship site, skills+MCP catalogs, 386 tests green
- d774fa6 Document native BYO-provider support: any OpenAI-compatible endpoint via config.yaml (custom profile + 32 built-in provider profiles, base_url/api_key, fallback_providers chain). Drop redundant /providers registry.
- 91efe37 Exclude sensitive content from public skills catalog (real-person dossiers, Epstein case notes, battle-arena attack playbooks). Add .gitignore guards.
- 944dbde Ship the full skills catalog in-tree: 170 SKILL.md across 42 domains (cloudflare, hyperframes, media-use, research, mlops, productivity, devops, security, web-perf). Ignore hermes runtime state. README updated to point at skills/.
- 1d4b07b Bundle Ollama: zero-install local models. start-ollama.ps1 (download once, auto-serve, pull qwen2.5:3b), /ollama commands, launcher hooks, XOMNI_HOME runtime dir. 357 tests passing.
- 5719e22 Add OpenClaw as 7th agent: omni-memory (local semantic memory) + omni-media (OCR/vision pipeline). 346 tests passing.
- a7e7033 Add skills section: 200+ skills inherited from the Hermes host
- bf77efa Add ARCHITECTURE/FEATURES docs, verified test matrix (329/329 pass) and live free-model routing table
- b049502 XOMNI: one agent, every feature, every free model
