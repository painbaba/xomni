# context-compact

Long-session context/RAM discipline (jcode P1 port): older history is
compacted into a summary injected into the current turn's api_content only
(cache-safe, never mutates stored history).

**What it does:** `pre_llm_call` fires when history ≥ `threshold` (40) AND
cooldown (60 s) elapsed AND auto mode on; auto path deterministic
(verbatim tail of 10 + omission counts, ~0 ms — never calls the LLM);
trivial messages skipped; once per session until reset; `/ctxcompact now`
is the only LLM-summary path (host `ctx.llm.complete`, temp 0.2, fallback on failure).

**Commands:** `/ctxcompact [status|on|off|now|threshold <n>|pause|resume|
reset]`

**Speed posture:** single `pre_llm_call` hook — deterministic, ~0 ms, no
LLM/network/subprocess; LLM summaries only on explicit `/ctxcompact now`.

**Config:** plugin-local `state.json` (never config.yaml): auto, paused,
threshold, cooldown_seconds, tail_n, last_compact_session, compactions;
corrupt/missing state falls back to defaults silently.

```bash
cd plugins/context-compact && python -m unittest tests.test_core -v
```
