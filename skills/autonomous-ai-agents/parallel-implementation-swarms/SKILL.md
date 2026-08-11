---
name: parallel-implementation-swarms
description: Run parallel implementation swarms with a verification gate.
---

# Parallel Implementation Swarms (delegate_task batch)

Dispatch N independent build tasks to parallel subagents, then verify
EVERYTHING yourself before it ships. Proven pattern (2026-08-10): 5 workers
built 4 plugins + 1 skill in ~10-16 min each; the orchestrator's QA gate
caught 2 real defects (a command-name conflict and a YAML frontmatter bug)
that workers self-reported as green.

## When to use
- User wants a batch of independent modules/features built fast ("use a swarm")
- A backlog of well-separated implementation lanes exists (e.g. a port plan)
- Any multi-worker build where the orchestrator owns integration

## Dispatch pattern

1. **Decompose into lanes, one directory per worker.** Every worker owns a
   SEPARATE dir (e.g. `plugins/<name>/`) so parallel writes never collide.
   Independent lanes = no parent links; only true data dependencies gate.
2. **Write RICH self-contained context per worker** — the worker must never
   need the orchestrator mid-flight. Always include:
   - The repo root (BOTH path forms: `C:/Users/...` for python/open, `/c/...`
     for bash — native Windows python cannot read MSYS paths)
   - A PROVEN TEMPLATE to copy (point at an existing, tested artifact of the
     same shape, e.g. an existing plugin: "read plugins/perkline first; it is
     the proven structure")
   - The exact contracts that matter (hook return shapes, config formats) with
     the source-of-truth file to grep (e.g. `agent/shell_hooks.py`)
   - Known pitfalls of the domain (shared-mutable defaults → deepcopy; hooks
     that don't transform must return None; tests are unittest not pytest)
   - The deliverable contract: exact paths, "run tests until ALL pass",
     "report absolute paths + paste final unittest output", "do not edit
     README/docs (orchestrator owns them)"
3. **Dispatch one `delegate_task` batch** (max concurrency 11). Do not poll —
   the consolidated result re-enters the conversation when all finish.
4. **Peek at live transcripts once, early**: `cache/delegation/live/<id>/task-N.log`
   (append-only per task). One early read catches derailment (wrong paths,
   confused contracts) minutes after dispatch, while there's still time to
   course-correct.

## The verification gate (mandatory — worker self-reports are CLAIMS, not evidence)

1. **Run every test suite yourself** — `python -m unittest discover -s tests`
   per module. Confirm the "Ran N tests" line: an `OK` with no count means the
   suite silently ran nothing.
2. **Audit contracts against the source of truth**, not the README: hook
   return shapes (e.g. `{"action": "block", "message": ...}`), no telemetry,
   no core edits, deepcopy on nested defaults. Grep the worker's code for the
   shape you specified.
3. **Catch silent failures discovery won't show you**:
   - A plugin whose registered command collides with a built-in is dropped
     SILENTLY — `commands=0` in discovery with a registered command = conflict.
     Rename, re-copy, re-enable.
   - Worker-authored SKILL.md frontmatter: an unquoted `: ` in `description:`
     breaks the YAML parse and surfaces as the misleading "Skill X is not
     supported on this platform". Quote descriptions containing colons; parse
     the frontmatter before installing.
4. **Live e2e proof**: one `hermes chat -q "..."` run that must fire the new
   hooks and write real state (state files, session DB) — not just unit mocks.
5. **Install + enable + verify discovery counts** (`list_plugins()` entries:
   name/source/enabled/commands/hooks/tools/error; filter source=='user'),
   then update the docs yourself.

## User preference (hard-won)

When this user says "every feature / everything / nothing to be missed", they
mean it LITERALLY: full enumeration, a status tracker where every feature of
every source repo has a row (HOST / SHIPPED / VENDORED / WIRED / QUEUED /
PARKED-with-reason), and each build round converts QUEUED rows into SHIPPED.
Never silently scope down; never claim "everything" without the matrix to
prove it. Expect pushback ("NO BITCH", "EVERY FUCKING FEATURE") if you scope
down silently — that frustration is a signal to enumerate and track, not to
argue.

## Pitfalls
- **Trusting worker self-reports** — the #1 failure mode. Always run the tests
  and read the code yourself before install.
- **Skipping the count check**: `Ran 0 tests ... OK` is a green lie.
- **Workers editing shared files** — one dir per worker, docs owned by the
  orchestrator, or you get merge chaos.
- **Insufficient context** — a worker without the template/contracts/pitfalls
  burns turns rediscovering them (or worse, ships wrong shapes).
- **Big-repo full clones in the same turn as the swarm**: 2+ GB of clones can
  still be running when the batch returns — start clones in background with
  notify_on_complete before dispatching, or after.

## Verification checklist
- [ ] Every suite run by the orchestrator; "Ran N tests" N > 0; all green
- [ ] Contracts audited against source (hook shapes, no telemetry, no core edits)
- [ ] Silent-failure checks done (command conflicts, frontmatter YAML)
- [ ] Live e2e fired the new hooks (state written, no crash)
- [ ] Discovery: all plugins enabled, counts match registrations, error=None
- [ ] Feature matrix / docs updated to match what actually shipped
