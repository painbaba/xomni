# PARALLEL-PLAYBOOK — omni-parallel

Research-backed patterns for running parallel agent swarms with XOMNI. Each
pattern: what it is, why it works, when to use it. Sources: 5-tool research
synthesis (Kimi, Cursor, Claude, Codex, Others) — see .tmp/omni-parallel/SYNTHESIS.md.

## 1. Decompose before you parallelize (anti-serial-collapse)

- **Pattern:** split the goal into independent subtasks FIRST; refuse to fall
  back to "just do them one after another".
- **Why:** Kimi's PARL training explicitly fights *serial collapse* — the #1
  failure of hand-rolled delegation is the orchestrator doing N sequential
  steps that could be one parallel batch. Cursor's "Build in Parallel" runs the
  same idea: detect independent plan parts, fan out, keep dependent steps ordered.
- **When:** any goal with 2+ independent deliverables (scan N vendors, migrate
  N modules, research N questions).
- **How:** `/swarm 'N | brief'` or a plan file; one queue entry per independent
  workstream. Keep entries genuinely independent — shared-state subtasks belong
  in ONE entry, not N.

## 2. Context packs: one self-contained brief per worker (context hygiene)

- **Pattern:** every worker gets a context block with goal, constraints, the
  deliverable contract, and an isolation note — never a pointer to "the chat".
- **Why:** Codex/Claude/Cursor all isolate worker context so noisy intermediate
  output never floods the main thread; a "summarize-or-fail" contract keeps
  results usable. Workers without shared context cannot corrupt each other.
- **When:** every fan-out, always. Cheap and removes the top cause of merged
  messes.
- **How:** `make_context_pack(brief, repo_path, template)` from templates/
  (default / research / coding). The contract line is mandatory:
  "write files to <out>, summary under 10 lines, VERDICT: done|partial|blocked".

## 3. Fan-out via the HOST's delegate_task (this plugin never spawns)

- **Pattern:** the plugin builds queue + packs; the host model drives one
  delegate_task per queue entry (Hermes cap: ~11 concurrent, depth 3 — schedule
  in waves if N > 11).
- **Why:** the plugin cannot call the host's delegate_task — it is the
  queue/status/judge/merge layer. Keeping fan-out model-driven (OpenAI SDK
  "orchestrator-workers" vs "code-decided") preserves the host's permissions,
  sandboxing and approval flow.
- **When:** every swarm run. The `swarm_plan` tool prints the exact
  delegate_task instructions for the host.

## 4. Queue + status surface (parallelism without observability is unusable)

- **Pattern:** a persistent task list with statuses (pending → in_progress →
  done/failed) and a table view.
- **Why:** OTHERS research: every serious tool ships a dashboard (Windsurf
  Command Center Kanban, Copilot Workspace task list, Q Developer dev-task
  list). Claude agent teams persist the task list as JSON; Kimi batch API keys
  results by custom_id.
- **When:** any run longer than one wave, or any run you might resume later.
- **How:** TaskQueue persists to state.json on every change, dedupes by id,
  survives corrupt state. `/swarm status` prints the table.

## 5. Judge: rank results deterministically, then let the model pick

- **Pattern:** after all workers finish, score each result against the brief
  (deliverable present? verdict line? summary sane? keywords hit?), emit a best
  pick with rationale.
- **Why:** Cursor's multi-agent judging auto-evaluates parallel runs and
  comments on the picked agent; OpenAI's evaluator-optimizer pattern does the
  same. Fan-out creates "which result do I trust?" — answer it explicitly.
- **When:** research sweeps, parallel implementations of one feature, arena
  comparisons. For contested picks, run the judge first, then have the host
  review the top 2.
- **How:** `/swarm judge results.json [--rubric default|code|research]` —
  deterministic, no LLM cost.

## 6. Merge: split results into logical PRs (split-into-PRs)

- **Pattern:** group worker diffs into logical chunks (per plugin/module
  prefix), each with files + a suggested commit message; review before merging.
- **Why:** Cursor's "Split changes into PRs" (backup snapshot + approval) is
  the strongest end-to-end parallel UX with safety rails; parallel outputs
  need a reviewable, reversible delivery flow, not a blind concatenation.
- **When:** any fan-out that touched the repo, before anything is committed.
- **How:** `/swarm split-pr <diff.txt>` → chunked merge plan; commit per chunk;
  snapshot (git stash/branch) before applying.

## 7. MapReduce for scanning/audit swarms

- **Pattern:** shard the scan space (files, URLs, targets) across N workers →
  each returns findings → triage → remediate → feedback loop.
- **Why:** Devin's Security Swarm is the reference: sharded parallel agents
  with a triage/merge phase beat one agent grinding through everything, and
  cost is bounded per shard.
- **When:** audits, bulk research sweeps, "check all N things" jobs.
- **How:** `/swarm 'N | <scan brief>'` with template research; judge ranks
  findings; merge plan orders remediation PRs.

## 8. Worktree isolation for parallel file edits

- **Pattern:** give each write-capable worker its own git worktree/branch so
  two agents never edit the same checkout.
- **Why:** Claude (`--worktree`), Gemini, Windsurf and Codex all converge on
  worktrees as the parallelism substrate; Codex explicitly warns parallel
  write agents collide otherwise.
- **When:** any fan-out with write access to a repo (default for coding
  template). Read-only workers don't need it.
- **How:** `git worktree add` per task id; the split-pr flow turns each
  worktree into one PR.

## 9. Background agents with a status surface

- **Pattern:** start long workers detached; they notify on completion; the
  main session stays responsive.
- **Why:** Claude made background the default for subagents (notify on
  completion, permission prompts forwarded); Devin/Cursor run whole sessions in
  background. "Start it, close the laptop, come back to a PR."
- **When:** runs > a few minutes, or while you keep working on something else.
- **How:** host background delegation per queue entry; `/swarm status` is the
  surface; complete() records the result for the judge.

## 10. Agent-team mailbox conventions (inter-agent messaging)

- **Pattern:** agents communicate through a shared file-based mailbox
  (JSON inbox per agent) with provenance — messages are never treated as
  approvals.
- **Why:** Claude agent teams: `~/.claude/teams/{team}/inboxes/{agent}.json`,
  task claiming via file locks, dependencies auto-unblocked. File-based state
  survives restarts and is inspectable.
- **When:** teams with real inter-agent dependencies (research handoffs,
  verify loops). Overkill for independent fan-outs.
- **How (future):** mailbox JSON files next to state.json; for now, note
  cross-task needs in summaries and let the host route them.

## 11. Wave scheduling under concurrency caps

- **Pattern:** chunk N tasks into waves of ≤11 (Hermes concurrent-subagent
  cap), aggregate per wave.
- **Why:** Kimi scales to 300 agents; Hermes deliberately bounds at ~11 × depth
  3. Waves emulate large swarms within the cap without changing the host.
- **When:** N > 11. `/swarm` caps a single fan-out at 25 entries; split bigger
  goals into plan files with waves.

## 12. Plan-then-execute gate

- **Pattern:** a read-only plan phase before any write; workers may only
  execute after approval.
- **Why:** the universal safety valve (Aider architect/ask→code, Gemini Plan
  Mode, Devin plan mode, Q Developer approval, Copilot Workspace plan list).
- **When:** any swarm touching a repo or spending real money.
- **How:** swarm_plan output IS the plan; review the queue table + merge recipe
  before delegating.
