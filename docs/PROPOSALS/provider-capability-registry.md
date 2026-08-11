# PROPOSAL: Provider Capability Registry

Status: DRAFT · 2026-08-12 · XOMNI 100-Agent Program, P0 competitive wave
Reference: docs/COMPETITIVE.md P0 #2 (kosong design, MoonshotAI/kimi-cli) · lands as an additive upgrade to plugins/provider-pool

## 1. Problem
- plugins/provider-pool/core.py models the pool as `{id, tags, vision}` — three
  fields, one boolean. No context window, no thinking/tool-use support, no output
  cap, no latency or cost. "Verified" (GATEWAY_MODELS docstring) means HTTP 200
  once on 2026-08-10 — a liveness fact, not a capability fact.
- /models output (`models_text()`) is a flat tags dump; machine consumers (P1
  router, budget alerts) cannot answer "which free models support vision AND tools".
- The site's "25 verified free models" claim (website/index.html `#models`) is not
  backed by machine-readable capability data — honest, but not self-describing.
- kosong's design (providers-as-protocols, per-model ctx/thinking/image/tool_use
  declarations, models.dev import + offline snapshot) is the reference target.
## 2. Proposed schema
New file `plugins/provider-pool/data/capabilities.json` — one record per model:

```json
{
  "id": "deepseek-v4-flash",
  "name": "DeepSeek V4 Flash",
  "provider": "opencode-zen",
  "context_window": 131072,
  "supports_vision": false,
  "supports_tools": true,
  "supports_thinking": true,
  "max_output": 8192,
  "verified": true,
  "verified_date": "2026-08-10",
  "latency_ms": 4100,
  "cost": 0.0
}
```

Semantics:
- `verified` = live HTTP 200 + capability spot-check (vision tested with image
  input, as minimax-m3 was); `verified_date` records when.
- `latency_ms` = median of the last N `gateway_health()` probes (2–26s realistic).
- `cost` = USD per 1M tokens; 0.0 for free channels.
- New module `plugins/provider-pool/registry.py`, pure stdlib like core.py.
  Load order: curated capabilities.json > models.dev snapshot.
## 3. models.dev import + offline snapshot fallback
- Import script pulls models.dev models.json, matches by id slug, fills missing
  fields (context_window, output tokens, modalities) into the registry.
- Offline snapshot checked in at `plugins/provider-pool/data/models-dev-snapshot.json`
  (kosong's approach): startup never blocks on the network; stale beats absent.
- Refresh policy: snapshot refreshed on a schedule; curated overrides always win
  on conflict; import is a merge, never a clobber.
## 4. provider-pool integration (new functions, no hooks)
Stays zero-hook / zero-Hermes-import, matching core.py's contract:
- `registry_load() -> dict[str, record]` — snapshot under curated overrides
- `capability(model_id) -> dict` — single-model lookup
- `filter_by_capability(**caps) -> list[str]` — e.g. supports_vision=True, supports_tools=True
- `capabilities_text() -> str` — /models output v2: per-model
  ctx/tools/think/vision columns replacing the tags-only dump; `models_text()`
  stays for backward compat
- `verified` flips false when `gateway_health()` stops returning the model
- `RECOMMENDED` map stays but becomes derived from `filter_by_capability()`
  instead of a hand-maintained dict

Website: the `#models` section renders capability cards (ctx, vision, thinking,
tools) from the same JSON emitted as `website/data/models.json`; the "25 verified"
stat gains a capability subtitle.
## 5. Migration
- Ship capabilities.json with all 25 GATEWAY_MODELS records; `verified=true` for
  the 25 live-verified; remaining fields filled from known specs (model cards,
  gateway /models) — record-by-record, one-time.
- vision stays honest: only minimax-m3 `verified=true` until re-tested with image
  input (existing policy).
- `latency_ms` seeded from the documented 2–26s envelope; refined by probes.
- Fully additive: GATEWAY_MODELS, `models_text()`, `recommend()` unchanged;
  registry is new surface only — no breaking change to callers or configs.
## 6. Risks / trade-offs
- models.dev drift: slugs won't match gateway ids → fuzzy name match + curated
  override; never auto-accept unknown ids.
- Spec vs reality: ctx/thinking from models.dev are vendor claims, not verified
  behavior; only vision/tool-use get live spot-checks — label source per field
  (verified | spec | estimated).
- Latency skew: cold starts and gateway rate limits pollute samples → median
  over a window, not single probes.
- Snapshot supply chain: import is a new external dependency → pin the snapshot,
  review diffs, add a CI job comparing records vs snapshot.
- Hand-filled records rot → a verify-registry CI job re-checks live status on a
  schedule.
- Scope guard: registry is advisory metadata. Routing/fallback behavior is NOT
  changed by this proposal; that is P1 (model routing with budget alerts).
## Decision
Adopt the schema + registry module with models.dev import and offline snapshot fallback, as an additive provider-pool upgrade. Follow-up: P1 routing doc.
