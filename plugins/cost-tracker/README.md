# cost-tracker

The honest-math ledger for XOMNI (Monetization V2, Phase 1): every model call
is logged to a local sqlite database with an estimated cost, budgets are
capped per day/week, and `/cost` reports it all. **Free forever** — it is the
proof for the "honest-latency + budget" story that sells sponsorship, not a
product to sell (docs/MONETIZATION-V2.md §4, §6).

**Zero hooks.** This plugin registers no hooks (new-plugin rule). `cost_track`
is called explicitly by provider-pool (or any caller) after a model call;
`/cost` reads the ledger on demand. Nothing sits on the agent hot path.

## What it does

- **Cost log** — `log_call(model, provider, tokens_in, tokens_out)` appends a
  row with an estimated USD cost from a built-in cost table (25 verified-free
  gateway models at $0; ~13 paid models at public list prices; unknown models
  use conservative fallback rates and are **flagged** in the ledger).
- **Budget caps** — per-day and per-week caps in USD (0 = no cap). Default is
  **warn-only**; `hard_stop` (opt-in) blocks new calls once a cap is reached —
  blocked calls are NOT logged.
- **Spend caps (rolling windows)** — `5h / 1d / 7d / 30d` caps stored in the
  ledger config table, each with an action: `warn` (warn text at >=80% of the
  limit, never blocks) or `park` (warn at >=80%, and at >=100% the **heavy
  tier** is parked). Windows are rolling (`ts - window .. ts`); `check_spend()`
  and `parked_models()` are pure reads — checking a cap **never mutates the
  ledger**. Heavy tier = paid models priced >= $1/1M input, derived live from
  the cost table (claude-opus-4, gpt-4o, …). Per-model caps
  (`/cost caps model <id> <limit>`) park a single model once its cumulative
  spend reaches the limit.
- **`/cost` commands** — `/cost` (report: top models by cost, totals, budget
  status), `/cost budget <daily> [weekly]`, `/cost budget hard on|off`,
  `/cost caps` / `set <period> <limit_usd> <warn|park>` / `clear <period>`,
  `/cost today`, `/cost week`, `/cost model <id>`, `/cost top` (top-5 models
  by spend), `/cost sync [path]` (re-sync costs from the omni-registry
  snapshot).
- **`cost_track` tool** — the gate + logger in one call for provider-pool
  integration: checks the budget first, then logs.

## Data

Everything is local — `~/.xomni-cost/costs.db` (sqlite). Tables: `calls`
(append-only ledger: ts, day, week, model, provider, tokens, est_cost,
flagged) and `config` (daily_cap, weekly_cap, hard_stop). No telemetry, no
sync, nothing leaves the machine.

## Single source of truth

Model costs are synced from the **omni-registry pinned snapshot** —
`plugins/omni-registry/data/models.snapshot.json` (the pinned models.dev
fetch). That snapshot is the single source of truth for what a model costs;
the built-in table in `core.py` is just the offline fallback.

- **Trigger** — `/cost sync` re-syncs the cost table on demand. An optional
  path argument or the `XOMNI_MODELS_SNAPSHOT` env var overrides the default
  snapshot location (e.g. for CI or a local copy).
- **Mapping** — snapshot pricing fields are mapped into the ledger's
  (input, output) USD-per-1M-token format. All three common shapes are
  understood: `cost_per_1m: {input, output}` (omni-registry),
  `pricing: {prompt, completion}` (models.dev api.json), and flat
  `input`/`output` keys. Snapshot records without pricing are treated as $0
  (the pinned snapshot covers the verified-free gateway set).
- **Merge, not wipe** — the synced table is the built-in table merged with
  snapshot entries: the snapshot governs the models it knows, paid models it
  does not cover keep their public list prices.
- **Graceful fallback** — if the snapshot is missing, unparseable, or has no
  `models` mapping, the sync **never crashes**: `/cost sync` prints a clear
  `WARNING` and the plugin keeps operating on the built-in (last-known)
  table, so the ledger and budget caps are unaffected.

```bash
cd plugins/cost-tracker && python -m unittest tests.test_core -v
```

## Integration with provider-pool

No hooks, no imports across plugins: provider-pool (or any caller) invokes the
tool after each call completes:

```python
from core import CostTracker
tr = CostTracker()
result = tr.cost_track("deepseek-v4-flash", provider="opencode-zen",
                       tokens_in=1234, tokens_out=567, task="refactor")
if result.get("blocked"):
    # hard-stop fired: route the next call to a cheaper model or refuse
    ...
```
