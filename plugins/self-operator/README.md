# Self-Operator (M6)

The loop engine behind XOMNI's improvement workforce: it reads the backlog,
proposes a plan of open items, **waits for human approval before executing
anything**, and keeps a JSON-lines audit trail of every action.

Zero-hook: this plugin registers no hooks and creates no cron jobs — it is
driven by the existing cron improvement workforce, never the other way round.
Stdlib only (`json`, `re`, `time`, `pathlib`).

## Loop

1. **parse** — `parse_backlog(path)` finds open items (`- [ ] ` lines) in
   `docs/BACKLOG.md`, read-only, in file order with line numbers.
2. **propose** — `propose_plan(items, max_items=8)` builds a plan
   (`plan-<n>`) capped at 8 items, preserving file order.
3. **approve** — `submit_plan` persists the plan to `state/approvals.json`
   as `pending`; a human calls `approve_plan(plan_id, state_dir)` or
   `reject_plan(...)`. Only `pending` plans may transition — anything else
   raises `OperatorError`.
4. **execute** — `execute_approved(plan_id, state_dir, runner)` runs
   `runner(item_title)` per item. It raises `OperatorError` ("human approval
   required") unless the plan is `approved`.
5. **audit** — every executed item appends one JSON line to
   `state/operator.jsonl`; `audit_trail(state_dir)` parses it back.

`run_cycle(backlog_path, state_dir, runner=None, auto_approve=False)` runs
the whole loop: with a plan awaiting a human decision it returns
`{'status': 'awaiting_approval', 'plan_id': ...}`; with
`auto_approve=True` (explicit opt-out) it approves and executes, returning
`{'status': 'executed', 'results': [...]}`.

## State files

* `state/approvals.json` — `{"plans": [{"plan_id", "items", "count",
  "proposed_at", "status"}]}`, status ∈ pending/approved/rejected.
* `state/operator.jsonl` — one JSON record per executed item:
  `{"ts", "plan_id", "item", "ok", "note"}`.

## Rules

* Fail-loud: rule violations raise `OperatorError` naming the violation.
* Human-on-top: nothing executes without explicit approval (or the explicit
  `auto_approve=True` opt-out).

## Tests

```bash
cd plugins/self-operator && python -m unittest tests.test_core -q
```
