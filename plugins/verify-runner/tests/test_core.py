"""Tests for verify-runner (core.py pure logic + __init__ plugin wiring).

Core tests import the pure stdlib module; wiring tests load the plugin
package the same way the host does (hermes_cli.plugins._load_directory_module:
importlib spec from the plugin dir's __init__.py with __path__ set) and drive
register()/handlers with a fake ctx. All tests are fast — real subprocesses
are tiny one-liners, everything else is mocked.
"""
import importlib.util
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

import core  # noqa: E402

PASS = {"ok": True, "exit_code": 0, "stdout_tail": "", "stderr_tail": "", "timed_out": False}
FAIL = {"ok": False, "exit_code": 1, "stdout_tail": "", "stderr_tail": "boom\n", "timed_out": False}


def _py(cmd_body: str) -> str:
    """A real, tiny python command string (shlex-safe on Windows paths)."""
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(cmd_body)}"


def _load_plugin_pkg():
    """Mirror hermes_cli.plugins._load_directory_module."""
    init_file = os.path.join(_PLUGIN_DIR, "__init__.py")
    spec = importlib.util.spec_from_file_location(
        "verify_runner_test", init_file,
        submodule_search_locations=[_PLUGIN_DIR],
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "verify_runner_test"
    mod.__path__ = [_PLUGIN_DIR]
    sys.modules["verify_runner_test"] = mod
    # Reuse the already-imported core module so patching core.* affects pkg.core.
    sys.modules["verify_runner_test.core"] = core
    spec.loader.exec_module(mod)
    return mod


pkg = _load_plugin_pkg()


class _FakeCtx:
    def __init__(self):
        self.commands = []
        self.tools = []

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands.append({"name": name, "handler": handler, "description": description, "args_hint": args_hint})

    def register_tool(self, name, toolset, schema, handler, **kwargs):
        self.tools.append({"name": name, "toolset": toolset, "schema": schema, "handler": handler, "kwargs": kwargs})


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

class DiscoverTestCommandTests(unittest.TestCase):
    """Mock shutil.which + os.path.exists per the spec."""

    def test_prefers_pytest_when_pytest_ini_exists(self):
        with mock.patch("core.os.path.exists", side_effect=lambda p: p == os.path.join("/proj", "pytest.ini")), \
                mock.patch("core.shutil.which", return_value=None):
            self.assertEqual(core.discover_test_command("/proj"), "pytest")

    def test_prefers_pytest_when_pyproject_toml_exists(self):
        with mock.patch("core.os.path.exists", side_effect=lambda p: p == os.path.join("/proj", "pyproject.toml")), \
                mock.patch("core.shutil.which", return_value=None):
            self.assertEqual(core.discover_test_command("/proj"), "pytest")

    def test_prefers_pytest_when_setup_cfg_exists(self):
        with mock.patch("core.os.path.exists", side_effect=lambda p: p == os.path.join("/proj", "setup.cfg")), \
                mock.patch("core.shutil.which", return_value=None):
            self.assertEqual(core.discover_test_command("/proj"), "pytest")

    def test_prefers_pytest_when_on_path(self):
        with mock.patch("core.os.path.exists", return_value=False), \
                mock.patch("core.shutil.which", return_value="C:/tools/pytest.exe"):
            self.assertEqual(core.discover_test_command("/proj"), "pytest")

    def test_falls_back_to_unittest(self):
        with mock.patch("core.os.path.exists", return_value=False), \
                mock.patch("core.shutil.which", return_value=None):
            self.assertEqual(core.discover_test_command("/proj"), "python -m unittest discover")


class DiscoverLintCommandTests(unittest.TestCase):
    def test_ruff_when_ruff_toml_exists(self):
        with mock.patch("core.os.path.exists", side_effect=lambda p: p == os.path.join("/proj", "ruff.toml")), \
                mock.patch("core.shutil.which", return_value=None):
            self.assertEqual(core.discover_lint_command("/proj"), "ruff check .")

    def test_ruff_when_dot_ruff_toml_exists(self):
        with mock.patch("core.os.path.exists", side_effect=lambda p: p == os.path.join("/proj", ".ruff.toml")), \
                mock.patch("core.shutil.which", return_value=None):
            self.assertEqual(core.discover_lint_command("/proj"), "ruff check .")

    def test_ruff_when_pyproject_has_tool_ruff(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "pyproject.toml"), "w", encoding="utf-8") as fh:
                fh.write("[tool.ruff]\nline-length = 100\n")
            with mock.patch("core.shutil.which", return_value=None):
                self.assertEqual(core.discover_lint_command(d), "ruff check .")

    def test_ruff_when_on_path(self):
        with mock.patch("core.os.path.exists", return_value=False), \
                mock.patch("core.shutil.which", return_value="C:/tools/ruff.exe"):
            self.assertEqual(core.discover_lint_command("/proj"), "ruff check .")

    def test_py_compile_fallback_compiles_changed_files(self):
        with mock.patch("core.changed_py_files", return_value=["C:/proj/a.py", "C:/proj/b.py"]), \
                mock.patch("core.os.path.exists", return_value=False), \
                mock.patch("core.shutil.which", return_value=None):
            cmd = core.discover_lint_command("/proj")
        self.assertTrue(cmd.startswith("python -m py_compile "))
        self.assertIn("a.py", cmd)
        self.assertIn("b.py", cmd)

    def test_py_compile_fallback_with_no_files(self):
        with mock.patch("core.changed_py_files", return_value=[]), \
                mock.patch("core.os.path.exists", return_value=False), \
                mock.patch("core.shutil.which", return_value=None):
            self.assertEqual(core.discover_lint_command("/proj"), "python -m py_compile")


class ChangedPyFilesTests(unittest.TestCase):
    def test_git_repo_detects_modified_and_untracked(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q"], cwd=d, check=True)
            subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=d, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=d, check=True)
            for name, content in (("app.py", "x = 1\n"), ("readme.md", "hi\n")):
                with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                    fh.write(content)
            subprocess.run(["git", "add", "."], cwd=d, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=d, check=True)
            with open(os.path.join(d, "app.py"), "a", encoding="utf-8") as fh:
                fh.write("y = 2\n")
            with open(os.path.join(d, "new.py"), "w", encoding="utf-8") as fh:
                fh.write("z = 3\n")
            files = core.changed_py_files(d)
        self.assertIn(os.path.join(d, "app.py"), files)
        self.assertIn(os.path.join(d, "new.py"), files)
        self.assertNotIn(os.path.join(d, "readme.md"), files)

    def test_non_repo_falls_back_to_tree_scan(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "src"))
            os.makedirs(os.path.join(d, "node_modules"))
            for rel in ("src/a.py", "b.py", "node_modules/junk.py"):
                with open(os.path.join(d, rel), "w", encoding="utf-8") as fh:
                    fh.write("")
            files = core.changed_py_files(d)
        self.assertIn(os.path.join(d, "src", "a.py"), files)
        self.assertIn(os.path.join(d, "b.py"), files)
        self.assertNotIn(os.path.join(d, "node_modules", "junk.py"), files)


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------

class RunCommandTests(unittest.TestCase):
    def _tmp(self):
        return tempfile.TemporaryDirectory()

    def test_success(self):
        with self._tmp() as d:
            res = core.run_command(_py("print('hello verify')"), d)
        self.assertTrue(res["ok"])
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("hello verify", res["stdout_tail"])
        self.assertFalse(res["timed_out"])

    def test_failure_exit_code(self):
        with self._tmp() as d:
            res = core.run_command(_py("import sys; sys.exit(3)"), d)
        self.assertFalse(res["ok"])
        self.assertEqual(res["exit_code"], 3)
        self.assertFalse(res["timed_out"])

    def test_captures_stderr(self):
        with self._tmp() as d:
            res = core.run_command(_py("import sys; sys.stderr.write('boom'); sys.exit(1)"), d)
        self.assertFalse(res["ok"])
        self.assertIn("boom", res["stderr_tail"])
        self.assertEqual(res["stdout_tail"], "")

    def test_timeout_never_hangs(self):
        argv = ["python", "-c", "print(1)"]
        exc = subprocess.TimeoutExpired(argv, timeout=0.01, output="partial out\n", stderr="")
        with mock.patch.object(core.subprocess, "run", side_effect=exc):
            res = core.run_command("python -c \"print(1)\"", os.getcwd())
        self.assertTrue(res["timed_out"])
        self.assertFalse(res["ok"])
        self.assertIsNone(res["exit_code"])
        self.assertIn("partial out", res["stdout_tail"])

    def test_command_not_found(self):
        with self._tmp() as d:
            res = core.run_command("definitely-not-a-real-cmd-xyz-123", d)
        self.assertFalse(res["ok"])
        self.assertIsNone(res["exit_code"])
        self.assertIn("command not found", res["stderr_tail"])
        self.assertFalse(res["timed_out"])

    def test_missing_cwd(self):
        res = core.run_command("pytest", "C:/no/such/dir-xyz-123")
        self.assertFalse(res["ok"])
        self.assertIn("working directory not found", res["stderr_tail"])

    def test_bad_command_string(self):
        with self._tmp() as d:
            res = core.run_command('python -c "unclosed', d)
        self.assertFalse(res["ok"])
        self.assertIn("bad command", res["stderr_tail"])

    def test_tail_truncated_to_3000(self):
        with self._tmp() as d:
            res = core.run_command(_py("import sys; sys.stdout.write('x' * 5000)"), d)
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["stdout_tail"]), 3000)
        self.assertEqual(res["stdout_tail"], "x" * 3000)


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------

class SummarizeTests(unittest.TestCase):
    def test_pass_shape(self):
        self.assertEqual(core.summarize(dict(PASS), "test"), "TEST PASS (exit 0)")

    def test_fail_shape_with_exit_and_detail(self):
        r = dict(PASS, ok=False, exit_code=1, stderr_tail="app.py:5: syntax error\n")
        s = core.summarize(r, "LINT")
        self.assertTrue(s.startswith("LINT FAIL (exit 1)"), s)
        self.assertIn("app.py:5: syntax error", s)

    def test_timeout_shape(self):
        r = dict(PASS, ok=False, exit_code=None, timed_out=True)
        self.assertEqual(core.summarize(r, "test"), "TEST TIMEOUT")

    def test_kind_uppercased_and_defaulted(self):
        self.assertEqual(core.summarize(dict(PASS), ""), "RUN PASS (exit 0)")

    def test_fail_without_exit_code(self):
        r = dict(PASS, ok=False, exit_code=None, stderr_tail="", timed_out=False)
        self.assertEqual(core.summarize(r, "lint"), "LINT FAIL")


# ---------------------------------------------------------------------------
# stdlib coverage (verify_coverage / parse_trace_summary / count_cover_file)
# ---------------------------------------------------------------------------

class CoverageTests(unittest.TestCase):
    """Coverage mode: trace-summary parsing, cover files, graceful edge cases.

    The e2e tests pin ``discover_test_command`` to unittest so results don't
    depend on whether pytest happens to be installed on the host.
    """

    def test_coverage_output_parses(self):
        """Trace summary rows + .cover files parse into exact per-file stats."""
        with tempfile.TemporaryDirectory() as d:
            sample = (
                "lines   cov%   module   (path)\n"
                f"   10   100%   argparse   ({os.path.join(d, '..', 'site-packages', 'argparse.py')})\n"
                f"    6   100%   mathy   ({os.path.join(d, 'mathy.py')})\n"
                f"   16    81%   test_mathy   ({os.path.join(d, 'test_mathy.py')})\n"
            )
            rows = core.parse_trace_summary(sample, d)
        self.assertEqual(len(rows), 2)
        self.assertEqual([os.path.basename(r["file"]) for r in rows], ["mathy.py", "test_mathy.py"])
        self.assertEqual(rows[0]["module"], "mathy")
        self.assertEqual(rows[0]["total"], 6)
        self.assertEqual(rows[0]["pct"], 100)
        self.assertEqual(rows[1]["pct"], 81)
        with tempfile.TemporaryDirectory() as d2:
            cover = os.path.join(d2, "mathy.cover")
            with open(cover, "w", encoding="utf-8") as fh:
                fh.write("    2: def add(a, b):\n")
                fh.write("    3:     return a + b\n")
                fh.write(">>>>>> def never():\n")
                fh.write("       \n")
            self.assertEqual(core.count_cover_file(cover), (2, 3))

    def test_verify_coverage_real_run_parses_rows(self):
        """End-to-end: a tiny project reports exact covered/total per file."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "mathy.py"), "w", encoding="utf-8") as fh:
                fh.write("def add(a, b):\n    return a + b\n\n\ndef never():\n    return 0\n")
            with open(os.path.join(d, "test_mathy.py"), "w", encoding="utf-8") as fh:
                fh.write(
                    "import unittest\n\n"
                    "from mathy import add\n\n\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_add(self):\n"
                    "        self.assertEqual(add(1, 2), 3)\n"
                )
            with mock.patch.object(core, "discover_test_command", return_value="python -m unittest discover"):
                res = core.verify_coverage(d)
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["exit_code"], 0)
        self.assertFalse(res["timed_out"])
        by_name = {os.path.basename(r["file"]): r for r in res["rows"]}
        self.assertIn("mathy.py", by_name)
        self.assertIn("test_mathy.py", by_name)
        row = by_name["mathy.py"]
        self.assertEqual(row["covered"], 3)  # def add, return a+b, def never (defs run at import)
        self.assertEqual(row["total"], 4)
        self.assertEqual(row["pct"], 75)
        test_row = by_name["test_mathy.py"]
        self.assertEqual(test_row["covered"], test_row["total"])  # fully covered
        self.assertEqual(test_row["pct"], 100)
        self.assertEqual(res["covered"], 3 + test_row["covered"])
        self.assertEqual(res["total"], res["covered"] + 1)  # mathy's one missing line

    def test_verify_coverage_missing_module_graceful(self):
        """A test importing a missing module → FAIL verdict, no exception."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "test_broken.py"), "w", encoding="utf-8") as fh:
                fh.write(
                    "import unittest\n"
                    "import definitely_missing_module_xyz\n\n\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_x(self):\n"
                    "        pass\n"
                )
            with mock.patch.object(core, "discover_test_command", return_value="python -m unittest discover"):
                res = core.verify_coverage(d)
        self.assertFalse(res["ok"])
        self.assertIsNotNone(res["exit_code"])
        self.assertNotEqual(res["exit_code"], 0)
        self.assertIn("definitely_missing_module_xyz", res["stderr_tail"])

    def test_verify_coverage_empty_project_graceful(self):
        """An empty directory → PASS verdict with zero rows, no exception."""
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(core, "discover_test_command", return_value="python -m unittest discover"):
                res = core.verify_coverage(d)
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["rows"], [])
        self.assertEqual(res["total"], 0)
        self.assertEqual(res["covered"], 0)
        self.assertEqual(res["pct"], 0.0)


# ---------------------------------------------------------------------------
# Plugin wiring: register() + handler routing
# ---------------------------------------------------------------------------

class PluginRoutingTests(unittest.TestCase):
    def setUp(self):
        self.ctx = _FakeCtx()
        pkg.register(self.ctx)

    def _tool(self):
        return next(t for t in self.ctx.tools if t["name"] == "verify_project")

    def _command(self):
        return next(c for c in self.ctx.commands if c["name"] == "verify")

    def test_registers_command_and_tool(self):
        self.assertIn("verify", [c["name"] for c in self.ctx.commands])
        self.assertIn("verify_project", [t["name"] for t in self.ctx.tools])
        self.assertEqual(self._tool()["toolset"], "file")
        self.assertEqual(self._tool()["kwargs"]["description"], "Run tests + lint in a project dir and return a PASS/FAIL verdict")

    def test_tool_handler_routes_dir_param(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(core, "run_command", side_effect=[PASS, PASS]) as rc, \
                    mock.patch.object(core, "discover_test_command", return_value="pytest"), \
                    mock.patch.object(core, "discover_lint_command", return_value="ruff"):
                out = self._tool()["handler"]({"dir": d})
        self.assertEqual(rc.call_count, 2)
        self.assertIn(f"VERIFY {d}", out)
        self.assertIn("TEST PASS", out)
        self.assertIn("LINT PASS", out)
        self.assertIn("VERDICT: PASS", out)

    def test_command_handler_routes_raw_arg(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(core, "run_command", side_effect=[PASS, PASS]), \
                    mock.patch.object(core, "discover_test_command", return_value="pytest"), \
                    mock.patch.object(core, "discover_lint_command", return_value="ruff"):
                out = self._command()["handler"](d)
        self.assertIn("VERDICT: PASS", out)

    def test_command_handler_defaults_to_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("verify_runner_test.os.getcwd", return_value=d), \
                    mock.patch.object(core, "run_command", return_value=PASS), \
                    mock.patch.object(core, "discover_test_command", return_value="pytest"), \
                    mock.patch.object(core, "discover_lint_command", return_value="ruff"):
                out = self._command()["handler"]("")
        self.assertIn(f"VERIFY {d}", out)
        self.assertIn("VERDICT: PASS", out)

    def test_command_handler_coverage_flag_routes(self):
        with mock.patch("verify_runner_test.verify_project", return_value="COVERAGE OK") as vp:
            out = self._command()["handler"]("--coverage /proj/x")
        vp.assert_called_once_with("/proj/x", coverage=True)
        self.assertEqual(out, "COVERAGE OK")

    def test_command_handler_plain_dir_is_not_coverage(self):
        with mock.patch("verify_runner_test.verify_project", return_value="VERIFY OK") as vp:
            out = self._command()["handler"]("/proj/x")
        vp.assert_called_once_with("/proj/x", coverage=False)
        self.assertEqual(out, "VERIFY OK")

    def test_tool_handler_routes_coverage_param(self):
        with mock.patch("verify_runner_test.verify_project", return_value="COVERAGE OK") as vp:
            out = self._tool()["handler"]({"dir": "/proj/x", "coverage": True})
        vp.assert_called_once_with("/proj/x", coverage=True)
        self.assertEqual(out, "COVERAGE OK")

    def test_verify_project_coverage_renders_rows(self):
        with tempfile.TemporaryDirectory() as d:
            fake = {
                "ok": True, "exit_code": 0, "timed_out": False,
                "rows": [
                    {"file": os.path.join(d, "mathy.py"), "module": "mathy",
                     "covered": 2, "total": 4, "pct": 50},
                ],
                "covered": 2, "total": 4, "pct": 50.0,
                "stdout_tail": "", "stderr_tail": "",
            }
            with mock.patch.object(core, "verify_coverage", return_value=fake):
                out = pkg.verify_project(d, coverage=True)
        self.assertIn("COVERAGE", out)
        self.assertIn("COVERAGE PASS (exit 0)", out)
        self.assertIn("2/4 lines", out)
        self.assertIn("50%", out)
        self.assertIn("TOTAL 2/4 lines (50.0%)", out)
        self.assertIn("VERDICT: PASS", out)

    def test_tool_handler_unknown_dir(self):
        out = self._tool()["handler"]({"dir": "C:/definitely/not/a/real/dir-xyz"})
        self.assertIn("not a directory", out)

    def test_command_handler_unknown_dir(self):
        out = self._command()["handler"]("C:/definitely/not/a/real/dir-xyz")
        self.assertIn("not a directory", out)

    def test_verify_project_unknown_dir(self):
        out = pkg.verify_project("C:/definitely/not/a/real/dir-xyz")
        self.assertIn("not a directory", out)

    def test_verify_project_includes_failing_tail(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(core, "run_command", side_effect=[FAIL, PASS]), \
                    mock.patch.object(core, "discover_test_command", return_value="pytest"), \
                    mock.patch.object(core, "discover_lint_command", return_value="ruff"):
                out = pkg.verify_project(d)
        self.assertIn("TEST FAIL", out)
        self.assertIn("--- TEST failing tail ---", out)
        self.assertIn("boom", out)
        self.assertIn("VERDICT: FAIL", out)

    def test_verify_project_skips_lint_when_not_configured(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(core, "run_command", return_value=PASS) as rc, \
                    mock.patch.object(core, "discover_test_command", return_value="pytest"), \
                    mock.patch.object(core, "discover_lint_command", return_value=""):
                out = pkg.verify_project(d)
        self.assertEqual(rc.call_count, 1)
        self.assertNotIn("LINT", out)
        self.assertIn("VERDICT: PASS", out)

    def test_verify_project_timeout_is_fail(self):
        tmo = dict(PASS, ok=False, exit_code=None, timed_out=True)
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(core, "run_command", side_effect=[tmo, PASS]), \
                    mock.patch.object(core, "discover_test_command", return_value="pytest"), \
                    mock.patch.object(core, "discover_lint_command", return_value="ruff"):
                out = pkg.verify_project(d)
        self.assertIn("TEST TIMEOUT", out)
        self.assertIn("VERDICT: FAIL", out)


# ---------------------------------------------------------------------------
# End-to-end (fast: real subprocesses are trivial commands)
# ---------------------------------------------------------------------------

class EndToEndTests(unittest.TestCase):
    def test_pass_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "test_trivial.py"), "w", encoding="utf-8") as fh:
                fh.write("import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1, 1)\n")
            out = pkg.verify_project(d)
        self.assertIn("TEST PASS", out)
        self.assertIn("LINT PASS", out)
        self.assertIn("VERDICT: PASS", out)

    def test_fail_verdict_shows_failing_tail(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "test_bad.py"), "w", encoding="utf-8") as fh:
                fh.write(
                    "import atexit\n"
                    "import os\n"
                    "import unittest\n"
                    "\n"
                    "atexit.register(lambda: os.write(2, b'AssertionError: 1 != 2\\n'))\n"
                    "\n"
                    "\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_fail(self):\n"
                    "        self.assertEqual(1, 2)\n"
                )
            out = pkg.verify_project(d)
        self.assertIn("TEST FAIL", out)
        self.assertIn("AssertionError", out)
        self.assertIn("VERDICT: FAIL", out)


if __name__ == "__main__":
    unittest.main()
