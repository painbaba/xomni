# XOMNI Changelog

> Current: **17 plugins / 677 tests / 519 skills / 311 MCPs**
> All entries are taken verbatim from `git log`; nothing invented.

## 2026-08-12

- `da432f3` — site: 7 theme columns (auto-fit grid), heading fix
- `ee24e9e` — XOMNI: 17 plugins, flagship site, skills+MCP catalogs, 677 tests green

## 2026-08-11

- `d774fa6` — Document native BYO-provider support: any OpenAI-compatible endpoint via config.yaml (custom profile + 32 built-in provider profiles, base_url/api_key, fallback_providers chain). Drop redundant /providers registry.
- `91efe37` — Exclude sensitive content from public skills catalog (real-person dossiers, Epstein case notes, battle-arena attack playbooks). Add .gitignore guards.
- `944dbde` — Ship the full skills catalog in-tree: 170 SKILL.md across 42 domains (cloudflare, hyperframes, media-use, research, mlops, productivity, devops, security, web-perf). Ignore hermes runtime state. README updated to point at skills/.
- `1d4b07b` — Bundle Ollama: zero-install local models. start-ollama.ps1 (download once, auto-serve, pull qwen2.5:3b), /ollama commands, launcher hooks, XOMNI_HOME runtime dir. All tests passing.
- `5719e22` — Add OpenClaw as 7th agent: omni-memory (local semantic memory) + omni-media (OCR/vision pipeline). 346 tests passing.
- `a7e7033` — Add skills section: 200+ skills inherited from the Hermes host
- `bf77efa` — Add ARCHITECTURE/FEATURES docs, verified test matrix (329/329 pass) and live free-model routing table
- `b049502` — XOMNI: one agent, every feature, every free model

---

*Generated from `git log` — 10 commits total across 2 days.*
