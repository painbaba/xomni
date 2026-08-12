# omni-registry — capability-declared model registry

Advisory metadata layer over the provider-pool free-model catalog (opencode
Zen gateway, 25 models). Every number and capability carries its own source
(`verified | spec | estimated`) and origin provenance, per
`.tmp/research-next/CAPABILITY-REGISTRY.md` (2026-08-12) and
`docs/PROPOSALS/provider-capability-registry.md` §2.

**Zero hooks, zero Hermes imports in core, zero network, zero subprocess.**
The registry is read-only data + text views; routing behavior is P1.

## Files

| File | Role |
|---|---|
| `data/capabilities.json` | Registry: 25 active records + 2 tombstones, `sources[]` snapshot pins (sha256) |
| `core.py` | Pure-stdlib API: `registry_load`, `capability`, `filter_by_capability`, `capabilities_text`, `conflict_report`, `recommend`, … |
| `__init__.py` | `/models2` command + `registry_status` tool — no hooks |
| `tests/test_core.py` | 15 unittest methods, offline |

## Schema (v1.0.0)

One record per model: `id` (gateway slug = merge key), `name`, `provider`
(channel id, `opencode-zen`), `status` (`active | removed | unverified`),
`context_window`/`max_output` as `{value, source, origin}` envelopes,
`capabilities` (closed enum: `image_in | video_in | thinking |
always_thinking | tools | structured_output`) + `capability_sources`
(per-capability source map), `cost_per_1m` (USD/1M, 0.0 = free channel),
`latency_ms` (median over a probe window), `verified {ok, date, method,
last_seen}`, `provenance {primary, updated_at}`.

- **Per-field source**: `verified` = live spot-check, `spec` = vendor/registry
  claim (models.dev intent labels, LiteLLM), `estimated` = derived seed.
  Only `minimax-m3.image_in` is `verified` (live image-input test); everything
  else is `spec` (models.dev) or `estimated` (latency seed).
- **Tombstones**: removed models are preserved with `status: "removed"` +
  `provenance.reason` — never deleted (KLIP-6 precedent). `kimi-k2` and
  `glm-4.6` are sample history records demonstrating the mechanism; real
  decommissions get recorded the same way. `conflict_report` keeps them
  schema-valid.
- **Snapshot pins**: `sources[]` carries sha256 of the models.dev and LiteLLM
  files fetched 2026-08-12 (25/25 gateway slugs matched on models.dev).

## deepseek-v4-flash context correction

The old curated `131072` was wrong (research F3). Adopted value:
**1,000,000** (`spec`) — LiteLLM `max_input_tokens=1000000` (bare and
`azure_ai` entries) and research F3; models.dev live fetch shows
`limit.context=1048576`. All three numbers are recorded in the record's
`origin` so the conflict stays auditable instead of silently resolved.

## Consumers

- `registry_load() -> dict[str, record]`
- `capability(model_id, key=None)` — full record or field (envelopes intact)
- `filter_by_capability(status="active", **caps)` — e.g.
  `filter_by_capability(thinking=True, tools=True)`
- `capabilities_text()` — `/models2` output, retired rows shown as tombstones
- `conflict_report(registry=None, snapshot=None)` — CI-readable:
  internal consistency + slug/context diff vs a pinned snapshot
  (`MISSING-SLUG` / `CTX` / `OUT` lines; `conflict_report: OK` when clean)
- `recommend(role)` — derived from `filter_by_capability` (verified-first),
  replaces hand-maintained maps in P1

## Test

```
cd plugins/omni-registry && python -m unittest tests.test_core -q
```
