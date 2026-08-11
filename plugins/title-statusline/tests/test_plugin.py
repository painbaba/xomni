"""Tests for title-statusline plugin wiring (__init__.py) — hook + /title command.

The host loads directory plugins as ``hermes_plugins.<slug>`` packages
(hermes_cli.plugins._load_directory_module); _load_plugin() mirrors that so
the ``from . import core`` relative import works exactly as it does in prod.
"""
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_plugin():
    """Load the plugin __init__.py as ``hermes_plugins.title_statusline``."""
    ns_name = "hermes_plugins"
    if ns_name not in sys.modules:
        ns = types.ModuleType(ns_name)
        ns.__path__ = []
        sys.modules[ns_name] = ns
    pkg_name = f"{ns_name}.title_statusline"
    spec = importlib.util.spec_from_file_location(
        pkg_name, os.path.join(PLUGIN_DIR, "__init__.py"),
        submodule_search_locations=[PLUGIN_DIR],
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = pkg_name
    module.__path__ = [PLUGIN_DIR]
    sys.modules[pkg_name] = module
    spec.loader.exec_module(module)
    return module


PLUGIN = _load_plugin()


class PluginTestCase(unittest.TestCase):
    """Isolated plugin-local state.json for every test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._state_patch = mock.patch.object(
            PLUGIN, "_STATE_PATH", os.path.join(self._tmp.name, "state.json"))
        self._state_patch.start()
        self.addCleanup(self._state_patch.stop)

    def _write_sponsor_files(self, d):
        wp = os.path.join(d, "waitperk", "current.txt")
        pk = os.path.join(d, "perkline", "current.txt")
        os.makedirs(os.path.dirname(wp))
        os.makedirs(os.path.dirname(pk))
        with open(wp, "w", encoding="utf-8") as f:
            f.write("sponsor▸ Build faster with RepoBoost — try it free\n")
        with open(pk, "w", encoding="utf-8") as f:
            f.write("sponsor▸ PipeDeck: CI pipelines in minutes  [CPC]  (/perkline engage pk-demo-2)\n")
        return wp, pk

    def _patch_lines(self, d):
        wp, pk = self._write_sponsor_files(d)
        return mock.patch.object(PLUGIN.core, "WAITPERK_LINE", wp), \
            mock.patch.object(PLUGIN.core, "PERKLINE_LINE", pk)


class PostToolCallHookTests(PluginTestCase):
    def test_hook_returns_none_when_files_missing(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(PLUGIN.core, "WAITPERK_LINE", os.path.join(d, "wp.txt")), \
                 mock.patch.object(PLUGIN.core, "PERKLINE_LINE", os.path.join(d, "pk.txt")), \
                 mock.patch.object(PLUGIN.core, "set_title") as st:
                result = PLUGIN._on_post_tool_call(tool_name="read_file", args={})
        self.assertIsNone(result)  # hook contract: observer, never alters behavior
        st.assert_called_once_with("[agent]")  # neutral title, no crash

    def test_hook_refreshes_title_after_tool_call(self):
        with tempfile.TemporaryDirectory() as d:
            wp_patch, pk_patch = self._patch_lines(d)
            with wp_patch, pk_patch, mock.patch.object(PLUGIN.core, "set_title") as st:
                result = PLUGIN._on_post_tool_call(tool_name="terminal", args={"command": "ls"})
        self.assertIsNone(result)
        st.assert_called_once()
        self.assertIn("PipeDeck", st.call_args[0][0])  # perkline line preferred

    def test_hook_never_raises_on_title_failure(self):
        """A title-bar failure must NEVER break the agent."""
        with tempfile.TemporaryDirectory() as d:
            wp_patch, pk_patch = self._patch_lines(d)
            with wp_patch, pk_patch, \
                 mock.patch.object(PLUGIN.core, "set_title", side_effect=RuntimeError("boom")):
                result = PLUGIN._on_post_tool_call()
        self.assertIsNone(result)

    def test_hook_skips_when_disabled(self):
        PLUGIN._handle_title("off")  # persist disabled state
        with mock.patch.object(PLUGIN.core, "set_title") as st:
            result = PLUGIN._on_post_tool_call()
        self.assertIsNone(result)
        st.assert_not_called()


class TitleCommandTests(PluginTestCase):
    def test_off_then_on_state_round_trip(self):
        h = PLUGIN._handle_title
        out_off = h("off")
        with open(os.path.join(self._tmp.name, "state.json"), encoding="utf-8") as f:
            self.assertFalse(json.load(f)["enabled"])
        self.assertIn("OFF", out_off)
        out_on = h("on")
        with open(os.path.join(self._tmp.name, "state.json"), encoding="utf-8") as f:
            self.assertTrue(json.load(f)["enabled"])
        self.assertIn("ON", out_on)
        # a fresh load reflects the persisted round trip
        self.assertTrue(PLUGIN._load_state()["enabled"])
        # status reports the current state
        self.assertIn("enabled   : True", h("status"))

    def test_off_restores_neutral_title(self):
        with mock.patch.object(PLUGIN.core, "set_title") as st:
            PLUGIN._handle_title("off")
        st.assert_called_once_with(PLUGIN.core.NEUTRAL_TITLE)

    def test_on_refreshes_title_immediately(self):
        with tempfile.TemporaryDirectory() as d:
            wp_patch, pk_patch = self._patch_lines(d)
            with wp_patch, pk_patch, mock.patch.object(PLUGIN.core, "set_title") as st:
                PLUGIN._handle_title("on")
        st.assert_called_once()
        self.assertIn("PipeDeck", st.call_args[0][0])

    def test_now_force_refreshes(self):
        with tempfile.TemporaryDirectory() as d:
            wp_patch, pk_patch = self._patch_lines(d)
            with wp_patch, pk_patch, mock.patch.object(PLUGIN.core, "set_title") as st:
                out = PLUGIN._handle_title("now")
        self.assertIn("title set:", out)
        st.assert_called_once()

    def test_now_with_no_lines_reports_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(PLUGIN.core, "WAITPERK_LINE", os.path.join(d, "wp.txt")), \
                 mock.patch.object(PLUGIN.core, "PERKLINE_LINE", os.path.join(d, "pk.txt")):
                out = PLUGIN._handle_title("now")
        self.assertIn("nothing to show", out)

    def test_load_state_returns_independent_copies(self):
        """deepcopy: mutating one loaded state must not leak into the next."""
        a = PLUGIN._load_state()
        b = PLUGIN._load_state()
        a["enabled"] = False
        self.assertTrue(b["enabled"])
        # and the module-level default is never mutated
        self.assertTrue(PLUGIN.DEFAULT_STATE["enabled"])

    def test_unknown_args_returns_help(self):
        out = PLUGIN._handle_title("frobnicate")
        self.assertIn("/statusline", out)


class RegisterTests(unittest.TestCase):
    def test_register_wires_hook_and_command(self):
        class FakeCtx:
            def __init__(self):
                self.hooks = []
                self.commands = []

            def register_hook(self, name, cb):
                self.hooks.append((name, cb))

            def register_command(self, name, handler, description="", args_hint=""):
                self.commands.append((name, handler, description, args_hint))

        ctx = FakeCtx()
        PLUGIN.register(ctx)
        self.assertEqual([name for name, _ in ctx.hooks], ["post_tool_call"])
        self.assertEqual(ctx.hooks[0][1], PLUGIN._on_post_tool_call)
        self.assertEqual(len(ctx.commands), 1)
        name, handler, desc, hint = ctx.commands[0]
        self.assertEqual(name, "statusline")
        self.assertEqual(handler, PLUGIN._handle_title)
        self.assertIn("title bar", desc)
        self.assertEqual(hint, "[status|on|off|now]")


if __name__ == "__main__":
    unittest.main()
