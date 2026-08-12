"""notify tests — payload shape, queue append/readback, masked-target output,
digest formatting, loud unknown channels, never-send-by-default safety,
--send invoking the host command via a mocked runner, zero hooks.

Pure core tests (no host): the queue lives at a tempfile path via the
XOMNI_NOTIFY_QUEUE override so tests never touch the real ~/.xomni-notify.
"""
import json
import os
import shlex
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

# the plugin package's parent dir — how the host loads plugins/notify
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

CH = core.CHANNELS


def _tmp_queue_path():
    d = tempfile.mkdtemp(prefix="xomni-notify-test-")
    return os.path.join(d, "queue.jsonl"), d


class NotifyTests(unittest.TestCase):
    def setUp(self):
        self._old_env = os.environ.get("XOMNI_NOTIFY_QUEUE")
        self.qfile, self._tmpdir = _tmp_queue_path()
        os.environ["XOMNI_NOTIFY_QUEUE"] = self.qfile
        # wipe channel env vars so tests are hermetic
        self._old_vars = {}
        for var in core.ENV_TARGETS.values():
            self._old_vars[var] = os.environ.pop(var, None)
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        if self._old_env is None:
            os.environ.pop("XOMNI_NOTIFY_QUEUE", None)
        else:
            os.environ["XOMNI_NOTIFY_QUEUE"] = self._old_env
        for var, val in self._old_vars.items():
            if val is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = val

    def _cfg(self, **targets):
        def config_get(name):
            prefix = "notify.channels."
            suffix = ".target"
            if name.startswith(prefix) and name.endswith(suffix):
                ch = name[len(prefix):-len(suffix)]
                return targets.get(ch)
            return None
        return config_get

    # ── registry / resolution ────────────────────────────────────────────
    def test_channels_registry(self):
        self.assertEqual(CH, ("telegram", "whatsapp", "local"))

    def test_resolve_target_from_config(self):
        self.assertEqual(
            core.resolve_target("telegram", self._cfg(telegram="@botA")),
            "@botA")

    def test_resolve_target_from_env(self):
        os.environ["NOTIFY_WHATSAPP_TARGET"] = "+15551234"
        self.assertEqual(core.resolve_target("whatsapp"), "+15551234")

    def test_local_channel_self_targets(self):
        self.assertEqual(core.resolve_target("local"), "local")

    def test_unknown_channel_loud(self):
        with self.assertRaises(core.NotifyError):
            core.resolve_target("pigeon")

    # ── payload shape ────────────────────────────────────────────────────
    def test_payload_shape(self):
        p = core.build_payload("telegram", "hi", "@botA")
        for key in ("id", "channel", "target", "text", "ts"):
            self.assertIn(key, p)
        self.assertEqual(p["channel"], "telegram")
        self.assertEqual(p["target"], "@botA")
        self.assertEqual(p["text"], "hi")
        self.assertTrue(p["ts"].endswith("Z") or "+00:00" in p["ts"]
                        or "T" in p["ts"])  # ISO-ish UTC timestamp

    # ── queue ────────────────────────────────────────────────────────────
    def test_queue_append_and_readback(self):
        q = core.NotifyQueue()
        r1 = q.append(core.build_payload("telegram", "a", "@botA"))
        r2 = q.append(core.build_payload("whatsapp", "b", "+15551234"))
        fresh = core.NotifyQueue()          # new instance, same file
        got = fresh.read()
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0]["id"], r1["id"])    # append order preserved
        self.assertEqual(got[1]["id"], r2["id"])
        self.assertEqual(fresh.count(), 2)

    def test_queue_creates_dir_and_file(self):
        q = core.NotifyQueue()
        q.append(core.build_payload("local", "x", "local"))
        self.assertTrue(os.path.isfile(self.qfile))

    def test_queue_read_no_file_is_empty(self):
        self.assertEqual(core.NotifyQueue().read(), [])
        self.assertEqual(core.NotifyQueue().count(), 0)

    def test_env_override_of_queue_path(self):
        # setUp already points XOMNI_NOTIFY_QUEUE at the temp file
        self.assertEqual(core.queue_path(), self.qfile)

    # ── send safety ──────────────────────────────────────────────────────
    def test_send_never_transmits_by_default(self):
        calls = []
        result = core.send("telegram", "hi", config_get=self._cfg(
            telegram="@botA"), runner=lambda cmd: calls.append(cmd))
        self.assertTrue(result["queued"])
        self.assertFalse(result["ran"])
        self.assertEqual(calls, [])                 # runner never invoked
        self.assertEqual(core.NotifyQueue().count(), 1)  # queue only
        self.assertEqual(result["payload"]["channel"], "telegram")

    def test_send_run_invokes_host_command(self):
        calls = []
        result = core.send("whatsapp", "alert", config_get=self._cfg(
            whatsapp="+15551234"), run=True,
            runner=lambda cmd: calls.append(cmd))
        self.assertTrue(result["ran"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], result["command"])
        self.assertIn("hermes send --channel whatsapp", calls[0])
        self.assertIn("+15551234", calls[0])
        self.assertIn("alert", calls[0])

    def test_unknown_channel_send_loud_queue_untouched(self):
        with self.assertRaises(core.NotifyError):
            core.send("pigeon", "hi")
        self.assertEqual(core.NotifyQueue().count(), 0)

    def test_delivery_command_is_shell_quoted(self):
        p = core.build_payload("telegram", "say 'hi'", "@botA")
        cmd = core.delivery_command(p)
        # round-trips safely through a shell: quoting never loses data
        self.assertEqual(
            shlex.split(cmd),
            ["hermes", "send", "--channel", "telegram", "--to", "@botA",
             "--text", "say 'hi'"])

    # ── masking ──────────────────────────────────────────────────────────
    def test_mask_target_never_reveals_full_target(self):
        for t in ("@thepainnn_bot", "+155512345678", "channel-987654321"):
            m = core.mask_target(t)
            self.assertNotIn(t, m)
            self.assertTrue(m.startswith("***"))
            self.assertEqual(m[-4:], t[-4:])

    def test_reports_are_masked(self):
        cfg = self._cfg(telegram="@thepainnn_bot", whatsapp="+155512345678")
        table = core.channels_table(cfg)
        status = core.status_text(core.NotifyQueue(), cfg)
        for out in (table, status):
            self.assertNotIn("@thepainnn_bot", out)
            self.assertNotIn("+155512345678", out)
        self.assertIn("***_bot", table)        # masked form is shown
        self.assertIn("***5678", table)

    def test_send_report_masks_summary_target(self):
        result = core.send("telegram", "hi", config_get=self._cfg(
            telegram="@thepainnn_bot"))
        report = core.send_report(result)
        self.assertNotIn("@thepainnn_bot", report.split("\n")[0])
        self.assertIn("***_bot", report.split("\n")[0])
        self.assertIn("would run:", report)

    # ── digest ───────────────────────────────────────────────────────────
    def test_digest_formatting(self):
        body = core.digest(["cron digest", "disk 92%"], "Daily")
        lines = body.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("Daily ("))
        self.assertIn("1. cron digest", lines[1])
        self.assertIn("2. disk 92%", lines[2])

    def test_digest_queues_as_single_payload(self):
        result = core.send("telegram", core.digest(["a", "b"], "T"),
                           config_get=self._cfg(telegram="@botA"))
        self.assertEqual(core.NotifyQueue().count(), 1)
        stored = core.NotifyQueue().read()[0]
        self.assertIn("1. a", stored["text"])
        self.assertIn("T (", stored["text"])

    # ── host surface / zero hooks ────────────────────────────────────────
    def test_zero_hooks_in_core(self):
        src = open(os.path.join(os.path.dirname(core.__file__),
                                "core.py"), encoding="utf-8").read()
        self.assertNotIn("register_hook", src)
        self.assertNotIn("ctx.register_hook", src)

    def test_command_registration(self):
        calls = {}

        class FakeCtx:
            config = None
            def register_command(self, name, handler, description="",
                                 args_hint=""):
                calls["name"] = name
                calls["handler"] = handler
                calls["args_hint"] = args_hint

        import notify  # noqa: E402 — package __init__ (sibling of tests/)
        notify.register(FakeCtx())
        self.assertEqual(calls["name"], "notify")
        self.assertEqual(calls["args_hint"], "send|digest|status|channels")
        # send subcommand queues + reports, still never transmits
        os.environ["NOTIFY_TELEGRAM_TARGET"] = "@thepainnn_bot"
        before = core.NotifyQueue().count()
        out = calls["handler"]("send telegram hello")
        self.assertIn("queued (not sent)", out)
        self.assertIn("would run:", out)
        self.assertEqual(core.NotifyQueue().count(), before + 1)
        out2 = calls["handler"]("channels")
        self.assertIn("telegram", out2)
        self.assertIn("***_bot", out2)


if __name__ == "__main__":
    unittest.main()
