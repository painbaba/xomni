"""receipts tests — ledger issue/verify roundtrips, handle kinds, integration.

Pure core tests (no host) plus one end-to-end integration test that drives
the omni-skills /skills-install handler and asserts a verifiable receipt is
issued by default.
"""
import json
import os
import shlex
import shutil
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402


def _tmp_ledger_path():
    d = tempfile.mkdtemp(prefix="xomni-receipts-test-")
    return os.path.join(d, "ledger.jsonl"), d


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self._old_env = os.environ.get("XOMNI_RECEIPTS_FILE")
        self.ledger_file, self._tmpdir = _tmp_ledger_path()
        os.environ["XOMNI_RECEIPTS_FILE"] = self.ledger_file
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        if self._old_env is None:
            os.environ.pop("XOMNI_RECEIPTS_FILE", None)
        else:
            os.environ["XOMNI_RECEIPTS_FILE"] = self._old_env

    def _make_file(self, content=b"hello world\n"):
        p = os.path.join(self._tmpdir, "artifact.txt")
        with open(p, "wb") as f:
            f.write(content)
        return p

    # ── issue / roundtrip ────────────────────────────────────────────────
    def test_issue_returns_full_receipt(self):
        rec = core.ReceiptLedger().issue("test.action", "target-x", "ok", "exit:0:")
        self.assertTrue(rec["id"])
        self.assertTrue(rec["ts"])
        self.assertEqual(rec["action"], "test.action")
        self.assertEqual(rec["target"], "target-x")
        self.assertEqual(rec["result"], "ok")
        self.assertEqual(rec["handle"], "exit:0:")
        self.assertEqual(rec["meta"], {})

    def test_ledger_is_append_only_jsonl(self):
        ledger = core.ReceiptLedger()
        for i in range(3):
            ledger.issue("a.%d" % i, "t%d" % i, "ok", "exit:0:")
        with open(self.ledger_file, encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        self.assertEqual(len(lines), 3)
        for i, line in enumerate(lines):
            rec = json.loads(line)
            self.assertEqual(rec["action"], "a.%d" % i)
        self.assertEqual(ledger.count(), 3)

    def test_get_missing_receipt_raises_loud(self):
        with self.assertRaises(core.ReceiptError):
            core.ReceiptLedger().get("R-does-not-exist")

    def test_recent_newest_first_and_limit(self):
        ledger = core.ReceiptLedger()
        ids = [ledger.issue("a", "t", "ok", "exit:0:")["id"] for _ in range(5)]
        recent = ledger.recent(3)
        self.assertEqual([r["id"] for r in recent], ids[-1:-4:-1])

    def test_corrupt_line_skipped_not_fatal(self):
        ledger = core.ReceiptLedger()
        ledger.issue("good.1", "t", "ok", "exit:0:")
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write("{torn-json-line\n")
        rec = ledger.issue("good.2", "t", "ok", "exit:0:")
        self.assertEqual(ledger.count(), 2)
        self.assertEqual(ledger.corrupt_count(), 1)
        self.assertEqual(ledger.get(rec["id"])["action"], "good.2")

    # ── sha256 handle ────────────────────────────────────────────────────
    def test_verify_sha256_ok_roundtrip(self):
        p = self._make_file()
        rec = core.ReceiptLedger().issue("file.write", p, "written",
                                         core.sha256_file(p))
        res = core.ReceiptLedger().verify(rec["id"])
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["evidence"]["expected"], res["evidence"]["actual"])

    def test_verify_sha256_fails_after_file_changed(self):
        p = self._make_file(b"original")
        rec = core.ReceiptLedger().issue("file.write", p, "written",
                                         core.sha256_file(p))
        with open(p, "wb") as f:
            f.write(b"tampered")
        res = core.ReceiptLedger().verify(rec["id"])
        self.assertFalse(res["ok"])
        self.assertNotEqual(res["evidence"]["expected"], res["evidence"]["actual"])

    def test_verify_sha256_fails_when_file_missing(self):
        p = self._make_file(b"will vanish")
        handle = core.sha256_file(p)  # hash computed while the file exists
        os.remove(p)
        rec = core.ReceiptLedger().issue("file.write", p, "written", handle)
        res = core.ReceiptLedger().verify(rec["id"])
        self.assertFalse(res["ok"])
        self.assertIn("missing", res["evidence"]["error"])

    # ── url handle (mocked network) ──────────────────────────────────────
    def test_verify_url_200_ok(self):
        class FakeResp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch.object(core.urllib.request, "urlopen",
                               return_value=FakeResp()) as m:
            rec = core.ReceiptLedger().issue("http.post", "http://example.com/x",
                                             "created", core.url_handle("http://example.com/x"))
            res = core.ReceiptLedger().verify(rec["id"])
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["evidence"]["status"], 200)
        m.assert_called_once()

    def test_verify_url_non_200_fails(self):
        def boom(*a, **k):
            raise urllib.error.HTTPError("http://example.com/x", 503,
                                         "Service Unavailable", None, None)

        with mock.patch.object(core.urllib.request, "urlopen", side_effect=boom):
            rec = core.ReceiptLedger().issue("http.post", "http://example.com/x",
                                             "created", core.url_handle("http://example.com/x"))
            res = core.ReceiptLedger().verify(rec["id"])
        self.assertFalse(res["ok"])
        self.assertEqual(res["evidence"]["status"], 503)

    # ── exit-code handle ─────────────────────────────────────────────────
    def test_verify_exit_handle_ok_and_recheckable(self):
        cmd = "%s -c %s" % (shlex.quote(sys.executable),
                            shlex.quote("import sys; sys.exit(0)"))
        rec = core.ReceiptLedger().issue("cmd.run", "demo", "ran", core.exit_handle(0, "done"),
                                         {"command": cmd})
        res = core.ReceiptLedger().verify(rec["id"])
        self.assertTrue(res["ok"])
        self.assertTrue(res["evidence"]["recheckable"])
        # recheck_exit re-runs the recorded command
        res2 = core.ReceiptLedger().verify(rec["id"], recheck_exit=True)
        self.assertTrue(res2["ok"], res2)
        self.assertEqual(res2["evidence"]["actual"], 0)

    def test_verify_exit_recheck_detects_mismatch(self):
        cmd = "%s -c %s" % (shlex.quote(sys.executable),
                            shlex.quote("import sys; sys.exit(3)"))
        rec = core.ReceiptLedger().issue("cmd.run", "demo", "ran", core.exit_handle(0, ""),
                                         {"command": cmd})
        res = core.ReceiptLedger().verify(rec["id"], recheck_exit=True)
        self.assertFalse(res["ok"])
        self.assertEqual(res["evidence"]["expected"], 0)
        self.assertEqual(res["evidence"]["actual"], 3)

    # ── loud errors + never-raise helpers ────────────────────────────────
    def test_verify_missing_receipt_raises_loud(self):
        with self.assertRaises(core.ReceiptError):
            core.ReceiptLedger().verify("R-nope")

    def test_malformed_handle_reports_not_ok(self):
        rec = core.ReceiptLedger().issue("x", "t", "ok", "bogus:handle")
        res = core.ReceiptLedger().verify(rec["id"])
        self.assertFalse(res["ok"])
        self.assertIn("unknown handle kind", res["evidence"]["error"])

    def test_try_helpers_never_raise(self):
        self.assertIsNone(core.try_file_receipt("file.write", "/no/such/file", "x"))
        self.assertIsNotNone(core.try_exit_receipt("cmd.run", "t", "ran", 0, "ok"))
        # ledger path whose parent is a file -> makedirs fails -> None, no raise
        blocker = os.path.join(self._tmpdir, "blocker")
        with open(blocker, "w", encoding="utf-8") as f:
            f.write("i am a file")
        self.assertIsNone(core.try_issue("x", "t", "r", "exit:0:",
                                         path=os.path.join(blocker, "l.jsonl")))


class IntegrationTests(unittest.TestCase):
    """End-to-end: omni-skills /skills-install issues a verifiable receipt."""

    def setUp(self):
        self._old_env = os.environ.get("XOMNI_RECEIPTS_FILE")
        self._tmpdir = tempfile.mkdtemp(prefix="xomni-receipts-int-")
        self.ledger_file = os.path.join(self._tmpdir, "ledger.jsonl")
        os.environ["XOMNI_RECEIPTS_FILE"] = self.ledger_file
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        if self._old_env is None:
            os.environ.pop("XOMNI_RECEIPTS_FILE", None)
        else:
            os.environ["XOMNI_RECEIPTS_FILE"] = self._old_env

    def _load_omni_skills_init(self):
        plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                   "..", ".."))
        sys.path.insert(0, plugins_dir)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "omni_skills_init", os.path.join(plugins_dir, "omni-skills", "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["omni_skills_init"] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_skill_install_emits_verifiable_receipt(self):
        skill_dir = os.path.join(self._tmpdir, "demo-skill")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: demo-skill\ndescription: \"Demo for U7 receipts.\"\n"
                    "version: \"1.0.0\"\n---\n# Demo\nReceipts by default.\n")
        target = os.path.join(self._tmpdir, "skills-root")
        omni = self._load_omni_skills_init()
        out = omni._handle_install("%s --target=%s" % (skill_dir, target))
        self.assertIn("OK", out)
        ledger = core.ReceiptLedger()
        self.assertEqual(ledger.count(), 1)
        rec = ledger.recent(1)[0]
        self.assertEqual(rec["action"], "skill.install")
        self.assertTrue(rec["handle"].startswith("sha256:"))
        self.assertTrue(os.path.isfile(rec["target"]))
        res = ledger.verify(rec["id"])
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["evidence"]["kind"], "sha256")


if __name__ == "__main__":
    unittest.main()
