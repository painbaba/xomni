"""omni-tools — capability corpus + router on top of the host's native bridge.

Implements TOOL-SEARCH.md: the Hermes host already hides the long tail
behind its native ``tool_search`` bridge; this plugin extends what the model
can *discover* to the three surfaces the host cannot see — the 311-server MCP
catalog, the 180-skill curated DB, and all 17 plugins' tools + slash commands
— through one BM25 router tool.

Model tool::

    xomni_capabilities(query, kind='all', limit=5)

        BM25 over the merged corpus (pure stdlib, no deps). Every hit carries
        source + status + a load hint so the model knows how to invoke it:
          - plugin tool   -> load via the host bridge (tool_describe/tool_call)
          - plugin command-> run /<name>
          - MCP server    -> connect via /mcp add or config.yaml mcp_servers
          - skill         -> load on demand via skill_view

Slash commands::

    /tools-search <query> [--kind=<tool|command|mcp_server|skill>] [--limit=N]
    /tools-index            rebuild the corpus + print stats

Zero hooks: nothing here registers a hook; the plugin is pure on-demand.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP = (
    "/tools-search <query> [--kind=KIND] [--limit=N]  search the capability corpus (BM25)\n"
    "  kinds: tool | command | mcp_server | skill | all (default)\n"
    "/tools-index   rebuild the corpus from source files + print index stats\n"
)


def _handle_tools_search(raw: str) -> str:
    parts = (raw or "").strip().split()
    if not parts:
        return HELP
    kind = "all"
    limit = 5
    terms: list[str] = []
    for p in parts:
        if p.startswith("--kind="):
            kind = p.split("=", 1)[1]
        elif p.startswith("--limit="):
            try:
                limit = int(p.split("=", 1)[1])
            except ValueError:
                limit = 5
        else:
            terms.append(p)
    if not terms:
        return HELP
    return core.xomni_capabilities(" ".join(terms), kind=kind, limit=limit)


def _handle_tools_index(raw: str) -> str:
    idx = core.rebuild(use_cache=True)
    stats = idx.stats()
    lines = [
        "omni-tools index rebuilt.",
        f"corpus: {stats['total']} entries "
        f"(plugin surfaces={stats['by_source'].get('plugin', 0)}, "
        f"MCP servers={stats['by_source'].get('mcp', 0)}, "
        f"skills={stats['by_source'].get('skill', 0)})",
        "by kind: " + ", ".join(f"{k}={v}" for k, v in sorted(stats["by_kind"].items())),
        "router: xomni_capabilities(query, kind, limit)  ·  /tools-search <q>",
    ]
    return "\n".join(lines)


def register(ctx) -> None:
    global _CTX
    _CTX = ctx

    def _catalog_exists() -> bool:
        return core.MCP_CATALOG_PATH.exists() or core.SKILLS_CATALOG_PATH.exists()

    ctx.register_tool(
        "xomni_capabilities",
        toolset="omni-toolsearch",
        schema={
            "description": (
                "Capability router: BM25 search across ALL XOMNI capabilities — "
                "plugin tools + slash commands (17 plugins), MCP servers (311 in "
                "catalog), and skills (180 curated). Every hit reports its source, "
                "status, and how to load/invoke it. Use this FIRST whenever the "
                "needed tool is not already visible in the tool list — the full "
                "surface is deferred behind the host bridge."
            ),
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "capability keywords, e.g. 'vision image describe'",
                },
                "kind": {
                    "type": "string",
                    "enum": ["all", "tool", "command", "mcp_server", "skill"],
                    "description": "restrict to one surface kind (default all)",
                },
                "limit": {
                    "type": "integer",
                    "description": "max hits (1-20, default 5)",
                },
            },
            "required": ["query"],
        },
        handler=lambda params: core.xomni_capabilities(
            params.get("query", ""),
            kind=params.get("kind", "all"),
            limit=params.get("limit", 5),
        ),
        description=(
            "Search XOMNI's full capability corpus (17 plugin surfaces + 311 MCP "
            "servers + 180 skills) with BM25; returns ranked matches with "
            "source + status + load hints."
        ),
        check_fn=_catalog_exists,
        emoji="🔎",
    )
    ctx.register_command(
        "tools-search",
        handler=_handle_tools_search,
        description="BM25 search across the XOMNI capability corpus (plugins + MCP + skills).",
        args_hint="<query> [--kind=tool|command|mcp_server|skill] [--limit=N]",
    )
    ctx.register_command(
        "tools-index",
        handler=_handle_tools_index,
        description="Rebuild the omni-tools corpus from source files and print index stats.",
        args_hint="",
    )
