# Self-Operator (M6)

The self-improving operator: XOMNI runs its own improvement + task-execution
loop 24/7 with **human-on-top approvals** (the cron improvement workforce is
the seed; this plugin is the loop engine it drives).

## Loop stages

1. **parse** — read `docs/BACKLOG.md` (read-only); only `- [ ] ` unchecked
   items are open (`[x]` done, `[~]` in progress, indented/non-list lines are
   ignored). Returns items with line numbers.
2. **propose** — build a plan of open items (file order, capped at 8):
   `plan-<n>` with `items`, `count`, `proposed_at`.
3. **approve** — plan is submitted to `state/approvals.json` as `pending` and
   **waits for a human**. `approve_plan` / `reject_plan` only transition
   `pending` plans; violating transitions raise `OperatorError`.
4. **execute** — only an `approved` plan runs. `run_cycle` refuses with
   `{'status': 'awaiting_approval', ...}` while a decision is outstanding.
   `auto_approve=True` is the explicit opt-out for unattended runs.
5. **audit** — one JSON line per executed item appended to
   `state/operator.jsonl`; `audit_trail()` parses it back.

## Human-on-top rule

Nothing executes without explicit human approval. `execute_approved` raises
`OperatorError("human approval required ...")` for any non-approved plan.

## Audit file format (`state/operator.jsonl`)

One JSON object per line, one line per executed item:

```json
{"ts": 1750000000.0, "plan_id": "plan-1", "item": "fix login bug",
 "ok": true, "note": "dry-run"}
```
