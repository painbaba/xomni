# model-router — automatic per-task model routing

Picks the best free gateway model per task **automatically** — the user never
chooses. Routing reads REAL capability data from
[`omni-registry`](../omni-registry/) (`context_window`, `capabilities`,
`capability_sources`, `latency_ms`, `status`) enriched with
[`provider-pool`](../provider-pool/) `GATEWAY_MODELS` tags
(`fast`/`reasoning`/`vision`/`heavy`/`default`). Pure stdlib, zero
Hermes imports, zero network.

## Automatic routing hook (pre_llm_call)

One deterministic `pre_llm_call` hook (legacy-style, ci_gate-legal): it
classifies the user prompt task type with **keywords only** (no model-API
call, no network, no subprocess, no disk I/O — well under 1ms) and, when
`model-router.auto_route` is enabled (default `true`) and the classified
model differs from the configured model, records the suggestion in memory
(`core.last_suggestion()` + a pending-telemetry queue) and annotates
`ctx.model_router_suggestion`. The host may apply the override if its
per-call API allows it; otherwise the annotation is visible to the host's
model selection. The hook itself **never switches the model** — `/route`
remains advisory. The ledger write is deferred to the next `/route`
command (`core.flush_pending_telemetry()`), so the hook hot path is pure CPU.
Disable with `hermes config set model-router.auto_route false`.

## Task types (auto-detected from the prompt)

| task type | routing rule (over registry capabilities) | example pick |
|---|---|---|
| `quick` | fast-tagged **or** `latency_ms < 5000`; lightest context (fastest TTFT), tools-capable | `minimax-m2.5` |
| `reasoning` | `thinking`/`always_thinking` capability; prefers reasoning-tagged + verified thinking, biggest ctx | `deepseek-v4-pro` |
| `vision` | `image_in` capability **required**; prefers live-verified `image_in` (minimax-m3 is the only spot-checked one) | `minimax-m3` |
| `heavy` | largest `context_window` among active models | `gpt-5.6-luna` |
| `default` | tools+thinking workhorse, default-tagged preferred | `deepseek-v4-flash` |

Detection precedence: **vision > reasoning > heavy > quick > default**
(a "summarize this screenshot" is a vision task, not a quick one). Keyword sets
live in `core.KEYWORDS` (prefix-anchored word matches).

## Commands

```
/route <prompt>      chosen model + task type + reason + switch command
                     ('hermes config set model <id>') + provider hint
                     (ADVISORY — prints what the hook would do)
/route telemetry     last 10 routed calls: model, ms, $, task type
                     (auto-includes every call the hook classified)
/route record <model> <ms> [est_cost] [task_type]
                     manually log a routed call into the ledger
```

## Telemetry

`record_call()` appends to the **same ledger format as
[`cost-tracker`](../cost-tracker/)** (`calls` table:
ts/day/week/model/provider/tokens/est_cost/flagged) extended with
`latency_ms` + `task_type`. When cost-tracker is importable its
`CostTracker.est_cost()` math is reused (so `/cost` and `/route telemetry`
agree); otherwise an internal `FREE_MODELS`/fallback-rate table is used and
rows are flagged. Ledger: `~/.xomni-cost/route.db`.

## Tests & demo

```
cd plugins/model-router
python -m unittest tests.test_core -q     # 20 tests, all green
python scripts/demo.py                    # command-level demo (routing + telemetry)
```
