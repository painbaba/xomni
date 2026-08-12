"""offline-kit — offline-first readiness probe for the local XOMNI stack.

Probes the LOCAL Ollama runtime (chat + embeddings) and local search, then
produces an offline-ready report plus a concrete model plan so XOMNI keeps
working with no network and no API keys.

Design rules:
- Pure stdlib (urllib.request, json, os, time) — no third-party deps, no
  Hermes imports; cold import is a few ms.
- ``probe()`` is DIAGNOSTIC: it never raises on network failure. Unreachable
  Ollama is recorded as ``reachable: False`` with an error string.
- Zero hooks: this module never registers hooks or alters agent behavior.

Conventions (see docs/OLLAMA.md): the bundled Ollama runtime serves on
``http://127.0.0.1:11434``; the native tags endpoint is ``GET /api/tags``
which returns ``{"models": [{"name": "qwen2.5:3b", ...}, ...]}``.
"""
from __future__ import annotations

import json
import time

# --- Constants ------------------------------------------------------------
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Model-name substrings that mark a pulled model as embedding-capable.
EMBED_HINTS = ("embed", "nomic", "bge")
# Chat models we prefer, in order (first match present in the local stack wins).
CHAT_PREFERRED = ["qwen2.5", "llama3.2", "gemma2", "mistral", "phi3"]

# Local search is always available (SQLite FTS5 codebase index, no network).
SEARCH_BACKEND = "fts5-local"
STACK_SEARCH = "codebase-index (fts5)"

CHECK_NAMES = ("ollama-reachable", "embeddings-model", "local-search", "offline-ready")


# --- Helpers --------------------------------------------------------------
def _first_embedding_model(models) -> str | None:
    """First model whose name matches an EMBED_HINTS substring, else None."""
    for name in models:
        for hint in EMBED_HINTS:
            if hint in name:
                return name
    return None


def _choose_chat_model(models, prefer=None) -> str | None:
    """prefer override first, then CHAT_PREFERRED order, then first model."""
    if prefer:
        for name in models:
            if prefer in name:
                return name
    for hint in CHAT_PREFERRED:
        for name in models:
            if hint in name:
                return name
    return models[0] if models else None


def _build_checks(reachable, error, models, emb_model, offline_ready) -> list[dict]:
    return [
        {
            "name": "ollama-reachable",
            "ok": bool(reachable),
            "detail": error or f"{len(models)} model(s) on {BASE_URL}",
        },
        {
            "name": "embeddings-model",
            "ok": emb_model is not None,
            "detail": emb_model or f"no embed-capable model (hints: {', '.join(EMBED_HINTS)})",
        },
        {
            "name": "local-search",
            "ok": True,
            "detail": f"backend {SEARCH_BACKEND} — codebase index, no network needed",
        },
        {
            "name": "offline-ready",
            "ok": bool(offline_ready),
            "detail": (
                "chat + embeddings + search all local"
                if offline_ready
                else "missing local chat or embeddings model"
            ),
        },
    ]


def _plan_value(plan, key, default=None):
    if isinstance(plan, dict):
        return plan.get(key, default)
    return default


# --- Public API -----------------------------------------------------------
def probe(host=OLLAMA_HOST, port=OLLAMA_PORT, timeout=1.5, urlopen=None) -> dict:
    """Probe the local Ollama stack and local search; never raises.

    GETs ``http://host:port/api/tags`` and parses
    ``{"models": [{"name": ...}, ...]}``. Any URLError / OSError (incl.
    socket.timeout) / malformed payload -> ``reachable: False`` with the
    error recorded — diagnostic, not fatal. ``urlopen`` defaults to
    ``urllib.request.urlopen`` (imported lazily to keep cold import fast).
    """
    import urllib.error  # deferred: keeps module import well under 90 ms
    if urlopen is None:
        import urllib.request
        urlopen = urllib.request.urlopen
    started = time.time()
    url = f"http://{host}:{port}/api/tags"
    models: list[str] = []
    error = None
    try:
        resp = urlopen(url, timeout=timeout)
        try:
            raw = resp.read()
        finally:
            close = getattr(resp, "close", None)
            if close:
                close()
        data = json.loads(raw)
        rows = data.get("models") if isinstance(data, dict) else None
        if rows is None:
            raise ValueError("response has no 'models' key")
        for row in rows:
            if isinstance(row, dict) and row.get("name"):
                models.append(str(row["name"]))
            elif isinstance(row, str):
                models.append(row)
    except (urllib.error.URLError, OSError, ValueError) as exc:  # incl. socket.timeout
        error = f"{type(exc).__name__}: {exc}"

    reachable = error is None
    emb_model = _first_embedding_model(models)
    offline_ready = reachable and emb_model is not None
    return {
        "ollama": {"reachable": reachable, "error": error, "models": models},
        "embeddings": {"available": emb_model is not None, "model": emb_model},
        "search": {"available": True, "backend": SEARCH_BACKEND},
        "offline_ready": offline_ready,
        "probe_ms": int((time.time() - started) * 1000),
        "checks": _build_checks(reachable, error, models, emb_model, offline_ready),
    }


def build_offline_stack(report: dict, prefer: str | None = None) -> dict:
    """Model plan from a probe report (pure function, no network).

    chat_model: ``prefer`` first if it matches a pulled model, else the
    first CHAT_PREFERRED match, else the first model, else None.
    ``offline_ready`` is False whenever no chat model is available.
    """
    ollama = report.get("ollama") or {}
    models = list(ollama.get("models") or [])
    chat = _choose_chat_model(models, prefer)
    return {
        "provider": "ollama",
        "base_url": BASE_URL,
        "chat_model": chat,
        "embeddings_model": _first_embedding_model(models),
        "search": STACK_SEARCH,
        "offline_ready": chat is not None,
        "model_count": len(models),
    }


def offline_prompt_for(task: str, plan: dict) -> str:
    """Deterministic offline system prompt from a stack plan (no network)."""
    chat = _plan_value(plan, "chat_model") or "a local model"
    emb = _plan_value(plan, "embeddings_model") or "none"
    search = _plan_value(plan, "search") or STACK_SEARCH
    return (
        f"OFFLINE MODE — no network, no API keys. Chat: {chat}. "
        f"Embeddings: {emb}. Search: {search}.\n"
        f"Task: {task}\n"
        "Use only the local stack above; never call remote services."
    )


def smoke_prompt(plan: dict) -> str:
    """One-line deterministic status string, e.g.

    ``offline-kit: 3 models, chat=qwen2.5:7b, embeddings=nomic-embed-text:latest, search=fts5-local``
    """
    if isinstance(plan, dict):
        n = plan.get("model_count")
        if n is None and isinstance(plan.get("ollama"), dict):
            n = len(plan["ollama"].get("models") or [])
        chat = _plan_value(plan, "chat_model") or "none"
        emb = _plan_value(plan, "embeddings_model") or "none"
    else:
        n, chat, emb = 0, "none", "none"
    return f"offline-kit: {int(n or 0)} models, chat={chat}, embeddings={emb}, search={SEARCH_BACKEND}"


def render_markdown(report: dict) -> str:
    """Markdown report containing every check plus the model inventory."""
    ollama = report.get("ollama") or {}
    models = ollama.get("models") or []
    emb = report.get("embeddings") or {}
    lines = [
        "# Offline Kit Report",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in report.get("checks") or []:
        status = "✅ ok" if check.get("ok") else "❌ fail"
        lines.append(f"| {check.get('name', '?')} | {status} | {check.get('detail', '')} |")
    lines.append("")
    lines.append("**models:** " + (", ".join(models) if models else "none"))
    lines.append("**embeddings model:** " + (emb.get("model") or "none"))
    lines.append("**offline_ready:** " + ("yes" if report.get("offline_ready") else "no"))
    return "\n".join(lines)
