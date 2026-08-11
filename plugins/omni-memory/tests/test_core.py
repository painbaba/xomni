import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core import (
    CONSOLIDATE_THRESHOLD,
    DB_PATH,
    STATE_DIR,
    consolidate,
    inject_brief,
    recall,
    remember,
)


class OmniMemoryCoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_state = os.environ.get("OMNIMEM_STATE")
        # Redirect the store by patching the module-level paths.
        import core as core_mod

        core_mod.STATE_DIR = Path(self._tmp.name)
        core_mod.DB_PATH = core_mod.STATE_DIR / "memory.db"

    def tearDown(self):
        self._tmp.cleanup()

    def test_remember_and_recall_roundtrip(self):
        fid = remember("The user is building XOMNI, a multi-agent CLI product.")
        self.assertIsInstance(fid, int)
        hits = recall("xomni multi-agent")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["id"], fid)
        self.assertGreater(hits[0]["score"], 0)

    def test_remember_rejects_blank(self):
        with self.assertRaises(ValueError):
            remember("   ")

    def test_recall_ranks_relevant_higher(self):
        remember("User loves pizza toppings")
        remember("User is working on a tax filing tool")
        hits = recall("pizza")
        self.assertEqual(hits[0]["text"], "User loves pizza toppings")
        self.assertEqual(hits[0]["score"], 1.0)

    def test_recall_bumps_hits_and_accessed(self):
        remember("some fact about networking")
        first = recall("networking")[0]
        second = recall("networking")[0]
        self.assertEqual(second["hits"], first["hits"] + 1)

    def test_inject_brief_obeys_budget(self):
        remember("A " + "long fact " * 200)
        brief = inject_brief("long fact")
        self.assertLessEqual(len(brief), 900)

    def test_inject_brief_empty_when_no_facts(self):
        self.assertEqual(inject_brief("anything"), "")

    def test_consolidate_fails_open_below_threshold(self):
        for i in range(CONSOLIDATE_THRESHOLD - 1):
            remember(f"fact number {i}")
        result = consolidate(key="bad-key")
        self.assertFalse(result["consolidated"])
        self.assertIsNone(result["error"])

    def test_consolidate_with_bad_key_returns_error_not_crash(self):
        for i in range(CONSOLIDATE_THRESHOLD + 2):
            remember(f"fact number {i}")
        result = consolidate(key="definitely-not-a-real-key")
        self.assertFalse(result["consolidated"])
        self.assertIsNotNone(result["error"])


if __name__ == "__main__":
    unittest.main()
