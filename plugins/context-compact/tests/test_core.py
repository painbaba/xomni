"""Tests for Context Compact (core.py pure logic + __init__ hook wiring).

Core tests import the pure stdlib module; hook/command tests load the
plugin package the same way the host does (hermes_cli.plugins.py
``_load_directory_module``: importlib spec from the plugin dir's
``__init__.py`` with ``__path__`` set) and drive ``_on_pre_llm_call``
with the exact kwargs turn_context.py passes.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from copy import deepcopy
from unittest import mock

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

import core  # noqa: E402


def _history(n, start=0):
    out = []
    for i in range(start, start + n):
        role = "user" if i % 2 == 0 else "assistant"
        out.append({"role": role, "content": f"message number {i} with some real content"})
    return out


def _hook_kwargs(history, user_message="continue the analysis please",
                 session_id="sess-1", turn_id="turn-1"):
    """Exact kwargs the host passes to pre_llm_call (turn_context.py)."""
    return {
        "session_id": session_id,
        "task_id": "task-1",
        "turn_id": turn_id,
        "user_message": user_message,
        "conversation_history": history,
        "is_first_turn": False,
        "model": "test-model",
        "platform": "cli",
        "parent_session_id": "",
        "sender_id": "",
    }


class _FakeResult:
    def __init__(self, text):
        self.text = text


class _FakeLlm:
    def __init__(self, text="compacted recap of the older messages", fail=False):
        self.text = text
        self.fail = fail
        self.calls = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("simulated summarization failure")
        return _FakeResult(self.text)


class _FakeCtx:
    def __init__(self, llm):
        self.llm = llm


def _load_plugin_pkg():
    """Mirror hermes_cli.plugins._load_directory_module."""
    init_file = os.path.join(_PLUGIN_DIR, "__init__.py")
    spec = importlib.util.spec_from_file_location(
        "context_compact_test", init_file,
        submodule_search_locations=[_PLUGIN_DIR],
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "context_compact_test"
    mod.__path__ = [_PLUGIN_DIR]
    sys.modules["context_compact_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class CoreShouldCompactTests(unittest.TestCase):
    def setUp(self):
        self.state = deepcopy(core.DEFAULT_STATE)

    def test_fires_above_threshold(self):
        self.state["threshold"] = 40
        self.assertTrue(core.should_compact(self.state, 45, now=1000.0))
        self.assertTrue(core.should_compact(self.state, 40, now=1000.0))  # at threshold too

    def test_noop_below_threshold(self):
        self.state["threshold"] = 40
        self.assertFalse(core.should_compact(self.state, 39, now=1000.0))
        self.assertFalse(core.should_compact(self.state, 0, now=1000.0))

    def test_cooldown_blocks_repeat(self):
        self.state["threshold"] = 40
        core.mark_compacted(self.state, now=1000.0)
        self.assertFalse(core.should_compact(self.state, 60, now=1030.0))  # 30s < 60s
        self.assertFalse(core.should_compact(self.state, 60, now=1059.9))
        self.assertTrue(core.should_compact(self.state, 60, now=1060.0))   # cooldown elapsed

    def test_paused_blocks(self):
        self.state["threshold"] = 40
        self.state["paused"] = True
        self.assertFalse(core.should_compact(self.state, 100, now=1000.0))

    def test_auto_off_blocks(self):
        self.state["threshold"] = 40
        self.state["auto"] = False
        self.assertFalse(core.should_compact(self.state, 100, now=1000.0))

    def test_corrupt_numeric_state_falls_back_to_defaults(self):
        self.state["threshold"] = "garbage"
        self.state["cooldown_seconds"] = None
        self.state["last_compact_ts"] = "zzz"
        self.assertTrue(core.should_compact(self.state, 40, now=1000.0))

    def test_mark_compacted_stamps_clock_session_and_count(self):
        core.mark_compacted(self.state, now=500.0, session_id="s-9")
        self.assertEqual(self.state["last_compact_ts"], 500.0)
        self.assertEqual(self.state["last_compact_session"], "s-9")
        self.assertEqual(self.state["compactions"], 1)
        core.mark_compacted(self.state, now=600.0)
        self.assertEqual(self.state["compactions"], 2)


class CoreFormattingTests(unittest.TestCase):
    def test_split_history_older_and_tail(self):
        h = _history(50)
        older, tail = core.split_history(h, 10)
        self.assertEqual(len(older), 40)
        self.assertEqual(len(tail), 10)
        self.assertEqual(older[0], h[0])
        self.assertEqual(tail[0], h[40])
        self.assertEqual(tail[-1], h[-1])
        # never mutates the input list
        self.assertEqual(len(h), 50)

    def test_split_history_fits_in_tail(self):
        h = _history(5)
        older, tail = core.split_history(h, 10)
        self.assertEqual(older, [])
        self.assertEqual(len(tail), 5)

    def test_render_tail_flattens_roles_and_truncates(self):
        h = [{"role": "user", "content": "line one\nline two"},
             {"role": "assistant", "content": "x" * 200},
             {"role": "tool", "content": "tool output ignored"},
             {"role": "user", "content": "   "}]
        out = core.render_tail(h, max_chars=20)
        self.assertIn("[user]", out)
        self.assertIn("[assistant]", out)
        self.assertNotIn("[tool]", out)
        self.assertIn("line one line two", out)  # content newline flattened to space
        self.assertIn("x" * 20, out)    # snippet capped at max_chars
        self.assertNotIn("x" * 21, out)  # never longer than max_chars

    def test_format_summary_uses_real_summary_text(self):
        out = core.format_summary(30, "tail text", summary_text="LLM recap here")
        self.assertTrue(out.startswith("[compacted history]"))
        self.assertIn("LLM recap here", out)
        self.assertNotIn("omitted", out)

    def test_format_summary_fallback_counts_and_tail(self):
        out = core.format_summary(30, "[user] recent message", summary_text="")
        self.assertTrue(out.startswith("[compacted history]"))
        self.assertIn("30 earlier message(s) omitted", out)
        self.assertIn("[user] recent message", out)
        # empty tail -> no tail section, counts still present
        out2 = core.format_summary(30, "", summary_text="  ")
        self.assertIn("30 earlier message(s) omitted", out2)
        self.assertNotIn("verbatim tail", out2)


class CoreStateRoundTripTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._path = os.path.join(self._tmp.name, "state.json")
        self.addCleanup(self._tmp.cleanup)

    def test_save_then_load_round_trip(self):
        st = core.State.load(self._path)
        st.data["threshold"] = 55
        st.data["compactions"] = 3
        st.data["last_compact_session"] = "s-1"
        st.save()
        st2 = core.State.load(self._path)
        self.assertEqual(st2.data, st.data)
        self.assertEqual(st2.data["threshold"], 55)
        self.assertEqual(st2.data["compactions"], 3)
        self.assertEqual(st2.data["last_compact_session"], "s-1")

    def test_load_missing_file_uses_defaults(self):
        st = core.State.load(self._path)
        self.assertEqual(st.data, core.DEFAULT_STATE)
        self.assertTrue(st.data["auto"])

    def test_load_corrupt_file_uses_defaults(self):
        with open(self._path, "w", encoding="utf-8") as f:
            f.write("{not json")
        st = core.State.load(self._path)
        self.assertEqual(st.data["threshold"], core.DEFAULT_STATE["threshold"])

    def test_defaults_deepcopied_not_shared(self):
        a = core.State()
        b = core.State()
        a.data["compactions"] = 99
        a.data["last_compact_session"] = "mutated"
        self.assertEqual(b.data["compactions"], 0)
        self.assertEqual(b.data["last_compact_session"], "")
        self.assertIsNot(a.data, b.data)


class HookWiringTests(unittest.TestCase):
    """Drive _on_pre_llm_call with host-shaped kwargs + fake ctx.llm."""

    @classmethod
    def setUpClass(cls):
        cls.pkg = _load_plugin_pkg()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        state_path = os.path.join(self._tmp.name, "state.json")
        self._state_patch = mock.patch.object(self.pkg, "STATE_FILE",
                                              type(self.pkg.STATE_FILE)(state_path))
        self._state_patch.start()
        self.pkg._LAST_HISTORY = []
        self.llm = _FakeLlm()
        self.pkg._CTX = _FakeCtx(self.llm)
        self.addCleanup(self._state_patch.stop)
        self.addCleanup(self._tmp.cleanup)

    def _state_data(self):
        with open(self.pkg.STATE_FILE, encoding="utf-8") as f:
            return json.load(f)

    def test_fires_above_threshold_payload_shape(self):
        history = _history(45)
        result = self.pkg._on_pre_llm_call(**_hook_kwargs(history))
        self.assertIsInstance(result, dict)
        self.assertIn("context", result)
        self.assertIsInstance(result["context"], str)
        self.assertTrue(result["context"].startswith("[compacted history]"))
        self.assertIn("35 earlier message(s) omitted", result["context"])
        # PERF CONTRACT: the auto hook never calls the LLM (incident fix).
        self.assertEqual(len(self.llm.calls), 0)
        # state stamped: cooldown clock + session marker + counter
        data = self._state_data()
        self.assertGreater(data["last_compact_ts"], 0)
        self.assertEqual(data["last_compact_session"], "sess-1")
        self.assertEqual(data["compactions"], 1)

    def test_noop_below_threshold(self):
        history = _history(39)
        result = self.pkg._on_pre_llm_call(**_hook_kwargs(history))
        self.assertIsNone(result)
        self.assertEqual(self.llm.calls, [])
        self.assertFalse(os.path.exists(self.pkg.STATE_FILE))

    def test_trivial_message_never_triggers(self):
        history = _history(45)
        for trivial in ("ok", "yes", "👍", "k", "thanks", "/compact status"):
            result = self.pkg._on_pre_llm_call(**_hook_kwargs(history, user_message=trivial))
            self.assertIsNone(result, f"trivial message {trivial!r} must not trigger")
        self.assertEqual(self.llm.calls, [])

    def test_cooldown_blocks_repeat(self):
        history = _history(45)
        first = self.pkg._on_pre_llm_call(**_hook_kwargs(history, session_id="s-a"))
        self.assertIsNotNone(first)
        # same turn count but new session (session-once must not mask the
        # cooldown check): still inside the 60s window -> no-op
        second = self.pkg._on_pre_llm_call(**_hook_kwargs(history, session_id="s-b"))
        self.assertIsNone(second)
        self.assertEqual(len(self.llm.calls), 0)

    def test_paused_blocks(self):
        st = self.pkg._get_state()
        st.data["paused"] = True
        st.save()
        result = self.pkg._on_pre_llm_call(**_hook_kwargs(_history(45)))
        self.assertIsNone(result)
        self.assertEqual(self.llm.calls, [])

    def test_fires_at_most_once_per_session_until_reset(self):
        history = _history(45)
        first = self.pkg._on_pre_llm_call(**_hook_kwargs(history, session_id="s-1"))
        self.assertIsNotNone(first)
        # simulate the cooldown having elapsed (clock cleared) but the
        # session marker still set: the session-once rule still blocks
        st = self.pkg._get_state()
        st.data["last_compact_ts"] = 0.0
        st.save()
        again = self.pkg._on_pre_llm_call(**_hook_kwargs(history, session_id="s-1"))
        self.assertIsNone(again)
        self.assertEqual(len(self.llm.calls), 0)
        # /compact reset re-arms the session
        self.pkg._handle_compact("reset")
        rearmed = self.pkg._on_pre_llm_call(**_hook_kwargs(history, session_id="s-1"))
        self.assertIsNotNone(rearmed)
        self.assertEqual(len(self.llm.calls), 0)

    def test_auto_hook_never_calls_llm_even_on_failure_style_history(self):
        # Even with a full-length history the hook stays deterministic:
        # zero LLM calls, fallback text injected.
        history = _history(45)
        result = self.pkg._on_pre_llm_call(**_hook_kwargs(history))
        self.assertIsNotNone(result)
        ctx = result["context"]
        self.assertTrue(ctx.startswith("[compacted history]"))
        self.assertIn("35 earlier message(s) omitted", ctx)  # 45 - 10 tail
        self.assertIn("[user]", ctx)                          # verbatim tail present
        self.assertEqual(len(self.llm.calls), 0)              # never attempted

    def test_never_mutates_stored_history(self):
        history = _history(45)
        snapshot = deepcopy(history)
        self.pkg._on_pre_llm_call(**_hook_kwargs(history))
        self.assertEqual(history, snapshot)
        self.assertIsInstance(history[0], dict)
        self.assertEqual(history[0]["content"], snapshot[0]["content"])

    def test_empty_history_noop(self):
        result = self.pkg._on_pre_llm_call(**_hook_kwargs([]))
        self.assertIsNone(result)
        self.assertEqual(self.llm.calls, [])


class CommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = _load_plugin_pkg()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        state_path = os.path.join(self._tmp.name, "state.json")
        self._state_patch = mock.patch.object(self.pkg, "STATE_FILE",
                                              type(self.pkg.STATE_FILE)(state_path))
        self._state_patch.start()
        self.pkg._LAST_HISTORY = []
        self.llm = _FakeLlm()
        self.pkg._CTX = _FakeCtx(self.llm)
        self.addCleanup(self._state_patch.stop)
        self.addCleanup(self._tmp.cleanup)

    def _state_data(self):
        with open(self.pkg.STATE_FILE, encoding="utf-8") as f:
            return json.load(f)

    def test_status_shows_defaults(self):
        out = self.pkg._handle_compact("")
        self.assertIn("threshold   : 40 messages", out)
        self.assertIn("ON (auto)", out)
        self.assertIn("state.json", out)

    def test_on_off_toggle(self):
        self.pkg._handle_compact("off")
        self.assertFalse(self._state_data()["auto"])
        self.pkg._handle_compact("on")
        self.assertTrue(self._state_data()["auto"])

    def test_threshold_sets_value(self):
        out = self.pkg._handle_compact("threshold 55")
        self.assertIn("55", out)
        self.assertEqual(self._state_data()["threshold"], 55)
        # rejects garbage
        out2 = self.pkg._handle_compact("threshold abc")
        self.assertIn("usage", out2)
        self.assertEqual(self._state_data()["threshold"], 55)

    def test_now_arms_force_injection(self):
        self.pkg._LAST_HISTORY = _history(45)
        out = self.pkg._handle_compact("now")
        self.assertIn("[compaction ready", out)
        pending = self._state_data().get("pending_force")
        self.assertTrue(pending.startswith("[compacted history]"))
        # next hook turn injects the pre-built compaction WITHOUT a new llm call
        result = self.pkg._on_pre_llm_call(**_hook_kwargs(_history(2)))
        self.assertIsNotNone(result)
        self.assertEqual(result["context"], pending)
        self.assertEqual(len(self.llm.calls), 1)  # only the /compact now summary call
        self.assertNotIn("pending_force", self._state_data())

    def test_now_is_the_llm_path_with_host_contract(self):
        # PERF CONTRACT: /ctxcompact now is the ONLY path that calls the
        # LLM — host-owned, temperature 0.2, purpose set.
        self.pkg._LAST_HISTORY = _history(45)
        out = self.pkg._handle_compact("now")
        self.assertIn("[compaction ready", out)
        self.assertEqual(len(self.llm.calls), 1)
        self.assertEqual(self.llm.calls[0]["temperature"], 0.2)
        self.assertEqual(self.llm.calls[0]["purpose"], "context compaction")
        # a failed LLM still yields the deterministic fallback, and the
        # auto hook afterwards adds no further calls
        self.pkg.llm = _FakeLlm()
        self.pkg.llm.fail = True
        self.pkg._CTX = _FakeCtx(self.pkg.llm)
        self.pkg._handle_compact("reset")
        out2 = self.pkg._handle_compact("now")
        self.assertIn("earlier message(s) omitted", out2)
        self.assertEqual(len(self.pkg.llm.calls), 1)  # attempted once, fell back

    def test_reset_clears_cooldown_and_session(self):
        st = self.pkg._get_state()
        st.data["last_compact_ts"] = 123.0
        st.data["last_compact_session"] = "s-1"
        st.data["compactions"] = 5
        st.save()
        self.pkg._handle_compact("reset")
        data = self._state_data()
        self.assertEqual(data["last_compact_ts"], 0.0)
        self.assertEqual(data["last_compact_session"], "")
        self.assertEqual(data["compactions"], 5)  # counter preserved


if __name__ == "__main__":
    unittest.main()
