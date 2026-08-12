"""codebase-index (repomap v2) — hybrid incremental codebase index.

SQLite FTS5 (trigram) full-text index over a repo with Continue-style
incremental updates (stat-diff + sha256 content-hash dedup), BM25 ranking with
path weight + symbol-name boost. Pure stdlib; registers NO hooks — a tool and a
slash command only.

Surface:
  /cindex status [path]           index health (files, symbols, dirty count)
  /cindex build [path]            full rebuild (explicit refresh)
  /cindex query <q> [path]        ranked file + symbol hits
  tool codebase_query             model-callable version of the query surface
"""
from __future__ import annotations

import os

from . import core


def _resolve_root(path: str | None) -> str:
    root = (path or "").strip() or os.getcwd()
    return os.path.abspath(root)


def _codebase_query_tool(params: dict) -> str:
    root = _resolve_root(params.get("path") or params.get("root"))
    q = (params.get("query") or "").strip()
    limit = int(params.get("limit") or 10)
    if not os.path.isdir(root):
        return f"codebase_query: not a directory: {root}"
    try:
        if not q:
            st = core.index_status(root)
            return (f"index {('exists' if st['exists'] else 'missing')} for {root}\n"
                    + "\n".join(f"{k}: {v}" for k, v in st.items()
                                if k not in ("db_path", "root")))
        return core.query(root, q, top_n=limit, symbol_limit=max(10, limit * 2))
    except Exception as exc:  # tool handlers must not raise
        return f"codebase_query failed: {exc}"


def _handle_cindex(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        root = _resolve_root(None)
        st = core.index_status(root)
        head = f"codebase index for {root}"
        if not st["exists"]:
            return head + " — not built yet (run: /cindex build)"
        return head + "\n" + "\n".join(
            f"{k}: {v}" for k, v in st.items()
            if k not in ("db_path", "root"))
    parts = raw.split(None, 2)
    sub = parts[0].lower()
    rest = parts[1:]
    try:
        if sub == "build":
            root = _resolve_root(rest[0] if rest else None)
            if not os.path.isdir(root):
                return f"/cindex: not a directory: {root}"
            st = core.update_index(root, force=True)
            return (f"index rebuilt for {root}: {st['added']} added, "
                    f"{st['updated']} updated, {st['removed']} removed "
                    f"({st['duration_ms']}ms) -> {core.get_db_path(root)}")
        if sub == "status":
            root = _resolve_root(rest[0] if rest else None)
            if not os.path.isdir(root):
                return f"/cindex: not a directory: {root}"
            st = core.index_status(root)
            head = f"codebase index for {root}"
            if not st["exists"]:
                return head + " — not built yet (run: /cindex build)"
            return head + "\n" + "\n".join(
                f"{k}: {v}" for k, v in st.items()
                if k not in ("db_path", "root"))
        if sub == "query":
            if not rest:
                return "/cindex query <q> [path] — e.g. /cindex query fts5 index"
            q = rest[0]
            root = _resolve_root(rest[1] if len(rest) > 1 else None)
            if not os.path.isdir(root):
                return f"/cindex: not a directory: {root}"
            return core.query(root, q)
        return ("usage: /cindex build|status [path] | /cindex query <q> [path]")
    except Exception as exc:
        return f"/cindex failed: {exc}"


def register(ctx) -> None:
    ctx.register_tool(
        "codebase_query",
        toolset="file",
        schema={
            "description": (
                "Query the incremental codebase index (SQLite FTS5 + symbols) "
                "of a directory: ranked relevant files (BM25 with path and "
                "symbol-name boosts) plus exact symbol hits with line numbers. "
                "Args: path (directory, default cwd), query (search terms; "
                "when omitted returns index status), limit (max file hits, "
                "default 10). Read-only; builds the index on first use."
            ),
            "type": "object",
            "properties": {
                "path": {"type": "string",
                         "description": "directory to query (default: cwd)"},
                "query": {"type": "string",
                          "description": "search terms; omit for index status"},
                "limit": {"type": "integer",
                          "description": "max ranked file hits (default 10)"},
            },
        },
        handler=_codebase_query_tool,
        description="Hybrid codebase index query (BM25 + symbols)",
        emoji="🔎",
    )
    ctx.register_command(
        "cindex", handler=_handle_cindex,
        description="Hybrid codebase index: status, build, ranked query",
        args_hint="status|build [path] | query <q> [path]",
    )
