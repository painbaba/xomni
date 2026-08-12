"""Tests for cost-tracker — sqlite cost ledger, budget caps, /cost commands.

Covers: cost estimation (known/free/unknown models), day/week bucketing,
budget status + remaining, cap persistence, hard-stop blocking, warn-only
overage, top-models ranking, the cost_track tool gate, and /cost rendering.
"""
import datetime
import json
import os
import tempfile
import unittest
import csv
import importlib.util
import shutil
import sys

import core


def _ts(y, m, d, hh=12, mm=0):
    """Local-time timestamp for a given calendar date (timezone-agnostic tests)."""
    dt = datetime.datetime(y, m, d, hh, mm)
    return dt.timestamp()


class CostTrackerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self._tmp.name, "costs.db")
        self.addCleanup(self._tmp.cleanup)

    def _tracker(self, **cfg):
        tr = core.CostTracker(self.db)
        if cfg:
            tr.set_budget(**cfg)
        return tr

    # ---- cost math ----

    def test_est_cost_known_model(self):
        tr = self._tracker()
        cost, flagged = tr.est_cost("deepseek-chat", 1000, 500)
        # (0.27*1000 + 1.10*500) / 1M = $0.00082
        self.assertAlmostEqual(cost, 0.00082, places=8)
        self.assertFalse(flagged)

    def test_unknown_model_uses_fallback_and_flags(self):
        tr = self._tracker()
        cost, flagged = tr.est_cost("future-model-x", 1000, 500)
        # (0.50*1000 + 1.50*500) / 1M = $0.00125
        self.assertAlmostEqual(cost, 0.00125, places=8)
        self.assertTrue(flagged)

    # ---- ledger writes / reads ----

    def test_log_call_computes_est_cost(self):
        tr = self._tracker()
        r = tr.log_call("deepseek-chat", provider="openrouter", tokens_in=1000, tokens_out=500,
                        ts=_ts(2026, 8, 12, 10))
        self.assertTrue(r["logged"])
        self.assertAlmostEqual(r["est_cost"], 0.00082, places=8)
        self.assertEqual(tr.totals()["calls"], 1)
        # verified-free gateway models are logged honestly at $0
        free, flagged = tr.est_cost("deepseek-v4-flash", 10_000, 2_000)
        self.assertEqual(free, 0.0)
        self.assertFalse(flagged)

    def test_log_persists_across_instances(self):
        tr = self._tracker()
        tr.log_call("gpt-4o", tokens_in=2000, tokens_out=1000, ts=_ts(2026, 8, 12, 10))
        tr2 = core.CostTracker(self.db)  # fresh connection, same file
        tot = tr2.totals()
        self.assertEqual(tot["calls"], 1)
        self.assertAlmostEqual(tot["est_cost"], (2.5 * 2000 + 10.0 * 1000) / 1e6, places=8)

    def test_day_and_week_buckets(self):
        tr = self._tracker()
        ts = _ts(2026, 8, 12, 10)
        r = tr.log_call("deepseek-chat", tokens_in=1, tokens_out=1, ts=ts)
        self.assertEqual(r["day"], "2026-08-12")
        self.assertEqual(r["week"], datetime.date(2026, 8, 12).strftime("%G-W%V"))

    def test_spent_day_and_week(self):
        tr = self._tracker()
        tr.log_call("deepseek-chat", tokens_in=1_000_000, tokens_out=0, ts=_ts(2026, 8, 12, 10))   # $0.27
        tr.log_call("deepseek-chat", tokens_in=1_000_000, tokens_out=0, ts=_ts(2026, 8, 13, 10))   # $0.27, next day
        tr.log_call("deepseek-chat", tokens_in=0, tokens_out=1_000_000, ts=_ts(2026, 8, 19, 10))   # $1.10, next week
        self.assertAlmostEqual(tr.spent("day", _ts(2026, 8, 12, 12)), 0.27, places=8)
        self.assertAlmostEqual(tr.spent("day", _ts(2026, 8, 13, 12)), 0.27, places=8)
        self.assertAlmostEqual(tr.spent("week", _ts(2026, 8, 13, 12)), 0.54, places=8)

    # ---- budget caps ----

    def test_budget_status_remaining(self):
        tr = self._tracker(daily_cap=1.0, weekly_cap=10.0)
        tr.log_call("deepseek-chat", tokens_in=1_000_000, tokens_out=0, ts=_ts(2026, 8, 12, 10))  # $0.27
        s = tr.budget_status(ts=_ts(2026, 8, 12, 12))
        self.assertAlmostEqual(s["day_spent"], 0.27, places=8)
        self.assertAlmostEqual(s["day_remaining"], 0.73, places=8)
        self.assertFalse(s["blocked"])
        self.assertTrue(s["allowed"])

    def test_set_budget_persists(self):
        tr = self._tracker()
        tr.set_budget(daily_cap=2.0, weekly_cap=12.0, hard_stop=True)
        tr2 = core.CostTracker(self.db)
        s = tr2.budget_status(ts=_ts(2026, 8, 12, 12))
        self.assertEqual(s["daily_cap"], 2.0)
        self.assertEqual(s["weekly_cap"], 12.0)
        self.assertTrue(s["hard_stop"])

    def test_hard_stop_blocks_when_over_daily_cap(self):
        tr = self._tracker(daily_cap=0.001, hard_stop=True)
        r1 = tr.log_call("claude-opus-4", tokens_in=1000, tokens_out=1000, ts=_ts(2026, 8, 12, 10))
        self.assertTrue(r1["logged"])  # first call fits under the cap
        r2 = tr.log_call("claude-opus-4", tokens_in=100_000, tokens_out=100_000, ts=_ts(2026, 8, 12, 11))
        self.assertFalse(r2["logged"])
        self.assertTrue(r2["blocked"])
        self.assertIn("hard-stop", r2["reason"])
        self.assertEqual(tr.totals()["calls"], 1)  # blocked call NOT recorded

    def test_hard_stop_off_warns_but_logs(self):
        tr = self._tracker(daily_cap=0.001, hard_stop=False)  # warn-only default
        tr.log_call("claude-opus-4", tokens_in=100_000, tokens_out=100_000, ts=_ts(2026, 8, 12, 10))
        s = tr.budget_status(ts=_ts(2026, 8, 12, 12))
        self.assertTrue(s["blocked"] is False or s["allowed"])  # over cap but not blocked
        r = tr.log_call("claude-opus-4", tokens_in=1000, tokens_out=1000, ts=_ts(2026, 8, 12, 11))
        self.assertTrue(r["logged"])  # still logged in warn-only mode
        self.assertEqual(tr.totals()["calls"], 2)

    def test_top_models_orders_by_cost(self):
        tr = self._tracker()
        tr.log_call("gpt-4o-mini", tokens_in=1000, tokens_out=1000, ts=_ts(2026, 8, 12, 10))   # cheap
        tr.log_call("gpt-4o-mini", tokens_in=1000, tokens_out=1000, ts=_ts(2026, 8, 12, 11))
        tr.log_call("claude-opus-4", tokens_in=1000, tokens_out=1000, ts=_ts(2026, 8, 12, 12))  # expensive
        top = tr.top_models(limit=5)
        self.assertEqual(top[0]["model"], "claude-opus-4")
        self.assertEqual(top[0]["calls"], 1)
        self.assertEqual(top[1]["model"], "gpt-4o-mini")

    # ---- tools / commands ----

    def test_cost_track_tool_blocks_on_hard_stop(self):
        tr = self._tracker(daily_cap=0.001, hard_stop=True)
        tr.log_call("claude-opus-4", tokens_in=100_000, tokens_out=100_000, ts=_ts(2026, 8, 12, 10))
        r = tr.cost_track("claude-opus-4", provider="openrouter", tokens_in=1000, tokens_out=1000,
                          task="continue refactor", ts=_ts(2026, 8, 12, 11))
        self.assertFalse(r["logged"])
        self.assertTrue(r["blocked"])
        self.assertEqual(tr.totals()["calls"], 1)
        # and it logs fine when under cap (explicitly clear the caps above)
        tr2 = self._tracker(daily_cap=0.0, weekly_cap=0.0, hard_stop=False)
        ok = tr2.cost_track("deepseek-chat", tokens_in=1000, tokens_out=500, task="triage",
                            ts=_ts(2026, 8, 12, 10))
        self.assertTrue(ok["logged"])
        self.assertAlmostEqual(ok["est_cost"], 0.00082, places=8)

    def test_cmd_report_renders(self):
        tr = self._tracker(daily_cap=1.0)
        tr.log_call("deepseek-chat", provider="openrouter", tokens_in=1000, tokens_out=500,
                    ts=_ts(2026, 8, 12, 10))
        tr.log_call("gpt-4o", tokens_in=2000, tokens_out=1000, ts=_ts(2026, 8, 12, 11))
        text = tr.cmd_report(ts=_ts(2026, 8, 12, 12))
        self.assertIn("cost-tracker", text)
        self.assertIn("deepseek-chat", text)
        self.assertIn("gpt-4o", text)
        self.assertIn("budget (day)", text)
        self.assertIn("hard-stop", text)
        self.assertIn("$", text)

    def test_cmd_budget_parses_and_confirms(self):
        tr = self._tracker()
        out = tr.cmd_budget("2 10", ts=_ts(2026, 8, 12, 12))
        self.assertIn("daily $2.0000", out)
        self.assertIn("weekly $10.0000", out)
        out2 = tr.cmd_budget("hard on", ts=_ts(2026, 8, 12, 12))
        self.assertIn("hard-stop ON", out2)
        out3 = tr.cmd_budget("junk", ts=_ts(2026, 8, 12, 12))
        self.assertIn("usage:", out3)
        s = tr.budget_status(ts=_ts(2026, 8, 12, 12))
        self.assertEqual(s["daily_cap"], 2.0)
        self.assertTrue(s["hard_stop"])

    # ---- export / digest ----

    def test_export_csv_rows_match_ledger(self):
        tr = self._tracker()
        tr.log_call("deepseek-chat", provider="openrouter", tokens_in=1000, tokens_out=500,
                    ts=_ts(2026, 8, 12, 10))                      # $0.00082
        tr.log_call("gpt-4o", tokens_in=2000, tokens_out=1000, ts=_ts(2026, 8, 12, 11))  # $0.015
        csv_path = os.path.join(self._tmp.name, "ledger.csv")
        res = tr.export_csv(csv_path)
        self.assertEqual(res["rows"], 2)
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        self.assertEqual(rows[0], ["timestamp", "model", "tokens_in", "tokens_out", "est_cost"])
        self.assertEqual(len(rows), 3)  # header + one line per ledger row
        by_model = {r[1]: r for r in rows[1:]}
        self.assertEqual(by_model["deepseek-chat"][2:], ["1000", "500", "0.00082"])
        self.assertEqual(by_model["gpt-4o"][2:], ["2000", "1000", "0.015"])
        self.assertEqual(tr.totals()["calls"], len(rows) - 1)  # csv rows match ledger

    def test_digest_contains_totals(self):
        tr = self._tracker(daily_cap=1.0)
        tr.log_call("deepseek-chat", tokens_in=1_000_000, tokens_out=0, ts=_ts(2026, 8, 12, 10))   # $0.27
        tr.log_call("gpt-4o", tokens_in=2_000_000, tokens_out=1_000_000, ts=_ts(2026, 8, 12, 11))   # $15.00
        text = tr.digest_text(ts=_ts(2026, 8, 12, 12))
        self.assertIn("weekly digest", text)
        self.assertIn("calls: 2", text)
        self.assertIn("$15.270000", text)      # week total = 0.27 + 15.00
        self.assertIn("gpt-4o", text)          # top model by cost
        self.assertIn("deepseek-chat", text)
        self.assertIn("budget (week)", text)

    def test_digest_empty_ledger_graceful(self):
        tr = self._tracker()
        text = tr.digest_text(ts=_ts(2026, 8, 12, 12))
        self.assertIn("weekly digest", text)
        self.assertIn("no calls logged this week", text)
        self.assertIn("budget (week)", text)

    # ---- snapshot sync (single source of truth: omni-registry pinned snapshot) ----

    def test_sync_from_snapshot_maps_prices(self):
        snap = os.path.join(self._tmp.name, "models.snapshot.json")
        payload = {
            "schema_version": "1.0.0",
            "models": {
                "deepseek-v4-flash": {"context_window": 1048576,
                                      "cost_per_1m": {"input": 0.0, "output": 0.0}},
                "gpt-4o": {"pricing": {"prompt": 2.5, "completion": 10.0}},
                "claude-opus-4": {"input": 15.0, "output": 75.0},
            },
        }
        with open(snap, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        r = core.sync_costs_from_snapshot(snap)
        self.assertEqual(r["source"], "snapshot")
        self.assertGreater(r["models"], 0)
        self.assertEqual(r["models"], 3)
        for slug in ("deepseek-v4-flash", "gpt-4o", "claude-opus-4"):
            in_p, out_p = r["table"][slug]
            self.assertIsInstance(in_p, float)
            self.assertIsInstance(out_p, float)
        self.assertEqual(r["table"]["deepseek-v4-flash"], (0.0, 0.0))
        self.assertEqual(r["table"]["gpt-4o"], (2.5, 10.0))
        self.assertEqual(r["table"]["claude-opus-4"], (15.0, 75.0))

    def test_sync_missing_snapshot_falls_back_gracefully(self):
        r = core.sync_costs_from_snapshot(os.path.join(self._tmp.name, "nope.json"))
        self.assertEqual(r["source"], "fallback")
        self.assertEqual(r["models"], 0)
        self.assertGreater(len(r["table"]), 0)          # built-in table still usable
        self.assertEqual(r["table"], dict(core.COST_TABLE))
        self.assertTrue(r.get("reason"))

    def test_sync_corrupt_snapshot_falls_back(self):
        bad = os.path.join(self._tmp.name, "bad.json")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("{not json!!")
        r = core.sync_costs_from_snapshot(bad)
        self.assertEqual(r["source"], "fallback")
        self.assertEqual(r["models"], 0)
        self.assertGreater(len(r["table"]), 0)

    def test_sync_record_without_pricing_defaults_zero(self):
        snap = os.path.join(self._tmp.name, "s2.json")
        with open(snap, "w", encoding="utf-8") as fh:
            json.dump({"models": {"deepseek-v4-flash": {"context_window": 1}}}, fh)
        r = core.sync_costs_from_snapshot(snap)
        self.assertEqual(r["source"], "snapshot")
        self.assertEqual(r["table"]["deepseek-v4-flash"], (0.0, 0.0))

    def test_cmd_sync_applies_table_and_warns_on_fallback(self):
        tr = self._tracker()
        saved = dict(core.COST_TABLE)
        self.addCleanup(lambda: (core.COST_TABLE.clear(), core.COST_TABLE.update(saved)))
        snap = os.path.join(self._tmp.name, "sync.json")
        with open(snap, "w", encoding="utf-8") as fh:
            json.dump({"models": {"gpt-4o": {"pricing": {"prompt": 9.9, "completion": 8.8}}}}, fh)
        out = tr.cmd_sync(snap)
        self.assertIn("synced", out)
        self.assertEqual(core.COST_TABLE["gpt-4o"], (9.9, 8.8))  # table applied globally
        # fallback keeps last-known data and surfaces a clear warning
        out2 = tr.cmd_sync(os.path.join(self._tmp.name, "missing.json"))
        self.assertIn("WARNING", out2)
        self.assertEqual(core.COST_TABLE["gpt-4o"], (9.9, 8.8))


    # ---- spend caps (U-CORE-3) ----

    def test_spend_cap_set_get_roundtrip(self):
        tr = self._tracker()
        tr.set_spend_cap("5h", 12.0, "warn")
        tr.set_spend_cap("30d", 100.0, "park")
        tr2 = core.CostTracker(self.db)  # fresh connection, same file
        caps = tr2.get_spend_caps()
        self.assertEqual(caps["5h"]["limit_usd"], 12.0)
        self.assertEqual(caps["5h"]["action"], "warn")
        self.assertEqual(caps["30d"]["limit_usd"], 100.0)
        self.assertEqual(caps["30d"]["action"], "park")
        self.assertNotIn("1d", caps)  # only what was set

    def test_spend_cap_clear_removes(self):
        tr = self._tracker()
        tr.set_spend_cap("7d", 50.0, "warn")
        self.assertIn("7d", tr.get_spend_caps())
        r = tr.clear_spend_cap("7d")
        self.assertEqual(r["cleared"], "7d")
        self.assertEqual(tr.get_spend_caps(), {})

    def test_spend_cap_invalid_inputs_rejected(self):
        tr = self._tracker()
        for bad in (("9d", 5.0, "warn"), ("1d", 0.0, "warn"),
                    ("1d", -3.0, "park"), ("1d", 5.0, "nuke")):
            with self.assertRaises(ValueError):
                tr.set_spend_cap(*bad)
        with self.assertRaises(ValueError):
            tr.clear_spend_cap("9d")

    def test_spend_cap_warn_boundary_80(self):
        tr = self._tracker()
        tr.set_spend_cap("1d", 0.34, "warn")   # $0.27 → 79.4%: below warn
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 10))
        check = tr.check_spend(ts=_ts(2026, 8, 12, 12))
        self.assertEqual(check["periods"]["1d"]["status"], "ok")
        self.assertNotIn("1d", check["warn"])
        # a second small call crosses 80% → warn text, never parks
        tr.log_call("deepseek-chat", tokens_in=100_000, ts=_ts(2026, 8, 12, 11))  # +$0.027 → 87.4%
        check = tr.check_spend(ts=_ts(2026, 8, 12, 12))
        st = check["periods"]["1d"]
        self.assertGreaterEqual(st["pct"], 80.0)
        self.assertEqual(st["status"], "warn")
        self.assertIn("1d", check["warn"])
        self.assertEqual(check["parked"]["models"], [])

    def test_spend_cap_park_boundary_100(self):
        tr = self._tracker()
        tr.set_spend_cap("5h", 0.27, "park")   # limit == call cost → exactly 100%
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 10))
        check = tr.check_spend(ts=_ts(2026, 8, 12, 12))
        st = check["periods"]["5h"]
        self.assertEqual(st["pct"], 100.0)
        self.assertEqual(st["status"], "parked")
        self.assertIn("5h", check["parked"]["periods"])
        self.assertTrue(check["heavy_tier_parked"])
        self.assertEqual(check["parked"]["models"], core.heavy_tier())

    def test_spend_cap_warn_action_never_parks(self):
        tr = self._tracker()
        tr.set_spend_cap("1d", 0.27, "warn")   # at 100% but action=warn
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 10))
        check = tr.check_spend(ts=_ts(2026, 8, 12, 12))
        self.assertEqual(check["periods"]["1d"]["status"], "over")
        self.assertIn("1d", check["warn"])
        self.assertFalse(check["heavy_tier_parked"])
        self.assertEqual(check["parked"]["models"], [])

    def test_check_spend_rolling_window_math(self):
        tr = self._tracker()
        t0 = _ts(2026, 8, 12, 12)
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=t0)             # $0.27 now
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=t0 - 6 * 3600)  # $0.27 −6h
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=t0 - 26 * 3600) # $0.27 −26h
        for p in ("5h", "1d", "7d"):
            tr.set_spend_cap(p, 1.0, "warn")
        check = tr.check_spend(ts=t0)
        self.assertAlmostEqual(check["periods"]["5h"]["spend"], 0.27, places=8)
        self.assertAlmostEqual(check["periods"]["1d"]["spend"], 0.54, places=8)
        self.assertAlmostEqual(check["periods"]["7d"]["spend"], 0.81, places=8)
        self.assertAlmostEqual(check["periods"]["5h"]["pct"], 27.0, places=6)

    def test_check_spend_never_mutates_ledger(self):
        tr = self._tracker()
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 10))
        tr.log_call("gpt-4o", tokens_in=100_000, tokens_out=50_000, ts=_ts(2026, 8, 12, 11))
        tr.set_spend_cap("5h", 1.0, "warn")
        tr.set_spend_cap("1d", 5.0, "park")
        tr.set_model_cap("gpt-4o", 0.01)
        q = "SELECT COUNT(*), COALESCE(SUM(id),0), COALESCE(SUM(est_cost),0), COALESCE(MAX(ts),0) FROM calls"
        before = tr._query(q)
        for _ in range(3):  # every read-only entry point, hammered
            tr.check_spend(ts=_ts(2026, 8, 12, 12))
            tr.parked_models(ts=_ts(2026, 8, 12, 12))
            tr.get_spend_caps()
            tr.rollup_today(ts=_ts(2026, 8, 12, 12))
            tr.rollup_week(ts=_ts(2026, 8, 12, 12))
            tr.model_spend("gpt-4o", ts=_ts(2026, 8, 12, 12))
            tr.cmd_caps("", ts=_ts(2026, 8, 12, 12))
        self.assertEqual(before, tr._query(q))  # ledger bit-for-bit untouched

    def test_model_cap_parks_only_that_model(self):
        tr = self._tracker()
        tr.set_model_cap("gpt-4o", 0.005)
        tr.log_call("gpt-4o", tokens_in=1000, tokens_out=500, ts=_ts(2026, 8, 12, 10))  # $0.0075 > cap
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 11))      # $0.27, no cap
        parked = tr.parked_models(ts=_ts(2026, 8, 12, 12))
        self.assertEqual(parked, ["gpt-4o"])  # no period cap → no heavy tier

    def test_heavy_tier_derivation(self):
        tier = core.heavy_tier()
        for slug in ("claude-opus-4", "gpt-4o", "claude-sonnet-4", "gemini-2.5-pro", "o3-mini"):
            self.assertIn(slug, tier)
        for slug in ("deepseek-chat", "deepseek-v4-flash", "gpt-4o-mini"):
            self.assertNotIn(slug, tier)
        # heavy tier is derived from the (sync-able) cost table at call time
        repriced = {**core.COST_TABLE, "deepseek-chat": (2.0, 2.0)}
        self.assertIn("deepseek-chat", core.heavy_tier(repriced))

    def test_parked_models_heavy_tier_on_period_cap(self):
        tr = self._tracker()
        tr.set_spend_cap("5h", 0.27, "park")
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 10))  # exhausts the cap
        parked = tr.parked_models(ts=_ts(2026, 8, 12, 12))
        self.assertEqual(parked, core.heavy_tier())  # whole heavy tier parked

    # ---- rollups (U-CORE-3) ----

    def test_rollup_today_math(self):
        tr = self._tracker()
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 10))  # $0.27
        tr.log_call("gpt-4o", tokens_in=100_000, tokens_out=50_000, ts=_ts(2026, 8, 12, 11))  # $0.0125
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 13, 10))  # other day
        r = tr.rollup_today(ts=_ts(2026, 8, 12, 12))
        self.assertEqual(r["calls"], 2)
        self.assertAlmostEqual(r["est_cost"], 1.02, places=8)  # 0.27 + 0.75
        self.assertEqual(r["period"], "today 2026-08-12")

    def test_rollup_week_math(self):
        tr = self._tracker()
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 10))  # $0.27
        tr.log_call("deepseek-chat", tokens_in=0, tokens_out=1_000_000, ts=_ts(2026, 8, 19, 10))  # $1.10 next ISO week
        r = tr.rollup_week(ts=_ts(2026, 8, 12, 12))
        self.assertEqual(r["calls"], 1)
        self.assertAlmostEqual(r["est_cost"], 0.27, places=8)
        self.assertEqual(r["week"], datetime.date(2026, 8, 12).strftime("%G-W%V"))

    def test_model_spend_rollup(self):
        tr = self._tracker()
        tr.log_call("gpt-4o", tokens_in=100_000, tokens_out=50_000, ts=_ts(2026, 8, 12, 10))  # $0.0125
        tr.log_call("gpt-4o", tokens_in=100_000, tokens_out=50_000, ts=_ts(2026, 8, 12, 11))  # $0.0125
        tr.log_call("gpt-4o", tokens_in=100_000, tokens_out=50_000, ts=_ts(2026, 8, 19, 10))  # next week
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 12))  # other model
        r = tr.model_spend("gpt-4o", ts=_ts(2026, 8, 12, 12))
        self.assertEqual(r["model"], "gpt-4o")
        self.assertEqual(r["all_time"]["calls"], 3)
        self.assertAlmostEqual(r["all_time"]["est_cost"], 2.25, places=8)  # 3 × $0.75
        self.assertEqual(r["today"]["calls"], 2)
        self.assertAlmostEqual(r["today"]["est_cost"], 1.50, places=8)
        self.assertEqual(r["week"]["calls"], 2)
        self.assertAlmostEqual(r["week"]["est_cost"], 1.50, places=8)

    # ---- /cost commands (U-CORE-3) ----

    def test_cmd_caps_set_show_clear(self):
        tr = self._tracker()
        self.assertIn("no caps set", tr.cmd_caps("", ts=_ts(2026, 8, 12, 12)))
        out = tr.cmd_caps("set 5h 12 warn", ts=_ts(2026, 8, 12, 12))
        self.assertIn("spend cap set: 5h $12.0000 action=warn", out)
        out = tr.cmd_caps("", ts=_ts(2026, 8, 12, 12))
        self.assertIn("5h", out)
        self.assertIn("limit $12.0000", out)
        self.assertIn("spent $0.000000", out)
        self.assertIn("error:", tr.cmd_caps("set nope 5 warn", ts=_ts(2026, 8, 12, 12)))
        self.assertIn("spend cap cleared: 5h",
                      tr.cmd_caps("clear 5h", ts=_ts(2026, 8, 12, 12)))
        self.assertEqual(tr.get_spend_caps(), {})

    def test_cmd_rollups_render(self):
        tr = self._tracker()
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 10))       # $0.27
        tr.log_call("claude-opus-4", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 11))       # $15.00
        t = tr.cmd_today(ts=_ts(2026, 8, 12, 12))
        self.assertIn("today 2026-08-12", t)
        self.assertIn("calls: 2", t)
        self.assertIn("$15.270000", t)
        w = tr.cmd_week(ts=_ts(2026, 8, 12, 12))
        self.assertIn("week", w)
        self.assertIn("calls: 2", w)
        m = tr.cmd_model("claude-opus-4", ts=_ts(2026, 8, 12, 12))
        self.assertIn("model 'claude-opus-4'", m)
        self.assertIn("$15.000000", m)
        self.assertIn("today", m)
        top = tr.cmd_top(ts=_ts(2026, 8, 12, 12))
        self.assertIn("top 5 models", top)
        self.assertIn("deepseek-chat", top)
        self.assertIn("claude-opus-4", top)
        self.assertLess(top.index("claude-opus-4"), top.index("deepseek-chat"))  # #1 spender first

    # ---- zero hooks + plugin dispatch (U-CORE-3) ----

    def _load_plugin(self, name):
        """Import the plugin __init__.py as a real package (relative `from . import
        core` needs package context), by copying it + core.py into a temp dir."""
        plugin_dir = os.path.dirname(os.path.abspath(core.__file__))
        tmp = tempfile.mkdtemp(prefix="ct_plugin_")
        pkg = os.path.join(tmp, name)
        os.makedirs(pkg)
        shutil.copy(os.path.join(plugin_dir, "__init__.py"), os.path.join(pkg, "__init__.py"))
        shutil.copy(os.path.join(plugin_dir, "core.py"), os.path.join(pkg, "core.py"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        sys.path.insert(0, tmp)
        try:
            return importlib.import_module(name)
        finally:
            sys.path.remove(tmp)

    def test_plugin_registers_only_cost_command_no_hooks(self):
        mod = self._load_plugin("cost_tracker_plugin")

        class FakeCtx:
            def __init__(self):
                self.commands = []
                self.hooks = []

            def register_command(self, name, handler=None, description="", args_hint=""):
                self.commands.append(name)

            def __getattr__(self, name):
                if "hook" in name.lower():
                    self.hooks.append(name)
                    return lambda *a, **k: None
                raise AttributeError(name)

        ctx = FakeCtx()
        mod.register(ctx)
        self.assertEqual(ctx.commands, ["cost"])  # exactly one command registered
        self.assertEqual(ctx.hooks, [])           # ZERO hooks registered

    def test_plugin_cost_dispatch_new_commands(self):
        mod = self._load_plugin("cost_tracker_plugin2")
        tr = self._tracker()
        tr.log_call("deepseek-chat", tokens_in=1_000_000, ts=_ts(2026, 8, 12, 10))
        saved = mod.core.CostTracker
        mod.core.CostTracker = lambda: tr
        self.addCleanup(setattr, mod.core, "CostTracker", saved)
        self.assertIn("today", mod._handle_cost("today"))
        self.assertIn("spend cap set: 5h $12.0000", mod._handle_cost("caps set 5h 12 warn"))
        self.assertIn("deepseek-chat", mod._handle_cost("top"))
        self.assertIn("model 'deepseek-chat'", mod._handle_cost("model deepseek-chat"))
        self.assertIn("week", mod._handle_cost("week"))


if __name__ == "__main__":
    unittest.main()
