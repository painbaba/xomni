# offline-kit

Offline-first readiness kit for XOMNI: probes the LOCAL Ollama stack (chat +
embeddings) and local search, then produces an offline-ready report and a
concrete model plan. Pure stdlib (`urllib.request`, `json`, `os`, `time`) —
no third-party dependencies, no Hermes imports, zero hooks (no
`register_hook` anywhere; the plugin never alters agent behavior).

## What it checks

- **Ollama chat** — `GET http://127.0.0.1:11434/api/tags` (1.5 s timeout);
  lists every pulled model.
- **Embeddings** — available if a pulled model matches
  `EMBED_HINTS = ("embed", "nomic", "bge")` (e.g. `nomic-embed-text:latest`).
- **Local search** — always-available `fts5-local` codebase index
  (SQLite FTS5, no network).

`probe()` is **diagnostic**: it never raises on network failure. An
unreachable or misbehaving Ollama is recorded as `reachable: False` with an
error string, and `offline_ready` becomes `False`.

## API (`core.py`)

| Function | Purpose |
|---|---|
| `probe(host, port, timeout, urlopen)` | Live probe → report dict (never raises) |
| `build_offline_stack(report, prefer=None)` | Model plan (chat + embeddings) from a report |
| `offline_prompt_for(task, plan)` | Deterministic offline system prompt (no network) |
| `smoke_prompt(plan)` | One-line status string, e.g. `offline-kit: 3 models, chat=qwen2.5:7b, ...` |
| `render_markdown(report)` | Markdown table of all checks + model inventory |

### Report shape

```python
{
    "ollama":      {"reachable": bool, "error": str|None, "models": [names]},
    "embeddings":  {"available": bool, "model": str|None},
    "search":      {"available": True, "backend": "fts5-local"},
    "offline_ready": bool,
    "checks":      [{"name": str, "ok": bool, "detail": str}, ...],
}
```

### Model plan (`build_offline_stack`)

`chat_model` picks the `prefer` override first (if it matches a pulled
model), else the first match from
`CHAT_PREFERRED = ["qwen2.5", "llama3.2", "gemma2", "mistral", "phi3"]`,
else the first model, else `None`. `offline_ready` is `False` whenever no
chat model is available.

## Commands / tool

- `/offline status` — probe and print the offline-ready report (markdown).
- `/offline plan` — probe and print the model plan (chat + embeddings).
- Tool `offline_kit` (`action=status|plan`) — model-callable equivalent.

## Test

```bash
cd plugins/offline-kit && python -m unittest tests.test_core -q
```

All tests stub `urlopen` (fake response / injected errors) — no network
touched. See also `docs/OFFLINE-FIRST.md` in the repo root.
