"""Tests for the capability-probe plugin (core.py + register() wiring).

18 methods, zero hooks, zero monkeypatching: the network call is injected via
probe(..., urlopen=fake), the registry path via data_path=tempfile, and the
provider table via table=[...]. The API key is never printed — tests assert
the rendered text, exceptions, and the request URL never contain the key.

Run: cd plugins/capability-probe && python -m unittest tests.test_core -q
"""
import importlib.util
import io
import json
import os
import socket
import sys
import tempfile
import types
import unittest
import urllib.error

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.dirname(_HERE)
sys.path.insert(0, _PLUGIN_DIR)  # capability-probe/ -> import core

import core  # noqa: E402

SECRET = "sk-PROBE-SECRET-do-not-print-9f3a"
OPENAI_PAYLOAD = {"object": "list", "data": [
    {"id": "minimax-m3", "object": "model", "created": 1, "owned_by": "minimax"},
    {"id": "deepseek-v4-flash", "object": "model", "created": 2, "owned_by": "deepseek"},
    {"id": "grok-4.5", "object": "model", "created": 3, "owned_by": "xai"},
]}
ANTHROPIC_PAYLOAD = {"data": [
    {"type": "model", "id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5",
     "created_at": "2026-01-01T00:00:00Z"},
    {"type": "model", "id": "claude-opus-4-6", "display_name": "Claude Opus 4.6",
     "created_at": "2026-02-01T00:00:00Z"},
], "has_more": False}


class FakeResp:
    """Minimal urlopen response: context manager with .status and .read()."""

    def __init__(self, body, status=200):
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.body


class RecordingUrlopen:
    """Captures the request (url + headers) and returns a canned response."""

    def __init__(self, body, status=200, exc=None):
        self.body, self.status, self.exc = body, status, exc
        self.last_req = None

    def __call__(self, req, timeout=None):
        self.last_req = req
        if self.exc is not None:
            raise self.exc
        return FakeResp(self.body, self.status)


def _temp_registry(extra_models=()):
    """Copy of the real capabilities.json into a temp file (plus extras)."""
    real = os.path.join(os.path.dirname(_PLUGIN_DIR), "omni-registry",
                        "data", "capabilities.json")
    with open(real, encoding="utf-8") as f:
        data = json.load(f)
    data["models"] = list(data["models"]) + [dict(m) for m in extra_models]
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


class ParseTests(unittest.TestCase):
    """OpenAI + Anthropic /models shapes -> normalized entries."""

    def test_parse_openai_data_list_and_bare_list(self):
        entries = core.parse_openai(OPENAI_PAYLOAD, probed_at="2026-08-13T00:00:00Z")
        self.assertEqual([m["id"] for m in entries],
                         ["minimax-m3", "deepseek-v4-flash", "grok-4.5"])
        for m in entries:
            self.assertEqual(m["source"], "live-probe")
            self.assertEqual(m["probed_at"], "2026-08-13T00:00:00Z")
            self.assertIn("context_window", m)  # None when metadata absent
            self.assertIsNone(m["vision"])
        bare = core.parse_openai(OPENAI_PAYLOAD["data"], probed_at="t")
        self.assertEqual(len(bare), 3)

    def test_parse_openai_metadata_and_ctx_coercion(self):
        payload = {"data": [
            {"id": "big", "context_length": 131072, "vision": True, "reasoning": True},
            {"id": "strctx", "context": "128k"},
            {"id": "mctx", "max_context": "1m"},
            {"id": "noctx", "owned_by": "x"},
        ]}
        by_id = {m["id"]: m for m in core.parse_openai(payload, probed_at="t")}
        self.assertEqual(by_id["big"]["context_window"], 131072)
        self.assertIs(by_id["big"]["vision"], True)
        self.assertIs(by_id["big"]["reasoning"], True)
        self.assertEqual(by_id["strctx"]["context_window"], 128 * 1024)
        self.assertEqual(by_id["mctx"]["context_window"], 1024 * 1024)
        self.assertIsNone(by_id["noctx"]["context_window"])

    def test_parse_anthropic_shape(self):
        entries = core.parse_anthropic(ANTHROPIC_PAYLOAD, probed_at="t")
        self.assertEqual([m["id"] for m in entries],
                         ["claude-sonnet-4-5", "claude-opus-4-6"])
        self.assertEqual(entries[0]["name"], "Claude Sonnet 4.5")
        self.assertEqual(entries[0]["source"], "live-probe")
        # the OpenAI shape is tolerated by the anthropic parser too
        self.assertEqual(len(core.parse_anthropic(OPENAI_PAYLOAD, probed_at="t")), 3)

    def test_parse_bad_shape_loud(self):
        for parser in (core.parse_openai, core.parse_anthropic):
            with self.assertRaises(core.ProbeError) as cm:
                parser({"data": "nope"}, probed_at="t")
            self.assertIn("api_type", str(cm.exception))
            self.assertIn("Fix:", str(cm.exception))
        with self.assertRaises(core.ProbeError):
            core.parse_models({"data": 42}, api_type="openai", probed_at="t")


class ProbeTests(unittest.TestCase):
    """probe(): live GET /models, loud failures, key hygiene."""

    def test_probe_http_200_normalized(self):
        rec = RecordingUrlopen(OPENAI_PAYLOAD)
        res = core.probe("zen", "https://opencode.ai/zen/go/v1", key_env="K",
                         key=SECRET, urlopen=rec)
        self.assertEqual(res["http"], 200)
        self.assertEqual(res["count"], 3)
        self.assertEqual(res["models"][0]["id"], "minimax-m3")
        self.assertEqual(res["api_type"], "openai")
        # key hygiene: Authorization header carries it, URL never does
        self.assertEqual(rec.last_req.headers["Authorization"], f"Bearer {SECRET}")
        self.assertNotIn(SECRET, rec.last_req.full_url)
        self.assertEqual(rec.last_req.full_url,
                         "https://opencode.ai/zen/go/v1/models")

    def test_probe_401_key_rejected_loud(self):
        rec = RecordingUrlopen(None, exc=urllib.error.HTTPError(
            "https://x/models", 401, "Unauthorized", {}, None))
        with self.assertRaises(core.ProbeError) as cm:
            core.probe("p", "https://x.example/v1", key_env="MY_KEY",
                       key=SECRET, urlopen=rec)
        msg = str(cm.exception)
        self.assertIn("401", msg)
        self.assertIn("key rejected", msg)
        self.assertIn("MY_KEY", msg)          # names the env var...
        self.assertIn(core.ENV_PATH, msg)     # ...and the .env path
        self.assertNotIn(SECRET, msg)         # ...but never the key itself

    def test_probe_network_error_loud(self):
        rec = RecordingUrlopen(None, exc=urllib.error.URLError(
            socket.gaierror(-2, "Name or service not known")))
        with self.assertRaises(core.ProbeError) as cm:
            core.probe("p", "https://unreachable.example/v1", key_env="K",
                       key=SECRET, urlopen=rec)
        msg = str(cm.exception)
        self.assertIn("network error", msg)
        self.assertIn("https://unreachable.example/v1/models", msg)
        self.assertIn("Fix:", msg)
        self.assertNotIn(SECRET, msg)
        # timeout is a distinct network failure — same loud, fix-naming contract
        rec = RecordingUrlopen(None, exc=socket.timeout("timed out"))
        with self.assertRaises(core.ProbeError) as cm:
            core.probe("p", "https://slow.example/v1", key_env="K",
                       key=SECRET, timeout=15, urlopen=rec)
        msg = str(cm.exception)
        self.assertIn("timeout", msg)
        self.assertIn("15", msg)
        self.assertNotIn(SECRET, msg)

    def test_probe_non_200_loud(self):
        rec = RecordingUrlopen(b"nope", status=500)
        with self.assertRaises(core.ProbeError) as cm:
            core.probe("p", "https://x.example/v1", key_env="K",
                       key=SECRET, urlopen=rec)
        msg = str(cm.exception)
        self.assertIn("HTTP 500", msg)
        self.assertIn("api_type=openai", msg)
        self.assertIn("Fix:", msg)
        self.assertNotIn(SECRET, msg)

    def test_probe_non_json_loud(self):
        rec = RecordingUrlopen(b"<html>not json</html>", status=200)
        with self.assertRaises(core.ProbeError) as cm:
            core.probe("p", "https://x.example/v1", key_env="K",
                       key=SECRET, urlopen=rec)
        self.assertIn("non-JSON", str(cm.exception))
        self.assertIn("Fix:", str(cm.exception))

    def test_probe_missing_key_loud(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write("OTHER_KEY=abc\n")  # target env var absent
            old = core.ENV_PATH
            core.ENV_PATH = env
            try:
                for k in ("", "  "):
                    with self.assertRaises(core.ProbeError) as cm:
                        core.probe("p", "https://x.example/v1", key_env="NEEDED_KEY",
                                   urlopen=RecordingUrlopen(OPENAI_PAYLOAD))
                    msg = str(cm.exception)
                    self.assertIn("NEEDED_KEY", msg)
                    self.assertIn("no API key", msg)
                    self.assertIn(env, msg)
                    self.assertNotIn(SECRET, msg)
            finally:
                core.ENV_PATH = old


class DiffAndMergeTests(unittest.TestCase):
    """diff_against + merge_into_registry (source='live-probe' semantics)."""

    def test_diff_added_removed_changed(self):
        reg = {
            "a": {"id": "a", "status": "active",
                  "context_window": {"value": 500}},
            "b": {"id": "b", "status": "active"},
            "c": {"id": "c", "status": "removed"},  # tombstone: never re-flagged
            "d": {"id": "d", "status": "unverified", "source": "live-probe"},
        }
        probed = [
            {"id": "a", "context_window": 1000},   # changed: 500 -> 1000
            {"id": "d", "context_window": None},   # still present
            {"id": "e", "context_window": None},   # new
        ]
        d = core.diff_against(probed, reg)
        self.assertEqual(d["added"], ["e"])
        self.assertEqual(d["removed"], ["b"])      # active but not probed
        self.assertNotIn("c", d["removed"])        # tombstone stays quiet
        self.assertEqual(d["changed"], [{"id": "a", "from": 500, "to": 1000}])

    def test_merge_tags_existing_preserves_envelopes(self):
        path = _temp_registry()
        try:
            before = core.registry_load(path)
            probed = core.parse_openai(OPENAI_PAYLOAD, probed_at="t")
            m = core.merge_into_registry(
                probed, data_path=path, provider_id="Zen gateway (opencode.ai)",
                base_url="https://opencode.ai/zen/go/v1", now="2026-08-13T00:00:00Z")
            self.assertEqual(m["probed"], 3)
            self.assertEqual(m["added"], [])
            self.assertEqual(len(m["updated"]), 3)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            by_id = {r["id"]: r for r in data["models"]}
            rec = by_id["minimax-m3"]
            self.assertEqual(rec["source"], "live-probe")       # distinct tag
            self.assertEqual(rec["live_probe"]["provider"], "Zen gateway (opencode.ai)")
            self.assertEqual(rec["live_probe"]["probed_at"], "t")
            # capability envelopes untouched (F3: report, don't auto-accept):
            # same value AND same source attribution as before the merge
            self.assertEqual(rec["context_window"],
                             before["minimax-m3"]["context_window"])
            self.assertEqual(rec["capabilities"],
                             before["minimax-m3"]["capabilities"])
            self.assertEqual(rec["verified"], before["minimax-m3"]["verified"])
            self.assertEqual(rec["provenance"]["updated_at"], "2026-08-13T00:00:00Z")
            srcs = [s["name"] for s in data["sources"]]
            self.assertIn("capability-probe:Zen gateway (opencode.ai)", srcs)
            self.assertEqual(by_id["deepseek-v4-flash"]["context_window"]["value"],
                             1_000_000)  # deepseek envelope intact
        finally:
            os.unlink(path)

    def test_merge_adds_new_unverified_and_missing_registry_loud(self):
        path = _temp_registry()
        try:
            probed = [{"id": "brand-new-model-42", "name": "Brand New 42",
                       "context_window": None, "vision": None, "reasoning": None,
                       "source": "live-probe", "probed_at": "t"}]
            m = core.merge_into_registry(probed, data_path=path,
                                         provider_id="p", now="t")
            self.assertEqual(m["added"], ["brand-new-model-42"])
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            rec = next(r for r in data["models"] if r["id"] == "brand-new-model-42")
            self.assertEqual(rec["status"], "unverified")  # listed, never call-verified
            self.assertEqual(rec["source"], "live-probe")
            self.assertIsNone(rec["context_window"])       # unknown, not fabricated
            self.assertFalse(rec["verified"]["ok"])
            self.assertEqual(rec["provenance"]["primary"], "live-probe")
        finally:
            os.unlink(path)
        # missing registry -> loud ProbeError naming the path
        missing = os.path.join(tempfile.gettempdir(), "no-such-capabilities.json")
        with self.assertRaises(core.ProbeError) as cm:
            core.merge_into_registry([], data_path=missing)
        self.assertIn(missing, str(cm.exception))
        self.assertIn("Fix:", str(cm.exception))

    def test_tombstones_never_retagged(self):
        path = _temp_registry()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            tid = data["tombstones"][0]["id"]  # kimi-k2 or glm-4.6
            core.merge_into_registry(
                [{"id": tid, "context_window": None, "probed_at": "t"}],
                data_path=path, provider_id="p", now="t")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            tomb = next(r for r in data["tombstones"] if r["id"] == tid)
            self.assertNotIn("source", tomb)          # frozen history untouched
            self.assertNotIn("live_probe", tomb)
            self.assertEqual(tomb["status"], "removed")
        finally:
            os.unlink(path)


class CommandTests(unittest.TestCase):
    """/probe <id> and /probe all rendering (injected table + urlopen)."""

    TABLE = [
        {"name": "Zen gateway (opencode.ai)", "env": "CAP_PROBE_ZEN",
         "base_url": "https://opencode.ai/zen/go/v1", "api_type": "openai"},
        {"name": "Anthropic (Claude)", "env": "CAP_PROBE_ANTHROPIC",
         "base_url": "https://api.anthropic.com", "api_type": "anthropic"},
    ]

    def setUp(self):
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_probe_command_renders_count_diff_no_key(self):
        os.environ["CAP_PROBE_ZEN"] = SECRET
        path = _temp_registry()
        try:
            text = core.probe_command_text(
                "Zen gateway (opencode.ai)", table=self.TABLE,
                urlopen=RecordingUrlopen(OPENAI_PAYLOAD), data_path=path)
            self.assertIn("LIVE ✓ HTTP 200", text)
            self.assertIn("3 models", text)
            self.assertIn("diff vs registry: 0 added, 22 removed, 0 changed",
                          text)  # 25 active - 3 probed = 22 removed
            self.assertIn("source=live-probe", text)
            self.assertIn("minimax-m3", text)
            self.assertIn("never printed", text)
            self.assertNotIn(SECRET, text)  # key never in rendered output
        finally:
            os.unlink(path)

    def test_probe_command_unknown_provider_and_failure_loud(self):
        text = core.probe_command_text("nope", table=self.TABLE,
                                       urlopen=RecordingUrlopen(OPENAI_PAYLOAD))
        self.assertIn("unknown provider 'nope'", text)
        self.assertIn("Anthropic (Claude)", text)
        # live failure renders loud, keyless
        os.environ["CAP_PROBE_ZEN"] = SECRET
        path = _temp_registry()
        try:
            rec = RecordingUrlopen(None, exc=urllib.error.HTTPError(
                "https://x/models", 401, "Unauthorized", {}, None))
            text = core.probe_command_text("Zen gateway (opencode.ai)",
                                           table=self.TABLE, urlopen=rec,
                                           data_path=path)
            self.assertIn("key rejected", text)
            self.assertIn("CAP_PROBE_ZEN", text)
            self.assertNotIn(SECRET, text)
        finally:
            os.unlink(path)

    def test_probe_all_renders_skips_keyless(self):
        os.environ["CAP_PROBE_ZEN"] = SECRET  # only one key present
        path = _temp_registry()
        try:
            text = core.probe_all_command_text(
                table=self.TABLE,
                urlopen=RecordingUrlopen(OPENAI_PAYLOAD), data_path=path)
            self.assertIn("2 providers in table", text)
            self.assertIn("✓ Zen gateway (opencode.ai): LIVE HTTP 200 — 3 models", text)
            self.assertIn("no key (env 'CAP_PROBE_ANTHROPIC' empty) — skipped", text)
            self.assertIn("probed 1 provider(s), 0 failed", text)
            self.assertNotIn(SECRET, text)
        finally:
            os.unlink(path)

    def test_register_zero_hooks(self):
        with open(os.path.join(_PLUGIN_DIR, "__init__.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("register_hook", src)  # zero-hooks rule

        pkg = types.ModuleType("capability_probe")
        pkg.__path__ = [_PLUGIN_DIR]
        sys.modules["capability_probe"] = pkg
        # share the SAME core module instance (gh-ops pattern) so env/path
        # swaps below apply to the module the __init__ actually uses
        sys.modules["capability_probe.core"] = core
        spec = importlib.util.spec_from_file_location(
            "capability_probe.__init__", os.path.join(_PLUGIN_DIR, "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["capability_probe.__init__"] = mod
        spec.loader.exec_module(mod)

        class FakeCtx:
            def __init__(self):
                self.commands, self.tools, self.hooks = [], [], []

            def register_command(self, name, handler=None, description="",
                                 args_hint=""):
                self.commands.append(name)

            def register_tool(self, name, **kw):
                self.tools.append(name)

            def register_hook(self, *a, **k):
                self.hooks.append(a)

        ctx = FakeCtx()
        mod.register(ctx)
        self.assertEqual(ctx.commands, ["probe"])
        self.assertEqual(ctx.tools, [])
        self.assertEqual(ctx.hooks, [])  # zero hooks registered
        # handler routing: 'all' -> probe_all, anything else -> probe <id>.
        # Fully hermetic: blank BOTH key sources (os.environ may carry real
        # *_API_KEY vars exported by the host session, and the real .env holds
        # OPENCODE_GO_API_KEY) and point the registry path at a temp file so
        # no live probe / registry write can happen from a unit test.
        saved_env = dict(os.environ)
        for k in list(os.environ):
            if "API_KEY" in k or k in ("XOMNI_OLLAMA", "LMSTUDIO", "GROWW_API_KEY"):
                del os.environ[k]
        old_env, old_reg = core.ENV_PATH, core.REGISTRY_PATH
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("UNRELATED=1\n")
            blank_env = f.name
        fd, blank_reg = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        core.ENV_PATH, core.REGISTRY_PATH = blank_env, blank_reg
        try:
            out = mod._handle_probe("all")
            self.assertTrue(out.startswith("/probe all"), out)
            self.assertIn("probed 0 provider(s)", out)  # no keys -> nothing probed
            with open(blank_reg, encoding="utf-8") as f:
                self.assertEqual(f.read(), "")  # registry never written
        finally:
            os.environ.clear()
            os.environ.update(saved_env)
            core.ENV_PATH, core.REGISTRY_PATH = old_env, old_reg
            os.unlink(blank_env)
            os.unlink(blank_reg)
        self.assertIn("unknown provider", mod._handle_probe("no-such-provider"))


if __name__ == "__main__":
    unittest.main()
