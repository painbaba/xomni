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
- **`/cost` commands** — `/cost` (report: top models by cost, totals, budget
  status), `/cost budget <daily> [weekly]`, `/cost budget hard on|off`.
- **`cost_track` tool** — the gate + logger in one call for provider-pool
  integration: checks the budget first, then logs.

## Data

Everything is local — `~/.xomni-cost/costs.db` (sqlite). Tables: `calls`
(append-only ledger: ts, day, week, model, provider, tokens, est_cost,
flagged) and `config` (daily_cap, weekly_cap, hard_stop). No telemetry, no
sync, nothing leaves the machine.

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
