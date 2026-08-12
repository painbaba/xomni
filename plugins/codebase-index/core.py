"""Hybrid codebase index (repomap v2) — pure stdlib, zero hooks.

SQLite FTS5 (trigram tokenizer) full-text index + symbol catalog over a repo,
with Continue-style incremental updates: stat-diff (size, mtime) against a
SQLite catalog, content-hash (sha256) dedup so mtime-touches with unchanged
content are no-ops, and per-file re-parse of only dirty files.

Design per .tmp/research-next/CODEBASE-INDEX.md:
  - schema: files / meta / symbols / chunks / fts (fts5 trigram) / fts_meta
  - query: BM25 with path-column weight 10.0 + symbol-name boost merge
  - index DB lives in the XOMNI cache dir (~/.cache/xomni/repomap/<sha1(root)>/index.db)
  - API stays v1-compatible: build_map / rank_files / stack_tags, plus the
    new search_symbols / index_status / query surfaces.

Embeddings are an OPT-IN layer: `build_embeddings` stores per-file vectors in
the `vectors` table via a pluggable provider (default: Ollama
http://127.0.0.1:11434/api/embeddings), and `query_hybrid` fuses BM25 +
vector rankings with reciprocal-rank fusion (RRF). Every provider call fails
soft: unreachable Ollama / no vectors => graceful fallback to the plain BM25
query, never a raise. meta.embedding_model reports the active model tag or
"none".
"""
from __future__ import annotations

import array
import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request

SCHEMA_VERSION = "2"

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "dist", "build", ".next", ".nuxt", ".output", "target", "vendor",
    ".idea", ".vscode", ".vs", "coverage", ".cache", "site-packages",
    ".terraform", ".serverless", "Pods", ".gradle", ".xomni", ".tmp",
}

MAX_FILE_BYTES = 500_000          # files larger than this are catalog-only (never parsed)
MAX_CHUNK_LINES = 400             # code-aware chunk size cap
MAX_CHUNK_BYTES = 256_000         # cap on a single chunk's stored content
MAX_DIRTY_DEFER = 200             # spec: > N dirty files => serve stale + banner
BM25_PATH_WEIGHT = 10.0           # Continue trick: bm25(fts, 10.0)

RRF_K = 60.0                      # reciprocal-rank fusion constant (standard)
EMBED_MAX_CHARS = 6000            # per-file embed text cap (path + chunks)
EMBED_TIMEOUT = float(os.environ.get("CINDEX_EMBED_TIMEOUT", "3"))
EMBED_BASE_URL = os.environ.get("CINDEX_EMBED_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("CINDEX_EMBED_MODEL", "nomic-embed-text")

# Text-ish extensions that get chunked into FTS (code langs come from _SYMBOL_PATTERNS).
TEXT_EXTS = {
    ".md", ".markdown", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".html", ".htm", ".css", ".xml", ".csv",
    ".pyi", ".jsx", ".tsx", ".mjs", ".cjs", ".h", ".hpp", ".cc", ".svelte",
    ".gitignore", ".dockerignore", ".editorconfig",
}

_SYMBOL_PATTERNS = [
    (".py", re.compile(r"^[ \t]*(?:async\s+def|def|class)\s+([A-Za-z_]\w*)", re.M)),
    (".js", re.compile(r"^[ \t]*(?:export\s+(?:default\s+)?(?:class|function|const|let|var)\s+|function\s+|class\s+)([A-Za-z_$][\w$]*)", re.M)),
    (".ts", re.compile(r"^[ \t]*(?:export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type|enum)\s+|function\s+|class\s+|interface\s+|type\s+|enum\s+)([A-Za-z_$][\w$]*)", re.M)),
    (".go", re.compile(r"^[ \t]*(?:func\s+\([^)]*\)\s+)?(?:func|type)\s+([A-Za-z_]\w*)", re.M)),
    (".rs", re.compile(r"^[ \t]*(?:pub\s+)?(?:fn|struct|enum|trait|impl|mod|type|const)\s+([A-Za-z_]\w*)", re.M)),
    (".c", re.compile(r"^[ \t]*(?:static\s+|inline\s+)*[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*\([^;]*\)\s*\{|^[ \t]*typedef\s+.*?\b([A-Za-z_]\w*)\s*;|^[ \t]*#define\s+([A-Za-z_]\w*)", re.M)),
    (".cpp", re.compile(r"^[ \t]*(?:static\s+|inline\s+|virtual\s+)*[A-Za-z_~][\w\s\*&:<>,]*?\b([A-Za-z_~]\w*)\s*\([^;]*\)\s*(?:const\s*)?\{|^[ \t]*class\s+([A-Za-z_]\w*)|^[ \t]*struct\s+([A-Za-z_]\w*)", re.M)),
    (".java", re.compile(r"^[ \t]*(?:public|private|protected|static|final|abstract|synchronized|native|transient|volatile|default)\s+.*?\b(class|interface|enum)\s+([A-Z]\w*)|^[ \t]*(?:public|private|protected|static|final|abstract)\s+[\w<>,?\[\]\s]+\s+([a-z]\w*)\s*\(", re.M)),
    (".rb", re.compile(r"^[ \t]*(?:class|module|def)\s+([A-Za-z_]\w*(?:::\w+)*)", re.M)),
    (".php", re.compile(r"^[ \t]*(?:public|private|protected|static|final|abstract)?\s*function\s+([A-Za-z_]\w*)|^[ \t]*(?:abstract\s+|final\s+)?class\s+([A-Za-z_]\w*)", re.M)),
    (".sh", re.compile(r"^[ \t]*([A-Za-z_]\w*)\s*\(\s*\)\s*\{", re.M)),
    (".sql", re.compile(r"^[ \t]*(?:CREATE|create)\s+(?:TABLE|table|VIEW|view|FUNCTION|function|PROCEDURE|procedure)\s+([\w.]+)", re.M)),
    (".kt", re.compile(r"^[ \t]*(?:(?:public|private|protected|internal|sealed|data|enum|annotation|abstract|final|open|suspend|inline|override)\s+)*(?:companion\s+object|object|interface|class|fun)\s+([A-Za-z_]\w*)", re.M)),
    (".swift", re.compile(r"^[ \t]*(?:(?:public|private|internal|fileprivate|open|final|indirect|mutating|nonmutating|static|class)\s+)*(?:extension|protocol|struct|enum|class|func)\s+([A-Za-z_]\w*)", re.M)),
    (".dart", re.compile(r"^[ \t]*(?:abstract\s+|base\s+|final\s+|sealed\s+|interface\s+|mixin\s+)*class\s+([A-Za-z_]\w*)|^[ \t]*(?:void|Future\s*<[^>]*>|Stream\s*<[^>]*>|[A-Za-z_]\w*)\s+([a-z_]\w*)\s*\(|^[ \t]*enum\s+([A-Za-z_]\w*)|^[ \t]*typedef\s+(?:[A-Za-z_]\w*\s+)?([A-Za-z_]\w*)", re.M)),
    (".scala", re.compile(r"^[ \t]*(?:(?:private|protected|final|abstract|sealed|case|implicit|lazy|override)\s+)*(?:object|trait|class|def)\s+([A-Za-z_]\w*)", re.M)),
    (".lua", re.compile(r"^[ \t]*(?:local\s+)?function\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)", re.M)),
    (".r", re.compile(r"^[ \t]*([A-Za-z_.]\w*)\s*(?:<-|=)\s*function\s*\(|^[ \t]*setClass\s*\(\s*['\"]([A-Za-z_]\w*)['\"]", re.M)),
    (".tf", re.compile(r"^[ \t]*(?:resource|data)\s+[\"'][A-Za-z_][\w-]*[\"']\s+[\"']([A-Za-z_][\w-]*)[\"']\s*\{|^[ \t]*(?:variable|output|module)\s+[\"']([A-Za-z_][\w-]*)[\"']\s*\{", re.M)),
    (".vue", re.compile(r"^[ \t]*(?:export\s+default\s+)?(?:class|function|const|let|var)\s+([A-Za-z_$][\w$]*)|^[ \t]*name\s*:\s*['\"]([A-Za-z_$][\w$]*)['\"]", re.M)),
]

_KIND_HINTS = (
    (("class", "interface", "enum", "struct", "trait", "object", "module",
      "table", "view", "type", "protocol", "companion"), "type"),
    (("def", "func", "fn", "function", "fun", "procedure", "constructor"), "function"),
)

DEFAULT_MAX_FILES = 60
DEFAULT_MAX_CHARS = 6000


# --------------------------------------------------------------------------- #
# paths / schema
# --------------------------------------------------------------------------- #

def _cache_root() -> str:
    return os.environ.get("XOMNI_CACHE") or os.path.join(
        os.path.expanduser("~"), ".cache", "xomni")


def get_db_path(root: str, cache_dir: str | None = None) -> str:
    """Deterministic per-repo index DB path (spec §3: cache dir, sha1(root))."""
    key = hashlib.sha1(os.path.normcase(os.path.realpath(root)).encode("utf-8")).hexdigest()[:16]
    base = cache_dir or os.path.join(_cache_root(), "repomap")
    return os.path.join(base, key, "index.db")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
  id INTEGER PRIMARY KEY, path TEXT UNIQUE, size INTEGER, mtime REAL,
  sha256 TEXT, depth INTEGER, skipped INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS symbols (
  id INTEGER PRIMARY KEY, file_id INTEGER REFERENCES files(id),
  name TEXT, kind TEXT, line INTEGER
);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY, file_id INTEGER REFERENCES files(id),
  idx INTEGER, start_line INTEGER, end_line INTEGER, content TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(path, content, tokenize='trigram');
CREATE TABLE IF NOT EXISTS fts_meta (
  id INTEGER PRIMARY KEY, file_id INTEGER, chunk_id INTEGER, path TEXT, cache_key TEXT
);
CREATE INDEX IF NOT EXISTS idx_fts_meta_file ON fts_meta(file_id);
CREATE TABLE IF NOT EXISTS vectors (
  file_id INTEGER PRIMARY KEY REFERENCES files(id),
  model TEXT NOT NULL, dim INTEGER NOT NULL, embedding BLOB NOT NULL
);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn


def _meta(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def _set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def _embedding_model_of(conn: sqlite3.Connection) -> str:
    """Model tag of stored vectors, or 'none' when the table is empty."""
    row = conn.execute("SELECT model FROM vectors LIMIT 1").fetchone()
    return row[0] if row else "none"


def _git_head(root: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", root, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2)
        return out.stdout.strip() or None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# walk / parse / chunk
# --------------------------------------------------------------------------- #

def _stat_walk(root: str) -> dict[str, tuple[int, float]]:
    """Fast stat-only walk: relpath -> (size, mtime). Never reads file contents."""
    out: dict[str, tuple[int, float]] = {}
    stack = [root]
    while stack:
        base = stack.pop()
        try:
            with os.scandir(base) as it:
                for e in it:
                    if e.is_dir(follow_symlinks=False):
                        if e.name in SKIP_DIRS:
                            continue
                        stack.append(e.path)
                    elif e.is_file(follow_symlinks=False):
                        st = e.stat(follow_symlinks=False)
                        rel = os.path.relpath(e.path, root).replace("\\", "/")
                        out[rel] = (st.st_size, st.st_mtime)
        except OSError:
            continue
    return out


def _vue_script_section(text: str) -> str | None:
    m = re.search(r"<script[^>]*>(.*?)</script>", text, re.S | re.I)
    return m.group(1) if m else None


def _kind_of(matched: str) -> str:
    low = matched.lower()
    for words, kind in _KIND_HINTS:
        for w in words:
            if w in low:
                return kind
    return "symbol"


def _iter_symbols(text: str, ext: str, path: str) -> list[tuple[str, int, str]]:
    """Yield (name, line, kind) for a file's top-level symbols (v1 regex set)."""
    if not text or len(text.encode("utf-8", "replace")) > MAX_FILE_BYTES:
        return []
    for pattern_ext, rx in _SYMBOL_PATTERNS:
        if ext == pattern_ext or (pattern_ext in (".c", ".cpp") and ext in (".h", ".hpp", ".cc")):
            search_text = text
            if ext == ".vue":
                section = _vue_script_section(text)
                if section is None:
                    return [(os.path.splitext(os.path.basename(path))[0], 1, "symbol")]
                search_text = section
            found: list[tuple[str, int, str]] = []
            for m in rx.finditer(search_text):
                name = next((g for g in m.groups() if g), None)
                if not name:
                    continue
                line = search_text.count("\n", 0, m.start()) + 1
                found.append((name, line, _kind_of(m.group(0))))
            if ext == ".vue" and not found:
                found.append((os.path.splitext(os.path.basename(path))[0], 1, "symbol"))
            # dedupe by (name, line), keep order
            seen: set[tuple[str, int]] = set()
            out: list[tuple[str, int, str]] = []
            for s in found:
                if (s[0], s[1]) not in seen:
                    seen.add((s[0], s[1]))
                    out.append(s)
            return out
    return []


def _chunk_lines(symbols: list[tuple[str, int, str]], nlines: int) -> list[tuple[int, int]]:
    """Code-aware chunk boundaries: symbol start lines, capped at MAX_CHUNK_LINES."""
    bounds = sorted({s[1] for s in symbols})
    raw: list[tuple[int, int]] = []
    prev = 1
    for b in bounds:
        if b > prev:
            raw.append((prev, b - 1))
        prev = b
    if prev <= nlines:
        raw.append((prev, nlines))
    if not raw and nlines >= 1:
        raw.append((1, nlines))
    out: list[tuple[int, int]] = []
    for a, b in raw:
        if b - a + 1 <= MAX_CHUNK_LINES:
            out.append((a, b))
        else:
            for s in range(a, b + 1, MAX_CHUNK_LINES):
                out.append((s, min(s + MAX_CHUNK_LINES - 1, b)))
    return out


def _should_chunk(ext: str) -> bool:
    return ext in TEXT_EXTS or any(
        ext == pe or (pe in (".c", ".cpp") and ext in (".h", ".hpp", ".cc"))
        for pe, _ in _SYMBOL_PATTERNS)


def _read_text(path: str, size: int) -> str | None:
    if size > MAX_FILE_BYTES or size == 0:
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


# --------------------------------------------------------------------------- #
# incremental update
# --------------------------------------------------------------------------- #

def _delete_file_rows(conn: sqlite3.Connection, file_id: int) -> None:
    chunk_ids = [r[0] for r in conn.execute(
        "SELECT id FROM chunks WHERE file_id=?", (file_id,))]
    conn.execute("DELETE FROM symbols WHERE file_id=?", (file_id,))
    conn.execute("DELETE FROM chunks WHERE file_id=?", (file_id,))
    conn.execute("DELETE FROM vectors WHERE file_id=?", (file_id,))
    conn.execute("DELETE FROM fts_meta WHERE file_id=?", (file_id,))
    for cid in chunk_ids:
        conn.execute("DELETE FROM fts WHERE rowid=?", (cid,))
    conn.execute("DELETE FROM files WHERE id=?", (file_id,))


def _index_file(conn: sqlite3.Connection, root: str, rel: str, size: int,
                mtime: float, sha256: str | None, file_id: int) -> None:
    """Parse + chunk + FTS-insert one file into an open transaction."""
    ext = os.path.splitext(rel)[1].lower()
    full = os.path.join(root, rel)
    text = _read_text(full, size) if _should_chunk(ext) else None
    symbols = _iter_symbols(text, ext, full) if text else []
    conn.executemany(
        "INSERT INTO symbols(file_id,name,kind,line) VALUES(?,?,?,?)",
        [(file_id, s[0], s[2], s[1]) for s in symbols])
    if text is None:
        return
    lines = text.splitlines()
    chunks = _chunk_lines(symbols, len(lines))
    for idx, (a, b) in enumerate(chunks):
        content = "\n".join(lines[a - 1:b])
        if len(content.encode("utf-8", "replace")) > MAX_CHUNK_BYTES:
            content = content[:MAX_CHUNK_BYTES]
        cur = conn.execute(
            "INSERT INTO chunks(file_id,idx,start_line,end_line,content) "
            "VALUES(?,?,?,?,?)", (file_id, idx, a, b, content))
        cid = cur.lastrowid
        conn.execute("INSERT INTO fts(rowid,path,content) VALUES(?,?,?)",
                     (cid, rel, content))
        conn.execute(
            "INSERT INTO fts_meta(id,file_id,chunk_id,path,cache_key) "
            "VALUES(?,?,?,?,?)", (cid, file_id, idx, rel, sha256))


def update_index(root: str, db_path: str | None = None, force: bool = False,
                 max_dirty: int | None = None) -> dict:
    """Continue-style incremental update. Returns {added, updated, removed,
    unchanged, skipped, dirty, deferred, duration_ms, banner}.

    force=True re-verifies every file; otherwise only stat-dirty files are
    re-read, and files whose sha256 is unchanged are no-ops (content-hash dedup).
    If the dirty set exceeds max_dirty (default MAX_DIRTY_DEFER) and force is
    False, re-parse is deferred (stale index served; banner returned) per spec
    trigger #3.
    """
    if max_dirty is None:
        max_dirty = MAX_DIRTY_DEFER
    t0 = time.perf_counter()
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise NotADirectoryError(root)
    db_path = db_path or get_db_path(root)
    fresh = not os.path.isfile(db_path)
    stats = {"added": 0, "updated": 0, "removed": 0, "unchanged": 0,
             "skipped": 0, "dirty": 0, "deferred": False, "banner": ""}

    disk = _stat_walk(root)
    conn = _connect(db_path)
    try:
        if fresh:
            conn.execute("DELETE FROM files")
        catalog = {r["path"]: r for r in conn.execute("SELECT * FROM files")}
        new_rel = sorted(set(disk) - set(catalog))
        gone = sorted(set(catalog) - set(disk))
        changed = sorted(
            p for p in set(disk) & set(catalog)
            if (disk[p][0], disk[p][1]) != (catalog[p]["size"], catalog[p]["mtime"]))

        dirty = len(new_rel) + len(gone) + len(changed)
        stats["dirty"] = dirty
        if dirty > max_dirty and not fresh and not force:
            stats["deferred"] = True
            stats["banner"] = (f"⚠️ {dirty} files pending re-index "
                               f"(run 'cindex build' to refresh)")
            return stats

        with conn:
            if not fresh and _meta(conn, "schema_version") != SCHEMA_VERSION:
                force = True  # schema drift: re-verify every file
            if force and not fresh:
                # user/CI refresh: re-verify every file; content-identical
                # files keep their (still valid) chunks via hash-dedup below.
                changed = sorted(set(disk))
                new_rel, gone = [], []
            for rel in gone:
                _delete_file_rows(conn, catalog[rel]["id"])
                stats["removed"] += 1
            for rel in new_rel:
                size, mtime = disk[rel]
                ext = os.path.splitext(rel)[1].lower()
                if size > MAX_FILE_BYTES:
                    sha = None
                else:
                    sha = _sha256(os.path.join(root, rel)) if _should_chunk(ext) else None
                cur = conn.execute(
                    "INSERT INTO files(path,size,mtime,sha256,depth,skipped) "
                    "VALUES(?,?,?,?,?,0)", (rel, size, mtime, sha, rel.count("/")))
                _index_file(conn, root, rel, size, mtime, sha, cur.lastrowid)
                stats["added"] += 1
            for rel in changed:
                size, mtime = disk[rel]
                old = catalog[rel]
                ext = os.path.splitext(rel)[1].lower()
                if size > MAX_FILE_BYTES:
                    sha = None
                else:
                    sha = _sha256(os.path.join(root, rel)) if _should_chunk(ext) else None
                if sha is not None and sha == old["sha256"]:
                    # content-hash dedup: mtime/size moved, content identical
                    conn.execute(
                        "UPDATE files SET size=?,mtime=? WHERE id=?",
                        (size, mtime, old["id"]))
                    stats["unchanged"] += 1
                    continue
                _delete_file_rows(conn, old["id"])
                cur = conn.execute(
                    "INSERT INTO files(path,size,mtime,sha256,depth,skipped) "
                    "VALUES(?,?,?,?,?,0)", (rel, size, mtime, sha, rel.count("/")))
                _index_file(conn, root, rel, size, mtime, sha, cur.lastrowid)
                stats["updated"] += 1
            stats["skipped"] = sum(
                1 for rel, (size, _m) in disk.items() if size > MAX_FILE_BYTES)
            _set_meta(conn, "schema_version", SCHEMA_VERSION)
            _set_meta(conn, "indexed_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
            # rebuilt_at only moves when the index actually changed (or was
            # force/fresh rebuilt): a stat-diff no-op must not bump it.
            if fresh or force or stats["added"] or stats["updated"] or stats["removed"]:
                _set_meta(conn, "rebuilt_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
            _set_meta(conn, "embedding_model", _embedding_model_of(conn))
            _set_meta(conn, "git_head", _git_head(root) or "")
            _set_meta(conn, "root", root)
    finally:
        conn.close()
    stats["duration_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return stats


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 16), b""):
                h.update(block)
    except OSError:
        return ""
    return h.hexdigest()


def ensure_index(root: str, db_path: str | None = None, force: bool = False) -> dict:
    """Build if missing, else incremental stat-diff update. Returns stats dict."""
    return update_index(root, db_path=db_path, force=force)


# --------------------------------------------------------------------------- #
# queries
# --------------------------------------------------------------------------- #

def _fts_query(terms: list[str]) -> str:
    """AND of quoted trigram-safe terms (>=3 chars); '' if none usable."""
    parts = []
    for t in terms:
        if len(t) >= 3:
            parts.append('"' + t.replace('"', '""') + '"')
    return " AND ".join(parts)


def _symbol_boost(file_id: int, terms: list[str], conn: sqlite3.Connection) -> float:
    """Symbol-name boost: +3.0 exact/prefix on a symbol, +1.5 substring."""
    rows = conn.execute(
        "SELECT name FROM symbols WHERE file_id=?", (file_id,))
    names = [r[0] for r in rows]
    boost = 0.0
    for t in terms:
        for n in names:
            nl = n.lower()
            if nl == t or nl.startswith(t):
                boost += 3.0
            elif t in nl:
                boost += 1.5
    return boost


def _file_symbols(conn: sqlite3.Connection, file_id: int, limit: int = 12) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT name FROM symbols WHERE file_id=? ORDER BY line LIMIT ?",
        (file_id, limit))]


def _like_escape(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_symbols(root: str, query: str, db_path: str | None = None,
                   limit: int = 20) -> str:
    """Symbol hits (prefix/exact first, then substring) — 'find by name'."""
    terms = [t.lower() for t in re.split(r"\s+", query.strip()) if t]
    if not terms:
        return ""
    db_path = db_path or get_db_path(root)
    if not os.path.isfile(db_path):
        update_index(root, db_path=db_path)
    conn = _connect(db_path)
    try:
        seen: set[tuple] = set()
        rows: list[tuple] = []
        for t in terms:
            esc = _like_escape(t)
            for sql, args in (
                ("SELECT s.name,s.kind,s.line,f.path FROM symbols s "
                 "JOIN files f ON f.id=s.file_id WHERE lower(s.name) LIKE ? ESCAPE '\\' "
                 "ORDER BY (CASE WHEN lower(s.name)=? THEN 0 ELSE 1 END), s.name, f.path LIMIT ?",
                 (esc + "%", t, limit)),
                ("SELECT s.name,s.kind,s.line,f.path FROM symbols s "
                 "JOIN files f ON f.id=s.file_id WHERE lower(s.name) LIKE ? ESCAPE '\\' "
                 "ORDER BY s.name, f.path LIMIT ?",
                 ("%" + esc + "%", limit)),
            ):
                for r in conn.execute(sql, args):
                    key = (r["path"], r["line"], r["name"])
                    if key not in seen:
                        seen.add(key)
                        rows.append((r["path"], r["line"], r["kind"], r["name"]))
        rows.sort(key=lambda r: (r[0], r[1]))
        out = [f"{p}:{ln}  {kind:<9} {name}" for p, ln, kind, name in rows[:limit]]
        return "\n".join(out)
    finally:
        conn.close()


def _ranked_file_ids(conn: sqlite3.Connection, terms: list[str],
                     top_n: int) -> list[tuple[int, float]]:
    """BM25(path-weighted) + symbol boost -> ordered [(file_id, score)].
    Shared by rank_files (v1 surface) and query_hybrid (RRF fusion)."""
    fq = _fts_query(terms)
    scored: dict[int, float] = {}
    path: dict[int, str] = {}
    if fq:
        rows = conn.execute(
            "SELECT fts.rowid AS rid, bm25(fts, ?) AS b, fm.file_id, fm.path "
            "FROM fts JOIN fts_meta fm ON fm.id = fts.rowid "
            "WHERE fts MATCH ? ORDER BY b ASC LIMIT 200", (BM25_PATH_WEIGHT, fq))
        for r in rows:
            fid = r["file_id"]
            s = -r["b"]  # bm25: more negative = better -> positive score
            if fid not in scored or s > scored[fid]:
                scored[fid] = s
                path[fid] = r["path"]
    for fid in scored:
        scored[fid] += _symbol_boost(fid, terms, conn)
    # symbol-only hits (short terms / no FTS row): base 0 + boost
    for r in conn.execute(
            "SELECT DISTINCT s.file_id AS fid, f.depth AS d, f.path AS p "
            "FROM symbols s JOIN files f ON f.id=s.file_id"):
        if r["fid"] not in scored:
            b = _symbol_boost(r["fid"], terms, conn)
            if b > 0:
                scored[r["fid"]] = 0.0 + b
                path[r["fid"]] = r["p"]
    ranked = sorted(scored.items(), key=lambda kv: (-kv[1], path.get(kv[0], "")))
    return ranked[:top_n]


def _render_file_ids(conn: sqlite3.Connection,
                     ranked: list[tuple[int, float]], terms: list[str],
                     fmt: str = "{:.2f}") -> str:
    """Render [(file_id, score)] as the v1 ranked-file lines (path, symbols)."""
    out: list[str] = []
    total = 0
    for fid, score in ranked:
        row = conn.execute(
            "SELECT depth, path FROM files WHERE id=?", (fid,)).fetchone()
        if row is None:
            continue
        depth, p = row["depth"], row["path"]
        syms = _file_symbols(conn, fid)
        line = f"{fmt.format(score)}  {'  ' * depth}{p}"
        if syms:
            line += "  [" + ", ".join(syms[:12]) + "]"
        if len(syms) > 12:
            line += f" (+{len(syms) - 12} more)"
        if total + len(line) > DEFAULT_MAX_CHARS:
            break
        out.append(line)
        total += len(line)
    return "\n".join(out)


def rank_files(root: str, query: str, top_n: int = 10,
               db_path: str | None = None) -> str:
    """v1-compatible ranked file list: BM25(path-weighted) + symbol boost."""
    terms = [t.lower() for t in re.split(r"\s+", query.strip()) if t]
    if not terms:
        return ""
    db_path = db_path or get_db_path(root)
    if not os.path.isfile(db_path):
        update_index(root, db_path=db_path)
    conn = _connect(db_path)
    try:
        return _render_file_ids(conn, _ranked_file_ids(conn, terms, top_n), terms)
    finally:
        conn.close()


def build_map(root: str, max_files: int = DEFAULT_MAX_FILES,
              max_chars: int = DEFAULT_MAX_CHARS, db_path: str | None = None) -> str:
    """v1-compatible symbol map, served warm from the index (ms, not 10s)."""
    db_path = db_path or get_db_path(root)
    if not os.path.isfile(db_path):
        update_index(root, db_path=db_path)
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT f.path, f.depth, "
            "(SELECT group_concat(name, ',') FROM (SELECT name FROM symbols s "
            " WHERE s.file_id=f.id ORDER BY s.line LIMIT 12)) AS syms, "
            "(SELECT COUNT(*) FROM symbols s WHERE s.file_id=f.id) AS nsyms "
            "FROM files f ORDER BY f.depth, f.path LIMIT ?", (max_files * 2,))
        out: list[str] = []
        total = 0
        for r in rows:
            line = f"{'  ' * r['depth']}{r['path']}"
            if r["syms"]:
                line += "  [" + r["syms"] + "]"
            if r["nsyms"] > 12:
                line += f" (+{r['nsyms'] - 12} more)"
            if total + len(line) > max_chars:
                break
            out.append(line)
            total += len(line)
        return "\n".join(out)
    finally:
        conn.close()


def stack_tags(root: str) -> list[str]:
    """Extension-scan stack detection (v1 parity). Nothing leaves the machine."""
    tags: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            low = fn.lower()
            if low == "package.json" or low.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
                tags.add("node")
            if low in ("requirements.txt", "pyproject.toml", "setup.py") or low.endswith(".py"):
                tags.add("python")
            if low == "go.mod" or low.endswith(".go"):
                tags.add("go")
            if low == "cargo.toml" or low.endswith(".rs"):
                tags.add("rust")
            if low == "pom.xml" or low.endswith(".java"):
                tags.add("java")
            if low == "gemfile" or low.endswith(".rb"):
                tags.add("ruby")
            if low in ("dockerfile", "compose.yml", "compose.yaml") or low.endswith(".dockerfile"):
                tags.add("docker")
            if low.endswith(".php"):
                tags.add("php")
            if low.endswith(".sql"):
                tags.add("sql")
            if low.endswith((".c", ".h")):
                tags.add("c")
            if low.endswith((".cpp", ".cc", ".hpp")):
                tags.add("cpp")
    return sorted(tags)


def index_status(root: str, db_path: str | None = None) -> dict:
    """Spec: file count, dirty count, last build, embedding model (or 'none')."""
    db_path = db_path or get_db_path(root)
    exists = os.path.isfile(db_path)
    st = {
        "db_path": db_path, "exists": exists, "schema_version": None,
        "file_count": 0, "symbol_count": 0, "chunk_count": 0, "vector_count": 0,
        "dirty_count": 0, "indexed_at": None, "rebuilt_at": None,
        "embedding_model": "none", "git_head": None, "db_size_bytes": 0,
        "root": os.path.abspath(root),
    }
    if not exists:
        return st
    st["db_size_bytes"] = os.path.getsize(db_path)
    conn = _connect(db_path)
    try:
        st["schema_version"] = _meta(conn, "schema_version") or None
        st["indexed_at"] = _meta(conn, "indexed_at") or None
        st["rebuilt_at"] = _meta(conn, "rebuilt_at") or None
        st["embedding_model"] = _meta(conn, "embedding_model") or "none"
        st["git_head"] = _meta(conn, "git_head") or None
        st["file_count"] = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        st["symbol_count"] = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        st["chunk_count"] = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        st["vector_count"] = conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
    finally:
        conn.close()
    disk = _stat_walk(root)
    conn = _connect(db_path)
    try:
        dirty = 0
        for r in conn.execute("SELECT path,size,mtime FROM files"):
            d = disk.get(r["path"])
            if d is None or (d[0], d[1]) != (r["size"], r["mtime"]):
                dirty += 1
        dirty += len(set(disk) - {r["path"] for r in conn.execute("SELECT path FROM files")})
    finally:
        conn.close()
    st["dirty_count"] = dirty
    return st


def query(root: str, q: str, top_n: int = 10, symbol_limit: int = 20,
          db_path: str | None = None, freshness: bool = True) -> str:
    """Unified ranked query: BM25 file hits (+symbol boost) + symbol hits.

    Returns the rendered result (files section then symbols section). When
    freshness=True, serves the stale index plus a pending-reindex banner if the
    dirty set exceeds the defer threshold (spec trigger #3).
    """
    q = (q or "").strip()
    if not q:
        return build_map(root, db_path=db_path)
    db_path = db_path or get_db_path(root)
    banner = ""
    if freshness:
        st = update_index(root, db_path=db_path)
        if st.get("deferred"):
            banner = st["banner"]
    elif not os.path.isfile(db_path):
        update_index(root, db_path=db_path)
    files_part = rank_files(root, q, top_n=top_n, db_path=db_path)
    syms_part = search_symbols(root, q, db_path=db_path, limit=symbol_limit)
    st = index_status(root, db_path=db_path)
    head = (f"index: {st['file_count']} files, {st['symbol_count']} symbols, "
            f"{st['chunk_count']} chunks @ {st['indexed_at']} "
            f"(git {st['git_head'] or '?'}, embeddings {st['embedding_model']})")
    if banner:
        head += "\n" + banner
    parts = [head]
    if files_part:
        parts.append("-- ranked files (bm25 + symbol boost) --\n" + files_part)
    if syms_part:
        parts.append("-- symbol hits --\n" + syms_part)
    return "\n".join(parts)


def query_json(root: str, q: str, top_n: int = 10, symbols_only: bool = False,
               db_path: str | None = None, freshness: bool = True) -> list[dict]:
    """Machine-readable ranked hits (JSON-serializable list of dicts).

    Each hit is either a file hit
      {"type": "file", "path", "score", "symbols": [names]}
    or a symbol/definition hit
      {"type": "symbol", "path", "line", "kind", "name"}.

    symbols_only=True filters to symbol/definition hits only (no file rows).
    top_n caps BOTH sections (default 10). Same freshness semantics as query().
    """
    q = (q or "").strip()
    if not q:
        return []
    db_path = db_path or get_db_path(root)
    if freshness:
        update_index(root, db_path=db_path)
    elif not os.path.isfile(db_path):
        update_index(root, db_path=db_path)
    terms = [t.lower() for t in re.split(r"\s+", q) if t]
    if not terms:
        return []
    conn = _connect(db_path)
    try:
        hits: list[dict] = []
        # ---- file hits: BM25 (path-weighted) + symbol-name boost --------- #
        if not symbols_only:
            scored: dict[int, dict] = {}
            fq = _fts_query(terms)
            if fq:
                rows = conn.execute(
                    "SELECT fts.rowid AS rid, bm25(fts, ?) AS b, fm.file_id, fm.path "
                    "FROM fts JOIN fts_meta fm ON fm.id = fts.rowid "
                    "WHERE fts MATCH ? ORDER BY b ASC LIMIT 200",
                    (BM25_PATH_WEIGHT, fq))
                for r in rows:
                    fid = r["file_id"]
                    s = -r["b"]  # bm25: more negative = better -> positive score
                    if fid not in scored or s > scored[fid]["score"]:
                        scored[fid] = {"score": s, "path": r["path"]}
            for fid in scored:
                scored[fid]["score"] += _symbol_boost(fid, terms, conn)
            # symbol-only hits (short terms / no FTS row): base 0 + boost
            for r in conn.execute(
                "SELECT DISTINCT s.file_id AS fid, f.path AS p "
                "FROM symbols s JOIN files f ON f.id=s.file_id"):
                if r["fid"] not in scored:
                    b = _symbol_boost(r["fid"], terms, conn)
                    if b > 0:
                        scored[r["fid"]] = {"score": 0.0 + b, "path": r["p"]}
            ranked = sorted(scored.items(),
                            key=lambda kv: (-kv[1]["score"], kv[1]["path"]))
            for fid, info in ranked[:top_n]:
                hits.append({
                    "type": "file",
                    "path": info["path"],
                    "score": round(info["score"], 2),
                    "symbols": _file_symbols(conn, fid),
                })
        # ---- symbol/definition hits -------------------------------------- #
        seen: set[tuple] = set()
        sym_hits: list[dict] = []
        for t in terms:
            esc = _like_escape(t)
            for sql, args in (
                ("SELECT s.name,s.kind,s.line,f.path FROM symbols s "
                 "JOIN files f ON f.id=s.file_id WHERE lower(s.name) LIKE ? ESCAPE '\\' "
                 "ORDER BY (CASE WHEN lower(s.name)=? THEN 0 ELSE 1 END), s.name, f.path LIMIT ?",
                 (esc + "%", t, top_n)),
                ("SELECT s.name,s.kind,s.line,f.path FROM symbols s "
                 "JOIN files f ON f.id=s.file_id WHERE lower(s.name) LIKE ? ESCAPE '\\' "
                 "ORDER BY s.name, f.path LIMIT ?",
                 ("%" + esc + "%", top_n)),
            ):
                for r in conn.execute(sql, args):
                    key = (r["path"], r["line"], r["name"])
                    if key not in seen:
                        seen.add(key)
                        sym_hits.append({
                            "type": "symbol",
                            "path": r["path"],
                            "line": r["line"],
                            "kind": r["kind"],
                            "name": r["name"],
                        })
        hits.extend(sym_hits[:top_n])
        return hits
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# embeddings (OPT-IN) / RRF hybrid
# --------------------------------------------------------------------------- #

def _post_json(url: str, payload: dict, timeout: float) -> dict | None:
    """POST JSON, return parsed dict. None on ANY failure (connect/HTTP/parse)
    — the single network touchpoint tests mock."""
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def embed_texts(texts: list[str], model: str = EMBED_MODEL,
                base_url: str = EMBED_BASE_URL,
                timeout: float = EMBED_TIMEOUT) -> list[list[float]] | None:
    """Pluggable embeddings provider (default: Ollama /api/embeddings).

    Returns a vector per input text (aligned order), or None when the
    provider is unreachable / errors / returns garbage — callers treat None
    as 'graceful skip' and fall back to BM25. All-or-nothing: a single bad
    response aborts the batch so stored vectors always align with files.
    """
    out: list[list[float]] = []
    for t in texts:
        body = _post_json(f"{base_url.rstrip('/')}/api/embeddings",
                          {"model": model, "prompt": t}, timeout)
        vec = body.get("embedding") if body else None
        if not vec:
            return None
        out.append([float(x) for x in vec])
    return out


def _pack_vec(v: list[float]) -> bytes:
    return array.array("f", v).tobytes()


def _unpack_vec(blob: bytes) -> list[float]:
    a = array.array("f")
    a.frombytes(blob)
    return list(a)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _file_embed_text(conn: sqlite3.Connection, file_id: int, path: str) -> str:
    """Embeddable text for a file: relpath + chunk contents, capped."""
    rows = conn.execute(
        "SELECT content FROM chunks WHERE file_id=? ORDER BY idx", (file_id,))
    text = "\n\n".join([path] + [r[0] for r in rows])
    return text[:EMBED_MAX_CHARS]


def build_embeddings(root: str, db_path: str | None = None,
                     model: str | None = None, base_url: str | None = None,
                     timeout: float | None = None,
                     force: bool = False) -> dict:
    """OPT-IN: embed every indexed file into the `vectors` table.

    Fails soft by design: an unreachable provider returns
    {"ok": False, "reason": ...} without touching the DB — the index stays
    fully usable in BM25 mode. Files already embedded with the same model
    tag are skipped unless force=True (which re-embeds everything).
    """
    model = model or EMBED_MODEL
    base_url = base_url or EMBED_BASE_URL
    timeout = timeout if timeout is not None else EMBED_TIMEOUT
    root = os.path.abspath(root)
    db_path = db_path or get_db_path(root)
    if not os.path.isfile(db_path):
        update_index(root, db_path=db_path)
    conn = _connect(db_path)
    try:
        if force:
            conn.execute("DELETE FROM vectors")
        existing = {r[0] for r in conn.execute(
            "SELECT file_id FROM vectors WHERE model=?", (model,))}
        todo = [(r["id"], r["path"]) for r in conn.execute(
            "SELECT id, path FROM files ORDER BY id") if r["id"] not in existing]
        if not todo:
            with conn:
                _set_meta(conn, "embedding_model", model)
            return {"ok": True, "embedded": 0, "skipped": len(existing),
                    "model": model, "reason": ""}
        texts = [_file_embed_text(conn, fid, p) for fid, p in todo]
        vecs = embed_texts(texts, model=model, base_url=base_url, timeout=timeout)
        if vecs is None:
            return {"ok": False, "embedded": 0, "skipped": 0, "model": model,
                    "reason": (f"embedding provider unreachable at "
                               f"{base_url} (graceful skip; index stays in "
                               f"BM25 mode)")}
        with conn:
            for (fid, _p), vec in zip(todo, vecs):
                conn.execute(
                    "INSERT INTO vectors(file_id,model,dim,embedding) "
                    "VALUES(?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET "
                    "model=excluded.model, dim=excluded.dim, "
                    "embedding=excluded.embedding",
                    (fid, model, len(vec), _pack_vec(vec)))
            _set_meta(conn, "embedding_model", model)
        return {"ok": True, "embedded": len(todo), "skipped": len(existing),
                "model": model, "reason": ""}
    finally:
        conn.close()


def rrf_fuse(rankings: list[list], k: float = RRF_K) -> list[tuple]:
    """Reciprocal-rank fusion: score(doc) = Σ 1/(k + rank_i) over rankings.

    Pure math, unit-testable. Higher k flattens the curve; 60 is the
    standard constant. Ties break on doc id for determinism.
    """
    scores: dict = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], str(kv[0])))


def _vector_rank(conn: sqlite3.Connection, q: str,
                 top_n: int) -> list[tuple[int, float]]:
    """File ids ranked by cosine similarity of the query embedding, or [] on
    graceful skip (no vectors stored / provider unreachable / dim mismatch)."""
    row = conn.execute("SELECT model FROM vectors LIMIT 1").fetchone()
    if row is None:
        return []
    model = row[0]
    qv = embed_texts([q], model=model)
    if qv is None:
        return []
    qvec = qv[0]
    scored: list[tuple[float, int]] = []
    for fid, blob in conn.execute(
            "SELECT file_id, embedding FROM vectors WHERE model=?", (model,)):
        scored.append((_cosine(qvec, _unpack_vec(blob)), fid))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [(fid, sim) for sim, fid in scored[:top_n]]


def query_hybrid(root: str, q: str, top_n: int = 10, symbol_limit: int = 20,
                 db_path: str | None = None, k: float = RRF_K,
                 freshness: bool = True) -> str:
    """Opt-in hybrid query: RRF fusion of BM25 + embedding rankings.

    Graceful degradation, never raises on the provider: no vectors stored
    or Ollama unreachable => the plain BM25 ranking, with the mode line
    saying which path ran.
    """
    q = (q or "").strip()
    if not q:
        return build_map(root, db_path=db_path)
    db_path = db_path or get_db_path(root)
    banner = ""
    if freshness:
        st = update_index(root, db_path=db_path)
        if st.get("deferred"):
            banner = st["banner"]
    elif not os.path.isfile(db_path):
        update_index(root, db_path=db_path)
    terms = [t.lower() for t in re.split(r"\s+", q) if t]
    conn = _connect(db_path)
    try:
        bm25 = _ranked_file_ids(conn, terms, max(top_n * 3, 30))
        vec = _vector_rank(conn, q, max(top_n * 3, 30))
        if vec:
            fused = rrf_fuse([[fid for fid, _ in bm25],
                              [fid for fid, _ in vec]], k=k)[:top_n]
            files_part = _render_file_ids(conn, fused, terms, fmt="{:.4f}")
            mode = f"hybrid rrf (bm25 + vectors, k={k:g})"
        else:
            files_part = _render_file_ids(conn, bm25[:top_n], terms)
            if _embedding_model_of(conn) == "none":
                mode = "bm25 (no vectors — run 'cindex embed' to enable hybrid)"
            else:
                mode = "bm25 (vector provider unreachable — graceful fallback)"
        syms_part = search_symbols(root, q, db_path=db_path, limit=symbol_limit)
        st = index_status(root, db_path=db_path)
        head = (f"index: {st['file_count']} files, {st['symbol_count']} symbols, "
                f"{st['chunk_count']} chunks @ {st['indexed_at']} "
                f"(git {st['git_head'] or '?'}, embeddings {st['embedding_model']})")
        head += "\nquery mode: " + mode
        if banner:
            head += "\n" + banner
        parts = [head]
        if files_part:
            parts.append("-- ranked files --\n" + files_part)
        if syms_part:
            parts.append("-- symbol hits --\n" + syms_part)
        return "\n".join(parts)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# CLI  (spec: explicit refresh for scripting/CI)
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__.splitlines()[0])
        print("usage: python -m codebase_index build|status|embed <root>")
        print("       python -m codebase_index query [--hybrid|--json] "
              "[--top N] <root> <query>")
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "build":
        root = rest[0] if rest else os.getcwd()
        st = update_index(root, force=True)
        print(f"built index for {os.path.abspath(root)}: "
              f"{st['added']} added, {st['updated']} updated, "
              f"{st['removed']} removed in {st['duration_ms']}ms")
        print(f"db: {get_db_path(root)}")
        return 0
    if cmd == "status":
        root = rest[0] if rest else os.getcwd()
        for k, v in index_status(root).items():
            print(f"{k}: {v}")
        return 0
    if cmd == "embed":
        root = rest[0] if rest else os.getcwd()
        r = build_embeddings(root)
        if r["ok"]:
            print(f"embedded {r['embedded']} files ({r['skipped']} already "
                  f"cached) with {r['model']} -> {get_db_path(root)}")
        else:
            print(r["reason"])
        return 0
    if cmd == "query":
        json_out, symbols_only, hybrid, top = False, False, False, 10
        positional: list[str] = []
        i = 0
        while i < len(rest):
            a = rest[i]
            if a == "--json":
                json_out = True
            elif a == "--hybrid":
                hybrid = True
            elif a == "--symbols-only":
                symbols_only = True
            elif a == "--top":
                i += 1
                if i >= len(rest):
                    print("--top expects an integer, e.g. --top 5")
                    return 2
                try:
                    top = max(1, int(rest[i]))
                except ValueError:
                    print(f"--top expects an integer, got: {rest[i]}")
                    return 2
            elif a.startswith("--top="):
                try:
                    top = max(1, int(a.split("=", 1)[1]))
                except ValueError:
                    print(f"--top expects an integer, got: {a}")
                    return 2
            else:
                positional.append(a)
            i += 1
        if len(positional) < 2:
            print("usage: python -m codebase_index query [--json] [--hybrid] "
                  "[--top N] [--symbols-only] <root> <query>")
            return 2
        root, q = positional[0], " ".join(positional[1:])
        if json_out:
            print(json.dumps(query_json(root, q, top_n=top,
                                        symbols_only=symbols_only), indent=2))
        elif hybrid:
            print(query_hybrid(root, q, top_n=top))
        else:
            print(query(root, q, top_n=top))
        return 0
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
