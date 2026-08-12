"""Tests for the marketplace plugin core (bare `from core import ...`)."""
import tempfile
import unittest
from pathlib import Path

import core
from core import (
    install,
    load_catalog,
    publish,
    rails_report,
    sales_ledger,
    save_catalog,
    search,
    verify_receipt,
)

SEED_ITEMS = [
    {
        "id": "it-1",
        "kind": "skill",
        "name": "test-case-farmer",
        "version": "1.0.0",
        "author": "kulfi-labs",
        "description": "writes unit tests from changelogs",
        "price_inr": 499,
        "rails_pct": 0.15,
        "payin_method": "upi",
        "source": "kulfi-labs/xomni",
        "published_at": "2026-08-12T10:00:00Z",
        "verified": True,
    },
    {
        "id": "it-2",
        "kind": "skill",
        "name": "gst-receipt-parser",
        "version": "1.2.0",
        "author": "pani-labs",
        "description": "extracts GSTIN and invoice lines from PDF receipts",
        "price_inr": 799,
        "rails_pct": 0.15,
        "payin_method": "upi",
        "source": "pani-labs/skills",
        "published_at": "2026-08-12T10:05:00Z",
        "verified": True,
    },
    {
        "id": "it-3",
        "kind": "mcp",
        "name": "inr-price-feed-mcp",
        "version": "0.9.0",
        "author": "bandra-ai",
        "description": "live INR commodity and forex price feed server",
        "price_inr": 499,
        "rails_pct": 0.15,
        "payin_method": "upi",
        "source": "bandra-ai/mcp",
        "published_at": "2026-08-12T10:10:00Z",
        "verified": False,
    },
    {
        "id": "it-4",
        "kind": "plugin",
        "name": "cost-tracker-pro",
        "version": "2.0.0",
        "author": "xomni",
        "description": "maintained cost-tracker with priority review and support",
        "price_inr": 999,
        "rails_pct": 0.15,
        "payin_method": "upi",
        "source": "painbaba/xomni",
        "published_at": "2026-08-12T10:15:00Z",
        "verified": True,
    },
]

NEW_ITEM = {
    "kind": "skill",
    "name": "hindi-tone-writer",
    "version": "1.0.0",
    "author": "kulfi-labs",
    "description": "rewrites copy in warm Hinglish tone",
    "price_inr": 299,
    "source": "kulfi-labs/xomni",
    "verified": False,
}


class MarketplaceCoreTest(unittest.TestCase):
    """Tests patch the module-level CATALOG_PATH and STATE_DIR to temp dirs."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self._old_catalog_path = core.CATALOG_PATH
        self._old_state_dir = core.STATE_DIR
        self.catalog_path = tmp / "catalog.json"
        self.state_dir = tmp / "state"
        core.CATALOG_PATH = self.catalog_path
        core.STATE_DIR = self.state_dir
        save_catalog(SEED_ITEMS, self.catalog_path)

    def tearDown(self):
        core.CATALOG_PATH = self._old_catalog_path
        core.STATE_DIR = self._old_state_dir

    # -- catalog ---------------------------------------------------------

    def test_load_catalog_defaults_and_missing_file_fails_loud(self):
        items = load_catalog()
        self.assertEqual(len(items), len(SEED_ITEMS))
        self.assertEqual(items[0]["id"], "it-1")
        core.CATALOG_PATH = Path(self._tmp.name) / "nope.json"
        with self.assertRaises(ValueError) as ctx:
            load_catalog()
        self.assertIn("catalog file not found", str(ctx.exception))

    # -- search ----------------------------------------------------------

    def test_search_filters_by_kind_and_query(self):
        self.assertEqual([i["id"] for i in search(kind="mcp")], ["it-3"])
        self.assertTrue(all(i["kind"] == "skill" for i in search(kind="skill")))
        self.assertEqual([i["id"] for i in search("gst")], ["it-2"])
        self.assertEqual(search("GSTIN")[0]["id"], "it-2")  # case-insensitive
        self.assertEqual(search("zzz-not-in-catalog"), [])
        self.assertEqual(len(search()), len(SEED_ITEMS))  # empty query = all

    # -- publish ---------------------------------------------------------

    def test_publish_adds_item_and_returns_receipt(self):
        result = publish(NEW_ITEM, seller_id="kulfi-labs")
        item = result["item"]
        self.assertEqual(item["id"], "it-5")  # max seed suffix it-4 + 1
        self.assertIn("published_at", item)
        self.assertEqual(item["rails_pct"], 0.15)
        self.assertEqual(item["payin_method"], "upi")
        receipt = result["receipt"]
        self.assertEqual(receipt["type"], "marketplace.publish")
        self.assertEqual(receipt["item_id"], "it-5")
        self.assertEqual(receipt["seller_id"], "kulfi-labs")
        self.assertEqual(receipt["ts"], item["published_at"])
        self.assertTrue(verify_receipt(receipt))
        self.assertIn("it-5", [i["id"] for i in load_catalog()])  # persisted
        self.assertEqual(core._read_ledger(self.state_dir)[0]["type"], "marketplace.publish")

    def test_publish_auto_increments_ids(self):
        first = publish(NEW_ITEM, seller_id="a")["item"]
        second = publish(NEW_ITEM, seller_id="a")["item"]
        self.assertEqual((first["id"], second["id"]), ("it-5", "it-6"))

    def test_publish_invalid_item_fails_loud(self):
        with self.assertRaises(ValueError) as ctx:
            publish({"kind": "skill", "name": "x"}, seller_id="a")
        self.assertIn("price_inr", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx2:
            publish({"kind": "widget", "name": "x", "price_inr": 100}, seller_id="a")
        self.assertIn("kind", str(ctx2.exception))
        with self.assertRaises(ValueError) as ctx3:
            publish(NEW_ITEM, seller_id="")
        self.assertIn("seller_id", str(ctx3.exception))

    # -- install + rails math -------------------------------------------

    def test_rails_math_exact(self):
        # Pinned M2 acceptance values (take floored, net = residual):
        self.assertEqual(core._rails_split(100), (15, 85))
        self.assertEqual(core._rails_split(999), (149, 850))
        self.assertEqual(core._rails_split(500), (75, 425))
        for price in (100, 299, 499, 500, 799, 999, 1499):
            rails, net = core._rails_split(price)
            self.assertEqual(rails + net, price, f"split must sum to gross for {price}")
            self.assertLessEqual(net, price)

    def test_install_records_sale_and_receipt_verifies(self):
        result = install("it-2", buyer_id="dev-42")  # 799 -> 119 / 680
        sale, receipt = result["sale"], result["receipt"]
        self.assertEqual(sale["item_id"], "it-2")
        self.assertEqual(sale["buyer_id"], "dev-42")
        self.assertEqual(receipt["type"], "marketplace.sale")
        self.assertEqual(receipt["price_inr"], 799)
        self.assertEqual(receipt["rails_inr"], 119)
        self.assertEqual(receipt["seller_net_inr"], 680)
        self.assertEqual(receipt["payin_method"], "upi")
        self.assertTrue(verify_receipt(receipt))
        self.assertEqual(sale["receipt_id"], receipt["receipt_id"])
        self.assertEqual(len(sales_ledger()), 1)

    def test_install_double_claim_raises(self):
        install("it-1", buyer_id="dev-42")
        with self.assertRaises(ValueError) as ctx:
            install("it-1", buyer_id="dev-42")
        self.assertIn("already installed", str(ctx.exception))
        install("it-1", buyer_id="dev-7")  # different buyer may install
        self.assertEqual(len(sales_ledger()), 2)

    def test_install_unknown_id_raises(self):
        with self.assertRaises(ValueError) as ctx:
            install("it-999", buyer_id="dev-42")
        self.assertIn("it-999", str(ctx.exception))
        self.assertEqual(sales_ledger(), [])

    # -- receipts --------------------------------------------------------

    def test_verify_receipt_detects_tampering(self):
        receipt = install("it-4", buyer_id="dev-42")["receipt"]  # price 999
        self.assertTrue(verify_receipt(receipt))
        self.assertFalse(verify_receipt(dict(receipt, price_inr=499)))  # flip price
        self.assertFalse(verify_receipt(dict(receipt, buyer_id="mallory")))
        pub_receipt = publish(NEW_ITEM, seller_id="kulfi-labs")["receipt"]
        self.assertTrue(verify_receipt(pub_receipt))
        self.assertFalse(verify_receipt(dict(pub_receipt, item_id="it-99")))
        self.assertFalse(verify_receipt({"no": "receipt_id"}))
        self.assertFalse(verify_receipt(None))

    # -- reports ---------------------------------------------------------

    def test_rails_report_totals_match(self):
        empty = rails_report()
        self.assertEqual(empty, {"gross_inr": 0, "rails_inr": 0,
                                 "seller_net_inr": 0, "sales_count": 0})
        self.assertEqual(sales_ledger(), [])
        install("it-1", buyer_id="dev-42")  # 499 -> 74 / 425
        install("it-4", buyer_id="dev-42")  # 999 -> 149 / 850
        report = rails_report()
        self.assertEqual(report["sales_count"], 2)
        self.assertEqual(report["gross_inr"], 1498)
        self.assertEqual(report["rails_inr"], 223)
        self.assertEqual(report["seller_net_inr"], 1275)
        self.assertEqual(report["gross_inr"], report["rails_inr"] + report["seller_net_inr"])

    # -- integration -----------------------------------------------------

    def test_publish_then_install_round_trip(self):
        pub = publish(NEW_ITEM, seller_id="kulfi-labs")
        item_id = pub["item"]["id"]
        res = install(item_id, buyer_id="dev-42")  # 299 -> 44 / 255
        self.assertTrue(verify_receipt(res["receipt"]))
        self.assertEqual(res["receipt"]["price_inr"], 299)
        self.assertEqual(res["receipt"]["rails_inr"], 44)
        self.assertEqual(res["receipt"]["seller_net_inr"], 255)
        report = rails_report()
        self.assertEqual(report["sales_count"], 1)
        self.assertEqual(report["gross_inr"], 299)


class SeedCatalogTest(unittest.TestCase):
    """The repo seed catalog (data/marketplace/catalog.json) must load and
    every item must be schema-valid."""

    def test_seed_catalog_loads_and_items_schema_valid(self):
        seed_path = Path(__file__).resolve().parents[3] / "data" / "marketplace" / "catalog.json"
        self.assertTrue(seed_path.exists(), f"seed catalog missing: {seed_path}")
        items = load_catalog(seed_path)
        self.assertGreaterEqual(len(items), 6)
        required = ("id", "kind", "name", "version", "author", "description",
                    "price_inr", "rails_pct", "payin_method", "source",
                    "published_at", "verified")
        for item in items:
            missing = [k for k in required if k not in item]
            self.assertEqual(missing, [], f"item {item.get('id')} missing {missing}")
            self.assertIn(item["kind"], ("skill", "mcp", "plugin"))
            self.assertEqual(item["rails_pct"], 0.15)
            self.assertEqual(item["payin_method"], "upi")
            self.assertIsInstance(item["price_inr"], int)
            self.assertGreater(item["price_inr"], 0)
            self.assertIsInstance(item["verified"], bool)
        kinds = {i["kind"] for i in items}
        self.assertEqual(kinds, {"skill", "mcp", "plugin"})


if __name__ == "__main__":
    unittest.main()
