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
import os
import sqlite3
import time

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

    def top_models(self, limit: int = 5, ts: float | None = None) -> list[dict]:
        """Top models by est cost (desc), with call/token counts."""
        if ts is not None:
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
