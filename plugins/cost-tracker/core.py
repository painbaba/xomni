"""cost-tracker — the honest-math ledger for XOMNI (Monetization V2, Phase 1).

A local, sqlite-backed model-cost ledger with per-day/per-week budget caps and
an optional hard-stop. Pure stdlib (sqlite3), no Hermes imports, no hooks —
the plugin registers ZERO hooks (new-plugin rule); ``cost_track`` is called
explicitly by provider-pool or any agent caller, and ``/cost`` reads the
ledger on demand.

Design anchors (docs/MONETIZATION-V2.md §4):
  * Cost volatility is structural (OpenRouter: 406 models, 16 :free) → budget
    caps are a retention feature, not a commodity.
  * Free forever: the ledger is the *proof* for the "honest-latency + budget"
    story that sells sponsorship — devs see exactly what the agent costs.
  * Privacy: everything stays local (~/.xomni-cost/costs.db). No telemetry.

The ledger is append-only: rows are never mutated, only read (report/top) or
summed (budget status). The 25 verified-free gateway models are priced $0 so
their usage is logged honestly without inventing cost.
"""
from __future__ import annotations

import datetime
import json
import os
import sqlite3
import time
import csv

DB_DIR = os.path.expanduser("~/.xomni-cost")
DB_PATH = os.path.join(DB_DIR, "costs.db")

# Public list prices, USD per 1M tokens (input, output) — order-of-magnitude
# estimates for the ledger. The 25 gateway models (provider-pool
# GATEWAY_MODELS, verified free 2026-08-10) cost $0; paid models use widely
# published list rates. Unknown models fall back to FALLBACK_RATES and are
# flagged in the log entry.
COST_TABLE: dict[str, tuple[float, float]] = {
    # --- 25 verified-free opencode-zen gateway models (provider-pool) ---
    "deepseek-v4-flash": (0.0, 0.0),
    "deepseek-v4-pro": (0.0, 0.0),
    "kimi-k3": (0.0, 0.0),
    "kimi-k2.7-code": (0.0, 0.0),
    "kimi-k2.6": (0.0, 0.0),
    "kimi-k2.5": (0.0, 0.0),
    "glm-5.2": (0.0, 0.0),
    "glm-5.1": (0.0, 0.0),
    "glm-5": (0.0, 0.0),
    "qwen3.8-max": (0.0, 0.0),
    "qwen3.7-max": (0.0, 0.0),
    "qwen3.7-plus": (0.0, 0.0),
    "qwen3.6-plus": (0.0, 0.0),
    "qwen3.5-plus": (0.0, 0.0),
    "minimax-m3": (0.0, 0.0),
    "minimax-m2.7": (0.0, 0.0),
    "minimax-m2.5": (0.0, 0.0),
    "mimo-v2-pro": (0.0, 0.0),
    "mimo-v2-omni": (0.0, 0.0),
    "mimo-v2.5-pro": (0.0, 0.0),
    "mimo-v2.5": (0.0, 0.0),
    "hy3": (0.0, 0.0),
    "hy3-preview": (0.0, 0.0),
    "gpt-5.6-luna": (0.0, 0.0),
    "grok-4.5": (0.0, 0.0),
    # --- paid models (public list prices, USD/1M tokens) ---
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-opus-4": (15.00, 75.00),
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-pro": (1.25, 10.00),
    "llama-3.3-70b": (0.59, 0.79),
    "mistral-large": (2.00, 6.00),
    "o3-mini": (1.10, 4.40),
    "command-r-plus": (2.50, 10.00),
}

# Conservative estimate for unknown models (USD/1M tokens); flagged per row.
FALLBACK_RATES: tuple[float, float] = (0.50, 1.50)

# --- spend caps (U-CORE-3: universal telemetry) ---------------------------
# Rolling-window spend caps. Each cap lives in the ledger config table as
# cap_<period> = JSON {"limit_usd": ..., "action": "warn"|"park"}.
#   action warn -> warn text at >=80% of the limit (never blocks).
#   action park -> warn at >=80%; at >=100% the HEAVY TIER is parked (see
#   parked_models()): cost consumers should stop routing to heavy models.
# Windows are ROLLING (ts - window .. ts), summed from the ledger on demand;
# checking a cap NEVER writes to the ledger (pure read).
CAP_PERIODS: dict[str, float] = {
    "5h": 5 * 3600.0,
    "1d": 24 * 3600.0,
    "7d": 7 * 24 * 3600.0,
    "30d": 30 * 24 * 3600.0,
}
WARN_PCT = 80.0    # >= 80% of a cap limit -> warn text
PARK_PCT = 100.0   # >= 100% of a park cap -> heavy tier parked

# Heavy tier = paid models priced >= this (USD per 1M input tokens), derived
# from COST_TABLE at call time so /cost sync re-pricing stays authoritative.
# Free gateway models are never heavy. Parking the heavy tier on an exhausted
# period cap is the cost-control semantic: cut the expensive models first.
HEAVY_TIER_INPUT_RATE_USD = 1.0


def heavy_tier(rates: dict | None = None) -> list[str]:
    """Sorted model ids in the heavy tier (input list price >= $1/1M tokens)."""
    table = rates if rates is not None else COST_TABLE
    return sorted(
        slug for slug, (inp, _out) in table.items()
        if inp >= HEAVY_TIER_INPUT_RATE_USD
    )

# Pinned models.dev snapshot (single source of truth for model costs) — the
# omni-registry plugin fetches and pins it at plugins/omni-registry/data/
# models.snapshot.json. Override per-run with $XOMNI_MODELS_SNAPSHOT.
DEFAULT_SNAPSHOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "omni-registry", "data", "models.snapshot.json",
)


def _extract_pricing(rec: dict) -> tuple[float, float] | None:
    """Pull (input, output) USD/1M-token prices from one snapshot record.

    Accepts the omni-registry shape (``cost_per_1m: {input, output}``), the
    models.dev api.json shape (``pricing: {prompt, completion}``), or flat
    ``input``/``output`` keys. Returns None when the record carries no
    pricing — snapshot models then default to $0 (the pinned snapshot covers
    the verified-free gateway set).
    """
    for container, in_key, out_key in (
        ("cost_per_1m", "input", "output"),
        ("pricing", "prompt", "completion"),
    ):
        block = rec.get(container)
        if isinstance(block, dict) and in_key in block and out_key in block:
            try:
                return float(block[in_key]), float(block[out_key])
            except (TypeError, ValueError):
                return None
    if "input" in rec and "output" in rec:
        try:
            return float(rec["input"]), float(rec["output"])
        except (TypeError, ValueError):
            return None
    return None


def sync_costs_from_snapshot(snapshot_path: str | None = None) -> dict:
    """Re-sync the model-cost table from the omni-registry pinned snapshot.

    Single source of truth: the pinned snapshot at
    ``plugins/omni-registry/data/models.snapshot.json`` (repo-relative to this
    file), overridable with ``$XOMNI_MODELS_SNAPSHOT`` or ``snapshot_path``.
    Snapshot pricing fields are mapped into COST_TABLE's (input, output)
    USD/1M format; snapshot models without pricing are $0 (verified-free
    gateway set). The result is a *merge* over the built-in table, so paid
    models the snapshot does not cover keep their public list prices.

    Never raises: on a missing/unparseable snapshot the built-in hardcoded
    table is returned with ``source="fallback"`` so callers keep operating on
    last-known data and can surface the warning themselves.

    Returns ``{"models": <count>, "table": <dict>, "source": "snapshot"|"fallback"}``
    plus ``path`` and (on fallback) ``reason``.
    """
    path = snapshot_path or os.environ.get("XOMNI_MODELS_SNAPSHOT") or DEFAULT_SNAPSHOT
    try:
        with open(path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
        models = data.get("models") if isinstance(data, dict) else None
        if not isinstance(models, dict) or not models:
            raise ValueError("snapshot has no 'models' mapping")
        table = dict(COST_TABLE)
        for slug, rec in models.items():
            if not isinstance(rec, dict):
                continue
            rates = _extract_pricing(rec) or (0.0, 0.0)
            table[str(slug).strip().lower()] = (float(rates[0]), float(rates[1]))
        return {"models": len(models), "table": table, "source": "snapshot",
                "path": os.path.abspath(path)}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return {"models": 0, "table": dict(COST_TABLE), "source": "fallback",
                "reason": str(exc), "path": os.path.abspath(path)}


# Warn-only by default: the agent never silently stops working. hard_stop is
# opt-in (/cost budget hard on) for users who want a true budget hard-stop.
DEFAULT_CONFIG = {
    "daily_cap": 5.0,     # USD, 0 = no cap
    "weekly_cap": 25.0,   # USD, 0 = no cap
    "hard_stop": False,   # True = block new calls when a cap is exceeded
}

SCHEMA = """
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
    flagged    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _day_of(ts: float) -> str:
    return datetime.date.fromtimestamp(ts).isoformat()


def _week_of(ts: float) -> str:
    # %G-W%V (ISO week) is implemented by datetime.strftime on all platforms,
    # unlike time.strftime's %V which is missing on Windows/MSVC.
    return datetime.date.fromtimestamp(ts).strftime("%G-W%V")


class CostTracker:
    """Sqlite-backed cost ledger with per-day/per-week budget caps."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_schema()
        self._seed_config()

    # ---- low-level sqlite helpers (connection per op: simple + thread-safe) ----

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur
        finally:
            conn.close()

    def _query(self, sql: str, params: tuple = ()) -> list[tuple]:
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _seed_config(self) -> None:
        for key, value in DEFAULT_CONFIG.items():
            self._execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                (key, str(value)),
            )

    # ---- config / budget caps ----

    def _get_config(self) -> dict:
        rows = self._query("SELECT key, value FROM config")
        out = dict(DEFAULT_CONFIG)
        for key, value in rows:
            if key == "hard_stop":
                out[key] = str(value).strip().lower() in ("1", "true", "yes", "on")
            elif key.startswith("cap_") or key.startswith("mcap_"):
                # spend-cap rows are JSON blobs (U-CORE-3)
                try:
                    out[key] = json.loads(value)
                except ValueError:
                    out[key] = value
            else:
                try:
                    out[key] = float(value)
                except ValueError:
                    out[key] = value
        return out

    def set_budget(self, daily_cap: float | None = None, weekly_cap: float | None = None,
                   hard_stop: bool | None = None) -> dict:
        """Set budget caps (0 = no cap) and/or toggle the hard-stop. Persisted."""
        if daily_cap is not None:
            self._execute("INSERT OR REPLACE INTO config (key, value) VALUES ('daily_cap', ?)",
                          (str(float(daily_cap)),))
        if weekly_cap is not None:
            self._execute("INSERT OR REPLACE INTO config (key, value) VALUES ('weekly_cap', ?)",
                          (str(float(weekly_cap)),))
        if hard_stop is not None:
            self._execute("INSERT OR REPLACE INTO config (key, value) VALUES ('hard_stop', ?)",
                          ("1" if hard_stop else "0",))
        return self.budget_status()

    # ---- cost math ----

    def est_cost(self, model: str, tokens_in: int = 0, tokens_out: int = 0) -> tuple[float, bool]:
        """Estimated USD cost of a call from the cost table.

        Returns (cost, flagged): flagged=True when the model is not in the
        table and fallback rates were used (honest-math: estimates are marked).
        """
        rates = COST_TABLE.get(model.strip().lower())
        flagged = rates is None
        if rates is None:
            rates = FALLBACK_RATES
        cost = (rates[0] * max(0, int(tokens_in)) + rates[1] * max(0, int(tokens_out))) / 1_000_000.0
        return cost, flagged

    # ---- ledger writes ----

    def log_call(self, model: str, provider: str = "", tokens_in: int = 0, tokens_out: int = 0,
                 task: str = "", ts: float | None = None) -> dict:
        """Append one model call to the ledger.

        Honoring a hard-stop cap: when hard_stop is on AND a cap is exceeded,
        the call is NOT logged and ``blocked=True`` is returned — the caller
        (provider-pool routing) should pick a cheaper model or refuse.
        Warn-only mode (hard_stop off) always logs and reports the overage.
        """
        now = ts if ts is not None else time.time()
        status = self.budget_status(ts=now)
        if not status["allowed"]:
            return {"logged": False, "blocked": True, "reason": status["reason"],
                    "est_cost": 0.0, "day": _day_of(now), "week": _week_of(now)}
        cost, flagged = self.est_cost(model, tokens_in, tokens_out)
        cur = self._execute(
            "INSERT INTO calls (ts, day, week, model, provider, tokens_in, tokens_out, est_cost, flagged) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (now, _day_of(now), _week_of(now), model.strip(), provider, int(tokens_in),
             int(tokens_out), cost, 1 if flagged else 0),
        )
        return {"logged": True, "blocked": False, "id": cur.lastrowid,
                "model": model, "provider": provider, "est_cost": cost,
                "flagged": flagged, "task": task,
                "day": _day_of(now), "week": _week_of(now)}

    # ---- ledger reads ----

    def totals(self, ts: float | None = None) -> dict:
        """All-time (or single-day/week) totals: calls, tokens, est cost."""
        if ts is not None:
            day = _day_of(ts)
            rows = self._query(
                "SELECT COUNT(*), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), "
                "COALESCE(SUM(est_cost),0) FROM calls WHERE day = ?", (day,))
            label = f"day {day}"
        else:
            rows = self._query(
                "SELECT COUNT(*), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), "
                "COALESCE(SUM(est_cost),0) FROM calls")
            label = "all-time"
        n, tin, tout, cost = rows[0]
        return {"period": label, "calls": int(n), "tokens_in": int(tin),
                "tokens_out": int(tout), "est_cost": float(cost)}

    def spent(self, period: str = "day", ts: float | None = None) -> float:
        """USD spent in the current day or week (local time)."""
        now = ts if ts is not None else time.time()
        if period == "week":
            rows = self._query("SELECT COALESCE(SUM(est_cost),0) FROM calls WHERE week = ?",
                               (_week_of(now),))
        else:
            rows = self._query("SELECT COALESCE(SUM(est_cost),0) FROM calls WHERE day = ?",
                               (_day_of(now),))
        return float(rows[0][0])

    def budget_status(self, ts: float | None = None) -> dict:
        """Spent vs caps for day and week; ``allowed`` is False only when the
        hard-stop is on and a cap is exceeded."""
        now = ts if ts is not None else time.time()
        cfg = self._get_config()
        day_spent = self.spent("day", now)
        week_spent = self.spent("week", now)
        daily_cap = float(cfg.get("daily_cap", 0.0))
        weekly_cap = float(cfg.get("weekly_cap", 0.0))
        day_over = daily_cap > 0 and day_spent >= daily_cap
        week_over = weekly_cap > 0 and week_spent >= weekly_cap
        hard_stop = bool(cfg.get("hard_stop", False))
        blocked = hard_stop and (day_over or week_over)
        reason = ""
        if blocked:
            reasons = []
            if day_over:
                reasons.append(f"daily cap ${daily_cap:.4f} reached (${day_spent:.4f})")
            if week_over:
                reasons.append(f"weekly cap ${weekly_cap:.4f} reached (${week_spent:.4f})")
            reason = "hard-stop: " + "; ".join(reasons)
        return {
            "day_spent": day_spent, "week_spent": week_spent,
            "daily_cap": daily_cap, "weekly_cap": weekly_cap,
            "day_remaining": max(0.0, daily_cap - day_spent) if daily_cap > 0 else None,
            "week_remaining": max(0.0, weekly_cap - week_spent) if weekly_cap > 0 else None,
            "hard_stop": hard_stop, "blocked": blocked, "reason": reason,
            "allowed": not blocked,
        }

    def check_budget(self, ts: float | None = None) -> dict:
        """Pre-call gate used by cost_track: cheap, read-only."""
        return self.budget_status(ts=ts)

    # ---- spend caps (U-CORE-3) ----

    def get_spend_caps(self) -> dict:
        """Period spend caps from the ledger config table (pure read).

        Returns {period: {"limit_usd": float, "action": "warn"|"park"}} for
        every cap currently stored (periods without a cap are absent).
        """
        cfg = self._get_config()
        caps: dict[str, dict] = {}
        for key, val in cfg.items():
            if key.startswith("cap_") and isinstance(val, dict):
                period = key[len("cap_"):]
                try:
                    limit = float(val.get("limit_usd", 0.0))
                except (TypeError, ValueError):
                    limit = 0.0
                caps[period] = {
                    "limit_usd": limit,
                    "action": str(val.get("action", "warn")).lower(),
                }
        return caps

    def set_spend_cap(self, period: str, limit_usd: float, action: str = "warn") -> dict:
        """Set/replace a rolling spend cap. period in CAP_PERIODS (5h|1d|7d|30d),
        action 'warn' (never blocks) or 'park' (heavy tier parked at 100%)."""
        period = str(period).strip().lower()
        if period not in CAP_PERIODS:
            raise ValueError("period must be one of: %s" % ", ".join(CAP_PERIODS))
        limit = float(limit_usd)
        if limit <= 0:
            raise ValueError("limit_usd must be > 0 (use clear to remove a cap)")
        action = str(action).strip().lower()
        if action not in ("warn", "park"):
            raise ValueError("action must be 'warn' or 'park'")
        self._execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                      ("cap_%s" % period, json.dumps({"limit_usd": limit, "action": action})))
        return {"period": period, "limit_usd": limit, "action": action}

    def clear_spend_cap(self, period: str) -> dict:
        """Remove a rolling spend cap. period in CAP_PERIODS."""
        period = str(period).strip().lower()
        if period not in CAP_PERIODS:
            raise ValueError("period must be one of: %s" % ", ".join(CAP_PERIODS))
        self._execute("DELETE FROM config WHERE key = ?", ("cap_%s" % period,))
        return {"cleared": period}

    def get_model_caps(self) -> dict:
        """Per-model spend caps {model: {"limit_usd": float}} (pure read).

        A model whose CUMULATIVE spend reaches its cap is parked (its id lands
        in parked_models()) regardless of period caps.
        """
        cfg = self._get_config()
        caps: dict[str, dict] = {}
        for key, val in cfg.items():
            if key.startswith("mcap_") and isinstance(val, dict):
                try:
                    limit = float(val.get("limit_usd", 0.0))
                except (TypeError, ValueError):
                    limit = 0.0
                caps[key[len("mcap_"):]] = {"limit_usd": limit}
        return caps

    def set_model_cap(self, model: str, limit_usd: float) -> dict:
        """Per-model cap: when cumulative spend reaches it the model is parked."""
        model = str(model).strip()
        if not model:
            raise ValueError("model required")
        limit = float(limit_usd)
        if limit <= 0:
            raise ValueError("limit_usd must be > 0 (use clear_model_cap to remove)")
        self._execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                      ("mcap_%s" % model, json.dumps({"limit_usd": limit})))
        return {"model": model, "limit_usd": limit}

    def clear_model_cap(self, model: str) -> dict:
        """Remove a per-model cap."""
        model = str(model).strip()
        self._execute("DELETE FROM config WHERE key = ?", ("mcap_%s" % model,))
        return {"cleared": model}

    def _window_spend(self, since: float, ts: float) -> float:
        row = self._query(
            "SELECT COALESCE(SUM(est_cost),0) FROM calls WHERE ts >= ? AND ts <= ?",
            (since, ts))
        return float(row[0][0])

    def _model_cumulative_spend(self, model: str) -> float:
        row = self._query(
            "SELECT COALESCE(SUM(est_cost),0) FROM calls WHERE lower(model) = lower(?)",
            (model,))
        return float(row[0][0])

    def _spend_state(self, ts: float | None = None) -> dict:
        """Pure-read spend-cap state: period statuses + parked model ids.

        NEVER writes to the ledger — only SELECTs (the contract for /cost caps
        and cost consumers). Status per period: ok | warn (>=80%) | parked
        (>=100% + park action) | over (>=100% + warn action).
        """
        now = ts if ts is not None else time.time()
        caps = self.get_spend_caps()
        periods: dict[str, dict] = {}
        warn_periods: list[str] = []
        parked_periods: list[str] = []
        heavy_parked = False
        for period, window in CAP_PERIODS.items():
            cap = caps.get(period)
            if not cap or cap["limit_usd"] <= 0:
                continue
            spend = self._window_spend(now - window, now)
            limit = cap["limit_usd"]
            pct = spend / limit * 100.0
            action = cap["action"]
            if pct >= PARK_PCT:
                status = "parked" if action == "park" else "over"
            elif pct >= WARN_PCT:
                status = "warn"
            else:
                status = "ok"
            if status in ("warn", "over"):
                warn_periods.append(period)
            if status == "parked":
                parked_periods.append(period)
                heavy_parked = True
            periods[period] = {
                "spend": spend, "limit": limit, "pct": pct,
                "action": action, "status": status,
            }
        # models over their own cumulative cap
        over_model_caps: list[str] = []
        for model, mcap in self.get_model_caps().items():
            limit = mcap.get("limit_usd", 0.0)
            if limit > 0 and self._model_cumulative_spend(model) >= limit:
                over_model_caps.append(model)
        return {
            "periods": periods,
            "warn_periods": sorted(warn_periods),
            "parked_periods": sorted(parked_periods),
            "over_model_caps": sorted(over_model_caps),
            "heavy_parked": heavy_parked,
            "heavy_tier": heavy_tier(),
        }

    def check_spend(self, ts: float | None = None) -> dict:
        """Rolling spend vs caps, per period: {spend, limit, pct, action, status}.

        Pure read — the ledger is never mutated (``read_only`` is part of the
        contract). ``warn`` lists periods at >=80%; ``parked`` carries the
        exhausted periods and the model ids to stop routing to.
        """
        state = self._spend_state(ts)
        parked = list(state["over_model_caps"])
        if state["heavy_parked"]:
            parked += state["heavy_tier"]
        return {
            "periods": state["periods"],
            "warn": state["warn_periods"],
            "parked": {
                "periods": state["parked_periods"],
                "models": sorted(set(parked)),
            },
            "heavy_tier_parked": state["heavy_parked"],
            "over_model_caps": state["over_model_caps"],
            "read_only": True,
        }

    def parked_models(self, ts: float | None = None) -> list[str]:
        """Model ids cost consumers must stop routing to.

        = models over their per-model cap, PLUS the whole heavy tier when a
        park-action period cap is exhausted. Pure read.
        """
        state = self._spend_state(ts)
        parked = list(state["over_model_caps"])
        if state["heavy_parked"]:
            parked += state["heavy_tier"]
        return sorted(set(parked))

    # ---- rollups (U-CORE-3) ----

    def rollup_today(self, ts: float | None = None) -> dict:
        """Calendar-day rollup: calls, tokens in/out, est cost."""
        now = ts if ts is not None else time.time()
        row = self._query(
            "SELECT COUNT(*), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), "
            "COALESCE(SUM(est_cost),0) FROM calls WHERE day = ?", (_day_of(now),))[0]
        return {"period": "today %s" % _day_of(now), "calls": int(row[0]),
                "tokens_in": int(row[1]), "tokens_out": int(row[2]),
                "est_cost": float(row[3])}

    def rollup_week(self, ts: float | None = None) -> dict:
        """ISO-week rollup: calls, tokens in/out, est cost."""
        now = ts if ts is not None else time.time()
        week = _week_of(now)
        row = self._query(
            "SELECT COUNT(*), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), "
            "COALESCE(SUM(est_cost),0) FROM calls WHERE week = ?", (week,))[0]
        return {"period": "week %s" % week, "week": week, "calls": int(row[0]),
                "tokens_in": int(row[1]), "tokens_out": int(row[2]),
                "est_cost": float(row[3])}

    def model_spend(self, model: str, ts: float | None = None) -> dict:
        """Per-model spend: all-time + current calendar day + current ISO week."""
        now = ts if ts is not None else time.time()
        model = str(model).strip()
        base = ("SELECT COUNT(*), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), "
                "COALESCE(SUM(est_cost),0) FROM calls WHERE lower(model) = lower(?)")

        def _sum(extra: str, params: tuple) -> dict:
            row = self._query(base + extra, (model,) + tuple(params))[0]
            return {"calls": int(row[0]), "tokens_in": int(row[1]),
                    "tokens_out": int(row[2]), "est_cost": float(row[3])}

        return {
            "model": model,
            "all_time": _sum("", ()),
            "today": _sum(" AND day = ?", (_day_of(now),)),
            "week": _sum(" AND week = ?", (_week_of(now),)),
        }

    def top_models(self, limit: int = 5, ts: float | None = None,
                   week: bool = False) -> list[dict]:
        """Top models by est cost (desc), with call/token counts.

        ts=None → all-time; ts set → that calendar day; week=True → the ISO
        week containing ts (or now when ts is None).
        """
        if week:
            rows = self._query(
                "SELECT model, COUNT(*), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), "
                "COALESCE(SUM(est_cost),0) FROM calls WHERE week = ? "
                "GROUP BY model ORDER BY SUM(est_cost) DESC, COUNT(*) DESC LIMIT ?",
                (_week_of(ts if ts is not None else time.time()), int(limit)))
        elif ts is not None:
            rows = self._query(
                "SELECT model, COUNT(*), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), "
                "COALESCE(SUM(est_cost),0) FROM calls WHERE day = ? "
                "GROUP BY model ORDER BY SUM(est_cost) DESC, COUNT(*) DESC LIMIT ?",
                (_day_of(ts), int(limit)))
        else:
            rows = self._query(
                "SELECT model, COUNT(*), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), "
                "COALESCE(SUM(est_cost),0) FROM calls "
                "GROUP BY model ORDER BY SUM(est_cost) DESC, COUNT(*) DESC LIMIT ?",
                (int(limit),))
        return [{"model": r[0], "calls": int(r[1]), "tokens_in": int(r[2]),
                 "tokens_out": int(r[3]), "est_cost": float(r[4])} for r in rows]

    def recent(self, limit: int = 10) -> list[dict]:
        """Most recent ledger rows (for /cost detail)."""
        rows = self._query(
            "SELECT id, ts, day, model, provider, tokens_in, tokens_out, est_cost, flagged "
            "FROM calls ORDER BY id DESC LIMIT ?", (int(limit),))
        return [{"id": r[0], "ts": r[1], "day": r[2], "model": r[3], "provider": r[4],
                 "tokens_in": r[5], "tokens_out": r[6], "est_cost": r[7],
                 "flagged": bool(r[8])} for r in rows]

    # ---- tools / commands ----

    def cost_track(self, model: str, provider: str = "", tokens_in: int = 0,
                   tokens_out: int = 0, task: str = "", ts: float | None = None) -> dict:
        """The cost_track tool: what provider-pool (or any caller) invokes.

        Zero hooks — this is called explicitly, never wired to agent events.
        Returns the log result; ``blocked=True`` means a hard-stop cap fired
        and the call was NOT logged (route to a cheaper model or refuse).
        """
        check = self.check_budget(ts=ts)
        if not check["allowed"]:
            return {"logged": False, "blocked": True, "reason": check["reason"],
                    "est_cost": 0.0}
        return self.log_call(model, provider, tokens_in, tokens_out, task=task, ts=ts)

    def export_csv(self, path: str) -> dict:
        """Full ledger → CSV: timestamp, model, tokens_in, tokens_out, est_cost.

        Append-only snapshot (oldest first). Returns {"path": ..., "rows": n}.
        """
        rows = self._query(
            "SELECT ts, model, tokens_in, tokens_out, est_cost FROM calls ORDER BY id")
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["timestamp", "model", "tokens_in", "tokens_out", "est_cost"])
            for ts_row, model, tin, tout, cost in rows:
                writer.writerow([
                    datetime.datetime.fromtimestamp(ts_row).isoformat(sep=" "),
                    model, tin, tout, cost])
        return {"path": os.path.abspath(path), "rows": len(rows)}

    def digest_text(self, ts: float | None = None) -> str:
        """/cost digest — weekly summary: totals, top 3 models, budget status."""
        now = ts if ts is not None else time.time()
        week = _week_of(now)
        row = self._query(
            "SELECT COUNT(*), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), "
            "COALESCE(SUM(est_cost),0) FROM calls WHERE week = ?", (week,))[0]
        n, tin, tout, cost = int(row[0]), int(row[1]), int(row[2]), float(row[3])
        status = self.budget_status(ts=now)
        top = self.top_models(limit=3, week=True, ts=now)
        lines = [
            "cost-tracker — weekly digest (ISO week %s)" % week,
            "",
        ]
        if n:
            lines.append("  calls: %d   tokens in: %d / out: %d   est cost: $%.6f"
                         % (n, tin, tout, cost))
        else:
            lines.append("  no calls logged this week — the ledger is quiet.")
        lines.append("  top models (this week):")
        if top:
            for m in top:
                lines.append("    %-20s %5d calls  $%.6f"
                             % (m["model"][:20], m["calls"], m["est_cost"]))
        else:
            lines.append("    (none)")
        cap_w = status["weekly_cap"]
        lines.append("  budget (week): spent $%.6f of %s — %s"
                     % (status["week_spent"],
                        ("$%.6f" % cap_w) if cap_w > 0 else "no cap",
                        "OVER" if (cap_w > 0 and status["week_spent"] >= cap_w) else "ok"))
        return "\n".join(lines)

    def cmd_export(self, raw: str) -> str:
        """/cost export <path> — full ledger to CSV."""
        path = (raw or "").strip().strip('"')
        if not path:
            return ("usage: /cost export <path.csv> — full ledger → CSV "
                    "(timestamp, model, tokens_in, tokens_out, est_cost)")
        try:
            res = self.export_csv(path)
        except OSError as exc:
            return "export failed: %s" % exc
        return "exported %d ledger rows → %s" % (res["rows"], res["path"])

    def cmd_digest(self, ts: float | None = None) -> str:
        """/cost digest — weekly summary (plain text)."""
        return self.digest_text(ts=ts)

    def cmd_report(self, ts: float | None = None) -> str:
        """/cost report — top models, totals, budget status."""
        now = ts if ts is not None else time.time()
        status = self.budget_status(ts=now)
        top = self.top_models(limit=5, ts=None)
        tot = self.totals()
        lines = [
            "cost-tracker — model cost ledger (sqlite: %s)" % self.db_path,
            "",
            "  top models by est. cost (all-time):",
        ]
        if top:
            for m in top:
                lines.append(
                    "    %-20s %5d calls  %8d in / %-8d out  $%.6f%s"
                    % (m["model"][:20], m["calls"], m["tokens_in"], m["tokens_out"],
                       m["est_cost"], "  (fallback rate)" if False else ""))
        else:
            lines.append("    (no calls logged yet — the ledger is empty)")
        lines.append("")
        lines.append("  totals: %d calls, %d tokens in / %d tokens out, est $%.6f"
                     % (tot["calls"], tot["tokens_in"], tot["tokens_out"], tot["est_cost"]))
        cap_d = status["daily_cap"]
        cap_w = status["weekly_cap"]
        lines.append("  budget (day)  : spent $%.6f of %s — %s"
                     % (status["day_spent"],
                        ("$%.6f" % cap_d) if cap_d > 0 else "no cap",
                        "OVER" if (cap_d > 0 and status["day_spent"] >= cap_d) else "ok"))
        lines.append("  budget (week) : spent $%.6f of %s — %s"
                     % (status["week_spent"],
                        ("$%.6f" % cap_w) if cap_w > 0 else "no cap",
                        "OVER" if (cap_w > 0 and status["week_spent"] >= cap_w) else "ok"))
        lines.append("  hard-stop     : %s (%s)" % ("ON" if status["hard_stop"] else "off",
                                                    "new calls blocked over cap" if status["hard_stop"] else "warn-only"))
        return "\n".join(lines)

    def cmd_budget(self, raw: str, ts: float | None = None) -> str:
        """/cost budget <daily_cap> [weekly_cap] | hard on|off | 0 = no cap."""
        parts = (raw or "").strip().split()
        if not parts:
            s = self.budget_status(ts=ts)
            return ("budget: daily $%.6f / weekly $%.6f, hard-stop %s — "
                    "usage: /cost budget <daily> [weekly] | /cost budget hard on|off"
                    % (s["daily_cap"], s["weekly_cap"], "ON" if s["hard_stop"] else "off"))
        if parts[0].lower() == "hard":
            if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
                return "usage: /cost budget hard on|off"
            s = self.set_budget(hard_stop=parts[1].lower() == "on")
            return "hard-stop %s — new calls %s blocked when a cap is exceeded." % (
                "ON" if s["hard_stop"] else "off",
                "ARE" if s["hard_stop"] else "are NOT (warn-only)")
        try:
            daily = float(parts[0])
            weekly = float(parts[1]) if len(parts) > 1 else None
        except ValueError:
            return "usage: /cost budget <daily_cap> [weekly_cap] — 0 = no cap"
        s = self.set_budget(daily_cap=daily, weekly_cap=weekly)
        return "budget set: daily $%.4f, weekly $%.4f, hard-stop %s" % (
            s["daily_cap"], s["weekly_cap"], "ON" if s["hard_stop"] else "off")

    def cmd_caps(self, raw: str = "", ts: float | None = None) -> str:
        """/cost caps | set <period> <limit_usd> <warn|park> | clear <period>
        | model <id> <limit_usd> | model <id> clear — spend caps + status."""
        parts = (raw or "").strip().split()
        if not parts:
            check = self.check_spend(ts=ts)
            caps = self.get_spend_caps()
            lines = ["cost-tracker — spend caps (rolling windows, pure read)"]
            if not caps and not self.get_model_caps():
                lines.append("  no caps set — usage: /cost caps set <5h|1d|7d|30d> <limit_usd> <warn|park>")
            for period in CAP_PERIODS:
                cap = caps.get(period)
                if not cap:
                    continue
                st = check["periods"].get(period, {})
                mark = {"warn": "WARN >=80%", "parked": "PARKED >=100%",
                        "over": "OVER >=100%"}.get(st.get("status"), "ok")
                lines.append("  %-4s limit $%-9.4f  %-11s spent $%.6f (%.1f%%)" % (
                    period, cap["limit_usd"], mark, st.get("spend", 0.0), st.get("pct", 0.0)))
            mcap = self.get_model_caps()
            if mcap:
                lines.append("  per-model caps:")
                for model, mc in sorted(mcap.items()):
                    spent = self._model_cumulative_spend(model)
                    lines.append("    %-20s limit $%-9.4f  spent $%.6f %s" % (
                        model[:20], mc["limit_usd"], spent,
                        "PARKED" if spent >= mc["limit_usd"] else ""))
            parked = check["parked"]["models"]
            if parked:
                lines.append("  parked models: %s" % ", ".join(parked))
            if check["warn"]:
                lines.append("  warn: %s at >=80%% of cap" % ", ".join(check["warn"]))
            return "\n".join(lines)
        sub = parts[0].lower()
        if sub == "set":
            if len(parts) < 3:
                return "usage: /cost caps set <5h|1d|7d|30d> <limit_usd> <warn|park>"
            period = parts[1].lower()
            try:
                limit = float(parts[2])
            except ValueError:
                return "usage: /cost caps set <5h|1d|7d|30d> <limit_usd> <warn|park>"
            action = parts[3].lower() if len(parts) > 3 else "warn"
            try:
                r = self.set_spend_cap(period, limit, action)
            except ValueError as exc:
                return "error: %s" % exc
            return ("spend cap set: %s $%.4f action=%s — warn at 80%%, %s" % (
                r["period"], r["limit_usd"], r["action"],
                "heavy tier parked at 100%" if r["action"] == "park"
                else "overage warning at 100%"))
        if sub == "clear":
            if len(parts) < 2:
                return "usage: /cost caps clear <5h|1d|7d|30d>"
            try:
                r = self.clear_spend_cap(parts[1])
            except ValueError as exc:
                return "error: %s" % exc
            return "spend cap cleared: %s" % r["cleared"]
        if sub == "model":
            if len(parts) < 3:
                return "usage: /cost caps model <model_id> <limit_usd> | /cost caps model <model_id> clear"
            model = parts[1]
            if parts[2].lower() == "clear":
                return "model cap cleared: %s" % self.clear_model_cap(model)["cleared"]
            try:
                r = self.set_model_cap(model, float(parts[2]))
            except ValueError as exc:
                return "error: %s" % exc
            return ("model cap set: %s $%.4f — parked when cumulative spend "
                    "reaches it" % (r["model"], r["limit_usd"]))
        return "usage: /cost caps | set <period> <limit_usd> <warn|park> | clear <period> | model <id> <limit>"

    def cmd_today(self, ts: float | None = None) -> str:
        """/cost today — calendar-day rollup."""
        r = self.rollup_today(ts=ts)
        return ("cost-tracker — %s\n  calls: %d   tokens in: %d / out: %d   "
                "est cost: $%.6f" % (r["period"], r["calls"], r["tokens_in"],
                                     r["tokens_out"], r["est_cost"]))

    def cmd_week(self, ts: float | None = None) -> str:
        """/cost week — ISO-week rollup."""
        r = self.rollup_week(ts=ts)
        return ("cost-tracker — %s\n  calls: %d   tokens in: %d / out: %d   "
                "est cost: $%.6f" % (r["period"], r["calls"], r["tokens_in"],
                                     r["tokens_out"], r["est_cost"]))

    def cmd_model(self, raw: str = "", ts: float | None = None) -> str:
        """/cost model <id> — per-model spend (all-time + today + week)."""
        model = (raw or "").strip()
        if not model:
            return "usage: /cost model <model_id> — per-model spend (all-time + today + week)"
        r = self.model_spend(model, ts=ts)
        a, t, w = r["all_time"], r["today"], r["week"]
        return ("cost-tracker — model %r\n"
                "  all-time: %d calls, %d in / %d out tokens, $%.6f\n"
                "  today   : %d calls, %d in / %d out tokens, $%.6f\n"
                "  week    : %d calls, %d in / %d out tokens, $%.6f" % (
                    r["model"], a["calls"], a["tokens_in"], a["tokens_out"], a["est_cost"],
                    t["calls"], t["tokens_in"], t["tokens_out"], t["est_cost"],
                    w["calls"], w["tokens_in"], w["tokens_out"], w["est_cost"]))

    def cmd_top(self, ts: float | None = None) -> str:
        """/cost top — top-5 models by est. spend (all-time)."""
        top = self.top_models(limit=5, ts=None)
        lines = ["cost-tracker — top 5 models by est. spend (all-time)"]
        if not top:
            lines.append("  (no calls logged yet — the ledger is empty)")
        for i, m in enumerate(top, 1):
            lines.append("  #%d %-20s %5d calls  %8d in / %-8d out  $%.6f" % (
                i, m["model"][:20], m["calls"], m["tokens_in"],
                m["tokens_out"], m["est_cost"]))
        return "\n".join(lines)

    def cmd_sync(self, raw: str = "") -> str:
        """/cost sync [path] — re-sync the cost table from the omni-registry
        pinned snapshot (single source of truth); a path argument or
        $XOMNI_MODELS_SNAPSHOT overrides the default snapshot location."""
        path = (raw or "").strip() or None
        res = sync_costs_from_snapshot(path)
        if res["source"] == "snapshot":
            COST_TABLE.clear()
            COST_TABLE.update(res["table"])
            return ("cost table synced from omni-registry snapshot: %d models, "
                    "source %s (in: $%.4f-%.4f / out: $%.4f-%.4f per 1M tokens)"
                    % (res["models"], res["path"],
                       min(r[0] for r in res["table"].values()),
                       max(r[0] for r in res["table"].values()),
                       min(r[1] for r in res["table"].values()),
                       max(r[1] for r in res["table"].values())))
        # Fallback: keep the last-known table untouched and warn clearly.
        return ("WARNING: cost table sync failed — snapshot unavailable (%s). "
                "Continuing with the built-in table (%d models); ledger "
                "unaffected." % (res.get("reason", "unknown error"), len(COST_TABLE)))
