import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from core import (
    CONSOLIDATE_THRESHOLD,
    DB_PATH,
    STATE_DIR,
    consolidate,
    inject_brief,
    load_key,
    recall,
    remember,
)


class OmniMemoryCoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # Redirect the store by patching the module-level paths.
        import core as core_mod

        core_mod.STATE_DIR = Path(self._tmp.name)
        core_mod.DB_PATH = core_mod.STATE_DIR / "memory.db"

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------- roundtrip
    def test_remember_and_recall_roundtrip(self):
        fid = remember("The user is building XOMNI, a multi-agent CLI product.")
        self.assertIsInstance(fid, int)
        hits = recall("xomni multi-agent")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["id"], fid)
        self.assertGreater(hits[0]["score"], 0)

    def test_remember_recall_full_roundtrip_equality(self):
        text = "The user prefers dark mode in all tools"
        fid = remember(text, source="chat", tags="prefs,ui")
        hits = recall("dark mode")
        self.assertTrue(hits)
        top = hits[0]
        self.assertEqual(top["id"], fid)
        self.assertEqual(top["text"], text)
        self.assertEqual(top["source"], "chat")
        self.assertEqual(top["tags"], "prefs,ui")
        self.assertGreater(top["score"], 0)

    def test_remember_returns_incrementing_ids(self):
        first = remember("fact alpha")
        second = remember("fact beta")
        self.assertEqual(second, first + 1)

    def test_remember_stores_source_and_tags_defaults(self):
        fid = remember("bare fact")
        hits = recall("bare fact")
        self.assertEqual(hits[0]["id"], fid)
        self.assertEqual(hits[0]["source"], "user")
        self.assertEqual(hits[0]["tags"], "")

    def test_recall_empty_query_returns_newest_first(self):
        remember("oldest fact about apples")
        time.sleep(0.01)
        remember("newest fact about apples")
        hits = recall("")
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0]["text"], "newest fact about apples")

    def test_recall_limit_zero_returns_empty(self):
        remember("some fact")
        self.assertEqual(recall("some fact", limit=0), [])

    def test_recall_no_match_returns_zero_score(self):
        remember("user likes pizza toppings")
        hits = recall("quantum physics")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["score"], 0.0)

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

    # ------------------------------------------------------- argument handling
    def test_remember_rejects_blank(self):
        with self.assertRaises(ValueError):
            remember("   ")

    def test_remember_none_raises(self):
        with self.assertRaises(ValueError):
            remember(None)

    def test_remember_empty_string_raises(self):
        with self.assertRaises(ValueError):
            remember("")

    def test_recall_none_query_does_not_crash(self):
        remember("some stored fact")
        hits = recall(None)
        self.assertIsInstance(hits, list)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["score"], 0.0)

    def test_inject_brief_formats_dash_lines(self):
        remember("user prefers vim keybindings")
        remember("user works on xomni plugins")
        brief = inject_brief("vim")
        self.assertTrue(brief)
        for line in brief.split("\n"):
            self.assertTrue(line.startswith("- "))
            self.assertNotIn("\n", line.strip())

    def test_inject_brief_zero_budget_empty(self):
        remember("some fact about networking")
        self.assertEqual(inject_brief("networking", max_chars=0), "")

    def test_inject_brief_obeys_budget(self):
        remember("A " + "long fact " * 200)
        brief = inject_brief("long fact")
        self.assertLessEqual(len(brief), 900)

    def test_inject_brief_empty_when_no_facts(self):
        self.assertEqual(inject_brief("anything"), "")

    # ------------------------------------------------------ corrupt-state guard
    def test_corrupt_db_recovers_fresh_store(self):
        import core as core_mod

        core_mod.DB_PATH.write_bytes(b"this is not a sqlite database \x00\x01\x02")
        fid = remember("fact survives corruption")
        self.assertIsInstance(fid, int)
        hits = recall("corruption")
        self.assertEqual(hits[0]["id"], fid)
        # The corrupt file was quarantined, not silently destroyed.
        quarantined = list(core_mod.STATE_DIR.glob("memory.db.corrupt-*"))
        self.assertEqual(len(quarantined), 1)

    def test_corrupt_db_recall_safe(self):
        import core as core_mod

        core_mod.DB_PATH.write_bytes(b"\xde\xad\xbe\xef not sqlite")
        self.assertEqual(recall("anything"), [])
        # Store is usable again afterwards.
        self.assertIsInstance(remember("after corruption"), int)

    def test_partial_schema_quarantined_and_rebuilt(self):
        import core as core_mod

        db = sqlite3.connect(str(core_mod.DB_PATH))
        db.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY, text TEXT)")
        db.commit()
        db.close()
        fid = remember("works despite malformed schema")
        self.assertIsInstance(fid, int)
        self.assertEqual(recall("malformed schema")[0]["id"], fid)
        self.assertEqual(len(list(core_mod.STATE_DIR.glob("memory.db.corrupt-*"))), 1)

    def test_consolidate_corrupt_db_fails_open(self):
        import core as core_mod

        core_mod.DB_PATH.write_bytes(b"garbage bytes, not a db")
        result = consolidate(key="whatever-key")
        self.assertFalse(result["consolidated"])
        self.assertEqual(result["before"], 0)
        self.assertEqual(result["after"], 0)
        self.assertIsNone(result["error"])

    # ------------------------------------------------------------- consolidate
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

    # ---------------------------------------------------------------- load_key
    def test_load_key_missing_env_returns_none(self):
        self.assertIsNone(load_key(str(Path(self._tmp.name) / "nope.env")))

    def test_load_key_parses_value_and_strips_quotes(self):
        env = Path(self._tmp.name) / ".env"
        Path(env).write_text(
            'OPENCODE_GO_API_KEY = "my-secret-key"\n', encoding="utf-8"
        )
        self.assertEqual(load_key(str(env)), "my-secret-key")

    def test_load_key_skips_comments_and_other_vars(self):
        env = Path(self._tmp.name) / ".env"
        Path(env).write_text(
            "# a comment\nOTHER_VAR=zzz\n\nOPENCODE_GO_API_KEY='quoted-key'\n",
            encoding="utf-8",
        )
        self.assertEqual(load_key(str(env)), "quoted-key")


if __name__ == "__main__":
    unittest.main()
