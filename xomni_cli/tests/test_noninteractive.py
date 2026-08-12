"""U3 — non-interactive everything: --yes accepted, NO silent cancels.

Every mutating CLI command must:
  * accept --yes / -y (never block on a prompt);
  * on failure, exit non-zero with a loud error NAMING the cause (no raw
    tracebacks, no bare `return 0` after a failed install).

Covers the CLI surface of docs/NONINTERACTIVE.md: plugins install,
skill install, providers add, add <stack>, launch. All targets are mocked
temp dirs — nothing touches the real HERMES_HOME.
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import xomni_cli  # noqa: E402
from xomni_cli import main, cmd_plugins_install, cmd_skill_install, cmd_providers_add  # noqa: E402


def _good_skill(root: str, name: str = "u3-skill") -> str:
    d = os.path.join(root, name)
    os.makedirs(d)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(f"---\nname: {name}\ndescription: harmless u3 demo\n---\n# Demo\n")
    return d


class U3NonInteractiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="xomni-u3-")
        self._buf = io.StringIO()
        self._stdout = contextlib.redirect_stdout(self._buf)
        self._stdout.__enter__()

    def tearDown(self):
        self._stdout.__exit__(None, None, None)
        os.environ.pop("XOMNI_HERMES_CONFIG", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _out(self) -> str:
        return self._buf.getvalue()

    # ── plugins install ──────────────────────────────────────────────────
    def test_plugins_install_yes_accepted_and_installs(self):
        src = os.path.join(self.tmp, "fake-plugin")
        os.makedirs(src)
        with open(os.path.join(src, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("PLUGIN = True\n")
        target = os.path.join(self.tmp, "hermes-plugins")
        with mock.patch.object(xomni_cli, "HERMES_PLUGINS_DIR", target), \
             mock.patch.object(xomni_cli, "_plugin_dir", return_value=src):
            rc = cmd_plugins_install(["--yes", "fake-plugin"])
        self.assertEqual(rc, 0)
        self.assertIn("installed: fake-plugin", self._out())
        self.assertTrue(os.path.isfile(os.path.join(target, "fake-plugin", "__init__.py")))

    def test_plugins_install_unknown_plugin_loud(self):
        with mock.patch.object(xomni_cli, "HERMES_PLUGINS_DIR",
                               os.path.join(self.tmp, "hp")):
            rc = cmd_plugins_install(["--yes", "ghost-plugin"])
        self.assertEqual(rc, 1)
        out = self._out()
        self.assertIn("ghost-plugin", out)
        self.assertIn("unknown plugin", out)

    def test_plugins_install_uncreatable_dir_loud(self):
        target = os.path.join(self.tmp, "hp")  # nonexistent -> makedirs is called
        with mock.patch.object(xomni_cli, "HERMES_PLUGINS_DIR", target), \
             mock.patch.object(xomni_cli.os, "makedirs",
                               side_effect=PermissionError("read-only target")):
            rc = cmd_plugins_install(["--yes", "anything"])
        self.assertEqual(rc, 1)
        self.assertIn("cannot create", self._out())

    # ── skill install ────────────────────────────────────────────────────
    def test_skill_install_yes_missing_dir_loud(self):
        rc = cmd_skill_install("--yes /nonexistent-u3-dir")
        self.assertEqual(rc, 1)
        out = self._out()
        self.assertIn("not a directory", out)
        self.assertIn("/nonexistent-u3-dir", out)

    def test_skill_install_yes_accepted_and_installs(self):
        good = _good_skill(self.tmp)
        target = os.path.join(self.tmp, "target")
        with mock.patch.object(xomni_cli, "HERMES_SKILLS_DIR", target):
            rc = cmd_skill_install("--yes " + good)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(target, "u3-skill", "SKILL.md")))

    def test_skill_install_missing_core_loud(self):
        good = _good_skill(self.tmp)
        with mock.patch.object(xomni_cli, "_load_omni_skills_core",
                               side_effect=ImportError("omni-skills core not found")):
            rc = cmd_skill_install(good)
        self.assertEqual(rc, 1)
        self.assertIn("FAILED", self._out())
        self.assertIn("omni-skills core not found", self._out())

    # ── providers add ────────────────────────────────────────────────────
    def test_providers_add_unwritable_env_loud(self):
        config = os.path.join(self.tmp, "config.yaml")
        with open(config, "w", encoding="utf-8") as f:
            f.write("providers:\n  opencode-go:\n    request_timeout_seconds: 120\n")
        os.environ["XOMNI_HERMES_CONFIG"] = config
        with mock.patch.object(xomni_cli, "_env_path", return_value=self.tmp):
            # self.tmp is a directory -> open(..., "a") raises IsADirectoryError
            rc = cmd_providers_add(["envbad", "https://x.example/v1", "--yes"])
        self.assertEqual(rc, 1)
        out = self._out()
        self.assertIn("FAILED", out)
        self.assertIn(".env not writable", out)
        self.assertIn("envbad:", open(config, encoding="utf-8").read())  # config write happened

    # ── add <stack> / main dispatch ──────────────────────────────────────
    def test_add_yes_without_stack_name_usage(self):
        rc = main(["add", "--yes"])
        self.assertEqual(rc, 1)
        self.assertIn("usage: xomni add", self._out())

    def test_main_returns_subcommand_exit_code(self):
        self.assertEqual(main(["skill", "install", "/nonexistent-u3-dir"]), 1)
        with mock.patch.object(xomni_cli, "HERMES_PLUGINS_DIR",
                               os.path.join(self.tmp, "hp")):
            self.assertEqual(main(["plugins", "install", "--yes", "ghost-plugin"]), 1)

    # ── launch ───────────────────────────────────────────────────────────
    def test_launch_missing_hermes_loud(self):
        with mock.patch.object(xomni_cli.subprocess, "call",
                               side_effect=FileNotFoundError()):
            rc = main(["launch"])
        self.assertEqual(rc, 1)
        out = self._out()
        self.assertIn("launch: FAILED", out)
        self.assertIn("hermes binary was not found", out)

    def test_launch_propagates_host_exit_code(self):
        with mock.patch.object(xomni_cli.subprocess, "call", return_value=7):
            rc = main(["launch"])
        self.assertEqual(rc, 7)


if __name__ == "__main__":
    unittest.main()
