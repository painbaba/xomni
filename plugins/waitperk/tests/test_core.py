"""Tests for the WaitPerk sponsorship engine (core.py) — pure logic, no Hermes."""
import json
import os
import tempfile
import unittest

from unittest import mock

import core

P = {"sponsors": [{"id": "s1", "message": "msg", "paid": 100.0}], "network_total_impressions": 1000}


class WaitPerkCoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._patch = mock.patch.object(core, "STATE_DIR", self._tmp.name)
        self._patch.start()
        core.STATE_PATH = os.path.join(self._tmp.name, "state.json")
        core.CONFIG_PATH = os.path.join(self._tmp.name, "config.json")
        core.CURRENT_LINE_PATH = os.path.join(self._tmp.name, "current.txt")
        self.addCleanup(self._patch.stop)
        self.addCleanup(self._tmp.cleanup)

    def _ledger(self):
        led = core.Ledger.load()
        led.config.update(json.loads(json.dumps(P)))
        return led

    def test_work_events_increment_impressions(self):
        led = self._ledger()
        core.record_work_event(led, now=1000.0)
        core.record_work_event(led, now=1001.0)
        self.assertEqual(led.state["impressions"], 2)

    def test_pause_stops_impressions(self):
        led = self._ledger()
        core.record_work_event(led, now=1000.0)
        led.state["paused"] = True
        r = core.record_work_event(led, now=1001.0)
        self.assertFalse(r["counted"])
        self.assertEqual(led.state["impressions"], 1)
        led.state["paused"] = False
        core.record_work_event(led, now=1002.0)
        self.assertEqual(led.state["impressions"], 2)

    def test_impression_share_math(self):
        led = self._ledger()
        for i in range(100):
            core.record_work_event(led, now=1000.0 + i)
        self.assertAlmostEqual(core.impressions_share(led), 100 / 1000)

    def test_earnings_50_50_by_share(self):
        led = self._ledger()
        for i in range(100):
            core.record_work_event(led, now=1000.0 + i)
        # 0.5 * 100 * (100/1000) = $5.00
        self.assertAlmostEqual(core.compute_earnings(led), 5.0)

    def test_earnings_capped_at_half_sponsor_paid(self):
        led = self._ledger()
        for i in range(2000):  # more impressions than network total -> share caps at 1.0
            core.record_work_event(led, now=1000.0 + i)
        # cap = 0.5 * 100 = 50
        self.assertAlmostEqual(core.compute_earnings(led), 50.0)

    def test_payout_never_exceeds_sponsor_paid(self):
        led = self._ledger()
        for i in range(500):
            core.record_work_event(led, now=1000.0 + i)
        self.assertTrue(core.payout_invariant(led))
        # total payouts across the whole network = 0.5*P*(sum of shares) = 0.5*P <= P
        paid = 100.0
        self.assertLessEqual(core.SHARE_FRACTION * paid, paid)

    def test_state_persists_round_trip(self):
        led = self._ledger()
        core.record_work_event(led, now=1000.0)
        led.save()
        led2 = core.Ledger.load()
        self.assertEqual(led2.state["impressions"], 1)
        self.assertEqual(led2.state["device_id"], led.state["device_id"])

    def test_session_window(self):
        led = self._ledger()
        core.start_session(led, now=1000.0)
        core.record_work_event(led, now=1001.0)
        s = core.end_session(led, now=1002.0)
        self.assertIsNotNone(s.get("end"))
        self.assertEqual(s["impressions"], 1)

    def test_render_line_contains_sponsor_message(self):
        led = self._ledger()
        line = core.render_line(led)
        self.assertIn("msg", line)
        led.state["paused"] = True
        self.assertEqual(core.render_line(led), "")

    def test_sync_payload_has_no_prompt_or_code(self):
        led = self._ledger()
        p = core.sync_payload(led)
        self.assertIn("impressions", p)
        self.assertIn("session_hash", p)
        blob = json.dumps(p).lower()
        for banned in ("prompt", "message", "code", "content", "path"):
            self.assertNotIn(banned, blob)

    def test_sync_dry_run_without_url(self):
        led = self._ledger()
        led.config["sync_url"] = ""
        r = core.sync(led)
        self.assertEqual(r["mode"], "dry-run")
        self.assertIn("payload", r)

    def test_sync_live_posts_payload(self):
        led = self._ledger()
        led.config["sync_url"] = "https://example.invalid/sync"
        sent = {}
        def fake_post(url, data):
            sent["url"] = url
            sent["data"] = data
            return 200
        r = core.sync(led, http_post=fake_post)
        self.assertEqual(r["mode"], "live")
        self.assertEqual(sent["url"], "https://example.invalid/sync")
        self.assertEqual(sent["data"]["impressions"], led.state["impressions"])

    def test_sync_failure_never_raises(self):
        led = self._ledger()
        led.config["sync_url"] = "https://example.invalid/sync"
        def boom(url, data):
            raise RuntimeError("network down")
        r = core.sync(led, http_post=boom)
        self.assertEqual(r["mode"], "error")

    def test_current_line_file_written(self):
        led = self._ledger()
        core.record_work_event(led, now=1000.0)
        self.assertTrue(os.path.exists(core.CURRENT_LINE_PATH))
        with open(core.CURRENT_LINE_PATH, encoding="utf-8") as f:
            self.assertIn("msg", f.read())


if __name__ == "__main__":
    unittest.main()


class EdgeCaseTests(WaitPerkCoreTests):
    """Monetization edge cases: pause, idle gaps, earnings cap, persistence."""

    def test_paused_events_not_counted(self):
        led = self._ledger()
        led.state["paused"] = True
        before = led.state["impressions"]
        r = core.record_work_event(led, now=1000.0)
        self.assertEqual(r["counted"], False)
        self.assertEqual(led.state["impressions"], before)

    def test_idle_gap_over_600s_not_active_time(self):
        led = self._ledger()
        core.record_work_event(led, now=1000.0)
        before = led.state.get("active_seconds", 0.0)
        core.record_work_event(led, now=2000.0)  # gap > 600s = idle, not screen time
        self.assertEqual(led.state.get("active_seconds", 0.0), before)

    def test_work_events_accumulate_impressions(self):
        led = self._ledger()
        for i in range(3):
            core.record_work_event(led, now=100.0 + i)
        self.assertEqual(led.state["impressions"], 3)

    def test_earnings_capped_at_half_sponsor_paid(self):
        led = self._ledger()
        core.record_work_event(led, now=1.0)
        core.record_work_event(led, now=2.0)
        e = core.compute_earnings(led, sponsor_paid=100.0)
        self.assertLessEqual(e, 50.0 + 1e-9)  # min(0.5*P*share, 0.5*P) cap
        self.assertGreaterEqual(e, 0.0)

    def test_payout_invariant_holds_after_many_events(self):
        led = self._ledger()
        for i in range(20):
            core.record_work_event(led, now=10.0 + i)
        self.assertTrue(core.payout_invariant(led, sponsor_paid=100.0))

    def test_persistence_roundtrip(self):
        led = self._ledger()
        core.record_work_event(led, now=5.0)
        core.start_session(led, now=6.0)
        led.save()
        again = core.Ledger.load()
        self.assertEqual(again.state["impressions"], led.state["impressions"])
        self.assertEqual(again.state["device_id"], led.state["device_id"])

    def test_render_line_respects_width(self):
        led = self._ledger()
        line = core.render_line(led, width=30)
        self.assertLessEqual(len(line), 30)
