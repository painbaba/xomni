# omni-parallel

Parallel swarm layer for XOMNI: JSON-persisted TaskQueue + per-task context
packs + deterministic Judge + PR-split merge planning. Zero hooks — zero
per-turn cost.

**What it does:** `/swarm` queues N tasks (or loads a plan.md / plan.json)
and builds a self-contained context pack per task (deliverable contract +
verdict line); the deterministic Judge scores results with no LLM
(deliverable +30, verdict +20, summary length +10, brief keywords up to +40;
`code`/`research` rubrics add tests or sources/citations) and picks the best
with a stable tie-break; `/swarm split-pr` groups a unified diff's hunks by
path prefix (e.g. `plugins/<name>/`) into a chunked merge plan with
suggested commit messages. Fan-out is host-driven — the model calls its own
`delegate_task` per queue entry.

**Commands:** `/swarm` · `/swarm status` · `/swarm judge <results.json>
[--rubric default|code|research]` · `/swarm split-pr <diff.txt>
[--max-chunks N]` — **Tool:** `swarm_plan(brief, n, template)`

**Speed posture:** no hooks — pure stdlib, no LLM calls, no requests, no
subprocess. Corrupt/missing state degrades to empty, never raises.

**Config:** queue state at `plugins/omni-parallel/state.json` (atomic
tmp+rename); context-pack templates in `templates/` (fall back to builtin).

```bash
cd plugins/omni-parallel && python -m unittest tests.test_core -v
```
