# codebase-index (repomap v2)

Hybrid incremental codebase index: **SQLite FTS5 (trigram tokenizer)** full-text
search over a repo, plus a symbol catalog, with Continue-style incremental
updates and BM25 + symbol-boost ranking. Pure stdlib (`sqlite3` only, FTS5
bundled in CPython ≥3.10 / SQLite ≥3.34 — verified on this host: 3.53.1).
**Zero hooks** — a slash command and a model tool only.

Design follows `.tmp/research-next/CODEBASE-INDEX.md` (repomap v2 research).

## What it does

- **Catalog** (`files` table): relpath, size, mtime, sha256 per file —
  source of truth for incrementality.
- **Incremental updates**: stat-diff (size, mtime) via a fast `os.scandir`
  walk → only dirty files are re-read; **content-hash dedup** means a file
  whose mtime moved but sha256 is unchanged (git checkout, rebuild) is a
  no-op; deleted files are removed; new files are added. Re-parse cost scales
  with the dirty set, not the repo.
- **Chunking**: code-aware chunks at symbol (class/function/…) boundaries with
  start/end lines; text files (md/json/yaml/…) chunked by line blocks.
- **Ranking**: `bm25(fts, 10.0)` (path column weighted ×10, Continue's trick)
  merged with a **symbol-name boost** (+3 exact/prefix symbol match, +1.5
  substring) — files defining a matching identifier outrank incidental content
  matches. `search_symbols` gives exact/prefix symbol hits with line numbers.
- **Freshness**: on query, a stat-diff runs first; if >200 files are dirty the
  stale index is served with a `⚠️ N files pending re-index` banner (spec
  trigger #3); explicit `/cindex build` refreshes fully.
- **Embeddings (OPT-IN)**: `/cindex embed` embeds every indexed file through a
  pluggable provider — default Ollama `http://127.0.0.1:11434/api/embeddings`
  (small model `nomic-embed-text`, override via `CINDEX_EMBED_URL` /
  `CINDEX_EMBED_MODEL` / `CINDEX_EMBED_TIMEOUT`) — stored as float32 BLOBs in
  the `vectors` table with a model tag. `query_hybrid` (`/cindex query
  --hybrid`) fuses BM25 + vector rankings with reciprocal-rank fusion (RRF,
  k=60). Every provider call fails soft: Ollama down / no vectors => the
  plain BM25 query, never a raise. `meta.embedding_model` reports the active
  tag or `none`.
- **Index location**: `~/.cache/xomni/repomap/<sha1(root)>/index.db`
  (override with `XOMNI_CACHE`), so the scanned tree is never written to.
  BM25 mode is the complete, identical API; embeddings are an additive
  opt-in layer on top.

## Schema

```sql
CREATE TABLE files   (id INTEGER PRIMARY KEY, path TEXT UNIQUE, size INTEGER,
                      mtime REAL, sha256 TEXT, depth INTEGER, skipped INTEGER DEFAULT 0);
CREATE TABLE meta    (key TEXT PRIMARY KEY, value TEXT);   -- schema_version, indexed_at, git_head, embedding_model
CREATE TABLE symbols (id INTEGER PRIMARY KEY, file_id INTEGER REFERENCES files(id),
                      name TEXT, kind TEXT, line INTEGER);
CREATE TABLE chunks  (id INTEGER PRIMARY KEY, file_id INTEGER REFERENCES files(id),
                      idx INTEGER, start_line INTEGER, end_line INTEGER, content TEXT);
CREATE VIRTUAL TABLE fts USING fts5(path, content, tokenize='trigram');
CREATE TABLE fts_meta (id INTEGER PRIMARY KEY, file_id INTEGER, chunk_id INTEGER,
                       path TEXT, cache_key TEXT);         -- rowid = fts rowid
CREATE TABLE vectors (file_id INTEGER PRIMARY KEY REFERENCES files(id),
                      model TEXT NOT NULL, dim INTEGER NOT NULL,
                      embedding BLOB NOT NULL);            -- float32, OPT-IN
-- Query: SELECT … FROM fts JOIN fts_meta … WHERE fts MATCH ? ORDER BY bm25(fts, 10.0) LIMIT ?
```

## Usage

```
/cindex status [path]            # files, symbols, chunks, dirty count, git head
/cindex build [path]             # full rebuild (explicit refresh)
/cindex embed [path]             # OPT-IN: Ollama embeddings (graceful skip if down)
/cindex query <q> [path]         # ranked files + symbol hits
/cindex query --hybrid <q>       # RRF fusion of BM25 + vectors (opt-in)

tool: codebase_query(path=…, query=…, limit=…)
```

Scripting/CI (same engine — the plugin dir is hyphenated, so call via `-c`):

```
cd plugins/codebase-index
python -c "import core, sys; sys.exit(core.main(sys.argv[1:]))" build C:\path\to\repo
python -c "import core, sys; sys.exit(core.main(sys.argv[1:]))" query  C:\path\to\repo "fts5 trigram index"
python -c "import core, sys; sys.exit(core.main(sys.argv[1:]))" status C:\path\to\repo
```

## API (v1-compatible + v2 additions)

`build_map(root)` · `rank_files(root, query)` · `stack_tags(root)` —
repomap v1 signatures, now served warm from the index (ms, not seconds).
New: `search_symbols(root, q)` · `index_status(root)` · `query(root, q)` ·
`update_index(root, force=…)` · `ensure_index(root)` · `query_json(root, q)`
· **`build_embeddings(root, model=…, base_url=…)`** (opt-in vectors) ·
**`query_hybrid(root, q)`** (RRF fusion) · `rrf_fuse(rankings, k=60)` ·
`embed_texts(texts, model=…)` (pluggable provider; `None` on failure).

## Tests

```
cd plugins/codebase-index && python -m unittest tests.test_core -q
```

Covers: schema creation (incl. `vectors`), symbol extraction with lines/kinds,
chunk boundaries, incremental no-op on unchanged trees, mtime-touch
content-hash dedup, edit → re-index, delete → removal, skip-dirs, BM25
ranking, symbol-boost ordering, path-weight ordering, symbol search, JSON
query, status shape, defer-banner, CLI, the zero-hook surface registration
(tool + command, no `register_hook`), and the embeddings layer: RRF fusion
math, cosine similarity, provider-down graceful skip (`embed_texts` /
`build_embeddings` / hybrid query all return BM25 without raising — the HTTP
call is mocked, no network), vectors storage with model tag, and hybrid
query using stored vectors.

## Perf gate

Query path is pure SQLite (warm, ms). Stat-diff scales with the file count,
not content. Fresh build of XOMNI itself (~10k files, ~7k indexed):
see `python -m codebase_index build C:\Users\HP\xomni` timings.
