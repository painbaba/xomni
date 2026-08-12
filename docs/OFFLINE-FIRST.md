# OFFLINE-FIRST — XOMNI offline readiness kit

The `offline-kit` plugin (`plugins/offline-kit/`) verifies that XOMNI can run
with **no network and no API keys**, using only the local Ollama runtime and
the local FTS5 codebase index. Pure stdlib, zero hooks, never raises.

## What the kit checks

1. **Ollama chat** — `GET http://127.0.0.1:11434/api/tags` (1.5 s timeout).
   Reachable = the bundled runtime is serving (see `docs/OLLAMA.md`);
   the report lists every pulled model.
2. **Embeddings** — available when a pulled model matches
   `EMBED_HINTS = ("embed", "nomic", "bge")` (e.g. `nomic-embed-text:latest`).
3. **Local search** — always available: `fts5-local` (SQLite FTS5 codebase
   index, no network).

If any probe fails it is recorded as `reachable: False` / `offline_ready:
False` — `probe()` is diagnostic and never raises.

## Stack plan

`build_offline_stack(report, prefer=None)` produces the plan:

| Key | Value |
|---|---|
| `provider` | `ollama` |
| `base_url` | `http://127.0.0.1:11434` |
| `chat_model` | `prefer` override → first of `qwen2.5, llama3.2, gemma2, mistral, phi3` present → first model → `None` |
| `embeddings_model` | first embed-hint model, else `None` |
| `search` | `codebase-index (fts5)` |
| `offline_ready` | `False` if no chat model |

## How to run the probe

```bash
# live probe against the local stack (prints the JSON report)
cd plugins/offline-kit && python -c "import core, json; print(json.dumps(core.probe(), indent=2))"

# offline-ready markdown report + model plan
cd plugins/offline-kit && python -c "import core; print(core.render_markdown(core.probe()))"
cd plugins/offline-kit && python -c "import core; print(core.build_offline_stack(core.probe()))"

# tests (stubbed urlopen, no network)
cd plugins/offline-kit && python -m unittest tests.test_core -q
```

If `chat_model` is `None`, pull a small chat model first:
`/ollama pull qwen2.5:3b` (or `ollama pull qwen2.5:3b` directly) — see
`docs/OLLAMA.md` for the zero-install runtime flow.
