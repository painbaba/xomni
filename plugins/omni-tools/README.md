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

## Cross-surface recall eval

`core.cross_surface_recall()` scores recall@k per surface and overall against
**50 planted queries** in `data/cross_surface_eval.json` — 15 plugin, 15 MCP,
10 skill, 10 mixed — each carrying 1-3 expected hits that must land in the
top-k results (same case-insensitive substring rule as `EVAL_SET`). Where
`EVAL_SET` is a narrow smoke set, this is the broad cross-surface benchmark:
the `mixed` cases deliberately span two surfaces in one query (e.g.
"sqlite mcp and test driven development" must surface both a SQLite MCP
server *and* the TDD skill). `top_k` is configurable, default 5.

Run:

```
cd plugins/omni-tools && python scripts/cross_surface_eval.py            # recall@5
cd plugins/omni-tools && python scripts/cross_surface_eval.py --top-k 10
```

The runner prints a per-surface table + overall recall and writes per-case
ranks and per-surface/overall numbers to `data/cross_surface_report.json`
(repo root). Data files are loaded best-effort: if a source is missing that
surface scores 0 but the run does not crash.

Current overall recall@5: **1.000** (50/50 expected hits in top 5, verified
2026-08-12 against the live 591-entry corpus; plugin 1.000, mcp 1.000,
skill 1.000, mixed 1.000).

**Reading the numbers**: a case scores 1.0 only when *every* expected hit is
in the top k, so per-surface recall is the mean over that surface's cases.
Mixed queries are the hardest — two capabilities must survive one BM25 pass —
so a dip in the `mixed` row is the first sign of a cross-surface ranking
regression (e.g. synonym expansion flooding one surface, or a new surface
dominating the merged index).

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
├── core.py          corpus builder, BM25, cache, eval_recall, cross_surface_recall (pure)
├── __init__.py      register xomni_capabilities + /tools-search + /tools-index + /tools-stats
├── data/cross_surface_eval.json   50-query cross-surface eval set
├── scripts/cross_surface_eval.py  CLI runner for the cross-surface eval
├── plugin.yaml
├── README.md
└── tests/test_core.py   26 tests
```
