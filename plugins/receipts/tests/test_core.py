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
import time
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

    # ── U-ASSURE-1: newly-wired mutating paths each emit a verifiable receipt ──
    def _load_plugin_init(self, name: str) -> object:
        plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                   "..", ".."))
        sys.path.insert(0, plugins_dir)
        import importlib.util
        mod_name = name.replace("-", "_") + "_init"
        spec = importlib.util.spec_from_file_location(
            mod_name, os.path.join(plugins_dir, name, "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_cli_providers_add_emits_verifiable_receipt(self):
        repo = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            "..", "..", ".."))
        sys.path.insert(0, repo)
        hermes_home = os.path.join(self._tmpdir, "hermes-home")
        os.makedirs(hermes_home, exist_ok=True)
        config = os.path.join(hermes_home, "config.yaml")
        with open(config, "w", encoding="utf-8") as f:
            f.write("providers:\n")
        old_cfg = os.environ.get("XOMNI_HERMES_CONFIG")
        old_home = os.environ.get("HERMES_HOME")
        # set env BEFORE importing xomni_cli: HERMES_HOME is captured in a
        # module constant at import time (config path is read at call time)
        os.environ["XOMNI_HERMES_CONFIG"] = config
        os.environ["HERMES_HOME"] = hermes_home
        self.addCleanup(self._restore, "XOMNI_HERMES_CONFIG", old_cfg)
        self.addCleanup(self._restore, "HERMES_HOME", old_home)
        import xomni_cli
        key_env = "XOMNI_TEST_%X" % int(time.time() * 1000)  # unique per run
        rc = xomni_cli.cmd_providers_add(
            ["my-test-provider", "https://example.com/v1",
             "--key-env", key_env, "--yes"])
        self.assertEqual(rc, 0)
        ledger = core.ReceiptLedger()
        recs = ledger.recent(10)
        actions = [r["action"] for r in recs]
        self.assertIn("provider.add", actions)
        pa = next(r for r in recs if r["action"] == "provider.add")
        self.assertEqual(pa["target"], config)
        self.assertTrue(pa["handle"].startswith("sha256:"))
        self.assertTrue(ledger.verify(pa["id"])["ok"])
        self.assertIn("provider.env", actions)  # .env placeholder append

    def _restore(self, key, old):
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old

    def test_skill_drafter_save_emits_verifiable_receipt(self):
        drafter = self._load_plugin_init("skill-drafter")
        skill_md = ("---\nname: demo-skill\ndescription: \"Demo skill\"\n"
                    "version: \"1.0.0\"\n---\n# Demo\n"
                    "1. Run `echo a` (via terminal).\n"
                    "2. Run `echo b` (via terminal).\n"
                    "3. Run `echo c` (via terminal).\n")
        drafter._DRAFTS["demo-skill"] = skill_md
        root = os.path.join(self._tmpdir, "skills")
        out = drafter._handle_save("demo-skill --yes --target=%s" % root)
        self.assertIn("OK", out)
        ledger = core.ReceiptLedger()
        rec = ledger.recent(1)[0]
        self.assertEqual(rec["action"], "skill.draft.save")
        self.assertTrue(rec["handle"].startswith("sha256:"))
        self.assertTrue(os.path.isfile(rec["target"]))
        self.assertTrue(ledger.verify(rec["id"])["ok"])

    def test_omni_skills_publish_emits_verifiable_receipt(self):
        skill_dir = os.path.join(self._tmpdir, "pub-skill")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: pub-skill\ndescription: \"Publish demo\"\n"
                    "version: \"1.0.0\"\n---\n# Pub\nReceipt for publish.\n")
        repo = os.path.join(self._tmpdir, "market-repo")
        os.makedirs(repo)
        omni = self._load_omni_skills_init()
        # force the repo-copy fallback so no real host publish runs
        with mock.patch.object(omni.core, "host_publish_available",
                               return_value=(False, "test forces repo-copy")):
            out = omni._handle_publish("%s --repo=%s --yes" % (skill_dir, repo))
        self.assertIn("OK", out)
        ledger = core.ReceiptLedger()
        rec = ledger.recent(1)[0]
        self.assertEqual(rec["action"], "skill.publish")
        self.assertTrue(rec["handle"].startswith("sha256:"))
        self.assertTrue(os.path.isfile(rec["target"]))
        self.assertTrue(ledger.verify(rec["id"])["ok"])
        self.assertTrue(os.path.isfile(
            os.path.join(repo, "skills", "general", "pub-skill", "SKILL.md")))

    def test_receipts_audit_reports_all_covered_and_flags_stub_gap(self):
        repo = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            "..", "..", ".."))
        res = core.audit_coverage(repo_root=repo)
        self.assertEqual(res["total"], len(core.MUTATING_PATHS))
        gaps = [r["command"] for r in res["rows"] if not r["covered"]]
        self.assertEqual(gaps, [], "every mutating command must emit a receipt")
        self.assertEqual(res["unlisted"], [], "no handler may write without a receipt")
        text = core.audit_text(res)
        self.assertIn("RECEIPTS AUDIT", text)
        # missing-path detection: a fake stub handler that writes without a
        # receipt is flagged loud by the inventory row AND the write scan
        fake = os.path.join(self._tmpdir, "fake-repo")
        os.makedirs(os.path.join(fake, "xomni_cli"))
        with open(os.path.join(fake, "xomni_cli", "__init__.py"), "w",
                  encoding="utf-8") as f:
            f.write("def cmd_good():\n    _receipt_file('x', 't', 'r')\n\n"
                    "def cmd_bad():\n    with open('out.txt', 'w') as fh:\n"
                    "        fh.write('x')\n")
        inv = [("fake.good", "xomni_cli/__init__.py", "cmd_good", "x"),
               ("fake.bad", "xomni_cli/__init__.py", "cmd_bad", "y")]
        res2 = core.audit_coverage(repo_root=fake, inventory=inv)
        self.assertEqual(res2["covered"], 1)
        bad = next(r for r in res2["rows"] if r["command"] == "fake.bad")
        self.assertFalse(bad["covered"])
        self.assertTrue(any(f["func"] == "cmd_bad" for f in res2["unlisted"]))
        t2 = core.audit_text(res2)
        self.assertIn("GAP", t2)
        self.assertIn("UNLISTED WRITE PATHS", t2)


if __name__ == "__main__":
    unittest.main()
