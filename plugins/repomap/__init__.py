"""Aider-style repo map — Hermes plugin wiring.

Exposes a model-callable tool `repomap` (read-only; returns a compact symbol map
of a directory) and a `/repomap` slash command for interactive use.
"""
from __future__ import annotations

import os

from . import core

_CTX = None


def _repomap_tool(params: dict) -> str:
    root = params.get("path") or params.get("root") or os.getcwd()
    if not os.path.isdir(root):
        return f"repomap: not a directory: {root}"
    try:
        query = (params.get("query") or "").strip()
        if query:
            return core.rank_files(root, query)
        return core.build_map(root)
    except Exception as exc:
        return f"repomap failed: {exc}"


def _handle_repomap(raw: str) -> str:
    raw = (raw or "").strip()
    if raw:
        parts = raw.split(None, 1)
        target = parts[0]
        query = parts[1].strip() if len(parts) > 1 else ""
    else:
        target = os.getcwd()
        query = ""
    if not os.path.isdir(target):
        return f"/repomap: not a directory: {target}"
    tags = core.stack_tags(target)
    if query:
        m = core.rank_files(target, query)
        head = f"repo map for {target} (query: {query}; stack: {', '.join(tags) or 'unknown'})\n"
    else:
        m = core.build_map(target)
        head = f"repo map for {target} (stack: {', '.join(tags) or 'unknown'})\n"
    return head + m


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_tool(
        "repomap",
        toolset="file",
        schema={
            "description": (
                "Build a compact symbol-level map of a codebase directory "
                "(files with their classes/functions/types) so the model can "
                "navigate without dumping whole files. Args: path (directory). "
                "Optional query (string): when present, returns the top "
                "relevance-ranked files matching the query terms instead of "
                "the plain map. Read-only."
            ),
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "directory to map (default: cwd)"},
                "query": {"type": "string", "description": "optional relevance query; when present, returns ranked relevant files instead of the plain map"},
            },
        },
        handler=_repomap_tool,
        description="Symbol-level repo map (aider-style)",
        emoji="🗺️",
    )
    ctx.register_command(
        "repomap", handler=_handle_repomap,
        description="Symbol-level map of a codebase (aider-style)",
        args_hint="<directory> [query words...]",
    )
