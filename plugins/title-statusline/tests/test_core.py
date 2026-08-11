"""Tests for title-statusline core (core.py) — title setting, sponsor lines, pick_line."""
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

import core


class SetTitleTests(unittest.TestCase):
    def test_set_title_windows_uses_console_title_w(self):
        """Windows path: ctypes SetConsoleTitleW called with the exact string."""
        fake_kernel32 = mock.Mock()
        fake_ctypes = mock.Mock()
        fake_ctypes.windll.kernel32.SetConsoleTitleW = fake_kernel32
        with mock.patch.object(sys, "platform", "win32"), \
             mock.patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            core.set_title("hello world")
        fake_kernel32.assert_called_once_with("hello world")

    def test_set_title_fallback_emits_osc_escape(self):
        """Non-win32 path: OSC 0 title escape written to stdout."""
        buf = io.StringIO()
        with mock.patch.object(sys, "platform", "linux"), \
             mock.patch.object(sys, "stdout", buf):
            core.set_title("hello world")
        self.assertEqual(buf.getvalue(), "\x1b]0;hello world\x07")

    def test_set_title_falls_back_when_ctypes_unavailable_on_win32(self):
        """win32 but ctypes missing → must not raise, must emit the OSC escape."""
        buf = io.StringIO()
        with mock.patch.object(sys, "platform", "win32"), \
             mock.patch.dict(sys.modules, {"ctypes": None}), \
             mock.patch.object(sys, "stdout", buf):
            core.set_title("hello world")  # must not raise
        self.assertEqual(buf.getvalue(), "\x1b]0;hello world\x07")

    def test_set_title_falls_back_when_console_call_fails(self):
        """win32 + ctypes present but the call itself fails → OSC fallback."""
        fake_ctypes = mock.Mock()
        fake_ctypes.windll.kernel32.SetConsoleTitleW = mock.Mock(
            side_effect=OSError("no console"))
        buf = io.StringIO()
        with mock.patch.object(sys, "platform", "win32"), \
             mock.patch.dict(sys.modules, {"ctypes": fake_ctypes}), \
             mock.patch.object(sys, "stdout", buf):
            core.set_title("hello world")  # must not raise
        self.assertEqual(buf.getvalue(), "\x1b]0;hello world\x07")

    def test_set_title_sanitizes_control_chars(self):
        """ESC/BEL/newline inside the title must not leak into the escape."""
        buf = io.StringIO()
        with mock.patch.object(sys, "platform", "linux"), \
             mock.patch.object(sys, "stdout", buf):
            core.set_title("a\x1b]0;evil\x07b\nc")
        out = buf.getvalue()
        self.assertEqual(out, "\x1b]0;a]0;evilbc\x07")  # only the framing ESC/BEL remain


class ReadSponsorLinesTests(unittest.TestCase):
    def _paths(self, d):
        wp = os.path.join(d, "waitperk", "current.txt")
        pk = os.path.join(d, "perkline", "current.txt")
        return wp, pk

    def test_missing_files_return_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            wp, pk = self._paths(d)
            with mock.patch.object(core, "WAITPERK_LINE", wp), \
                 mock.patch.object(core, "PERKLINE_LINE", pk):
                self.assertEqual(core.read_sponsor_lines(), [])

    def test_reads_both_files_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            wp, pk = self._paths(d)
            os.makedirs(os.path.dirname(wp))
            os.makedirs(os.path.dirname(pk))
            with open(wp, "w", encoding="utf-8") as f:
                f.write("sponsor▸ Build faster with RepoBoost — try it free\n")
            with open(pk, "w", encoding="utf-8") as f:
                f.write("sponsor▸ PipeDeck: CI pipelines in minutes  [CPC]  (/perkline engage pk-demo-2)\n")
            with mock.patch.object(core, "WAITPERK_LINE", wp), \
                 mock.patch.object(core, "PERKLINE_LINE", pk):
                lines = core.read_sponsor_lines()
        self.assertEqual(len(lines), 2)
        self.assertIn("RepoBoost", lines[0])
        self.assertIn("PipeDeck", lines[1])
        self.assertIn("[CPC]", lines[1])

    def test_blank_perkline_file_is_skipped(self):
        """Paused perkline writes a blank line — it must not shadow anything."""
        with tempfile.TemporaryDirectory() as d:
            wp, pk = self._paths(d)
            os.makedirs(os.path.dirname(wp))
            os.makedirs(os.path.dirname(pk))
            with open(wp, "w", encoding="utf-8") as f:
                f.write("sponsor▸ RepoBoost\n")
            with open(pk, "w", encoding="utf-8") as f:
                f.write("\n")
            with mock.patch.object(core, "WAITPERK_LINE", wp), \
                 mock.patch.object(core, "PERKLINE_LINE", pk):
                lines = core.read_sponsor_lines()
        self.assertEqual(len(lines), 1)
        self.assertIn("RepoBoost", lines[0])


class PickLineTests(unittest.TestCase):
    WP = "sponsor▸ Build faster with RepoBoost — try it free"
    PK = "sponsor▸ PipeDeck: CI pipelines in minutes  [CPC]  (/perkline engage pk-demo-2)"

    def test_prefers_perkline_line(self):
        """Perkline's line (last, carries the model tier) wins over waitperk's."""
        title = core.pick_line([self.WP, self.PK])
        self.assertIn("PipeDeck", title)
        self.assertIn("[CPC]", title)
        self.assertNotIn("RepoBoost", title)

    def test_falls_back_to_waitperk_line(self):
        title = core.pick_line([self.WP])
        self.assertIn("RepoBoost", title)
        self.assertNotIn("PipeDeck", title)

    def test_empty_lines_yield_neutral_prefix_title(self):
        self.assertEqual(core.pick_line([]), "[agent]")
        self.assertEqual(core.pick_line(["", "  "]), "[agent]")

    def test_custom_prefix(self):
        title = core.pick_line([self.WP], prefix="[hermes]")
        self.assertTrue(title.startswith("[hermes] "))
        self.assertIn("RepoBoost", title)

    def test_truncates_to_title_max(self):
        long_line = "sponsor▸ " + "x" * 200
        title = core.pick_line([long_line])
        self.assertLessEqual(len(title), core.TITLE_MAX)
        self.assertTrue(title.startswith("[agent] "))
        # truncation keeps the prefix and the head of the sponsor line
        self.assertEqual(len(title), core.TITLE_MAX)


class CycleTitleTests(unittest.TestCase):
    def test_cycle_returns_title_and_sets_it(self):
        with tempfile.TemporaryDirectory() as d:
            wp = os.path.join(d, "waitperk", "current.txt")
            os.makedirs(os.path.dirname(wp))
            with open(wp, "w", encoding="utf-8") as f:
                f.write("sponsor▸ RepoBoost\n")
            with mock.patch.object(core, "WAITPERK_LINE", wp), \
                 mock.patch.object(core, "PERKLINE_LINE", os.path.join(d, "pk.txt")), \
                 mock.patch.object(core, "set_title") as st:
                result = core.cycle_title(interval_hint=30)
        self.assertIsNotNone(result)
        self.assertIn("RepoBoost", result)
        st.assert_called_once_with(result)

    def test_cycle_returns_none_when_no_lines(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(core, "WAITPERK_LINE", os.path.join(d, "wp.txt")), \
                 mock.patch.object(core, "PERKLINE_LINE", os.path.join(d, "pk.txt")), \
                 mock.patch.object(core, "set_title") as st:
                result = core.cycle_title(interval_hint=5)
        self.assertIsNone(result)
        st.assert_not_called()


if __name__ == "__main__":
    unittest.main()
