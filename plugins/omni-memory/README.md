# omni-memory

OpenClaw-style personal memory: local SQLite facts, `/remember` / `/recall`,
LLM consolidation — no external memory vendor.

**What it does:** stores facts in a local SQLite store (`~/.omni-memory/
memory.db`, auto-quarantined and rebuilt if corrupt); `/recall` ranks facts
by deterministic token-overlap scoring (no embeddings, newest-first, hits
tracked); `pre_llm_call` injects a compact memory brief (≤900 chars) into
non-trivial turns; `/memory-consolidate` folds the oldest facts into one
summary via the opencode gateway (`deepseek-v4-flash`) once the store holds
≥8 facts — fails open, store untouched on any error.

**Commands:** `/remember <fact>` · `/recall <query>` · `/memory-status` ·
`/memory-consolidate`

**Speed posture:** 1 legacy hook (`pre_llm_call`) — pure SQLite + token
overlap, returns `None` when nothing matches; consolidation is on-demand
only, never inside a hook. No subprocess.

**Config:** store at `~/.omni-memory/memory.db`; consolidation needs
`OPENCODE_GO_API_KEY` in the hermes `.env` (threshold 8 facts, batch 5).

```bash
cd plugins/omni-memory && python -m unittest tests.test_core -v
```
