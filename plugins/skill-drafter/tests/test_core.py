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


if __name__ == "__main__":
    unittest.main()
