"""skill-drafter tests — pure core + command handlers, no host needed.

Run: cd plugins/skill-drafter && python -m unittest tests.test_core -q
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(HERE)


def load_plugin_module():
    spec = importlib.util.spec_from_file_location(
        "skill_drafter_under_test", os.path.join(PLUGIN_DIR, "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, PLUGIN_DIR)
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


def transcript(goal="Set up a Python package and prove it installs",
               calls=6, errors=0):
    """Synthetic transcript: goal + N terminal calls (errors marked)."""
    entries = [{"role": "user", "content": goal}]
    for i in range(calls):
        entries.append({"role": "assistant", "content": f"step {i}",
                        "tool_calls": [{"name": "terminal",
                                        "arguments": {"command": f"echo step-{i}"}}]})
        is_err = i < errors
        entries.append({"role": "tool", "name": "terminal",
                        "content": "boom: failed" if is_err else "exit_code: 0",
                        "is_error": is_err})
    return entries


class DraftGateTests(unittest.TestCase):
    def test_draft_six_calls_returns_skill(self):
        draft = core.draft_skill(transcript(calls=6))
        self.assertIsNotNone(draft)
        self.assertIn("name", draft)
        self.assertIn("skill_md", draft)
        self.assertEqual(draft["success_calls"], 6)
        self.assertTrue(draft["skill_md"].startswith("---"))

    def test_draft_steps_carry_exact_commands(self):
        draft = core.draft_skill(transcript(calls=6))
        self.assertIn("Run `echo step-0` (via terminal).", draft["skill_md"])
        self.assertIn("Run `echo step-5` (via terminal).", draft["skill_md"])
        self.assertEqual(draft["steps"][0], "Run `echo step-0` (via terminal).")

    def test_draft_rejections_none_with_reason(self):
        # < 5 successful calls -> None + reason
        draft = core.draft_skill(transcript(calls=6, errors=2))
        self.assertIsNone(draft)
        self.assertIn("only 4 successful tool call(s)", core.draft_reason())
        checked = core.draft_skill_checked(transcript(calls=6, errors=2))
        self.assertFalse(checked["ok"])
        self.assertIn("4", checked["reason"])
        # empty transcript -> None + reason too
        self.assertIsNone(core.draft_skill([]))
        self.assertIn("empty transcript", core.draft_reason())

    def test_draft_error_calls_excluded_from_gate(self):
        # 7 calls, 2 failed -> 5 successful: gate passes but steps skip failures
        draft = core.draft_skill(transcript(calls=7, errors=2))
        self.assertIsNotNone(draft)
        self.assertEqual(draft["success_calls"], 5)
        self.assertNotIn("boom", draft["skill_md"])
        self.assertNotIn("step-0", draft["skill_md"])  # the 2 error calls were 0,1

    def test_draft_repeated_commands_deduped(self):
        t = [{"role": "user", "content": "List files"}]
        for cmd in ("echo a", "echo b", "echo c", "ls -la", "ls -la"):
            t.append({"role": "assistant", "content": cmd,
                      "tool_calls": [{"name": "terminal",
                                      "arguments": {"command": cmd}}]})
            t.append({"role": "tool", "name": "terminal",
                      "content": "exit_code: 0", "is_error": False})
        draft = core.draft_skill(t)
        self.assertIsNotNone(draft)
        self.assertEqual(draft["success_calls"], 5)
        self.assertEqual(len(draft["steps"]), 4)  # repeated `ls -la` collapsed
        procedure = draft["skill_md"].split("## Verification")[0]
        self.assertEqual(procedure.count("ls -la"), 1)


class DraftContentTests(unittest.TestCase):
    def test_draft_name_inferred_from_goal_line(self):
        draft = core.draft_skill(transcript(calls=5))
        self.assertEqual(draft["name"], "set-up-python-package")
        draft2 = core.draft_skill(transcript(goal="Debug the nightly cron failure", calls=5))
        self.assertEqual(draft2["name"], "debug-nightly-cron-failure")

    def test_draft_frontmatter_version_and_author(self):
        with mock.patch.dict(os.environ, {"XOMNI_USER": "Test Author"}, clear=False):
            draft = core.draft_skill(transcript(calls=5))
        self.assertIn('version: "1.0.0"', draft["skill_md"])
        self.assertIn('author: "Test Author"', draft["skill_md"])
        self.assertIn('name: set-up-python-package', draft["skill_md"])

    def test_draft_from_jsonl_file(self):
        tmp = tempfile.mkdtemp(prefix="skill-drafter-test-")
        try:
            path = os.path.join(tmp, "session.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for entry in transcript(calls=6):
                    f.write(json.dumps(entry) + "\n")
            entries = core.parse_transcript_file(path)
            self.assertEqual(len(entries), 13)
            draft = core.draft_skill(entries)
            self.assertIsNotNone(draft)
            self.assertEqual(draft["success_calls"], 6)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SaveTests(unittest.TestCase):
    def _draft_md(self):
        return core.draft_skill(transcript(calls=6))["skill_md"]

    def test_save_valid_draft_writes_skill(self):
        tmp = tempfile.mkdtemp(prefix="skill-drafter-save-")
        try:
            result = core.save_skill("set-up-python-package", self._draft_md(),
                                     skills_root=tmp, category="devops")
            self.assertTrue(result["ok"])
            self.assertEqual(result["verdict"], "PASS")
            self.assertTrue(os.path.isfile(os.path.join(
                result["dest"], "SKILL.md")))
            self.assertTrue(result["dest"].endswith(
                os.path.join("devops", "set-up-python-package")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_save_rejects_invalid_drafts(self):
        tmp = tempfile.mkdtemp(prefix="skill-drafter-save-")
        try:
            # dangerous body -> REJECT, nothing written
            evil = self._draft_md() + "\nrm -rf /tmp/x\n"
            result = core.save_skill("set-up-python-package", evil,
                                     skills_root=tmp, category="devops")
            self.assertFalse(result["ok"])
            self.assertEqual(result["verdict"], "REJECT")
            self.assertFalse(os.path.exists(os.path.join(
                tmp, "devops", "set-up-python-package")))
            # no frontmatter -> REJECT, nothing written
            bare = "no frontmatter\n\n## Procedure\n1. a\n2. b\n3. c\n"
            result2 = core.save_skill("anything", bare, skills_root=tmp)
            self.assertFalse(result2["ok"])
            self.assertEqual(result2["verdict"], "REJECT")
            self.assertFalse(os.path.exists(os.path.join(tmp, "anything")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ExportTests(unittest.TestCase):
    def test_export_session_missing_hermes_loud_error(self):
        with mock.patch.object(core.shutil, "which", return_value=None):
            result = core.export_session("abc123")
        self.assertFalse(result["ok"])
        self.assertIn("hermes sessions export abc123", result["reason"])
        self.assertIn("manually", result["reason"])  # loud, cause-naming

    def test_export_session_parses_exported_jsonl(self):
        exported = "\n".join(json.dumps(e) for e in transcript(calls=6))

        def fake(argv, **kw):
            return type("P", (), {"returncode": 0,
                                  "stdout": exported, "stderr": ""})()

        with mock.patch.object(core.shutil, "which", return_value="/fake/hermes"):
            result = core.export_session("abc123", runner=fake)
        self.assertTrue(result["ok"])
        draft = core.draft_skill(result["transcript"])
        self.assertIsNotNone(draft)
        self.assertEqual(draft["success_calls"], 6)


class DraftLastTests(unittest.TestCase):
    def test_draft_last_session_drafts_from_newest_session(self):
        fake = transcript(calls=6)
        with mock.patch.object(core, "list_session_ids",
                               return_value=["20260812_999999_000000"]), \
             mock.patch.object(core, "export_session",
                               return_value={"ok": True, "transcript": fake,
                                             "session_id": "20260812_999999_000000"}):
            result = core.draft_last_session()
        self.assertTrue(result["ok"])
        self.assertEqual(result["session_id"], "20260812_999999_000000")
        self.assertEqual(result["name"], "set-up-python-package")
        self.assertEqual(result["success_calls"], 6)

    def test_list_session_ids_parses_both_id_shapes(self):
        def fake(argv, **kw):
            return type("P", (), {"returncode": 0, "stderr": "",
                                  "stdout": ("Title  Workspace  Last Active  ID\n"
                                             "─────────────────────────────────\n"
                                             "top10-watch  —  7m ago  cron_49e3701733e8_20260812_151256\n"
                                             "—  Temp  4h ago  20260812_103607_b7524f\n")})()

        ids = core.list_session_ids(runner=fake)
        self.assertEqual(ids, ["cron_49e3701733e8_20260812_151256",
                               "20260812_103607_b7524f"])
        with mock.patch.object(core.shutil, "which", return_value=None):
            self.assertEqual(core.list_session_ids(), [])

    def test_draft_last_no_sessions_loud_error(self):
        with mock.patch.object(core, "list_session_ids", return_value=[]):
            result = core.draft_last_session()
        self.assertFalse(result["ok"])
        self.assertIn("no host sessions", result["reason"])

    def test_draft_last_skips_inflight_sessions(self):
        fake = transcript(calls=6)

        def fake_export(sid, **kw):
            if sid == "cron_20260812_153030_aaa":
                return {"ok": False, "session_id": sid,
                        "reason": "hermes sessions export returned no transcript entries for cron_20260812_153030_aaa"}
            return {"ok": True, "transcript": fake, "session_id": sid}

        with mock.patch.object(core, "list_session_ids",
                               return_value=["cron_20260812_153030_aaa",
                                             "cron_20260812_151256_bbb"]), \
             mock.patch.object(core, "export_session", side_effect=fake_export):
            result = core.draft_last_session()
        self.assertTrue(result["ok"])
        self.assertEqual(result["session_id"], "cron_20260812_151256_bbb")
        self.assertEqual(result["skipped"], ["cron_20260812_153030_aaa"])

    def test_draft_last_respects_limit_messages(self):
        big = []
        for i in range(110):
            big.append({"role": "assistant", "content": f"step {i}",
                        "tool_calls": [{"name": "terminal",
                                        "arguments": {"command": f"echo {i}"}}]})
            big.append({"role": "tool", "name": "terminal",
                        "content": "exit_code: 0"})
        captured = {}
        real = core.draft_skill_checked

        def spy(transcript, *a, **k):
            captured["n"] = len(transcript)
            return real(transcript, *a, **k)

        with mock.patch.object(core, "list_session_ids", return_value=["s1"]), \
             mock.patch.object(core, "export_session",
                               return_value={"ok": True, "transcript": big,
                                             "session_id": "s1"}), \
             mock.patch.object(core, "draft_skill_checked", side_effect=spy):
            core.draft_last_session(limit_messages=200)
        self.assertEqual(captured["n"], 200)


class HandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_plugin_module()

    def test_handler_save_unknown_draft_fails_loud(self):
        out = self.mod._handle_save("never-drafted")
        self.assertIn("FAILED", out)
        self.assertIn("unknown draft", out)

    def test_handler_draft_then_save_roundtrip(self):
        tmp = tempfile.mkdtemp(prefix="skill-drafter-handler-")
        try:
            fixture = os.path.join(HERE, os.pardir, "examples",
                                   "session-6calls.jsonl")
            out = self.mod._handle_draft(fixture)
            self.assertIn("DRAFT set-up-python-package", out)
            self.assertIn("approve with: /skill save set-up-python-package", out)
            saved = self.mod._handle_save(
                f"set-up-python-package --target={tmp} --category=devops")
            self.assertIn("saved: set-up-python-package", saved)
            self.assertTrue(os.path.isfile(os.path.join(
                tmp, "devops", "set-up-python-package", "SKILL.md")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_handler_save_yes_writes_host_skills_dir_flat(self):
        tmp = tempfile.mkdtemp(prefix="skill-drafter-yes-")
        try:
            fixture = os.path.join(HERE, os.pardir, "examples",
                                   "session-6calls.jsonl")
            self.mod._handle_draft(fixture)
            with mock.patch.object(self.mod.core, "DEFAULT_SKILLS_ROOT", tmp):
                out = self.mod._handle_save("set-up-python-package --yes")
            self.assertIn("saved: set-up-python-package", out)
            self.assertIn("host skills dir", out)
            dest = os.path.join(tmp, "set-up-python-package", "SKILL.md")
            self.assertTrue(os.path.isfile(dest))
            self.assertFalse(os.path.isdir(os.path.join(tmp, "auto-drafted")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class LifecycleTests(unittest.TestCase):
    """U-SURF-2 — lifecycle() one-call pipeline."""

    class FakeReceipts:
        def try_file_receipt(self, action, target, result, meta=None, path=None):
            return {"id": "Rtest0001", "action": action, "target": target,
                    "result": result, "meta": meta or {},
                    "handle": "sha256:" + "0" * 64}

    class FakeOmni:
        @staticmethod
        def build_publish_command(skill_dir, target="github"):
            return ["hermes", "skills", "publish", "--to", target, skill_dir]

    def test_12_lifecycle_happy_path_full_pipeline(self):
        tmp = tempfile.mkdtemp(prefix="skill-drafter-lifecycle-")
        try:
            with mock.patch.object(core, "DEFAULT_SKILLS_ROOT", tmp), \
                 mock.patch.object(core, "receipts_core",
                                   return_value=self.FakeReceipts()), \
                 mock.patch.object(core, "omni_skills_core",
                                   return_value=self.FakeOmni()):
                result = core.lifecycle(transcript(calls=6))
            self.assertTrue(result["ok"])
            self.assertEqual(result["name"], "set-up-python-package")
            names = [s["step"] for s in result["steps"]]
            self.assertEqual(names, ["draft", "validate", "save", "receipt",
                                     "publish"])
            self.assertEqual(result["steps"][0]["status"], "ok")
            self.assertEqual(result["steps"][1]["status"], "PASS")
            self.assertEqual(result["steps"][2]["status"], "ok")
            self.assertEqual(result["steps"][3]["status"], "ok")
            self.assertTrue(result["saved"]["ok"])
            saved_md = os.path.join(result["saved"]["dest"], "SKILL.md")
            self.assertTrue(os.path.isfile(saved_md))
            # flat host-skills-dir layout, no category dir
            self.assertEqual(result["saved"]["dest"], os.path.join(
                tmp, "set-up-python-package"))
            self.assertEqual(result["receipt"]["id"], "Rtest0001")
            self.assertEqual(result["receipt"]["action"], "skill.save")
            # publish offer carries the omni-skills delegated command
            self.assertEqual(result["publish_offer"]["command"][:4],
                             ["hermes", "skills", "publish", "--to"])
            self.assertIn("/skills publish", result["publish_offer"]["hint"])
            self.assertEqual(result["steps"][4]["step"], "publish")
            self.assertEqual(result["steps"][4]["status"], "offer")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_13_lifecycle_validate_blocks_reject(self):
        tmp = tempfile.mkdtemp(prefix="skill-drafter-lifecycle-")
        try:
            # a transcript whose successful calls carry destructive commands —
            # the DRAFT passes the gate but validate_draft must REJECT it
            evil_entries = [{"role": "user", "content": "Clean temp dirs"}]
            for i in range(6):
                evil_entries.append({"role": "assistant", "content": f"step {i}",
                                     "tool_calls": [{"name": "terminal",
                                                     "arguments": {"command": f"rm -rf /tmp/x{i}"}}]})
                evil_entries.append({"role": "tool", "name": "terminal",
                                     "content": "exit_code: 0", "is_error": False})
            with mock.patch.object(core, "DEFAULT_SKILLS_ROOT", tmp), \
                 mock.patch.object(core, "receipts_core",
                                   return_value=self.FakeReceipts()):
                result = core.lifecycle(evil_entries)
            # REJECT must stop before save/receipt/publish
            self.assertFalse(result["ok"])
            self.assertEqual(result["verdict"], "REJECT")
            step_names = [s["step"] for s in result["steps"]]
            self.assertIn("validate", step_names)
            self.assertNotIn("save", step_names)
            self.assertNotIn("receipt", step_names)
            self.assertNotIn("publish", step_names)
            self.assertIsNone(result.get("saved"))
            self.assertEqual(os.listdir(tmp), [])  # nothing written at all
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_14_lifecycle_receipt_emitted_and_skipped_gracefully(self):
        tmp = tempfile.mkdtemp(prefix="skill-drafter-lifecycle-")
        try:
            with mock.patch.object(core, "DEFAULT_SKILLS_ROOT", tmp), \
                 mock.patch.object(core, "receipts_core",
                                   return_value=self.FakeReceipts()):
                emitted = core.lifecycle(transcript(calls=6))
            self.assertTrue(emitted["ok"])
            self.assertIsNotNone(emitted["receipt"])
            self.assertEqual(emitted["steps"][3]["status"], "ok")
            # receipts unavailable -> skipped gracefully, pipeline still OK
            with mock.patch.object(core, "DEFAULT_SKILLS_ROOT", tmp), \
                 mock.patch.object(core, "receipts_core", return_value=None):
                skipped = core.lifecycle(transcript(calls=6))
            self.assertTrue(skipped["ok"])
            self.assertIsNone(skipped["receipt"])
            self.assertEqual(skipped["steps"][3]["status"], "skipped")
            self.assertIn("skipped gracefully", skipped["steps"][3]["detail"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_15_from_session_wiring(self):
        mod = load_plugin_module()
        tmp = tempfile.mkdtemp(prefix="skill-drafter-fromsession-")
        try:
            with mock.patch.object(core, "DEFAULT_SKILLS_ROOT", tmp), \
                 mock.patch.object(core, "export_session",
                                   return_value={"ok": True,
                                                 "transcript": transcript(calls=6),
                                                 "session_id": "20260813_000000_abc123"}), \
                 mock.patch.object(core, "receipts_core",
                                   return_value=self.FakeReceipts()), \
                 mock.patch.object(core, "omni_skills_core",
                                   return_value=self.FakeOmni()):
                out = mod._handle_from_session("20260813_000000_abc123")
            self.assertIn("DRAFT set-up-python-package", out)
            self.assertIn("--- SKILL.md ---", out)
            self.assertIn("name: set-up-python-package", out)
            self.assertIn("SAVED ->", out)
            self.assertIn(tmp, out)
            self.assertIn("RECEIPT Rtest0001", out)
            self.assertIn("PUBLISH OFFER: hermes skills publish --to github",
                          out)
            self.assertTrue(os.path.isfile(os.path.join(
                tmp, "set-up-python-package", "SKILL.md")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SyncTests(unittest.TestCase):
    """U-SURF-2 — cross-profile sync: diff math + no-clobber."""

    @staticmethod
    def _skill_md(name, version="1.0.0", extra=""):
        return (f"---\nname: {name}\ndescription: \"Test skill {name}.\"\n"
                f"version: \"{version}\"\n---\n# {name}\n"
                f"1. do a\n2. do b\n3. do c\n{extra}\n")

    def _roots(self):
        src = tempfile.mkdtemp(prefix="skill-drafter-sync-src-")
        dst = tempfile.mkdtemp(prefix="skill-drafter-sync-dst-")
        # alpha: only in src -> added
        os.makedirs(os.path.join(src, "alpha"))
        with open(os.path.join(src, "alpha", "SKILL.md"), "w",
                  encoding="utf-8") as f:
            f.write(self._skill_md("alpha"))
        # shared: identical on both sides -> skipped
        for root in (src, dst):
            os.makedirs(os.path.join(root, "shared"))
            with open(os.path.join(root, "shared", "SKILL.md"), "w",
                      encoding="utf-8") as f:
                f.write(self._skill_md("shared"))
        # conflict: differs -> updated, never clobbered
        for root, ver in ((src, "1.0.0"), (dst, "2.0.0")):
            os.makedirs(os.path.join(root, "conflict"))
            with open(os.path.join(root, "conflict", "SKILL.md"), "w",
                      encoding="utf-8") as f:
                f.write(self._skill_md("conflict", version=ver))
        # only-dst: untouched by the sync
        os.makedirs(os.path.join(dst, "only-dst"))
        with open(os.path.join(dst, "only-dst", "SKILL.md"), "w",
                  encoding="utf-8") as f:
            f.write(self._skill_md("only-dst"))
        return src, dst

    def test_16_sync_diff_math_and_no_clobber(self):
        src, dst = self._roots()
        try:
            result = core.sync_skills(src, dst)
            self.assertTrue(result["ok"])
            self.assertEqual([r for r, _ in result["added"]], ["alpha"])
            self.assertEqual([r for r, _ in result["updated"]], ["conflict"])
            self.assertEqual(result["skipped"], ["shared"])
            # alpha copied
            self.assertTrue(os.path.isfile(os.path.join(
                dst, "alpha", "SKILL.md")))
            # conflict NOT clobbered — dst keeps v2.0.0
            with open(os.path.join(dst, "conflict", "SKILL.md"),
                      encoding="utf-8") as f:
                self.assertIn('version: "2.0.0"', f.read())
            # only-dst untouched
            self.assertTrue(os.path.isfile(os.path.join(
                dst, "only-dst", "SKILL.md")))
            # second run is idempotent: alpha now identical -> skipped
            again = core.sync_skills(src, dst)
            self.assertEqual(again["added"], [])
            self.assertEqual([r for r, _ in again["updated"]], ["conflict"])
            self.assertEqual(sorted(again["skipped"]), ["alpha", "shared"])
        finally:
            shutil.rmtree(src, ignore_errors=True)
            shutil.rmtree(dst, ignore_errors=True)

    def test_16b_sync_dry_run_writes_nothing(self):
        src, dst = self._roots()
        try:
            result = core.sync_skills(src, dst, dry_run=True)
            self.assertTrue(result["dry_run"])
            self.assertEqual([r for r, _ in result["added"]], ["alpha"])
            self.assertFalse(os.path.exists(os.path.join(dst, "alpha")))
            with open(os.path.join(dst, "conflict", "SKILL.md"),
                      encoding="utf-8") as f:
                self.assertIn('version: "2.0.0"', f.read())
        finally:
            shutil.rmtree(src, ignore_errors=True)
            shutil.rmtree(dst, ignore_errors=True)

    def test_16c_sync_cross_profile_bidirectional(self):
        src, dst = self._roots()
        try:
            # both directions: alpha goes src->dst, only-dst comes dst->src
            result = core.sync_cross_profile(host_root=src,
                                             profile_root=dst,
                                             direction="both")
            self.assertTrue(result["ok"])
            self.assertEqual(len(result["passes"]), 2)
            h2x, x2h = result["passes"]
            self.assertEqual(h2x[0], "host->xomni")
            self.assertEqual([r for r, _ in h2x[1]["added"]], ["alpha"])
            self.assertEqual(x2h[0], "xomni->host")
            self.assertEqual([r for r, _ in x2h[1]["added"]], ["only-dst"])
            # conflict stays v2.0.0 in dst and v1.0.0 in src — no clobber
            with open(os.path.join(dst, "conflict", "SKILL.md"),
                      encoding="utf-8") as f:
                self.assertIn('version: "2.0.0"', f.read())
            with open(os.path.join(src, "conflict", "SKILL.md"),
                      encoding="utf-8") as f:
                self.assertIn('version: "1.0.0"', f.read())
            # bad direction -> loud failure
            bad = core.sync_cross_profile(host_root=src, profile_root=dst,
                                          direction="sideways")
            self.assertFalse(bad["ok"])
            self.assertIn("unknown direction", bad["reason"])
        finally:
            shutil.rmtree(src, ignore_errors=True)
            shutil.rmtree(dst, ignore_errors=True)


class LifecycleFlagsTests(unittest.TestCase):
    """U-SURF-2 — step flags: --no-save preview, --no-publish, zero hooks."""

    class FakeReceipts:
        issued = []

        def try_file_receipt(self, action, target, result, meta=None, path=None):
            self.issued.append(target)
            return {"id": "Rflag0001", "action": action, "target": target,
                    "result": result, "meta": meta or {},
                    "handle": "sha256:" + "1" * 64}

    def test_17_no_save_preview_writes_nothing(self):
        tmp = tempfile.mkdtemp(prefix="skill-drafter-preview-")
        try:
            fake = self.FakeReceipts()
            with mock.patch.object(core, "DEFAULT_SKILLS_ROOT", tmp), \
                 mock.patch.object(core, "receipts_core", return_value=fake), \
                 mock.patch.object(core, "omni_skills_core",
                                   return_value=LifecycleTests.FakeOmni()):
                result = core.lifecycle(transcript(calls=6), save=False)
            self.assertTrue(result["ok"])
            self.assertIsNone(result["saved"])
            self.assertIsNone(result["receipt"])
            statuses = {s["step"]: s["status"] for s in result["steps"]}
            self.assertEqual(statuses["save"], "skipped")
            self.assertEqual(statuses["receipt"], "skipped")
            self.assertEqual(statuses["publish"], "offer")
            self.assertEqual(fake.issued, [])  # no receipt for a preview
            self.assertEqual(os.listdir(tmp), [])  # literally nothing written
            # --no-publish: offer suppressed
            with mock.patch.object(core, "DEFAULT_SKILLS_ROOT", tmp), \
                 mock.patch.object(core, "receipts_core", return_value=fake):
                result2 = core.lifecycle(transcript(calls=6), publish=False)
            self.assertTrue(result2["ok"])
            self.assertIsNone(result2["publish_offer"])
            self.assertEqual(
                {s["step"]: s["status"] for s in result2["steps"]}["publish"],
                "skipped")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_18_zero_hooks(self):
        # the plugin registers commands only — no register_hook anywhere
        with open(os.path.join(PLUGIN_DIR, "__init__.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("register_hook", src)
        # register() with a ctx that fails loudly on any hook registration
        mod = load_plugin_module()

        class Ctx:
            def __init__(self):
                self.commands = []

            def register_command(self, name, handler=None, description="",
                                 args_hint=""):
                self.commands.append(name)

            def register_hook(self, *a, **k):
                raise AssertionError("register_hook must never be called")

            def register_tool(self, *a, **k):
                raise AssertionError("register_tool must never be called")

        ctx = Ctx()
        mod.register(ctx)
        self.assertIn("skill", ctx.commands)
        self.assertIn("skill-from-session", ctx.commands)
        self.assertIn("skill-sync", ctx.commands)


if __name__ == "__main__":
    unittest.main()
