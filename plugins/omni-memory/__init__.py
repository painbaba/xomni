"""OmniMemory — OpenClaw-style personal memory, local and free.

Hooks: pre_llm_call (inject a memory brief into non-trivial turns),
post_tool_call (auto-remember nothing by default — facts are stored on
purpose). Commands: /remember <fact>, /recall <query>, /memory-status,
/memory-consolidate. All hooks return None or a context string; the
module never alters agent behavior beyond injecting the brief.
"""
from __future__ import annotations

import time

from . import core

_CTX = None

HELP = (
    "/remember <fact>      store a personal fact\n"
    "/recall <query>       retrieve matching facts\n"
    "/memory-status        show fact count + store path\n"
    "/memory-consolidate   fold oldest facts into a summary (LLM)\n"
)


def _on_pre_llm_call(**kwargs) -> dict | None:
    raw = kwargs.get("user_message")
    if not isinstance(raw, str) or len(raw.strip()) < core.INJECT_MIN_QUERY_LEN:
        return None
    brief = core.inject_brief(raw)
    if not brief:
        return None
    return {
        "context": (
            "[Personal memory — from your own prior sessions. Use it only "
            "where it helps; ignore it when irrelevant.]\n\n" + brief
        )
    }


def _handle_remember(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return "usage: /remember <fact>"
    try:
        fid = core.remember(text, source="user")
    except ValueError as exc:
        return f"could not remember: {exc}"
    return f"remembered #{fid}"


def _handle_recall(raw: str) -> str:
    query = (raw or "").strip()
    if not query:
        return "usage: /recall <query>"
    hits = core.recall(query, limit=6)
    if not hits:
        return f"nothing found for {query!r}."
    lines = []
    for h in hits:
        when = time.strftime("%Y-%m-%d", time.localtime(h["created"]))
        lines.append(f"[{h['score']:.2f}] {h['text']}  ({when}, source={h['source']})")
    return "\n".join(lines)


def _handle_status() -> str:
    with core._conn() as db:  # noqa: SLF001 — internal status read
        total = db.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    return f"omni-memory: {total} fact(s) at {core.DB_PATH}"


def _handle_consolidate() -> str:
    key = core.load_key()
    if not key:
        return "consolidation needs OPENCODE_GO_API_KEY (missing from .env)"
    result = core.consolidate(key)
    if result.get("error"):
        return f"consolidation failed (store untouched): {result['error']}"
    if not result.get("consolidated"):
        return (
            f"nothing to consolidate: {result['before']} fact(s), need "
            f">= {core.CONSOLIDATE_THRESHOLD}"
        )
    return f"consolidated: {result['before']} -> {result['after']} fact(s)"


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_command("remember", handler=_handle_remember,
                         description="Store a personal fact in omni-memory",
                         args_hint="<fact>")
    ctx.register_command("recall", handler=_handle_recall,
                         description="Retrieve matching omni-memory facts",
                         args_hint="<query>")
    ctx.register_command("memory-status", handler=_handle_status,
                         description="Show omni-memory store status")
    ctx.register_command("memory-consolidate", handler=_handle_consolidate,
                         description="Fold oldest facts into a summary")
