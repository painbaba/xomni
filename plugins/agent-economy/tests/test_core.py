"""Tests for agent-economy core (pure stdlib, unittest).

Run from the plugin dir:  python -m unittest tests.test_core -q
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest

import core as _core
from core import (
    TradeError,
    accept,
    build_receipt,
    fulfill,
    is_expired,
    ledger,
    offer,
    request,
    settle,
    verify_receipt,
    verify_trade,
)


class EconomyTestCase(unittest.TestCase):

    def setUp(self):
        self._orig_state_dir = _core.STATE_DIR
        self.state_dir = tempfile.mkdtemp(prefix="xomni-econ-test-")
        _core.STATE_DIR = self.state_dir

    def tearDown(self):
        _core.STATE_DIR = self._orig_state_dir
        shutil.rmtree(self.state_dir, ignore_errors=True)

    # ── helpers ──────────────────────────────────────────────────────────
    def _make_offer(self, price=250, ttl=3600):
        return offer("svc-doc-gen", "agent-alice", "generate-docx",
                     price, ttl_sec=ttl)

    def _make_trade(self):
        off = self._make_offer()
        return off, request(off["offer_id"], "agent-bob")

    def _fulfilled_trade(self):
        off, tr = self._make_trade()
        accept(tr["trade_id"], "agent-alice")
        return off, fulfill(tr["trade_id"], {"pdf": "payload"})

    # ── offers ───────────────────────────────────────────────────────────
    def test_offer_creates_auto_id_and_fields(self):
        off = self._make_offer(price=500)
        self.assertEqual(off["offer_id"], "of-1")
        self.assertEqual(off["service_id"], "svc-doc-gen")
        self.assertEqual(off["agent_id"], "agent-alice")
        self.assertEqual(off["capability"], "generate-docx")
        self.assertEqual(off["price_inr"], 500)
        self.assertEqual(off["ttl_sec"], 3600)
        self.assertIsInstance(off["created_ts"], float)

    def test_offer_rejects_bad_price(self):
        with self.assertRaises(TradeError):
            self._make_offer(price="250")
        with self.assertRaises(TradeError):
            self._make_offer(price=-1)

    # ── happy path ───────────────────────────────────────────────────────
    def test_full_happy_path(self):
        off, tr = self._make_trade()
        self.assertEqual(tr["state"], "CREATED")
        self.assertEqual(tr["seller_id"], "agent-alice")
        self.assertEqual(tr["buyer_id"], "agent-bob")
        self.assertEqual(tr["price_inr"], off["price_inr"])
        self.assertIsNone(tr["result_sha256"])
        self.assertIsNone(tr["payment_ref"])

        acc = accept(tr["trade_id"], "agent-alice")
        self.assertEqual(acc["state"], "ACCEPTED")

        payload = {"doc": "hello", "n": 3}
        ful = fulfill(tr["trade_id"], payload)
        self.assertEqual(ful["state"], "FULFILLED")
        self.assertEqual(ful["result_sha256"], _core.digest(payload))

        st = settle(tr["trade_id"], "pay-REF-1")
        self.assertEqual(st["state"], "SETTLED")
        self.assertEqual(st["payment_ref"], "pay-REF-1")
        self.assertGreaterEqual(st["updated_ts"], st["created_ts"])

    # ── illegal transitions ──────────────────────────────────────────────
    def test_accept_by_non_seller_raises(self):
        _, tr = self._make_trade()
        with self.assertRaises(TradeError) as cm:
            accept(tr["trade_id"], "agent-mallory")
        self.assertIn("seller", str(cm.exception))
        self.assertIn("agent-mallory", str(cm.exception))

    def test_accept_from_fulfilled_raises(self):
        _, tr = self._make_trade()
        accept(tr["trade_id"], "agent-alice")
        fulfill(tr["trade_id"], {"out": 1})
        with self.assertRaises(TradeError) as cm:
            accept(tr["trade_id"], "agent-alice")
        self.assertIn("CREATED", str(cm.exception))
        self.assertIn("FULFILLED", str(cm.exception))

    def test_fulfill_before_accept_raises(self):
        _, tr = self._make_trade()
        with self.assertRaises(TradeError) as cm:
            fulfill(tr["trade_id"], {"out": 1})
        self.assertIn("ACCEPTED", str(cm.exception))
        self.assertIn("CREATED", str(cm.exception))

    def test_double_fulfill_raises(self):
        _, tr = self._make_trade()
        accept(tr["trade_id"], "agent-alice")
        fulfill(tr["trade_id"], {"out": 1})
        with self.assertRaises(TradeError) as cm:
            fulfill(tr["trade_id"], {"out": 2})
        self.assertIn("already fulfilled", str(cm.exception))
        self.assertIn("tr-1", str(cm.exception))

    def test_settle_before_fulfill_raises(self):
        _, tr = self._make_trade()
        accept(tr["trade_id"], "agent-alice")
        with self.assertRaises(TradeError) as cm:
            settle(tr["trade_id"], "pay-X")
        self.assertIn("FULFILLED", str(cm.exception))
        self.assertIn("ACCEPTED", str(cm.exception))

    def test_unknown_ids_raise(self):
        with self.assertRaises(TradeError):
            request("of-999", "agent-bob")
        with self.assertRaises(TradeError):
            accept("tr-999", "agent-alice")

    # ── digest verification ──────────────────────────────────────────────
    def test_verify_trade_digest(self):
        _, tr = self._make_trade()
        accept(tr["trade_id"], "agent-alice")
        payload = {"rows": [1, 2, 3], "fmt": "csv"}
        ful = fulfill(tr["trade_id"], payload)
        self.assertTrue(verify_trade(ful, payload))
        self.assertFalse(verify_trade(ful, {"rows": [1, 2, 3], "fmt": "xlsx"}))
        self.assertFalse(verify_trade(tr, payload))  # no digest yet

    # ── receipts ─────────────────────────────────────────────────────────
    def test_receipt_roundtrip(self):
        off, ful = self._fulfilled_trade()
        st = settle(ful["trade_id"], "pay-R1")
        receipt = build_receipt(st)
        self.assertEqual(receipt["type"], "agent-economy.trade")
        self.assertEqual(receipt["trade_id"], st["trade_id"])
        self.assertEqual(receipt["service_id"], off["service_id"])
        self.assertEqual(receipt["buyer_id"], "agent-bob")
        self.assertEqual(receipt["seller_id"], "agent-alice")
        self.assertEqual(receipt["price_inr"], off["price_inr"])
        self.assertEqual(receipt["result_sha256"], st["result_sha256"])
        self.assertEqual(receipt["payment_ref"], "pay-R1")
        self.assertTrue(verify_receipt(receipt, st))

    def test_receipt_tamper_detected(self):
        _, ful = self._fulfilled_trade()
        st = settle(ful["trade_id"], "pay-R1")
        receipt = build_receipt(st)

        forged_id = dict(receipt)
        forged_id["receipt_id"] = "0" * 64
        self.assertFalse(verify_receipt(forged_id, st))

        altered_field = dict(receipt)
        altered_field["price_inr"] = 1  # receipt_id kept — must still fail
        self.assertFalse(verify_receipt(altered_field, st))

        other = request(self._make_offer()["offer_id"], "agent-carol")
        self.assertFalse(verify_receipt(receipt, other))  # bound to another trade

        self.assertFalse(verify_receipt({"type": "nope"}, st))
        self.assertFalse(verify_receipt(None, st))

    # ── offer expiry ─────────────────────────────────────────────────────
    def test_offer_expiry_blocks_request(self):
        off = self._make_offer(ttl=3600)
        self.assertFalse(is_expired(off, now=off["created_ts"] + 60))
        self.assertTrue(is_expired(off, now=off["created_ts"] + 3601))

        # force expiry deterministically: rewind created_ts in the store
        path = os.path.join(self.state_dir, "offers.json")
        with open(path, "r", encoding="utf-8") as fh:
            recs = json.load(fh)
        recs[0]["created_ts"] = time.time() - 7200
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(recs, fh)

        with self.assertRaises(TradeError) as cm:
            request(off["offer_id"], "agent-bob")
        self.assertIn("expired", str(cm.exception))

    # ── ledger ───────────────────────────────────────────────────────────
    def test_ledger_totals(self):
        o1 = self._make_offer(price=100)
        o2 = offer("svc-ml", "agent-dave", "classify", 350)
        t1 = request(o1["offer_id"], "agent-bob")
        t2 = request(o2["offer_id"], "agent-carol")
        accept(t1["trade_id"], "agent-alice")
        fulfill(t1["trade_id"], {"x": 1})
        settle(t1["trade_id"], "pay-1")
        accept(t2["trade_id"], "agent-dave")
        fulfill(t2["trade_id"], {"y": 2})

        book = ledger(self.state_dir)
        self.assertEqual(len(book["trades"]), 2)
        self.assertEqual(book["total_value_inr"], 450)
        self.assertEqual(book["settled_count"], 1)
        self.assertIsInstance(book["total_value_inr"], int)

    # ── persistence / auto ids ───────────────────────────────────────────
    def test_auto_id_increments_across_files(self):
        o1 = self._make_offer()
        o2 = self._make_offer()
        self.assertEqual(o1["offer_id"], "of-1")
        self.assertEqual(o2["offer_id"], "of-2")

        t1 = request(o1["offer_id"], "agent-bob")
        t2 = request(o2["offer_id"], "agent-carol")
        self.assertEqual(t1["trade_id"], "tr-1")
        self.assertEqual(t2["trade_id"], "tr-2")

        # ids keep incrementing after re-loading from disk (state persists)
        o3 = self._make_offer()
        self.assertEqual(o3["offer_id"], "of-3")
        t3 = request(o3["offer_id"], "agent-dave")
        self.assertEqual(t3["trade_id"], "tr-3")

        self.assertTrue(os.path.isfile(os.path.join(self.state_dir, "offers.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.state_dir, "trades.json")))


if __name__ == "__main__":
    unittest.main()
