"""Tests for PerkLine v2 engine (core.py) — pricing tiers, relevance, receipts, auction."""
import json
import os
import tempfile
import unittest

from unittest import mock

import core

SPONSORS = [
    {"id": "s-cpc", "message": "m", "url": "https://x.invalid", "model": "cpc", "price": 3.0, "budget": 300.0, "targeting": ["python"]},
    {"id": "s-cpa", "message": "m", "url": "https://x.invalid", "model": "cpa", "price": 50.0, "budget": 500.0, "targeting": []},
    {"id": "s-cpm", "message": "m", "url": "https://x.invalid", "model": "cpm", "price": 25.0, "budget": 200.0, "targeting": ["rust"]},
]


class PerkLineCoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._patch = mock.patch.object(core, "STATE_DIR", self._tmp.name)
        self._patch.start()
        core.STATE_PATH = os.path.join(self._tmp.name, "state.json")
        core.CONFIG_PATH = os.path.join(self._tmp.name, "config.json")
        core.CURRENT_LINE_PATH = os.path.join(self._tmp.name, "current.txt")
        self.addCleanup(self._patch.stop)
        self.addCleanup(self._tmp.cleanup)

    def _ledger(self, sponsors=None):
        led = core.Ledger.load()
        led.config["sponsors"] = sponsors or json.loads(json.dumps(SPONSORS))
        return led

    def test_relevance_matching_filters_sponsors(self):
        led = self._ledger()
        elig = core.eligible_sponsors(led, ["python"])
        ids = {s["id"] for s in elig}
        self.assertIn("s-cpc", ids)
        self.assertIn("s-cpa", ids)   # empty targeting = everyone
        self.assertNotIn("s-cpm", ids)  # targets rust only
        elig2 = core.eligible_sponsors(led, ["rust"])
        ids2 = {s["id"] for s in elig2}
        self.assertIn("s-cpm", ids2)
        self.assertNotIn("s-cpc", ids2)

    def test_cpm_render_charges_fractional(self):
        led = self._ledger()
        led.state["current_sponsor_id"] = "s-cpm"
        for i in range(1000):
            core.record_render(led, repo_tags=["rust"], now=1000.0 + i)
        # 1000 renders * (25/1000) * 0.5 = $12.50
        self.assertAlmostEqual(core.compute_earnings(led), 12.5)
        self.assertEqual(led.state["renders"], 1000)

    def test_cpc_engagement_charges_full_price_half_split(self):
        led = self._ledger()
        led.state["current_sponsor_id"] = "s-cpc"
        core.engage(led, now=1000.0)
        core.engage(led, now=1001.0)
        # 2 engagements * $3 * 0.5 = $3.00
        self.assertAlmostEqual(core.compute_earnings(led), 3.0)
        self.assertEqual(led.state["engagements"]["s-cpc"], 2)

    def test_cpa_action_charges_price(self):
        led = self._ledger()
        core.complete_action(led, "s-cpa", now=1000.0)
        # 1 action * $50 * 0.5 = $25.00
        self.assertAlmostEqual(core.compute_earnings(led), 25.0)

    def test_escrow_cap_never_exceeds_budget(self):
        led = self._ledger()
        core.complete_action(led, "s-cpa", now=1000.0)
        for i in range(50):  # way more actions than budget allows
            core.complete_action(led, "s-cpa", now=1001.0 + i)
        self.assertTrue(core.escrow_invariant(led))
        self.assertLessEqual(led.state["escrow_spent"]["s-cpa"], 500.0)
        # earnings stop at the escrow cap: 0.5 * 500 = 250 max
        self.assertAlmostEqual(core.compute_earnings(led), 250.0)

    def test_receipt_sign_and_verify(self):
        led = self._ledger()
        core.record_render(led, repo_tags=["python"], now=1000.0)
        receipt = led.state["receipts"][-1]
        self.assertTrue(core.verify_receipt(receipt, led.state["secret"]))
        self.assertFalse(core.verify_receipt(receipt, "wrong-secret"))
        self.assertFalse(core.verify_receipt(receipt + "x", led.state["secret"]))

    def test_second_price_auction(self):
        led = self._ledger()
        bids = [
            {"sponsor_id": "a", "bid": 100.0},
            {"sponsor_id": "b", "bid": 60.0},
            {"sponsor_id": "c", "bid": 80.0},
        ]
        r = core.run_auction(led, bids)
        self.assertEqual(r["winner"], "a")
        self.assertAlmostEqual(r["price"], 80.0)  # second-highest, not 100

    def test_pause_blocks_all_events(self):
        led = self._ledger()
        led.state["paused"] = True
        r1 = core.record_render(led, repo_tags=["python"], now=1000.0)
        r2 = core.engage(led, now=1001.0)
        r3 = core.complete_action(led, "s-cpa", now=1002.0)
        self.assertFalse(r1["counted"])
        self.assertFalse(r2["counted"])
        self.assertFalse(r3["counted"])
        self.assertEqual(core.compute_earnings(led), 0.0)

    def test_sync_payload_no_prompts_or_tags(self):
        led = self._ledger()
        core.record_render(led, repo_tags=["python"], now=1000.0)
        p = core.sync_payload(led)
        blob = json.dumps(p).lower()
        for banned in ("prompt", "message", "code", "content", "path", "python"):
            self.assertNotIn(banned, blob)
        self.assertIn("receipts", p)
        self.assertIn("session_hash", p)

    def test_render_line_shows_model_tier(self):
        led = self._ledger()
        led.state["current_sponsor_id"] = "s-cpc"
        line = core.render_line(led, repo_tags=["python"])
        self.assertIn("[CPC]", line)
        led.state["paused"] = True
        self.assertEqual(core.render_line(led), "")

    def test_stack_tags_local_scan(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "src"))
            open(os.path.join(d, "src", "app.py"), "w").write("x = 1\n")
            open(os.path.join(d, "package.json"), "w").write("{}\n")
            open(os.path.join(d, "go.mod"), "w").write("module x\n")
            os.makedirs(os.path.join(d, "node_modules"))
            open(os.path.join(d, "node_modules", "junk.js"), "w").write("")
            tags = core.stack_tags(d)
        self.assertIn("python", tags)
        self.assertIn("node", tags)
        self.assertIn("go", tags)


if __name__ == "__main__":
    unittest.main()


class EdgeCaseTests(unittest.TestCase):
    """Monetization edge cases: escrow cap, second-price auction, receipts."""

    def _ledger(self):
        led = core.Ledger()
        led.config["sponsors"] = [
            {"id": "s1", "message": "one", "budget": 100.0, "model": "cpm"},
            {"id": "s2", "message": "two", "budget": 50.0, "model": "cpc"},
        ]
        return led

    def test_charge_never_exceeds_budget(self):
        led = self._ledger()
        sp = led.config["sponsors"][0]
        core._charge(led, sp, 500.0)  # attempt 5x over budget
        self.assertEqual(led.state["escrow_spent"]["s1"], 100.0)
        self.assertTrue(core.escrow_invariant(led))

    def test_earnings_half_of_actual_spend(self):
        led = self._ledger()
        sp = led.config["sponsors"][0]
        core._charge(led, sp, 40.0)
        self.assertAlmostEqual(led.state["earnings_total"], 20.0, places=6)

    def test_auction_second_price(self):
        led = self._ledger()
        r = core.run_auction(led, [{"sponsor_id": "s1", "bid": 10.0},
                                   {"sponsor_id": "s2", "bid": 7.0}])
        self.assertEqual(r["winner"], "s1")
        self.assertEqual(r["price"], 7.0)  # second price, not 10

    def test_auction_single_bid_pays_zero(self):
        led = self._ledger()
        r = core.run_auction(led, [{"sponsor_id": "s1", "bid": 10.0}])
        self.assertEqual(r["winner"], "s1")
        self.assertEqual(r["price"], 0.0)

    def test_auction_empty_no_winner(self):
        led = self._ledger()
        r = core.run_auction(led, [])
        self.assertIsNone(r["winner"])

    def test_receipt_roundtrip_and_tamper(self):
        led = self._ledger()
        led.state["secret"] = "test-secret-32-chars-long-xxxxxxxx"
        receipt = core._receipt(led, "s1", "render", 1234.5)
        self.assertTrue(core.verify_receipt(receipt, "test-secret-32-chars-long-xxxxxxxx"))
        self.assertFalse(core.verify_receipt(receipt + "x", "test-secret-32-chars-long-xxxxxxxx"))
        self.assertFalse(core.verify_receipt(receipt, "wrong-secret"))

    def test_render_line_paused_blank(self):
        led = self._ledger()
        led.state["paused"] = True
        self.assertEqual(core.render_line(led), "")
