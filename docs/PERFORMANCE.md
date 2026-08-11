# XOMNI Plugin Performance — 100x Incident Postmortem & Speed Workstream

Status: fixes landed in the working tree (uncommitted). Evidence: `.bench/results-before.json`
(original `.bench/results.json`, captured 2026-08-11 22:28, pre-fix code) and
`.bench/results-after.json` (re-run 2026-08-11, current code). Root-cause narrative recovered in
`.bench/rootcause-recovered.md`.

---

## 1. The 100x incident — root causes ranked by impact

14+ plugins were enabled in a live Hermes install at once, including `prompt-enhancer` **with auto
mode** (`allow_provider_override: true`) and three hook-heavy plugins. Per-turn overhead compounded
to ~100x. Ranked by measured/estimated impact:

| # | Root cause | Mechanism | Impact |
|---|-----------|-----------|--------|
| 1 | **prompt-enhancer auto mode** | One **extra `ctx.llm.complete` per turn** (~10–20s each on the slow provider) on top of every real turn | **Primary multiplier** — one LLM call per turn × 17 plugins' worth of context inflation |
| 2 | **15 plugins enabled at once** | `context-compact, context-loader, gh-ops, local-models, mcp-catalog, omni-media, omni-memory, perkline, PROMPT-ENHANCER, provider-pool, repomap, sandbox-gate, title-statusline, verify-runner, waitperk` | N hook-triggered LLM calls per turn multiply a ~17s baseline by 3–6x |
| 3 | **Per-event file I/O in hooks** | perkline + waitperk rewrote `state.json` AND `current.txt` on **every** `pre_llm_call`/`post_tool_call` (≥4 disk ops/turn); perkline also ran a full `os.walk` of the cwd per event | Measured 90.5ms + 106.8ms per event (perkline) |
| 4 | **omni-memory brief injection** | Injects a memory brief into **every** `pre_llm_call` when user message ≥ threshold | Per-turn token inflation + sqlite query |
| 5 | **context-compact LLM in compaction path** | `ctx.llm.complete` fired mid-turn when history exceeded the threshold (gated by cooldown, but could hit) | Extra LLM call on long sessions |
| 6 | **Provider misconfig + low timeout** | Invalid API keys (`sk-fake-…0000`) caused `invalid_api_key` errors; `request_timeout_seconds: 25` meant long-context calls on the slow gateway **timed out** — everything felt dead | Amplified perceived slowness; fixed at host level (25s → **120s**) |
| 7 | MSYS path mangling | python→bash subprocess `C:/Users/…` backslash issue (status.sh exit 127) | Operational noise during the omni era |

**Smoking gun:** auto-mode prompt-enhancer + hook-triggered LLM calls are the ~100x mechanism.
Pure hook CPU/IO was ~206ms/turn (perkline alone ~197ms) — real, but NOT the 100x.

### Verification: no LLM calls inside hooks (current code)

`grep -rn 'ctx.llm' plugins/*/__init__.py` — the only hit is `context-compact`, and only inside
`_summarize_older()`, which is unreachable from the hook path:

- `context-compact._on_pre_llm_call` — **PERF CONTRACT: never calls `ctx.llm.complete`**. Hook is
  deterministic (verbatim tail + omission counts, ~0.05ms); LLM-quality summaries only via the
  explicit `/ctxcompact now` command (`use_llm=True`).
- `omni-memory._on_pre_llm_call` — sqlite brief only (no LLM). `/memory-consolidate` is command-only.
- `perkline`, `waitperk`, `title-statusline`, `sandbox-gate` — no `ctx.llm`, no `requests`,
  no `subprocess` in any hook.

---

## 2. Per-plugin overhead — BEFORE vs AFTER (median ms, isolated harness, n=20)

Harness: `.bench/bench.py` (FakeLlm, no network; `python .bench/bench.py`). Imports are one-time
per process; hook medians are steady-state.

| Plugin | Hook | BEFORE (ms) | AFTER (ms) | Δ |
|---|---|---|---|---|
| **perkline** | pre_llm_call | **90.5200** | **0.0158** | ~5,700x faster |
| **perkline** | post_tool_call | **106.8053** | **0.0148** | ~7,200x faster |
| perkline | on_session_end | not registered pre-fix | 1.0448 | (rare event, flush) |
| **waitperk** | pre_llm_call | 3.8243 | **0.0036** | ~1,060x faster |
| **waitperk** | post_tool_call | 3.8704 | **0.0024** | ~1,600x faster |
| waitperk | on_session_start | 3.5910 | 4.4937 | rare event (disk) |
| waitperk | on_session_end | 2.4518 | 3.0808 | rare event (disk) |
| omni-memory | pre_llm_call | 0.6315 | 1.2517 | <1.3ms, noise |
| context-compact | pre_llm_call | 0.0233 | 0.0513 | noise |
| title-statusline | post_tool_call | 0.5277 | 0.5690 | noise |
| sandbox-gate | pre_tool_call | 0.0938 | 0.0683 | noise |
| gh-ops / local-models / mcp-catalog / omni-media / provider-pool / repomap / verify-runner / context-loader | — | no hooks | no hooks | — |

**Per-turn hook overhead (pre_llm_call + post_tool_call, all plugins):**

- BEFORE: ~95.0ms + ~111.2ms ≈ **~206ms/turn** (perkline alone ≈ 197ms)
- AFTER: ~1.32ms + ~0.59ms ≈ **~1.9ms/turn** (~108x reduction) — **well under the <1s/turn target**

Cold imports: all 17 plugins < 90ms one-time (`context-loader` 88ms worst on the after run;
perkline 21.7ms; waitperk 28.7ms). One-time per process, negligible.

### What the fixes actually do

- **perkline** (`plugins/perkline/__init__.py`, `core.py`): `stack_tags` results cached per-root
  with a 300s TTL (the `os.walk` of a large cwd — e.g. a home directory — now runs at most once
  per process); ledger held in memory for process lifetime; `state.json` + `current.txt` writes
  batched to at most once per 30s (`FLUSH_INTERVAL`) plus on session end; hooks pass
  `write_line=False`; paused state is a cheap early-return. Hooks still count every render
  in memory — impression correctness unchanged.
- **waitperk** (`plugins/waitperk/__init__.py`): same pattern — in-memory impression counting,
  30s flush window for `state.json`/`current.txt`, flush on session end.
- **context-compact** (`plugins/context-compact/__init__.py`): hook is deterministic-only; the
  `ctx.llm.complete` call lives behind `use_llm=True`, reachable only from the `/ctxcompact now`
  command.
- **Host level (not in this repo):** `request_timeout_seconds` 25s → **120s**. A 25s timeout on a
  slow gateway turns long-context calls into failures that feel like the agent is dead; low
  timeouts amplify any per-turn plugin overhead into hard errors.

---

## 3. Install guidance (how to use plugins without a repeat)

**Rule of thumb:** the incident was *configuration*, not any single plugin. Enable few, prefer
zero-LLM plugins, and never enable per-turn LLM hooks.

**Always-safe (no hooks or sub-1ms hooks, no LLM, no disk churn):**
`context-loader`, `gh-ops`, `local-models`, `mcp-catalog`, `omni-media`, `provider-pool`,
`repomap`, `sandbox-gate`, `title-statusline`, `verify-runner`.

**On-demand / optional (hook cost or token inflation — enable deliberately):**

- `perkline` — now ~0.03ms/event (safe to enable), but writes `~/.perkline` state; disable if you
  don't want the sponsor line.
- `waitperk` — now ~0.006ms/event; same caveat (`~/.waitperk`).
- `omni-memory` — injects a brief into **every** non-trivial turn (token inflation, not latency);
  consider raising `INJECT_MIN_QUERY_LEN` or using `/recall` on demand.
- `context-compact` — deterministic and ~0.05ms now; still injects context when it fires.
- **`prompt-enhancer` — NEVER enable auto mode** (`allow_provider_override: true`). If you want
  prompt enhancement, run it as an explicit command, never as a per-turn hook. This was root
  cause #1 of the 100x.

**Install checklist:**

1. `grep -rn 'ctx.llm' plugins/*/__init__.py` — any hit inside a `_on_*` hook function is a
   violation of the perf contract (see section 1). Gate it behind a command or a once-per-session
   flag.
2. Enable ≤ 5 plugins total; at most **one** plugin may touch `llm` at all, and never in a hook.
3. Keep `request_timeout_seconds` ≥ 120s (25s caused timeout-death on slow gateways).
4. Re-bench after any plugin change: `python .bench/bench.py`; re-test: `bash .bench/run_all_tests.sh`.
5. Target: **< 1s/turn total overhead**. Current steady-state hook overhead is ~1.9ms/turn —
  three orders of magnitude of headroom.

---

## 4. Test status

Full suite (`bash .bench/run_all_tests.sh`, `python` 3.11): **647/647 pass, 0 failures**
(17/17 plugin suites; the count grew 356→358 when the perf-contract regression tests
landed, then →647 with omni-design (8) + omni-parallel (20)).
