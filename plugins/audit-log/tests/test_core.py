"""audit-log tests — append/query roundtrips, hash-chain tamper detection,
corrupt-line resilience, filters, env override of the ledger path.

Pure core tests (no host): the ledger lives at a tempfile path via the
XOMNI_AUDIT_FILE override so tests never touch the real ~/.xomni-audit.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402


def _tmp_ledger_path():
    d = tempfile.mkdtemp(prefix="xomni-audit-test-")
    return os.path.join(d, "audit.jsonl"), d


class AuditTests(unittest.TestCase):
    def setUp(self):
        self._old_env = os.environ.get("XOMNI_AUDIT_FILE")
        self.ledger_file, self._tmpdir = _tmp_ledger_path()
        os.environ["XOMNI_AUDIT_FILE"] = self.ledger_file
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        if self._old_env is None:
            os.environ.pop("XOMNI_AUDIT_FILE", None)
        else:
            os.environ["XOMNI_AUDIT_FILE"] = self._old_env

    def _append_three(self, ledger=None):
        ledger = ledger or core.AuditLog()
        return [
            ledger.append("alice", "login", "session", "ok"),
            ledger.append("bob", "payment.capture", "order-42", "ok",
                          {"amount": 100}),
            ledger.append("alice", "logout", "session", "ok"),
        ]

    # ── append / roundtrip ───────────────────────────────────────────────
    def test_append_returns_full_record(self):
        rec = core.AuditLog().append("alice", "login", "session", "ok")
        for key in ("id", "ts", "actor", "action", "target", "result",
                    "prev_hash", "hash"):
            self.assertIn(key, rec)
        self.assertEqual(rec["actor"], "alice")
        self.assertEqual(rec["prev_hash"], "")   # genesis record
        self.assertEqual(len(rec["hash"]), 64)   # sha256 hex

    def test_append_and_reload_from_disk(self):
        recs = self._append_three()
        fresh = core.AuditLog()                  # new instance, same file
        got = fresh.query()
        self.assertEqual(len(got), 3)
        self.assertEqual(got[0]["id"], recs[-1]["id"])   # newest first
        self.assertEqual(fresh.count(), 3)

    def test_default_result_and_meta(self):
        rec = core.AuditLog().append("alice", "login", "session")
        self.assertEqual(rec["result"], "")
        self.assertEqual(rec["meta"], {})

    # ── hash chain ───────────────────────────────────────────────────────
    def test_hash_chain_links_records(self):
        recs = self._append_three()
        self.assertEqual(recs[1]["prev_hash"], recs[0]["hash"])
        self.assertEqual(recs[2]["prev_hash"], recs[1]["hash"])

    def test_hash_chain_integrity(self):
        self._append_three()
        ok, bad = core.AuditLog().verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(bad)

    def test_tamper_detection(self):
        """Edit a middle record's 'result' in the JSONL directly — the chain
        must break at exactly that record (index 1)."""
        recs = self._append_three()
        lines = open(self.ledger_file, encoding="utf-8").read().splitlines()
        middle = json.loads(lines[1])
        middle["result"] = "ok-but-forged"
        lines[1] = json.dumps(middle, ensure_ascii=False)
        with open(self.ledger_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        ok, bad = core.AuditLog().verify_chain()
        self.assertFalse(ok)
        self.assertEqual(bad, 1)
        self.assertEqual(recs[1]["id"], middle["id"])

    def test_deleted_record_detected(self):
        """Deleting a middle line breaks the next record's prev_hash link."""
        self._append_three()
        lines = open(self.ledger_file, encoding="utf-8").read().splitlines()
        del lines[1]
        with open(self.ledger_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        ok, bad = core.AuditLog().verify_chain()
        self.assertFalse(ok)
        self.assertEqual(bad, 1)

    # ── corrupt lines ────────────────────────────────────────────────────
    def test_corrupt_line_skipped_and_counted(self):
        self._append_three()
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write("this is not json {{{ \n")
        log = core.AuditLog()
        self.assertEqual(log.corrupt_count(), 1)
        self.assertEqual(log.count(), 3)         # corrupt line skipped
        ok, bad = log.verify_chain()
        self.assertTrue(ok)                      # chain still intact
        self.assertIsNone(bad)

    # ── query ────────────────────────────────────────────────────────────
    def test_query_actor_filter(self):
        self._append_three()
        log = core.AuditLog()
        alice = log.query(actor="alice")
        self.assertEqual([r["actor"] for r in alice], ["alice", "alice"])
        bob = log.query(actor="bob", limit=10)
        self.assertEqual(len(bob), 1)
        self.assertEqual(bob[0]["action"], "payment.capture")

    def test_query_action_filter(self):
        self._append_three()
        log = core.AuditLog()
        self.assertEqual(len(log.query(action="login")), 1)
        self.assertEqual(len(log.query(action="nope")), 0)

    def test_query_limit_newest_first(self):
        self._append_three()
        log = core.AuditLog()
        two = log.query(limit=2)
        self.assertEqual(len(two), 2)
        self.assertEqual(two[0]["action"], "logout")   # newest first

    # ── env override / path ──────────────────────────────────────────────
    def test_env_override_of_ledger_path(self):
        ledger = core.AuditLog()
        self.assertEqual(ledger.path, self.ledger_file)
        self.assertNotEqual(
            os.path.dirname(self.ledger_file),
            os.path.expanduser("~/.xomni-audit"))
        ledger.append("sys", "boot", "host", "ok")
        self.assertTrue(os.path.isfile(self.ledger_file))

    def test_get_by_id(self):
        recs = self._append_three()
        got = core.AuditLog().get(recs[1]["id"])
        self.assertEqual(got["action"], "payment.capture")
        with self.assertRaises(core.AuditError):
            core.AuditLog().get("does-not-exist")

    def test_read_helpers_never_raise_on_missing_file(self):
        log = core.AuditLog()
        self.assertEqual(log.query(), [])
        self.assertEqual(log.count(), 0)
        self.assertEqual(log.corrupt_count(), 0)
        ok, bad = log.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(bad)


if __name__ == "__main__":
    unittest.main()
