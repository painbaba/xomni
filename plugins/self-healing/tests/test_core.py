"""Tests for self-healing (U9) — watchdog, postconditions, drift scan/fix, audit.

All tests are hermetic: XOMNI_HEAL_DIR / XOMNI_HERMES_HOME / XOMNI_ROOT point
at temp dirs, so nothing touches the real hermes config, .env, or heal.jsonl.
Run: cd plugins/self-healing && python -m unittest tests.test_core -q
"""
import importlib.util
import json
import os
import socket
import tempfile
import threading
import time
import unittest

import core


def _fake_secret() -> str:
    return "sk-REAL-SECRET-VALUE-NEVER-LOG"


def _expected_state(plugins=("alpha", "beta"), env_keys=("GROQ_API_KEY",)) -> dict:
    return {
        "plugins": list(plugins),
        "provider": {
            "name": "opencode-go",
            "model_provider": "opencode-go",
            "block": {"request_timeout_seconds": "120",
                      "stale_timeout_seconds": "60"},
        },
        "env_keys": list(env_keys),
    }


class SelfHealingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.heal_dir = os.path.join(self._tmp.name, "heal")
        self.hermes = os.path.join(self._tmp.name, "hermes")
        self.root = os.path.join(self._tmp.name, "xomni")
        os.makedirs(self.hermes)
        os.makedirs(os.path.join(self.root, "plugins"))
        self._env = {}
        for var in ("XOMNI_HEAL_DIR", "XOMNI_HERMES_HOME", "XOMNI_ROOT",
                    "XOMNI_CHECKS"):
            self._env[var] = os.environ.get(var)
            os.environ.pop(var, None)
        os.environ["XOMNI_HEAL_DIR"] = self.heal_dir
        os.environ["XOMNI_HERMES_HOME"] = self.hermes
        os.environ["XOMNI_ROOT"] = self.root
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        for var, val in self._env.items():
            if val is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = val

    def _make_hermes(self, plugins=(), config=None, env_lines=None):
        if plugins:
            os.makedirs(os.path.join(self.hermes, "plugins"), exist_ok=True)
            for p in plugins:
                d = os.path.join(self.hermes, "plugins", p)
                os.makedirs(d, exist_ok=True)
                open(os.path.join(d, "__init__.py"), "w").close()
        if config is not None:
            with open(os.path.join(self.hermes, "config.yaml"), "w",
                      encoding="utf-8") as f:
                f.write(config)
        if env_lines is not None:
            with open(os.path.join(self.hermes, ".env"), "w",
                      encoding="utf-8") as f:
                f.write("\n".join(env_lines) + "\n")

    # ------------------------------------------------------------- watchdog

    def test_watchdog_kills_silent_hang(self):
        """Alive + silent = hang: the 300s-sleep / vectorbt case. Killed fast."""
        res = core.run_with_watchdog(
            ["python", "-c", "import time; time.sleep(300)"],
            timeout=10, quiet_after_s=2)
        self.assertTrue(res["killed"])
        self.assertFalse(res["timed_out"])  # quiet detector won, not timeout
        self.assertFalse(res["ok"])
        self.assertLess(res["elapsed"], 8)

    def test_watchdog_kill_is_audited(self):
        checks = {"watchdog": [{"name": "demo-silent-sleep",
                                "cmd": ["python", "-c",
                                        "import time; time.sleep(300)"],
                                "timeout": 10, "quiet_after_s": 2}],
                  "postconditions": []}
        results = core.run_checks(checks)
        self.assertFalse(results[0]["ok"])
        entries = core.last_audit_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["detector"], "watchdog")
        self.assertEqual(entries[0]["action"], "kill_silent_hang")
        self.assertEqual(entries[0]["subject"], "demo-silent-sleep")

    def test_watchdog_respects_timeout_for_chatty_process(self):
        """Output keeps coming, so the quiet detector can't fire — timeout wins."""
        res = core.run_with_watchdog(
            ["python", "-c",
             "import time\nfor i in range(30):\n print(i, flush=True)\n time.sleep(0.5)"],
            timeout=3, quiet_after_s=60)
        self.assertTrue(res["timed_out"])
        self.assertTrue(res["killed"])
        self.assertLess(res["elapsed"], 8)

    def test_watchdog_fast_command_ok_with_tail(self):
        res = core.run_with_watchdog(["python", "-c",
                                      "print('line1'); print('line2')"],
                                     timeout=10, quiet_after_s=0)
        self.assertTrue(res["ok"])
        self.assertEqual(res["exit_code"], 0)
        self.assertFalse(res["killed"])
        self.assertIn("line2", res["tail"])
        self.assertIn("line1", res["output"])

    def test_watchdog_nonzero_exit_not_killed(self):
        res = core.run_with_watchdog(["python", "-c", "import sys; sys.exit(3)"],
                                     timeout=10, quiet_after_s=0)
        self.assertFalse(res["ok"])
        self.assertEqual(res["exit_code"], 3)
        self.assertFalse(res["killed"])

    def test_watchdog_quiet_after_zero_disables_silence_detector(self):
        res = core.run_with_watchdog(["python", "-c", "import time; time.sleep(2)"],
                                     timeout=20, quiet_after_s=0)
        self.assertTrue(res["ok"])
        self.assertEqual(res["exit_code"], 0)
        self.assertFalse(res["killed"])

    def test_watchdog_output_resets_quiet_timer(self):
        """Printing every 1s with quiet_after 3s must NOT be killed."""
        res = core.run_with_watchdog(
            ["python", "-c",
             "import time\nfor i in range(4):\n print(i, flush=True)\n time.sleep(1)"],
            timeout=30, quiet_after_s=3)
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["exit_code"], 0)
        self.assertFalse(res["killed"])

    def test_watchdog_missing_command_reported_not_crashed(self):
        res = core.run_with_watchdog(
            ["definitely-not-a-real-binary-xyz-123"], timeout=5, quiet_after_s=0)
        self.assertFalse(res["ok"])
        self.assertFalse(res["killed"])
        self.assertIsNone(res["exit_code"])
        self.assertIn("error", res)

    # ------------------------------------------------------- postconditions

    def test_postcondition_file_exists_pass(self):
        target = os.path.join(self._tmp.name, "made.txt")
        open(target, "w").close()
        res = core.run_with_watchdog(["python", "-c", "print('done')"],
                                     timeout=10, quiet_after_s=0)
        verdict = core.verify_postconditions(
            res, [{"type": "file_exists", "target": target, "value": True}])
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["checks"][0]["passed"], True)

    def test_postcondition_exit0_nothing_happened_flagged(self):
        """Exit 0 but the expected artifact was never created -> FAILED."""
        target = os.path.join(self._tmp.name, "vectorbt_binary.exe")
        res = core.run_with_watchdog(
            ["python", "-c", "print('install complete')"],
            timeout=10, quiet_after_s=0)
        self.assertTrue(res["ok"])  # exit 0 — the lie
        verdict = core.verify_postconditions(
            res, [{"type": "file_exists", "target": target, "value": True}])
        self.assertFalse(verdict["ok"])
        self.assertEqual(len(verdict["failures"]), 1)
        self.assertEqual(verdict["failures"][0]["type"], "file_exists")

    def test_postcondition_output_contains(self):
        res = {"output": "Successfully installed vectorbt 0.28.0"}
        ok = core.verify_postconditions(
            res, [{"type": "output_contains", "target": "output",
                   "value": "vectorbt"}])
        self.assertTrue(ok["ok"])
        bad = core.verify_postconditions(
            res, [{"type": "output_contains", "target": "output",
                   "value": "binary installed"}])
        self.assertFalse(bad["ok"])

    def test_postcondition_service_ping_pass_and_fail(self):
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)
        def _serve():
            conn, _ = srv.accept()
            conn.close()
            srv.close()
        t = threading.Thread(target=_serve, daemon=True)
        t.start()
        try:
            ok = core.verify_postconditions(
                {}, [{"type": "service_ping", "target": f"127.0.0.1:{port}",
                      "value": True}])
            self.assertTrue(ok["ok"])
        finally:
            srv.close()
        # closed port -> unreachable -> flagged
        s2 = socket.socket()
        s2.bind(("127.0.0.1", 0))
        dead_port = s2.getsockname()[1]
        s2.close()
        bad = core.verify_postconditions(
            {}, [{"type": "service_ping", "target": f"127.0.0.1:{dead_port}",
                  "value": True}])
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["failures"][0]["actual"], "unreachable")

    # ----------------------------------------------------------- drift scan

    def test_drift_scan_missing_plugin_dir(self):
        self._make_hermes(plugins=["alpha"])
        drifts = core.drift_scan(_expected_state())
        keys = [d["key"] for d in drifts]
        self.assertIn("plugins.beta", keys)
        d = next(x for x in drifts if x["key"] == "plugins.beta")
        self.assertEqual(d["expected"], "present")
        self.assertEqual(d["actual"], "missing")

    def test_drift_scan_missing_provider_block(self):
        self._make_hermes(config="model:\n  provider: opencode-go\n")
        drifts = core.drift_scan(_expected_state())
        keys = [d["key"] for d in drifts]
        self.assertIn("provider.block.opencode-go", keys)
        # model.provider matches, so no model drift
        self.assertNotIn("provider.model_provider", keys)

    def test_drift_scan_missing_env_key(self):
        self._make_hermes(env_lines=["OPENAI_API_KEY=abc"])
        drifts = core.drift_scan(_expected_state())
        keys = [d["key"] for d in drifts]
        self.assertIn("env.GROQ_API_KEY", keys)
        self.assertNotIn("env.OPENAI_API_KEY", keys)  # present -> no drift

    def test_drift_scan_clean_state_no_drifts(self):
        config = ("model:\n  provider: opencode-go\n"
                  "providers:\n  opencode-go:\n"
                  "    request_timeout_seconds: 120\n"
                  "    stale_timeout_seconds: 60\n")
        self._make_hermes(plugins=["alpha", "beta"], config=config,
                          env_lines=["GROQ_API_KEY="])
        self.assertEqual(core.drift_scan(_expected_state()), [])

    # ------------------------------------------------------------- fix+audit

    def test_fix_drift_restores_plugin_dir_and_audits(self):
        beta = os.path.join(self.root, "plugins", "beta")
        os.makedirs(beta)
        open(os.path.join(beta, "__init__.py"), "w").write("x = 1\n")
        self._make_hermes(plugins=["alpha"])
        d = next(x for x in core.drift_scan(_expected_state())
                 if x["key"] == "plugins.beta")
        r = core.fix_drift(d)
        self.assertTrue(r["fixed"])
        restored = os.path.join(self.hermes, "plugins", "beta", "__init__.py")
        self.assertTrue(os.path.isfile(restored))
        # audit entry: complete shape {ts, detector, subject, action, before, after}
        entries = core.last_audit_entries()
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(set(e.keys()),
                         {"ts", "detector", "subject", "action", "before", "after"})
        self.assertEqual(e["detector"], "drift")
        self.assertEqual(e["subject"], "plugins.beta")
        self.assertEqual(e["action"], "fix")
        self.assertIsInstance(e["ts"], (int, float))

    def test_fix_drift_env_placeholder_no_secrets_logged(self):
        secret = _fake_secret()
        self._make_hermes(env_lines=[f"OPENAI_API_KEY={secret}"])
        d = {"key": "env.GROQ_API_KEY", "kind": "env",
             "expected": "present", "actual": "missing"}
        r = core.fix_drift(d)
        self.assertTrue(r["fixed"])
        with open(os.path.join(self.hermes, ".env"), "r",
                  encoding="utf-8") as f:
            content = f.read()
        self.assertIn("GROQ_API_KEY=\n", content)
        self.assertIn(f"OPENAI_API_KEY={secret}", content)  # value untouched
        log = open(os.path.join(self.heal_dir, "heal.jsonl"),
                   encoding="utf-8").read()
        self.assertNotIn(secret, log)  # secret NEVER logged
        self.assertNotIn("sk-REAL", log)

    def test_fix_drift_provider_block_inserts_and_backs_up(self):
        config = ("model:\n  provider: opencode-zen\n"  # wrong model provider
                  "providers:\n  opencode-zen:\n"
                  "    request_timeout_seconds: 60\n")
        self._make_hermes(config=config)
        # phase 1: missing providers.opencode-go block -> inserted
        d = {"key": "provider.block.opencode-go", "kind": "provider",
             "expected": "present", "actual": "missing"}
        r = core.fix_drift(d)
        self.assertTrue(r["fixed"])
        with open(os.path.join(self.hermes, "config.yaml"), "r",
                  encoding="utf-8") as f:
            text = f.read()
        self.assertIn("opencode-go:", text)
        self.assertIn("request_timeout_seconds: 120", text)
        self.assertIn("stale_timeout_seconds: 60", text)
        # original opencode-zen block untouched
        self.assertIn("opencode-zen:", text)
        # backup created
        baks = [n for n in os.listdir(self.hermes) if ".bak.heal." in n]
        self.assertEqual(len(baks), 1)
        # phase 2: wrong model.provider value -> corrected
        d2 = {"key": "provider.model_provider", "kind": "provider",
              "expected": "opencode-go", "actual": "opencode-zen"}
        r2 = core.fix_drift(d2)
        self.assertTrue(r2["fixed"])
        with open(os.path.join(self.hermes, "config.yaml"), "r",
                  encoding="utf-8") as f:
            self.assertIn("provider: opencode-go", f.read())

    # ------------------------------------------------------------- /heal cmds

    def test_heal_commands_scan_fix_status(self):
        # fake repo root with one plugin, hermes missing it + missing env key
        alpha = os.path.join(self.root, "plugins", "alpha")
        os.makedirs(alpha)
        open(os.path.join(alpha, "__init__.py"), "w").close()
        self._make_hermes(plugins=[], config="model:\n  provider: opencode-go\n")
        # temp checks.json: fast watchdog check + postcondition on config.yaml
        checks = {
            "watchdog": [{"name": "echo-ok",
                          "cmd": ["python", "-c", "print('ok')"],
                          "timeout": 5, "quiet_after_s": 0}],
            "postconditions": [{"name": "config-present", "type": "file_exists",
                                "target": os.path.join(self.hermes, "config.yaml"),
                                "value": True}],
        }
        checks_file = os.path.join(self._tmp.name, "checks.json")
        with open(checks_file, "w", encoding="utf-8") as f:
            json.dump(checks, f)
        os.environ["XOMNI_CHECKS"] = checks_file

        spec = importlib.util.spec_from_file_location(
            "self_healing_plugin",
            os.path.join(os.path.dirname(os.path.abspath(core.__file__)),
                         "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        scan = mod._handle_heal("scan")
        self.assertIn("echo-ok", scan)
        self.assertIn("config-present", scan)
        self.assertIn("PASS", scan)
        self.assertIn("drift(s) found", scan)
        # roster source is environment-dependent (real xomni_cli may be
        # installed); GROQ_API_KEY is always part of the expected env keys
        self.assertIn("env.GROQ_API_KEY", scan)

        fix = mod._handle_heal("fix env.GROQ_API_KEY")
        self.assertIn("FIXED", fix)
        with open(os.path.join(self.hermes, ".env"), "r",
                  encoding="utf-8") as f:
            self.assertIn("GROQ_API_KEY=", f.read())

        status = mod._handle_heal("status")
        # watchdog check passed (no kill) => only the drift fix is audited
        self.assertIn("drift", status)
        self.assertIn("env.GROQ_API_KEY", status)

        # audit log physically exists at ~/.xomni-heal (env-overridden)
        self.assertTrue(os.path.isfile(os.path.join(self.heal_dir, "heal.jsonl")))


    # ------------------------------------------- multi-profile (U-ASSURE-2)

    def _make_profiles(self, names=("xomni", "xomni-test")):
        """Build a FAKE profiles tree under the temp hermes home."""
        self._make_hermes(config="model:\n  provider: opencode-go\n")
        for n in names:
            home = os.path.join(self.hermes, "profiles", n)
            os.makedirs(home, exist_ok=True)
            with open(os.path.join(home, "config.yaml"), "w",
                      encoding="utf-8") as f:
                f.write("model:\n  provider: opencode-go\n")
        return self.hermes

    def _load_plugin(self, tag="self_healing_plugin"):
        spec = importlib.util.spec_from_file_location(
            tag, os.path.join(os.path.dirname(os.path.abspath(core.__file__)),
                              "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_discover_profiles_finds_base_plus_all(self):
        """Discovery finds base + every profiles/* child with a config.yaml."""
        self._make_profiles(("xomni", "xomni-test"))
        found = core.discover_profiles()
        self.assertEqual([p["name"] for p in found],
                         ["base", "xomni", "xomni-test"])
        homes = {p["name"]: p["home"] for p in found}
        self.assertEqual(homes["base"], self.hermes)
        self.assertEqual(homes["xomni"],
                         os.path.join(self.hermes, "profiles", "xomni"))
        self.assertEqual(homes["xomni-test"],
                         os.path.join(self.hermes, "profiles", "xomni-test"))
        # a profiles/* dir WITHOUT config.yaml is not a profile
        os.makedirs(os.path.join(self.hermes, "profiles", "not-a-profile"))
        self.assertEqual([p["name"] for p in core.discover_profiles()],
                         ["base", "xomni", "xomni-test"])
        # /heal profiles surfaces every profile
        out = self._load_plugin("self_healing_plugin_disc")._handle_heal("profiles")
        for name in ("base", "xomni", "xomni-test"):
            self.assertIn(name, out)
        self.assertIn("drift(s)", out)

    def test_scan_profile_detects_drift_per_profile(self):
        """Per-profile drift detection: same check, different homes."""
        self._make_profiles(("xomni",))
        # base has GROQ_API_KEY present; profile xomni does not
        self._make_hermes(env_lines=["GROQ_API_KEY="])
        res = core.scan_profiles()
        self.assertEqual(set(res), {"base", "xomni"})
        self.assertIsNone(res["base"]["error"])
        self.assertFalse(any(d["key"] == "env.GROQ_API_KEY"
                             for d in res["base"]["drifts"]))
        self.assertTrue(any(d["key"] == "env.GROQ_API_KEY"
                            for d in res["xomni"]["drifts"]))
        # targeted scan of one profile only
        one = core.scan_profiles(["xomni"])
        self.assertEqual(set(one), {"xomni"})
        self.assertEqual(one["xomni"]["profile"], "xomni")

    def test_fix_profile_writes_placeholder_and_audits_profile_name(self):
        """fix(profile) writes bare KEY= placeholders only + audited w/ name."""
        self._make_profiles(("xomni",))
        r = core.fix_profiles(["xomni"], apply=True)["xomni"]
        self.assertIsNone(r["error"])
        self.assertGreaterEqual(r["fixed"], 1)
        env_path = os.path.join(self.hermes, "profiles", "xomni", ".env")
        with open(env_path, "r", encoding="utf-8") as f:
            env = f.read()
        self.assertIn("GROQ_API_KEY=\n", env)   # placeholder, empty value
        self.assertNotIn("sk-", env)            # never a secret value
        # audit entries carry the profile name (fix and fix_failed both logged)
        entries = core.last_audit_entries(200)
        profiled = [e for e in entries if e.get("profile") == "xomni"]
        self.assertTrue(profiled)
        self.assertTrue(all(e["detector"] == "drift"
                            and e["action"] in ("fix", "fix_failed")
                            for e in profiled))
        # the placeholder .env fix must have succeeded
        self.assertTrue(any(e["action"] == "fix"
                            and e["subject"] == "env.GROQ_API_KEY"
                            for e in profiled))
        self.assertTrue(all(e["subject"].startswith(("env.", "provider.", "plugins."))
                            for e in profiled))
        # other profiles untouched by the xomni-only fix
        self.assertFalse(os.path.isfile(os.path.join(self.hermes, ".env")))

    def test_scan_unreadable_profile_loud_error(self):
        """Unreadable / unknown profiles -> loud error entries, never crash."""
        self._make_profiles(("xomni",))
        # unknown name -> loud error, scan continues
        res = core.scan_profiles(["xomni", "ghost"])
        self.assertFalse(res["ghost"]["ok"])
        self.assertIn("unknown profile", res["ghost"]["error"])
        self.assertIsNone(res["xomni"]["error"])
        # home exists but config.yaml vanished -> loud
        os.remove(os.path.join(self.hermes, "profiles", "xomni", "config.yaml"))
        res2 = core.scan_profile({"name": "xomni",
                                  "home": os.path.join(self.hermes, "profiles", "xomni")})
        self.assertFalse(res2["ok"])
        self.assertIn("unreadable", res2["error"])
        # home path gone entirely -> loud
        res3 = core.scan_profile({"name": "gone",
                                  "home": os.path.join(self.hermes, "profiles", "gone")})
        self.assertFalse(res3["ok"])
        self.assertIn("unreadable profile home", res3["error"])
        # fix on an unreadable profile is loud too and audits nothing
        r = core.fix_profile({"name": "gone",
                              "home": os.path.join(self.hermes, "profiles", "gone")})
        self.assertFalse(r["fixed"])
        self.assertIn("unreadable", r["error"])
        self.assertEqual(core.last_audit_entries(), [])

    def test_fix_all_mode_aggregates_and_requires_yes(self):
        """all-mode aggregates every profile; without --yes it's a dry run."""
        self._make_profiles(("xomni", "xomni-test"))
        # command layer: /heal fix all without --yes -> plan only, no writes
        mod = self._load_plugin("self_healing_plugin_all")
        dry = mod._handle_heal("fix all")
        self.assertIn("would fix", dry)
        self.assertIn("--yes", dry)
        self.assertFalse(os.path.isfile(os.path.join(self.hermes, ".env")))
        # core plan matches
        plan = core.fix_profiles(apply=False)
        self.assertEqual(set(plan), {"base", "xomni", "xomni-test"})
        # apply: every profile fixed, each audited under its own name
        out = core.fix_profiles(apply=True)
        for name in ("base", "xomni", "xomni-test"):
            self.assertIsNone(out[name]["error"], out[name])
            self.assertGreaterEqual(out[name]["fixed"], 1)
        entries = core.last_audit_entries(500)
        by_profile = {}
        for e in entries:
            if e.get("profile") and e["detector"] == "drift":
                by_profile[e["profile"]] = by_profile.get(e["profile"], 0) + 1
        self.assertEqual(set(by_profile), {"base", "xomni", "xomni-test"})
        # every profile's .env holds bare KEY= placeholders only
        for name in ("base", "xomni", "xomni-test"):
            home = (self.hermes if name == "base"
                    else os.path.join(self.hermes, "profiles", name))
            with open(os.path.join(home, ".env"), "r", encoding="utf-8") as f:
                env = f.read()
            self.assertIn("GROQ_API_KEY=\n", env)
            self.assertNotIn("sk-", env)

    def test_zero_hooks_register_only_heal_command(self):
        """register() wires ONLY the /heal command — zero hooks."""
        mod = self._load_plugin("self_healing_plugin_hooks")
        calls = []

        class Ctx:
            def register_command(self, name, **kw):
                calls.append(("command", name))

            def register_hook(self, *a, **kw):
                calls.append(("hook", a))

        mod.register(Ctx())
        kinds = [c[0] for c in calls]
        self.assertEqual(kinds, ["command"])
        self.assertEqual(calls[0][1], "heal")
        self.assertNotIn("hook", kinds)


if __name__ == "__main__":
    unittest.main()
