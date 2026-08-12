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
  corpus (12 verified query→target pairs).

## Test

```
cd plugins/omni-tools && python -m unittest tests.test_core -q
```

## Layout

```
plugins/omni-tools/
├── core.py          corpus builder, BM25, cache, router tool body (pure)
├── __init__.py      register xomni_capabilities + /tools-search + /tools-index
├── plugin.yaml
├── README.md
└── tests/test_core.py   19 tests
```
