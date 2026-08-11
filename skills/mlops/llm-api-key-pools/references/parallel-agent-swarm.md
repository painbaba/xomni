# Parallel Agent Swarm (run N agents across a pooled key workforce)

## When to use
- "Run 300 parallel agents", "swarm research", market/product research across
  many independent angles in minutes.
- Any goal that decomposes into many independent research questions, with
  multiple free-tier keys available (the Kimi K2.6 "300 agents at once" trick,
  replicated locally on a key pool).

## Verified run (2026-08-08)
- 300/300 agents completed, 0 failures, 4.6 min wall-clock, ~0 cost.
- Channels: 6x Gemini (gemini-3.1-flash-lite) + 2x OpenCode Go
  (deepseek-v4-flash). NIM skipped (peak-hour congestion), ZAI 429'd.

## Pattern
1. DECOMPOSE — one goal into tasks.json `{id, dimension, question}`.
   Verified shape: 25 dimensions x 12 template questions = 300 tasks
   (template lists per dimension; assert len==12 per dim and total==N).
   One agent per question; agents are independent by construction.
2. PROBE — health-check every channel first (probe_models.py / quick
   script). Only feed LIVE channels to the pool; NIM 404/429 and ZAI 429
   are common at peak.
3. RUN — threaded workers, `min(14, 2*len(channels))`. Each worker:
   pop task -> pick random channel -> call -> parse JSON -> write
   `results/agent_XXX.json`. Details that made it work:
   - Per-key rate limiting: each channel has `min_interval` (Gemini 4s,
     OpenCode 2.5s) enforced under a per-channel lock (sleep until
     last_call + interval).
   - Adaptive 429 backoff: on "429" in error, `min_interval *= 1.8`
     (cap 30s) — free tiers throttle, backoff absorbs it.
   - Retry loop: 4 attempts, transient-only; 404/400 = give up.
   - RESUMABLE: skip tasks whose result file already exists — kill and
     restart mid-run is safe.
   - Progress log every 25 tasks + per-channel stats (done/ok/fail/retries).
4. SYNTHESIZE — read all results, build matrix.csv (agent_id, dimension,
   question, confidence, channel, key_numbers, findings) and report.md
   (exec summary = top high-confidence key_numbers, then per-dimension
   deep dive with each Q + findings + numbers).
5. VERIFY — web-check the top 5-10 claims against live sources and append
   a "Live Verification Pass" section marking what was confirmed. DDG
   search works via the BROWSER; curl to html.duckduckgo.com gets
   bot-blocked on this host.

## Pitfalls
- Double-encoded JSON: some models (deepseek-v4-flash via OpenCode Go)
  return the JSON object with `findings` containing a STRING that is
  itself JSON. Unwrap recursively before synthesis (`unwrap()` that
  re-parses any string starting with `{`).
- JSON forcing: Gemini — set `generationConfig.responseMimeType =
  "application/json"` (returns clean JSON). OpenAI-compatible channels —
  demand JSON in the system prompt + regex-extract the first `{...}`
  block as fallback.
- Non-JSON fallback: if parse fails, wrap raw text as a single
  low-confidence finding instead of dropping the agent.
- Failure isolation: write `agent_XXX.json.fail` on exhausted retries;
  report the count in the final summary.
- Free-tier daily caps: Gemini ~15 RPM/key, daily quota — a rerun on a
  new day resumes via the resumable runner; keep the results/ dir.
- Big claim triage: multiple agents may cite the same figure ($40B by
  2030 vs $25-29B) — verification pass decides which survives in the
  final report's exec summary.

## Costs
300 calls across the free pool cost ~0 INR. Same run on a paid API at
$0.10/M tokens would be well under $1 — the pattern is cheap enough to
rerun per market decision.
