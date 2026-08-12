"""model-router core — automatic per-task model routing over the omni-registry.

Picks the best free gateway model per task by reading REAL capability data:
omni-registry's capabilities.json (context_window, capabilities,
capability_sources, latency_ms, status) plus provider-pool's GATEWAY_MODELS
tags (fast/reasoning/vision/heavy/default) when available. Pure stdlib, zero
hooks, zero Hermes imports, zero network.

Routing tiers (TASK_TYPES), all rules read registry capabilities — nothing is
hand-maintained:
  quick     — fast answers: fast-tagged or latency_ms.median < threshold,
              lightest context (fastest TTFT), tools-capable.
  reasoning — debugging/analysis: thinking/always_thinking capability,
              prefers reasoning-tier tag, verified thinking source, biggest ctx.
  vision    — screenshots/OCR: image_in capability; prefers live-verified
              image_in (minimax-m3 is the only image_in spot-checked live).
  heavy     — max context: largest context_window among active models.
  default   — general workhorse: tools+thinking, default-tagged preferred.

Task type is auto-detected from the prompt text (keywords), precedence:
vision > reasoning > heavy > quick > default (a screenshot-summary is vision,
not quick).

Telemetry: record_call() appends to the SAME ledger format as plugins/cost-tracker
(calls table: ts/day/week/model/provider/tokens_in/tokens_out/est_cost/flagged)
extended with latency_ms + task_type. When cost-tracker's CostTracker class is
importable its est_cost() math is reused; otherwise an internal fallback rate
table is used. Zero hooks — telemetry is written by explicit command/core calls
(/route record, record_call), never wired to agent events.
"""
from __future__ import annotations

import datetime
import importlib.util
import os
import re
import sqlite3
import time

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

TASK_TYPES = ("quick", "reasoning", "vision", "heavy", "default")

# quick tier: a model is "fast" when latency_ms.median < this OR it is
# fast-tagged in provider-pool's GATEWAY_MODELS.
LATENCY_THRESHOLD_MS = 5000

TELEMETRY_DB_DIR = os.path.expanduser("~/.xomni-cost")
TELEMETRY_DB_PATH = os.path.join(TELEMETRY_DB_DIR, "route.db")

# Estimation fallback when cost-tracker is not importable (mirrors its
# FALLBACK_RATES): conservative USD per 1M tokens; every such row is flagged.
FALLBACK_RATES: tuple[float, float] = (0.50, 1.50)

# The 25 verified-free gateway models cost $0 — logged honestly, never flagged
# (same pricing contract as cost-tracker's COST_TABLE).
FREE_MODELS: frozenset = frozenset({
    "deepseek-v4-flash", "deepseek-v4-pro", "kimi-k3", "kimi-k2.7-code",
    "kimi-k2.6", "kimi-k2.5", "glm-5.2", "glm-5.1", "glm-5", "qwen3.8-max",
    "qwen3.7-max", "qwen3.7-plus", "qwen3.6-plus", "qwen3.5-plus",
    "minimax-m3", "minimax-m2.7", "minimax-m2.5", "mimo-v2-pro",
    "mimo-v2-omni", "mimo-v2.5-pro", "mimo-v2.5", "hy3", "hy3-preview",
    "gpt-5.6-luna", "grok-4.5",
})

# Deterministic picks when the omni-registry is unavailable (empty registry or
# import failure). Self-consistent with the real picks so the fallback is
# indistinguishable in shape.
FALLBACK_MODELS: dict[str, str] = {
    "quick": "minimax-m2.5",
    "reasoning": "deepseek-v4-pro",
    "vision": "minimax-m3",
    "heavy": "gpt-5.6-luna",
    "default": "deepseek-v4-flash",
}

# Keyword auto-detection. Prefix-anchored word matches (re: \b<kw>) so "fail"
# catches "failed/failure" and "analy" catches "analyze/analysis" without
# substring false positives ("fix" won't match "prefix").
KEYWORDS: dict[str, tuple[str, ...]] = {
    "vision": (
        "screenshot", "image", "ocr", "vision", "picture", "photo", "diagram",
        "chart", "scan", "screen", "graph", "visual", "thumbnail", "render",
        "see", "look at", "ui",
    ),
    "reasoning": (
        "debug", "why", "error", "bug", "traceback", "exception", "crash",
        "failed", "fail", "fix", "root cause", "backtest", "analy", "reason",
        "incorrect", "wrong", "investigate", "diagnos", "explain", "regression",
        "not working", "malfunction", "unexpected", "issue",
    ),
    "heavy": (
        "long", "big", "huge", "large", "entire", "whole", "repo", "codebase",
        "repository", "full", "complete", "100k", "1m", "context", "batch",
        "document", "corpus", "massive", "all files", "entire project",
    ),
    "quick": (
        "summarize", "summary", "translate", "quick", "tl;dr", "tldr", "short",
        "brief", "reply", "rename", "format", "paraphrase", "draft", "email",
        "title", "heading", "fast",
    ),
}

DETECT_ORDER = ("vision", "reasoning", "heavy", "quick")

# Ledger schema — cost-tracker's `calls` table, extended with latency_ms and
# task_type (the two fields /route telemetry renders).
LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    day        TEXT NOT NULL,
    week       TEXT NOT NULL,
    model      TEXT NOT NULL,
    provider   TEXT NOT NULL DEFAULT '',
    tokens_in  INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    est_cost   REAL NOT NULL DEFAULT 0.0,
    flagged    INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    task_type  TEXT NOT NULL DEFAULT ''
);
"""

# ---------------------------------------------------------------------------
# sibling plugin loading (importlib, absolute paths — never sys.path games)
# ---------------------------------------------------------------------------

_PLUGINS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_sibling(rel_path: str, module_name: str):
    """Load a sibling plugin's core.py as an isolated module (stdlib only).

    Returns None on any failure (missing plugin, syntax error, ...) so callers
    degrade gracefully — routing must work even when omni-registry or
    cost-tracker is absent.
    """
    path = os.path.join(_PLUGINS_DIR, rel_path)
    if not os.path.isfile(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys_modules = __import__("sys").modules
        sys_modules[module_name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _omni_registry():
    """omni-registry.core module or None."""
    return _load_sibling(
        os.path.join("omni-registry", "core.py"), "omni_registry_core")


def _provider_pool():
    """provider-pool.core module or None (source of GATEWAY_MODELS tags)."""
    return _load_sibling(
        os.path.join("provider-pool", "core.py"), "provider_pool_core")


def _cost_tracker():
    """cost-tracker.core module or None (source of the CostTracker class)."""
    return _load_sibling(
        os.path.join("cost-tracker", "core.py"), "cost_tracker_core")


def _pool_tags() -> dict[str, set]:
    """{model_id: set(tags)} from provider-pool GATEWAY_MODELS ({} if absent)."""
    pool = _provider_pool()
    if pool is None or not getattr(pool, "GATEWAY_MODELS", None):
        return {}
    out: dict[str, set] = {}
    for m in pool.GATEWAY_MODELS:
        if isinstance(m, dict) and m.get("id"):
            out[m["id"]] = set(m.get("tags") or [])
    return out


# ---------------------------------------------------------------------------
# task type detection
# ---------------------------------------------------------------------------

def detect_task_type(prompt: str) -> tuple[str, list[str]]:
    """Auto-detect (task_type, matched_keywords) from prompt text.

    Precedence: vision > reasoning > heavy > quick > default — a "summarize
    this screenshot" is a vision task (visual input required), not a quick one.
    """
    text = (prompt or "").lower()
    for ttype in DETECT_ORDER:
        hits = []
        for kw in KEYWORDS[ttype]:
            if re.search(r"\b" + re.escape(kw), text):
                hits.append(kw)
        if hits:
            return ttype, hits
    return "default", []


# ---------------------------------------------------------------------------
# registry helpers
# ---------------------------------------------------------------------------

def _active(registry: dict) -> list[dict]:
    return [r for r in registry.values() if r.get("status") == "active"]


def _latency_ms(rec: dict) -> int | None:
    return (rec.get("latency_ms") or {}).get("median")


def _ctx(rec: dict) -> int:
    return (rec.get("context_window") or {}).get("value") or 0


def _has(rec: dict, cap: str) -> bool:
    return cap in rec.get("capabilities", [])


def _cap_src(rec: dict, cap: str) -> str | None:
    return (rec.get("capability_sources") or {}).get(cap)


def _provider_of(rec: dict) -> str:
    return rec.get("provider", "")


def _load_registry() -> dict:
    """Real omni-registry records {model_id: record} ({} if unavailable)."""
    omni = _omni_registry()
    if omni is None or not hasattr(omni, "registry_load"):
        return {}
    try:
        return omni.registry_load()
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------

def route(task_hint: str, registry: dict | None = None) -> dict:
    """Route a task prompt to the best free model over real registry capabilities.

    Returns {model, task_type, keywords, reason, alternatives,
    config_command, provider, provider_hint, registry_source}. With
    registry=None the real omni-registry is loaded (and provider-pool tags
    enrich quick/reasoning/default tiers); with an empty dict or an
    unavailable registry the FALLBACK_MODELS tier table is used.
    """
    task_type, keywords = detect_task_type(task_hint)

    if registry is None:
        registry = _load_registry()

    active = _active(registry)
    if not active:
        return _fallback_route(task_type, keywords)

    tags = _pool_tags()

    if task_type == "quick":
        cands = [
            r for r in active
            if _has(r, "tools")
            and ("fast" in tags.get(r["id"], set())
                 or (_latency_ms(r) is not None
                     and _latency_ms(r) < LATENCY_THRESHOLD_MS))
        ]
        cands.sort(key=lambda r: (
            0 if "fast" in tags.get(r["id"], set()) else 1,
            _latency_ms(r) or 0, _ctx(r), r["id"]))
        why = ("fast-tier: fast-tagged or latency < %dms, lightest context "
               "(fastest first token)" % LATENCY_THRESHOLD_MS)

    elif task_type == "reasoning":
        cands = [
            r for r in active
            if _has(r, "thinking") or _has(r, "always_thinking")
        ]
        cands.sort(key=lambda r: (
            0 if "reasoning" in tags.get(r["id"], set()) else 1,
            0 if _cap_src(r, "thinking") == "verified" else 1,
            0 if _has(r, "always_thinking") else 1,
            -_ctx(r), r["id"]))
        why = ("reasoning-tier: thinking/always_thinking capability, "
               "prefers reasoning-tagged + verified thinking, biggest context")

    elif task_type == "vision":
        cands = [r for r in active if _has(r, "image_in")]
        cands.sort(key=lambda r: (
            0 if _cap_src(r, "image_in") == "verified" else 1,
            -_ctx(r), r["id"]))
        why = ("vision-tier: image_in capability required; prefers the "
               "live-verified image_in source (spot-checked, not spec)")

    elif task_type == "heavy":
        cands = sorted(active, key=lambda r: (-_ctx(r), r["id"]))
        why = "heavy-tier: largest context_window among active models"

    else:  # default
        cands = [r for r in active if _has(r, "tools") and _has(r, "thinking")]
        cands.sort(key=lambda r: (
            0 if "default" in tags.get(r["id"], set()) else 1,
            0 if _cap_src(r, "tools") == "verified" else 1,
            _latency_ms(r) or 0, _ctx(r), r["id"]))
        why = ("default-tier: tools+thinking general workhorse, prefers the "
               "default-tagged gateway model")

    if not cands:
        return _fallback_route(task_type, keywords)

    pick = cands[0]
    model = pick["id"]
    provider = _provider_of(pick)
    alternatives = [
        {"model": r["id"], "provider": _provider_of(r)}
        for r in cands[1:4]
    ]
    reason = (
        f"task '{task_type}'"
        + (f" (keywords: {', '.join(keywords)})" if keywords else " (no keywords)")
        + f" -> {model}: {why}; ctx={_ctx(pick):,}, "
        f"latency={_latency_ms(pick) or '?'}ms, provider={provider}"
    )
    return {
        "model": model,
        "task_type": task_type,
        "keywords": keywords,
        "reason": reason,
        "alternatives": alternatives,
        "config_command": f"hermes config set model {model}",
        "provider": provider,
        "provider_hint": (
            f"{provider} (free gateway channel — verified free 2026-08-10)"),
        "registry_source": "omni-registry + provider-pool tags",
    }


def _fallback_route(task_type: str, keywords: list[str]) -> dict:
    model = FALLBACK_MODELS.get(task_type, FALLBACK_MODELS["default"])
    reason = (
        f"task '{task_type}'"
        + (f" (keywords: {', '.join(keywords)})" if keywords else "")
        + f" -> {model}: omni-registry unavailable — deterministic fallback "
          "tier table (same picks as the real registry)"
    )
    return {
        "model": model,
        "task_type": task_type,
        "keywords": keywords,
        "reason": reason,
        "alternatives": [
            {"model": m, "provider": "opencode-zen"}
            for t, m in FALLBACK_MODELS.items() if t != task_type
        ],
        "config_command": f"hermes config set model {model}",
        "provider": "opencode-zen",
        "provider_hint": "opencode-zen (free gateway channel — fallback table)",
        "registry_source": "fallback",
    }


def route_text(res: dict) -> str:
    """Render a route() result for /route <prompt> (model + reason + switch cmd)."""
    alts = ", ".join(
        f"{a['model']} ({a['provider']})" for a in res.get("alternatives", [])
    ) or "(none)"
    return "\n".join([
        f"/route → task: {res['task_type']}"
        + (f"  (keywords: {', '.join(res['keywords'])})" if res.get("keywords") else ""),
        f"  model:        {res['model']}",
        f"  provider:     {res['provider_hint']}",
        f"  why:          {res['reason'].split(' -> ', 1)[-1]}",
        f"  switch:       {res['config_command']}",
        f"  alternatives: {alts}",
        f"  source:       {res['registry_source']}",
    ])


# ---------------------------------------------------------------------------
# telemetry — cost-tracker-compatible ledger (+ latency_ms, task_type)
# ---------------------------------------------------------------------------

def _day_of(ts: float) -> str:
    return datetime.date.fromtimestamp(ts).isoformat()


def _week_of(ts: float) -> str:
    # %G-W%V (ISO week) — datetime.strftime implements it on all platforms,
    # unlike time.strftime's %V which is missing on Windows/MSVC.
    return datetime.date.fromtimestamp(ts).strftime("%G-W%V")


class RouteTelemetry:
    """Sqlite ledger for routed calls — same shape as cost-tracker's `calls`
    table, extended with latency_ms + task_type.

    Cost estimation REUSES cost-tracker's CostTracker.est_cost() when that
    plugin is importable (honest-math consistency: the same numbers /cost and
    /route report agree); otherwise the internal FREE_MODELS/FALLBACK_RATES
    table is used and rows are flagged.
    """

    def __init__(self, db_path: str = TELEMETRY_DB_PATH):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(LEDGER_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    # ---- cost estimation (cost-tracker reuse with fallback) ----

    def est_cost(self, model: str, tokens_in: int = 0,
                 tokens_out: int = 0) -> tuple[float, bool]:
        """(est_cost_usd, flagged) — reuses cost-tracker when importable."""
        ct = _cost_tracker()
        if ct is not None and hasattr(ct, "CostTracker"):
            try:
                return ct.CostTracker().est_cost(model, tokens_in, tokens_out)
            except Exception:
                pass  # fall through to the internal table
        mid = model.strip().lower()
        if mid in FREE_MODELS:
            return 0.0, False
        rates = FALLBACK_RATES
        cost = (rates[0] * max(0, int(tokens_in))
                + rates[1] * max(0, int(tokens_out))) / 1_000_000.0
        return cost, True

    # ---- ledger writes ----

    def record_call(self, model: str, latency_ms: int = 0, est_cost: float | None = None,
                    tokens_in: int = 0, tokens_out: int = 0, task_type: str = "",
                    provider: str = "", ts: float | None = None) -> dict:
        """Append one routed call to the ledger. est_cost=None -> estimated
        from tokens (cost-tracker math when available). Returns the row."""
        now = ts if ts is not None else time.time()
        if est_cost is None:
            est_cost, flagged = self.est_cost(model, tokens_in, tokens_out)
        else:
            flagged = False
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                "INSERT INTO calls (ts, day, week, model, provider, tokens_in, "
                "tokens_out, est_cost, flagged, latency_ms, task_type) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (now, _day_of(now), _week_of(now), model.strip(), provider,
                 int(tokens_in), int(tokens_out), float(est_cost),
                 1 if flagged else 0, int(latency_ms), task_type))
            conn.commit()
        finally:
            conn.close()
        return {"logged": True, "blocked": False, "id": cur.lastrowid,
                "model": model, "provider": provider, "est_cost": float(est_cost),
                "flagged": flagged, "latency_ms": int(latency_ms),
                "task_type": task_type, "task": task_type,
                "day": _day_of(now), "week": _week_of(now)}

    # ---- ledger reads ----

    def recent_calls(self, limit: int = 10) -> list[dict]:
        """Most recent routed calls (newest first), cost-tracker row shape +
        latency_ms/task_type."""
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT id, ts, day, model, provider, tokens_in, tokens_out, "
                "est_cost, flagged, latency_ms, task_type "
                "FROM calls ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        finally:
            conn.close()
        return [{"id": r[0], "ts": r[1], "day": r[2], "model": r[3],
                 "provider": r[4], "tokens_in": r[5], "tokens_out": r[6],
                 "est_cost": r[7], "flagged": bool(r[8]),
                 "latency_ms": r[9], "task_type": r[10]} for r in rows]

    def totals(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(est_cost),0), "
                "COALESCE(AVG(latency_ms),0) FROM calls").fetchone()
        finally:
            conn.close()
        return {"calls": int(row[0]), "est_cost": float(row[1]),
                "avg_latency_ms": float(row[2])}

    # ---- rendering ----

    def telemetry_text(self, limit: int = 10) -> str:
        """/route telemetry — last N routed calls (model, ms, $, task type)."""
        rows = self.recent_calls(limit)
        tot = self.totals()
        lines = [
            "model-router telemetry — last %d routed calls (ledger: %s)"
            % (min(limit, len(rows)) if rows else 0,
               os.path.normpath(self.db_path)),
            "  %-22s %8s %10s  %s" % ("model", "ms", "$", "task type"),
        ]
        if not rows:
            lines.append("  (no routed calls recorded yet — run "
                         "'/route record <model> <latency_ms> [est_cost] [task_type]')")
        for r in rows:
            lines.append("  %-22s %8d %10.6f  %s"
                         % (r["model"][:22], r["latency_ms"], r["est_cost"],
                            r["task_type"] or "-"))
        lines.append("  totals: %d calls, $%.6f est, avg %dms"
                     % (tot["calls"], tot["est_cost"], tot["avg_latency_ms"]))
        return "\n".join(lines)


def record_call(model: str, latency_ms: int = 0, est_cost: float | None = None,
                tokens_in: int = 0, tokens_out: int = 0, task_type: str = "",
                provider: str = "", ts: float | None = None) -> dict:
    """Module-level convenience: record one routed call (default ledger)."""
    return RouteTelemetry().record_call(
        model, latency_ms=latency_ms, est_cost=est_cost, tokens_in=tokens_in,
        tokens_out=tokens_out, task_type=task_type, provider=provider, ts=ts)


def recent_calls(limit: int = 10) -> list[dict]:
    return RouteTelemetry().recent_calls(limit)


def route_telemetry_text(limit: int = 10) -> str:
    """/route telemetry — renders the last 10 routed calls from the ledger.

    Auto-telemetry: suggestions recorded in memory by the pre_llm_call hook
    are flushed into the ledger first, so the report always includes every
    classified call (not just explicit /route record entries).
    """
    flush_pending_telemetry()
    return RouteTelemetry().telemetry_text(limit)


# ---------------------------------------------------------------------------
# automatic routing hook support — deterministic, in-memory, ZERO I/O
# ---------------------------------------------------------------------------
#
# The pre_llm_call hook (wired in plugins/model-router/__init__.py) classifies
# the user prompt with KEYWORDS ONLY and records the suggestion IN MEMORY. It
# never calls the model API, never touches the network, never spawns a
# process, and never writes to disk — that keeps the hot path under 1ms and
# satisfies ci_gate's FORBIDDEN_IN_HOOK_RE (no .complete( / requests. /
# subprocess in hook handlers). The ledger write is deferred to the next
# command call (flush_pending_telemetry), which is allowed to do I/O.

# config key: model-router.auto_route (read by __init__._auto_route_enabled)
AUTO_ROUTE_DEFAULT = True

_PENDING_TELEMETRY: list[dict] = []
_LAST_SUGGESTION: dict | None = None


def classify_suggestion(prompt: str,
                        configured_model: str | None = None) -> dict:
    """Deterministic keyword-only classification + tier-table suggestion.

    Pure CPU: detect_task_type() (regex over KEYWORDS) + a FALLBACK_MODELS
    dict lookup. No registry load, no I/O, no LLM — safe for the pre_llm_call
    hot path. The tier table is the same deterministic pick set /route falls
    back to; /route additionally consults the live omni-registry (command
    path only). An unknown configured model counts as differing (suggest).
    """
    task_type, keywords = detect_task_type(prompt)
    suggested = FALLBACK_MODELS.get(task_type, FALLBACK_MODELS["default"])
    configured = (configured_model or "").strip().lower()
    differs = (not configured) or configured != suggested
    return {
        "task_type": task_type,
        "keywords": keywords,
        "suggested_model": suggested,
        "configured_model": configured or None,
        "differs": differs,
        "action": "switch" if differs else "keep",
    }


def record_suggestion(sug: dict) -> None:
    """Record one classification IN MEMORY (pending telemetry + last hint).

    ZERO I/O — the ledger write is deferred to flush_pending_telemetry() so
    the hook never touches disk and stays well under 1ms.
    """
    global _LAST_SUGGESTION
    _LAST_SUGGESTION = dict(sug)
    _PENDING_TELEMETRY.append({
        "model": sug["suggested_model"],
        "task_type": sug["task_type"],
        "configured_model": sug.get("configured_model"),
        "differs": bool(sug.get("differs")),
        "action": sug.get("action", "keep"),
        "ts": time.time(),
    })


def last_suggestion() -> dict | None:
    """Last classification recorded by the hook (None before the first call)."""
    return _LAST_SUGGESTION


def flush_pending_telemetry() -> int:
    """Write pending hook classifications into the cost-tracker ledger.

    Command-path only (never called from the hook — the hook is I/O-free):
    drains the in-memory queue into route.db via RouteTelemetry.record_call
    (cost-tracker math when available). Returns the number of rows written.
    On failure the pending rows are restored and the error propagates
    (fail-loud, no data loss).
    """
    if not _PENDING_TELEMETRY:
        return 0
    pending = list(_PENDING_TELEMETRY)
    _PENDING_TELEMETRY.clear()
    try:
        tel = RouteTelemetry()
        for row in pending:
            tel.record_call(
                row["model"], latency_ms=0, est_cost=None,
                task_type=row["task_type"], provider="", ts=row["ts"])
    except Exception:
        _PENDING_TELEMETRY[:0] = pending  # restore on failure
        raise
    return len(pending)
