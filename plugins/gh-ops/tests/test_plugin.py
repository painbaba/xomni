"""Tests for the gh-ops plugin wiring layer: register(ctx), /gh handler routing, gh_ops tool handler."""
import importlib.util
import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_plugin():
    """Import ``gh-ops/__init__.py`` under the package name ``gh_ops``.

    The directory name contains a hyphen, so it cannot be imported by name;
    materialize the package namespace by hand so the plugin's own
    ``from . import core`` resolves to the same ``core`` module the
    core tests exercise.
    """
    if "gh_ops" not in sys.modules:
        pkg = types.ModuleType("gh_ops")
        pkg.__path__ = [PLUGIN_DIR]
        sys.modules["gh_ops"] = pkg
    if "gh_ops.core" not in sys.modules:
        spec = importlib.util.spec_from_file_location("gh_ops.core", os.path.join(PLUGIN_DIR, "core.py"))
        core_mod = importlib.util.module_from_spec(spec)
        sys.modules["gh_ops.core"] = core_mod
        spec.loader.exec_module(core_mod)
    spec = importlib.util.spec_from_file_location("gh_ops.__init__", os.path.join(PLUGIN_DIR, "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gh_ops.__init__"] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeCtx:
    """Minimal stand-in for PluginContext capturing registrations."""

    def __init__(self):
        self.commands = []
        self.tools = []

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands.append({"name": name, "handler": handler, "description": description, "args_hint": args_hint})

    def register_tool(self, name, toolset, schema, handler, **kwargs):
        self.tools.append({"name": name, "toolset": toolset, "schema": schema, "handler": handler, **kwargs})


class RegisterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin = load_plugin()

    def setUp(self):
        self.ctx = FakeCtx()
        self.plugin.register(self.ctx)

    def test_registers_gh_command(self):
        self.assertEqual(len(self.ctx.commands), 1)
        cmd = self.ctx.commands[0]
        self.assertEqual(cmd["name"], "gh")
        self.assertIn("prs", cmd["args_hint"])
        self.assertTrue(callable(cmd["handler"]))

    def test_registers_gh_ops_tool(self):
        self.assertEqual(len(self.ctx.tools), 1)
        tool = self.ctx.tools[0]
        self.assertEqual(tool["name"], "gh_ops")
        self.assertEqual(tool["toolset"], "gh_ops")
        self.assertEqual(tool["schema"]["required"], ["action"])
        self.assertEqual(
            tool["schema"]["properties"]["action"]["enum"],
            ["status", "prs", "issues", "me"],
        )
        self.assertTrue(callable(tool["handler"]))


class CommandHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin = load_plugin()

    def test_default_action_is_status(self):
        with mock.patch.object(self.plugin.core, "execute", return_value="ok") as m:
            out = self.plugin._handle_gh("")
        m.assert_called_once_with("status")
        self.assertEqual(out, "ok")

    def test_routes_action_and_repo(self):
        with mock.patch.object(self.plugin.core, "execute", return_value="ok") as m:
            self.plugin._handle_gh("prs cli/cli")
        m.assert_called_once_with("prs", "cli/cli")

    def test_action_without_repo(self):
        with mock.patch.object(self.plugin.core, "execute", return_value="ok") as m:
            self.plugin._handle_gh("issues")
        m.assert_called_once_with("issues", None)

    def test_case_insensitive(self):
        with mock.patch.object(self.plugin.core, "execute", return_value="ok") as m:
            self.plugin._handle_gh("  ME  ")
        m.assert_called_once_with("me", None)


class ToolHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin = load_plugin()

    def test_handler_signature_matches_registry_dispatch(self):
        # The registry calls handler(args, **kwargs) — args is the tool-args dict.
        with mock.patch.object(self.plugin.core, "execute", return_value="ok") as m:
            out = self.plugin._tool_gh_ops({"action": "prs", "repo": "cli/cli"})
        m.assert_called_once_with("prs", "cli/cli")
        self.assertEqual(out, "ok")

    def test_default_action_status(self):
        with mock.patch.object(self.plugin.core, "execute", return_value="ok") as m:
            self.plugin._tool_gh_ops({})
        m.assert_called_once_with("status", None)

    def test_repo_optional(self):
        with mock.patch.object(self.plugin.core, "execute", return_value="ok") as m:
            self.plugin._tool_gh_ops({"action": "me"})
        m.assert_called_once_with("me", None)

    def test_blank_repo_becomes_none(self):
        with mock.patch.object(self.plugin.core, "execute", return_value="ok") as m:
            self.plugin._tool_gh_ops({"action": "issues", "repo": "   "})
        m.assert_called_once_with("issues", None)


if __name__ == "__main__":
    unittest.main()
