"""Tests for cost-tracker — sqlite cost ledger, budget caps, /cost commands.

Covers: cost estimation (known/free/unknown models), day/week bucketing,
budget status + remaining, cap persistence, hard-stop blocking, warn-only
overage, top-models ranking, the cost_track tool gate, and /cost rendering.
"""
import datetime
import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
