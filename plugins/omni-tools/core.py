"""omni-tools core — pure-stdlib capability corpus + BM25 router.

XOMNI's tool-search layer (per .tmp/research-next/TOOL-SEARCH.md). The Hermes
host already ships a native search bridge (``tool_search`` / ``tool_describe`` /
``tool_call``); this module does NOT rebuild that mechanism. It builds the
*corpus the host cannot see* and exposes it through one router tool:

  * **plugin surfaces** — all 22 plugins in ``plugins/``: model tools and
    slash commands statically parsed from each ``__init__.py`` (register_tool /
    register_command calls plus the docstring "Commands::" sections) and
    enriched with the plugin.yaml description.
  * **MCP servers** — 311 entries from ``data/mcp/catalog.json`` (name,
    category, purpose, description, price model).
  * **skills** — 180 curated skills from ``data/curated-skills.json`` (name,
    category, description, source).

Everything here is pure stdlib (``re``, ``math``, ``json``, ``sqlite3``,
``pathlib``) — no third-party dependencies, matching the mcp-catalog /
omni-skills conventions. The corpus is built in-memory by
:func:`rebuild` and optionally cached in SQLite (keyed on source-file
mtimes so a stale cache is never served). Deterministic ordering
(sort by ``(score desc, id)``) keeps listings byte-stable across
rebuilds — the same prompt-cache-safety rule the host enforces.

The router tool :func:`xomni_capabilities` is the model-visible entry
point: BM25 over the merged index, returning ranked hits with
``source`` + ``status`` on every entry so the model knows *how to load*
each capability (host bridge for tools, ``/mcp add`` for unconnected
servers, ``skill_view`` for skills, the ``/command`` for commands).
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ─── repo layout ────────────────────────────────────────────────────────────
# core.py lives at <xomni>/plugins/omni-tools/core.py
XOMNI_ROOT: Path = Path(__file__).resolve().parents[2]
PLUGINS_DIR: Path = XOMNI_ROOT / "plugins"
MCP_CATALOG_PATH: Path = XOMNI_ROOT / "data" / "mcp" / "catalog.json"
SKILLS_CATALOG_PATH: Path = XOMNI_ROOT / "data" / "curated-skills.json"
CACHE_PATH: Path = XOMNI_ROOT / "plugins" / "omni-tools" / "corpus-cache.sqlite3"

# Env overrides (tests and other layouts use these).
ENV_PLUGINS_DIR = "XOMNI_PLUGINS_DIR"
ENV_MCP_CATALOG = "XOMNI_MCP_CATALOG"
ENV_SKILLS_CATALOG = "XOMNI_SKILLS_CATALOG"
ENV_CACHE_PATH = "XOMNI_TOOLSEARCH_CACHE"

# ─── lexical utilities ──────────────────────────────────────────────────────
_STOPWORDS = frozenset(
    """a an and are as at be by for from has have how in is it its of on or
    that the this to was were what when where which who will with you your
    via use used can could do does done may might must not our their them
    then there these they those very""".split()
)

_WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords and 1-char tokens."""
    if not text:
        return []
    return [t for t in _WORD_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def dedupe(seq: Iterable[str]) -> List[str]:
    """Order-preserving unique."""
    seen = set()
    out = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ─── BM25 (pure stdlib; same family as the host's inlined scorer) ───────────
class BM25:
    """Okapi BM25 over a list of pre-tokenized documents.

    ``docs`` is a list of ``(doc_id, tokens)`` tuples. Ranking is
    deterministic: ties break on doc_id ascending.
    """

    K1 = 1.5
    B = 0.75

    def __init__(self) -> None:
        self._docs: List[Tuple[str, List[str]]] = []
        self._doc_len: List[int] = []
        self._avgdl = 0.0
        self._df: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._n = 0

    def index(self, docs: Sequence[Tuple[str, List[str]]]) -> "BM25":
        self._docs = list(docs)
        self._n = len(self._docs)
        if self._n == 0:
            self._avgdl = 0.0
            self._df = {}
            self._idf = {}
            return self
        self._doc_len = [len(t) for _, t in self._docs]
        self._avgdl = sum(self._doc_len) / self._n
        df: Dict[str, int] = {}
        for _, tokens in self._docs:
            for tok in set(tokens):
                df[tok] = df.get(tok, 0) + 1
        self._df = df
        n = self._n
        # Smoothing identical to the host's approach: idf = ln(1 + (N-df+0.5)/(df+0.5)).
        self._idf = {tok: math.log(1.0 + (n - c + 0.5) / (c + 0.5)) for tok, c in df.items()}
        return self

    def search(self, query_tokens: Sequence[str], limit: int = 5) -> List[Tuple[str, float]]:
        """Return [(doc_id, score)] ranked best-first, ties by doc_id."""
        if self._n == 0 or not query_tokens:
            return []
        qtf: Dict[str, int] = {}
        for tok in query_tokens:
            qtf[tok] = qtf.get(tok, 0) + 1
        k1, b = self.K1, self.B
        scored: List[Tuple[str, float]] = []
        for i, (doc_id, tokens) in enumerate(self._docs):
            dl = self._doc_len[i]
            denom = 1.0 - b + b * (dl / self._avgdl) if self._avgdl else 1.0
            score = 0.0
            if dl:
                tf: Dict[str, int] = {}
                for tok in tokens:
                    tf[tok] = tf.get(tok, 0) + 1
                for tok, qc in qtf.items():
                    idf = self._idf.get(tok)
                    if idf is None:
                        continue
                    f = tf.get(tok, 0)
                    if f:
                        score += idf * ((f * (k1 + 1)) / (f + k1 * denom)) * qc
            if score > 0.0:
                scored.append((doc_id, score))
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[:limit]


def _name_substring_match(name: str, query_tokens: Sequence[str]) -> bool:
    """Fallback for zero-IDF queries (same idea as the host): every query token
    must appear as a substring of the (lowercased) name."""
    low = name.lower()
    return all(tok in low for tok in query_tokens)


# ─── plugin surface scanning (static parse of __init__.py) ──────────────────
_NAME_CHARS = r"[a-zA-Z_][a-zA-Z0-9_-]*"
_REG_TOOL = re.compile(r"register_tool\s*\(\s*(?:name\s*=\s*)?[\"'](" + _NAME_CHARS + r")")
_REG_CMD = re.compile(r"register_command\s*\(\s*(?:name\s*=\s*)?[\"'](" + _NAME_CHARS + r")")
_REG_DESC = re.compile(r"(?:description|help)\s*=\s*(?:f?r?)?[\"']([^\"']{8,400})[\"']")
_SLASH = re.compile(r"/([a-z][a-z0-9-]{1,40})")
_DOC_TOOL = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s*\([^)]*\)\s*[—-]", re.M)


def _docstring_of(src: str) -> str:
    if src.count('"""') >= 2:
        return src.split('"""')[1]
    return ""


def _commands_section(src: str) -> List[str]:
    """Commands explicitly documented under a 'Commands::' section.

    Lines are compact command lists: ``/mcp add <path>``, ``/remember <fact>,
    /recall <query>`` or ``/mediascan <dir> [ocr|caption].``. The *full path*
    (e.g. ``mcp add``) is the user-facing surface, so we keep up to three
    tokens per candidate instead of collapsing to the root command.
    """
    doc = _docstring_of(src)
    m = re.search(r"Commands::?\s*(.*?)(?:\n\s*\n|$)", doc, re.S)
    if not m:
        return []
    names: List[str] = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("/"):
            continue
        line = re.split(r"\s+[—–-]\s+", line, maxsplit=1)[0]
        for cand in line.split(","):
            cand = cand.strip()
            m2 = re.match(r"^/[\w-]+(?: [\w-]+){0,2}", cand)
            if m2:
                path = m2.group(0).lstrip("/").strip()
                if path:
                    names.append(path)
    return dedupe(names)


def parse_plugin_surface(src: str, plugin_name: str) -> List[Dict[str, Any]]:
    """Extract (kind, name, description) surfaces from one plugin __init__.py.

    Sources, in priority order:
      1. ``ctx.register_tool(...)`` calls  -> kind "tool"
      2. ``ctx.register_command(...)`` calls -> kind "command"
      3. docstring "Commands::" section      -> kind "command" (documented
         subcommands such as ``/mcp list``, ``/mcp tools``)
      4. docstring ``name(args) — ...``      -> kind "tool"
    """
    tools = dedupe(_REG_TOOL.findall(src))
    cmds = dedupe(_REG_CMD.findall(src))
    doc_cmds = [c for c in _commands_section(src) if c not in cmds]
    doc_tools = [t for t in _DOC_TOOL.findall(_docstring_of(src)) if t not in tools]

    surfaces: List[Dict[str, Any]] = []
    for name in tools:
        surfaces.append({"kind": "tool", "name": name, "plugin": plugin_name})
    for name in cmds + doc_cmds:
        surfaces.append({"kind": "command", "name": name, "plugin": plugin_name})
    for name in doc_tools:
        surfaces.append({"kind": "tool", "name": name, "plugin": plugin_name})
    return surfaces


def _plugin_description(plugin_dir: Path, fallback: str = "") -> str:
    yaml_path = plugin_dir / "plugin.yaml"
    if yaml_path.exists():
        try:
            text = yaml_path.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"(?m)^description:\s*[\"']?(.*?)[\"']?\s*$", text)
            if m and m.group(1):
                return m.group(1)
        except OSError:
            pass
    return fallback


def scan_plugin_surfaces(plugins_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Index every plugin's registered tools + slash commands."""
    root = Path(plugins_dir or os.environ.get(ENV_PLUGINS_DIR) or PLUGINS_DIR)
    entries: List[Dict[str, Any]] = []
    for init in sorted(root.glob("*/__init__.py")):
        plugin_name = init.parent.name
        try:
            src = init.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        surfaces = parse_plugin_surface(src, plugin_name)
        if not surfaces:
            continue
        desc = _plugin_description(init.parent, _docstring_of(src).split("\n")[0])
        for s in surfaces:
            entries.append(
                {
                    "source": "plugin",
                    "kind": s["kind"],
                    "name": s["name"],
                    "plugin": plugin_name,
                    "description": f"{plugin_name} plugin: {desc}" if desc else plugin_name,
                    "status": "registered",
                    "hint": (
                        f"invoke via the host bridge (tool_describe/tool_call)"
                        if s["kind"] == "tool"
                        else f"run /{s['name']}"
                    ),
                }
            )
    return entries


# ─── MCP + skill catalogs ───────────────────────────────────────────────────
def load_mcp_servers(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """311 MCP servers from data/mcp/catalog.json."""
    p = Path(path or os.environ.get(ENV_MCP_CATALOG) or MCP_CATALOG_PATH)
    with open(p, encoding="utf-8") as fh:
        raw = json.load(fh)
    out: List[Dict[str, Any]] = []
    for server in raw:
        name = server.get("name", "")
        if not name:
            continue
        purpose = server.get("purpose", "")
        category = server.get("category", "")
        desc = server.get("description", "")
        out.append(
            {
                "source": "mcp",
                "kind": "mcp_server",
                "name": name,
                "category": category,
                "description": f"{purpose} ({category})" if purpose else desc or category,
                "status": "catalog",  # cataloged; connection status is host-side
                "hint": (
                    f"connect via /mcp add or config.yaml mcp_servers "
                    f"(price_model={server.get('price_model', '?')})"
                ),
                "price_model": server.get("price_model", ""),
            }
        )
    return out


def load_curated_skills(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """180 curated skills from data/curated-skills.json."""
    p = Path(path or os.environ.get(ENV_SKILLS_CATALOG) or SKILLS_CATALOG_PATH)
    with open(p, encoding="utf-8") as fh:
        raw = json.load(fh)
    out: List[Dict[str, Any]] = []
    for skill in raw:
        name = skill.get("name", "")
        if not name:
            continue
        out.append(
            {
                "source": "skill",
                "kind": "skill",
                "name": name,
                "category": skill.get("category", ""),
                "description": skill.get("description", ""),
                "status": "catalog",
                "hint": "load on demand via skill_view (already on-demand)",
                "source_url": skill.get("source_url", ""),
            }
        )
    return out


# ─── keyword enrichment ─────────────────────────────────────────────────────
# High-signal synonym/category terms the raw schemas and purposes lack
# (the exact gap Finding 3 of TOOL-SEARCH.md identifies). Modest, curated.
_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "vision": ("image", "visual", "photo", "screenshot"),
    "image": ("vision", "visual", "photo", "picture"),
    "picture": ("image", "vision", "photo", "visual"),
    "photo": ("image", "vision", "picture", "visual"),
    "visual": ("vision", "image"),
    "browser": ("web", "automation", "dom", "selenium", "playwright", "scrape"),
    "web": ("browser", "internet", "http", "url"),
    "memory": ("recall", "remember", "long-term", "persistent"),
    "search": ("query", "retrieve", "find", "lookup", "discover"),
    "database": ("db", "sql", "query", "storage", "persistence"),
    "sql": ("database", "db", "query"),
    "media": ("video", "audio", "image", "multimedia", "transcript"),
    "video": ("youtube", "media", "clip", "transcript", "frames"),
    "youtube": ("video", "transcript", "media"),
    "github": ("git", "repo", "pull", "pr", "issue", "repository"),
    "git": ("github", "repo", "commit", "branch"),
    "pdf": ("document", "file", "extract", "parse"),
    "document": ("pdf", "docx", "file", "extract"),
    "file": ("document", "pdf", "read", "write"),
    "mcp": ("server", "tool", "catalog", "connect"),
    "skill": ("skills", "capability", "procedure", "workflow"),
    "automation": ("browser", "workflow", "agent", "script"),
    "cloud": ("deploy", "worker", "infra", "serverless"),
    "deploy": ("cloud", "worker", "publish"),
}

# MCP-CATALOG's 12 curated categories become queryable terms too.
_MCP_CATEGORIES = (
    "BROWSER-AUTOMATION", "DATABASE", "CLOUD-DEV", "SEARCH", "MEDIA",
    "DEVELOPMENT", "CODE-REVIEW", "DOCUMENT", "DATA-ANALYSIS", "MONITORING",
    "COMMUNICATION", "MISC",
)


def doc_keywords(entry: Dict[str, Any], name_weight: int = 2) -> List[str]:
    """BM25 token stream for one corpus entry.

    Name tokens are repeated ``name_weight`` times (names are the highest
    signal — Anthropic's namespacing best practice); description/category/
    plugin tokens once; curated synonyms appended. Deterministic.
    """
    name_tokens = tokenize(str(entry.get("name", "")))
    desc_tokens = tokenize(
        " ".join(str(entry.get(k, "")) for k in ("description", "category", "plugin"))
    )
    extra: List[str] = []
    for tok in name_tokens + desc_tokens:
        extra.extend(_SYNONYMS.get(tok, ()))
    for cat in _MCP_CATEGORIES:
        if cat.lower() in str(entry.get("category", "")).lower():
            extra.extend(tokenize(cat.replace("-", " ")))
    return list(name_tokens) * max(1, name_weight) + desc_tokens + extra


def enrich_keywords(entry: Dict[str, Any]) -> List[str]:
    """Deduped keyword view (cache meta / tests); same sources as doc_keywords."""
    return dedupe(doc_keywords(entry))


def enrich_query_tokens(query: str) -> List[str]:
    """Query tokens + the same synonym expansion applied to documents, so a
    paraphrase like 'picture' surfaces vision/image capabilities (this is the
    keyword-enrichment recall gap TOOL-SEARCH.md Finding 3 calls out)."""
    tokens = tokenize(query)
    extra: List[str] = []
    for tok in tokens:
        extra.extend(_SYNONYMS.get(tok, ()))
    return dedupe(tokens + extra)


# ─── corpus ─────────────────────────────────────────────────────────────────
def build_corpus(
    plugins_dir: Optional[Path] = None,
    mcp_path: Optional[Path] = None,
    skills_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Merged, keyword-enriched corpus: plugins + MCP + skills."""
    entries: List[Dict[str, Any]] = []
    entries.extend(scan_plugin_surfaces(plugins_dir))
    entries.extend(load_mcp_servers(mcp_path))
    entries.extend(load_curated_skills(skills_path))
    for i, entry in enumerate(entries):
        entry["id"] = f"{entry['source']}:{entry['kind']}:{entry['name']}:{i}"
        entry["_keywords"] = doc_keywords(entry)
    return entries


# ─── sqlite cache (optional; keyed on source mtimes) ────────────────────────
def _source_mtimes(
    plugins_dir: Path, mcp_path: Path, skills_path: Path
) -> Dict[str, float]:
    mtimes: Dict[str, float] = {}
    for init in sorted(plugins_dir.glob("*/__init__.py")):
        mtimes[str(init)] = init.stat().st_mtime
    mtimes[str(mcp_path)] = mcp_path.stat().st_mtime
    mtimes[str(skills_path)] = skills_path.stat().st_mtime
    return mtimes


def save_cache(db_path: Path, corpus: Sequence[Dict[str, Any]], mtimes: Dict[str, float]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DROP TABLE IF EXISTS meta")
        conn.execute("DROP TABLE IF EXISTS corpus")
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute(
            "CREATE TABLE corpus (id TEXT PRIMARY KEY, source TEXT, kind TEXT, "
            "name TEXT, description TEXT, status TEXT, hint TEXT, extra TEXT)"
        )
        for key, val in mtimes.items():
            conn.execute("INSERT INTO meta VALUES (?, ?)", (key, str(val)))
        for e in corpus:
            extra = {
                k: v
                for k, v in e.items()
                if k not in ("id", "source", "kind", "name", "description", "status", "hint")
            }
            conn.execute(
                "INSERT INTO corpus VALUES (?,?,?,?,?,?,?,?)",
                (
                    e["id"], e["source"], e["kind"], e["name"],
                    e.get("description", ""), e.get("status", ""),
                    e.get("hint", ""), json.dumps(extra, sort_keys=True),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def load_cache(db_path: Path, mtimes: Dict[str, float]) -> Optional[List[Dict[str, Any]]]:
    """Return cached corpus only if it matches current source mtimes."""
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT key, value FROM meta").fetchall()
        if {k: v for k, v in rows} != {k: str(v) for k, v in mtimes.items()}:
            return None
        corpus = []
        for row in conn.execute("SELECT * FROM corpus").fetchall():
            e = {
                "id": row[0], "source": row[1], "kind": row[2], "name": row[3],
                "description": row[4], "status": row[5], "hint": row[6],
            }
            e.update(json.loads(row[7]))
            e["_keywords"] = doc_keywords(e)
            corpus.append(e)
        return corpus
    finally:
        conn.close()


# ─── the index + router ─────────────────────────────────────────────────────
class ToolSearchIndex:
    """BM25 over the merged corpus with kind filters + status hints."""

    def __init__(self, corpus: Sequence[Dict[str, Any]]) -> None:
        self.corpus: List[Dict[str, Any]] = list(corpus)
        self._by_id: Dict[str, Dict[str, Any]] = {e["id"]: e for e in self.corpus}
        self._bm25 = BM25().index(
            [(e["id"], e.get("_keywords", doc_keywords(e))) for e in self.corpus]
        )

    def search(
        self, query: str, kind: Optional[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        q_tokens = enrich_query_tokens(query)
        if not q_tokens:
            return []
        # Filter corpus by kind BEFORE ranking so results are refilled
        # (post-filtering would leave short result lists).
        pool = self.corpus
        if kind and kind != "all":
            pool = [
                e for e in pool
                if e["kind"] == kind or e["source"] == kind
            ]
        bm25 = self._bm25 if pool is self.corpus else BM25().index(
            [(e["id"], e.get("_keywords", doc_keywords(e))) for e in pool]
        )
        ids = [doc_id for doc_id, _ in bm25.search(q_tokens, limit=limit)]
        # Zero-IDF fallback: query tokens that matched nothing at all still
        # resolve by name substring (host parity).
        if not ids or not any(
            tok in " ".join(e["name"].lower() for e in pool if e["id"] in ids)
            for tok in q_tokens
        ):
            for e in pool:
                if _name_substring_match(e["name"], q_tokens):
                    ids.append(e["id"])
                    if len(ids) >= limit:
                        break
            ids = dedupe(ids)[:limit]
        results = []
        by_id = {e["id"]: e for e in pool}
        for rank, doc_id in enumerate(ids[:limit], start=1):
            e = by_id[doc_id]
            results.append(
                {
                    "rank": rank,
                    "source": e["source"],
                    "kind": e["kind"],
                    "name": e["name"],
                    "status": e.get("status", ""),
                    "hint": e.get("hint", ""),
                    "description": e.get("description", ""),
                }
            )
        return results

    def stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        by_kind: Dict[str, int] = {}
        for e in self.corpus:
            counts["total"] = counts.get("total", 0) + 1
            by_source[e["source"]] = by_source.get(e["source"], 0) + 1
            by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
        return {"total": counts.get("total", 0), "by_source": by_source, "by_kind": by_kind}


def rebuild(
    use_cache: bool = True, cache_path: Optional[Path] = None,
    plugins_dir: Optional[Path] = None, mcp_path: Optional[Path] = None,
    skills_path: Optional[Path] = None,
) -> ToolSearchIndex:
    """Build (or load cached) corpus and return a ready index."""
    root = Path(plugins_dir or os.environ.get(ENV_PLUGINS_DIR) or PLUGINS_DIR)
    mp = Path(mcp_path or os.environ.get(ENV_MCP_CATALOG) or MCP_CATALOG_PATH)
    sp = Path(skills_path or os.environ.get(ENV_SKILLS_CATALOG) or SKILLS_CATALOG_PATH)
    cp = Path(cache_path or os.environ.get(ENV_CACHE_PATH) or CACHE_PATH)
    mtimes = _source_mtimes(root, mp, sp)
    if use_cache:
        cached = load_cache(cp, mtimes)
        if cached is not None:
            return ToolSearchIndex(cached)
    corpus = build_corpus(root, mp, sp)
    if use_cache:
        try:
            save_cache(cp, corpus, mtimes)
        except OSError:
            pass  # cache is an optimization; never fatal
    return ToolSearchIndex(corpus)


# ─── router tool body (registered by __init__.py as xomni_capabilities) ─────
_INDEX_CACHE: Dict[str, ToolSearchIndex] = {}


def get_index() -> ToolSearchIndex:
    """Process-wide lazily-built index (built once, reused across calls)."""
    if "default" not in _INDEX_CACHE:
        _INDEX_CACHE["default"] = rebuild(use_cache=True)
    return _INDEX_CACHE["default"]


def reset_index() -> None:
    _INDEX_CACHE.clear()


def xomni_capabilities(
    query: str, kind: str = "all", limit: int = 5, index: Optional[ToolSearchIndex] = None
) -> str:
    """Router tool: BM25 over plugins + MCP + skills; every hit carries
    source + status + a load hint."""
    idx = index if index is not None else get_index()
    try:
        lim = max(1, min(int(limit), 20))
    except (TypeError, ValueError):
        lim = 5
    results = idx.search(query or "", kind=kind or "all", limit=lim)
    if not results:
        return (
            f"xomni_capabilities: no matches for {query!r}. "
            "The capability may not be indexed; try different keywords or "
            "browse the index with /tools-index."
        )
    lines = [f"top {len(results)} capability match(es) for {query!r}:"]
    for r in results:
        lines.append(
            f"{r['rank']}. [{r['source']}:{r['kind']}] {r['name']} — {r['description'][:160]}"
            f" (status={r['status']}; {r['hint']})"
        )
    return "\n".join(lines)


# ─── recall benchmark (built-in eval set) ───────────────────────────────────
# ~20 planted queries, each with a known expected hit that must land in the
# top 5 on the live corpus. Verified 2026-08-12 against the real repo data
# (561-entry corpus: 70 plugin surfaces + 311 MCP + 180 skills). Covers all
# three surfaces plus the synonym-expansion path ("picture photo visual",
# "web scraping dom") and command paths ("mcp add", "mcp list").
EVAL_SET: List[Tuple[str, str]] = [
    ("vision image describe", "describe_image"),          # plugin tool
    ("browser automation web scraping", "playwright"),    # mcp
    ("sqlite database query", "sqlite"),                  # mcp
    ("youtube transcript subtitles", "youtube-transcript"),  # mcp
    ("memory consolidate recall", "memory-consolidate"),  # plugin command
    ("mcp server catalog add", "mcp add"),                # plugin command
    ("pdf extract document", "pdf"),                      # skill
    ("picture photo visual", "describe_image"),           # synonym path
    ("web scraping dom", "playwright"),                   # synonym path
    ("cloudflare workers deploy", "cloudflare"),          # mcp
    ("ocr scan text", "ocr"),                             # plugin command
    ("video transcript", "youtube-transcript"),           # mcp
    ("ffmpeg video clip transcode", "ffmpeg-mcp"),        # mcp
    ("media directory caption", "mediascan"),             # plugin command
    ("web page fetch readable", "fetch_page"),            # plugin tool
    ("caption vision model", "caption"),                  # plugin command
    ("command list tools mcp", "mcp list"),               # plugin command
    ("github pull request issue", "github"),              # mcp
    ("spreadsheet excel csv", "googlesheets"),            # mcp
    ("document parse extract table", "pdf"),              # skill
]


def eval_recall(
    index: Optional[ToolSearchIndex] = None,
    limit: int = 5,
    persist: bool = False,
    cache_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run the built-in EVAL_SET against an index; return top-N recall stats.

    ``recall`` = fraction of queries whose expected hit appears in the top
    ``limit`` results (case-insensitive name-substring match, same rule the
    test suite uses). ``last_eval`` is the run timestamp. When ``persist`` is
    true the summary is written to the SQLite cache (eval table) so
    ``/tools-stats`` can report the last eval time across runs.
    """
    idx = index if index is not None else get_index()
    results: List[Dict[str, Any]] = []
    hits = 0
    for query, expected in EVAL_SET:
        names = [r["name"] for r in idx.search(query, limit=limit)]
        rank = next(
            (i + 1 for i, n in enumerate(names) if expected.lower() in n.lower()),
            None,
        )
        hit = rank is not None
        hits += int(hit)
        results.append(
            {"query": query, "expected": expected, "hit": hit, "rank": rank}
        )
    ev: Dict[str, Any] = {
        "queries": len(EVAL_SET),
        "hits": hits,
        "recall": hits / len(EVAL_SET) if EVAL_SET else 0.0,
        "limit": limit,
        "last_eval": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    }
    if persist:
        try:
            cp = Path(cache_path or os.environ.get(ENV_CACHE_PATH) or CACHE_PATH)
            save_eval(cp, ev)
        except OSError:
            pass  # cache is an optimization; never fatal
    return ev


# ─── cross-surface recall eval ──────────────────────────────────────────────
# A broader, data-driven companion to EVAL_SET: 50 planted queries
# (data/cross_surface_eval.json) that intentionally mix the plugin, MCP and
# skill surfaces (including multi-surface "mixed" queries), scored as
# recall@k per surface and overall. Same substring hit rule as eval_recall.
CROSS_SURFACE_EVAL_PATH: Path = (
    Path(__file__).resolve().parent / "data" / "cross_surface_eval.json"
)
CROSS_SURFACE_REPORT_PATH: Path = XOMNI_ROOT / "data" / "cross_surface_report.json"


def _best_effort_index(
    plugins_dir: Optional[Path] = None,
    mcp_path: Optional[Path] = None,
    skills_path: Optional[Path] = None,
) -> Tuple[ToolSearchIndex, Dict[str, bool]]:
    """Build an index surface-by-surface so a missing data file degrades to
    a score of 0 for that surface instead of crashing the eval run."""
    loaded = {"plugin": True, "mcp": True, "skill": True}
    entries: List[Dict[str, Any]] = []
    try:
        entries.extend(scan_plugin_surfaces(plugins_dir))
    except (OSError, ValueError):
        loaded["plugin"] = False
    try:
        entries.extend(load_mcp_servers(mcp_path))
    except (OSError, ValueError):
        loaded["mcp"] = False
    try:
        entries.extend(load_curated_skills(skills_path))
    except (OSError, ValueError):
        loaded["skill"] = False
    for i, entry in enumerate(entries):
        entry.setdefault("id", f"{entry['source']}:{entry['kind']}:{entry['name']}:{i}")
        entry.setdefault("_keywords", doc_keywords(entry))
    return ToolSearchIndex(entries), loaded


def cross_surface_recall(
    cases_path: Optional[Path] = None,
    top_k: int = 5,
    index: Optional[ToolSearchIndex] = None,
    report_path: Optional[Path] = None,
    plugins_dir: Optional[Path] = None,
    mcp_path: Optional[Path] = None,
    skills_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run the 50-query cross-surface eval; score recall@top_k per surface.

    Each case in ``cases_path`` (default data/cross_surface_eval.json) is a
    dict with ``id``, ``query``, ``surface`` (plugin|mcp|skill|mixed) and
    ``expected_hits`` (1-3 names/substrings that must appear in the top-k
    results, case-insensitive substring match — same rule as eval_recall).
    Per-case recall = matched_expected / len(expected_hits); per-surface and
    overall recall are the mean over their cases. ``index`` defaults to the
    live corpus (built best-effort so a missing data file scores 0 for that
    surface rather than crashing). The per-case + summary report is written
    to ``report_path`` (default data/cross_surface_report.json).
    """
    cp = Path(cases_path or CROSS_SURFACE_EVAL_PATH)
    with open(cp, encoding="utf-8") as fh:
        cases = json.load(fh)
    k = max(1, int(top_k))
    idx = index
    loaded: Optional[Dict[str, bool]] = None
    if idx is None:
        if plugins_dir is None and mcp_path is None and skills_path is None:
            try:
                idx = get_index()
            except (OSError, ValueError):
                idx = None
        if idx is None:
            idx, loaded = _best_effort_index(plugins_dir, mcp_path, skills_path)

    per_case: List[Dict[str, Any]] = []
    for case in cases:
        names = [r["name"] for r in idx.search(case["query"], limit=k)]
        expected = case.get("expected_hits") or []
        ranks: Dict[str, Optional[int]] = {}
        matched = 0
        for exp in expected:
            rank = next(
                (i + 1 for i, n in enumerate(names) if str(exp).lower() in n.lower()),
                None,
            )
            ranks[str(exp)] = rank
            matched += int(rank is not None)
        per_case.append(
            {
                "id": case["id"],
                "query": case["query"],
                "surface": case["surface"],
                "expected_hits": list(expected),
                "ranks": ranks,
                "recall": matched / len(expected) if expected else 0.0,
            }
        )

    surfaces: List[str] = []
    for c in per_case:
        if c["surface"] not in surfaces:
            surfaces.append(c["surface"])
    per_surface: Dict[str, Dict[str, Any]] = {}
    for s in surfaces:
        group = [c for c in per_case if c["surface"] == s]
        per_surface[s] = {
            "cases": len(group),
            "recall": sum(c["recall"] for c in group) / len(group) if group else 0.0,
        }
    overall = (
        sum(c["recall"] for c in per_case) / len(per_case) if per_case else 0.0
    )

    result: Dict[str, Any] = {
        "eval": "cross_surface_recall",
        "queries": len(per_case),
        "top_k": k,
        "overall_recall": overall,
        "per_surface": per_surface,
        "sources_loaded": loaded
        if loaded is not None
        else {"plugin": True, "mcp": True, "skill": True},
        "last_eval": time.strftime("%Y-%m-%d %H:%M:%S"),
        "per_case": per_case,
    }

    # human-readable table
    rows = [s for s in surfaces if s in ("plugin", "mcp", "skill", "mixed")] + ["overall"]
    width = max(len("overall"), max(len(r) for r in rows))
    print(f"cross-surface recall@{k} ({len(per_case)} queries)")
    print(f"{'surface':<{width}}  {'cases':>5}  {'recall':>7}")
    for r in rows:
        if r == "overall":
            print(f"{'overall':<{width}}  {len(per_case):>5}  {overall:>7.3f}")
        else:
            ps = per_surface.get(r, {"cases": 0, "recall": 0.0})
            print(f"{r:<{width}}  {ps['cases']:>5}  {ps['recall']:>7.3f}")

    try:
        rp = Path(report_path or CROSS_SURFACE_REPORT_PATH)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        result["report_path"] = str(rp)
    except OSError:
        pass  # report file is best-effort; never fatal
    return result


def save_eval(db_path: Path, ev: Dict[str, Any]) -> None:
    """Persist the eval summary into a key/value 'eval' table (cache db)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS eval (key TEXT PRIMARY KEY, value TEXT)")
        payload = {k: v for k, v in ev.items() if k != "results"}
        payload["results"] = json.dumps(ev.get("results", []), sort_keys=True)
        for key, value in payload.items():
            encoded = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
            conn.execute(
                "INSERT INTO eval (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, encoded),
            )
        conn.commit()
    finally:
        conn.close()


def load_eval(db_path: Path) -> Optional[Dict[str, Any]]:
    """Last persisted eval summary, or None if never run / db missing."""
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    try:
        try:
            rows = conn.execute("SELECT key, value FROM eval").fetchall()
        except sqlite3.OperationalError:
            return None
    finally:
        conn.close()
    if not rows:
        return None
    out: Dict[str, Any] = {}
    for key, value in rows:
        try:
            out[key] = json.loads(value)
        except (ValueError, TypeError):
            out[key] = value
    return out


def stats_report(index: Optional[ToolSearchIndex] = None) -> str:
    """Rendered /tools-stats output: corpus size + recall + last eval time.

    Runs the built-in eval set live (cheap: ~20 in-memory BM25 searches),
    persists the summary to the cache, and prints corpus counts, top-5
    recall, and the eval timestamp.
    """
    idx = index if index is not None else get_index()
    stats = idx.stats()
    ev = eval_recall(index=idx, persist=True)
    lines = [
        "omni-tools stats:",
        f"corpus: {stats['total']} entries "
        f"(plugin surfaces={stats['by_source'].get('plugin', 0)}, "
        f"MCP servers={stats['by_source'].get('mcp', 0)}, "
        f"skills={stats['by_source'].get('skill', 0)})",
        f"recall: {ev['recall']:.3f} top-{ev['limit']} "
        f"({ev['hits']}/{ev['queries']} eval queries)",
        f"last eval: {ev['last_eval']}",
    ]
    return "\n".join(lines)
