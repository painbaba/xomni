# domain-guardrails — per-domain approval policies

All-or-nothing safety is wrong for a capable agent. This plugin makes approval
POLICY-DRIVEN: each domain gets its own analysis-vs-execution rule, so a
trading stack defaults to **analysis OK, execution requires explicit approval**.

## Policy table

| domain | analysis | execution |
|---|---|---|
| trading | allow | **block-approval** |
| money | allow | **block-approval** |
| medical | warn | **block-approval** |
| legal | warn | **block-approval** |
| crypto | allow | **block-approval** |
| code-exec | allow | warn |
| unknown | allow | warn |

`block-approval` = the action is NOT allowed until a human explicitly approves.

## Commands

- `/guardrails` — policy table
- `/guardrails check <text>` — verdict for a request:
  domain, action class, policy, allowed?, requires-approval?, reason

Example:

```
/guardrails check place a buy order for 100 shares of AAPL
VERDICT: REQUIRES APPROVAL
  domain: trading
  action: execution
  policy: block-approval
  reason: trading/execution: block-approval
```

## How it decides

- `classify_domain(text)` — pattern match against trading/money/medical/legal/
  crypto/code-exec vocabularies; no match → `unknown` (conservative).
- `action_class(text)` — execution markers (place/execute/transfer/send/
  delete/write/deploy/install/buy/sell/order/move/pay/submit/push/commit…)
  beat read markers (fetch/query/analyze/report/get/list/read/check/
  summarize/review…); unmarked requests default to analysis.
- `decide(text, stack=None)` — applies the policy (stack overrides via
  `STACK_POLICIES`; the trading-stack keeps the block-approval default).

## Speed posture

**Zero hooks** — nothing runs between turns; 0ms per-turn cost. All checks
happen inside the explicit command or via the `decide()` tool when the model
chooses to use it.

## Test

```bash
cd plugins/domain-guardrails && python -m unittest tests.test_core -v
```
