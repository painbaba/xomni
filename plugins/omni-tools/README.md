# omni-tools — capability corpus + BM25 router

Implements **TOOL-SEARCH.md** for XOMNI. The Hermes host already ships a
native search bridge (`tool_search` / `tool_describe` / `tool_call`) that
hides deferrable tools behind a small eager set — this plugin does **not**
rebuild that mechanism. It builds the corpus the host cannot see and exposes
it through one router tool, so the model can discover and load **any** XOMNI
capability on demand.

## What is indexed

| Surface | Source | Count |
|---|---|---|
| Plugin tools + slash commands | static parse of all `plugins/*/__init__.py` (`register_tool` / `register_command` / docstring `Commands::` sections) + `plugin.yaml` descriptions | ~66 |
| MCP servers | `data/mcp/catalog.json` (name, category, purpose, price model) | 311 |
| Skills | `data/curated-skills.json` (name, category, description) | 180 |

Every entry is keyword-enriched (curated synonym map + the 12 MCP catalog
categories), deterministically ordered, and byte-stable across rebuilds —
the same prompt-cache-safety rule the host enforces.

## Router tool

```
xomni_capabilities(query, kind='all', limit=5)
```

Pure-stdlib BM25 over the merged corpus. Every hit carries `source` +
`status` + a **load hint** so the model knows exactly how to invoke it:

- `[plugin:tool]` → load via the host bridge (`tool_describe` / `tool_call`)
- `[plugin:command]` → run `/<name>`
- `[mcp:mcp_server]` → connect via `/mcp add` or `config.yaml mcp_servers`
- `[skill:skill]` → load on demand via `skill_view`

## Commands

```
/tools-search <query> [--kind=tool|command|mcp_server|skill] [--limit=N]
/tools-index            rebuild corpus from source files + print stats
/tools-stats            corpus size + top-5 recall + last eval time
```

## Recall benchmark

`core.EVAL_SET` is a built-in eval set of **20 planted queries** (plugin tools
+ commands, MCP servers, skills, synonym-expansion paths), each with a known
expected hit that must land in the top 5 on the live corpus. `core.eval_recall()`
runs the set and returns `{queries, hits, recall, limit, last_eval, results}`;
the summary is persisted to the SQLite cache (eval table) so `/tools-stats`
reports the last eval time across runs.

```
>>> core.eval_recall()["recall"]
1.0   # 20/20 expected hits in top 5 (verified 2026-08-12)
```

## Design notes

- **Pure stdlib** (`re`, `math`, `json`, `sqlite3`, `pathlib`) — no deps,
  matching mcp-catalog / omni-skills conventions.
- **Zero hooks** — nothing registers a hook; zero per-turn cost until invoked.
- **Optional SQLite cache** (`corpus-cache.sqlite3`) keyed on source-file
  mtimes; a stale cache is never served. Cache is an optimization only.
- **BM25 details**: k1=1.5, b=0.75, smoothed idf; name tokens weighted 2×;
  query-side synonym expansion; zero-IDF name-substring fallback (host parity).
- **Recall gate**: top-5 recall ≥ 0.9 on both a planted corpus and the real
  corpus (built-in 20-query `EVAL_SET`, plus 12 legacy verified pairs).

## Test

```
cd plugins/omni-tools && python -m unittest tests.test_core -q
```

## Layout

```
plugins/omni-tools/
├── core.py          corpus builder, BM25, cache, eval_recall, stats_report (pure)
├── __init__.py      register xomni_capabilities + /tools-search + /tools-index + /tools-stats
├── plugin.yaml
├── README.md
└── tests/test_core.py   21 tests
```
