"""Tests for the local-models plugin — probing, detection, config gen, wiring.

Runs standalone: `python -m unittest tests.test_core -v` from the plugin dir.
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error

from unittest import mock

import core


def _load_init():
    """Load the plugin's __init__.py under a plain module name so the
    `from . import core` falls back to `import core` (cwd is on sys.path)."""
    init_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "__init__.py")
    spec = importlib.util.spec_from_file_location("local_models_plugin", init_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["local_models_plugin"] = mod
    spec.loader.exec_module(mod)
    return mod


def _fake_resp(status: int, payload: dict | list) -> mock.MagicMock:
    """A urlopen result: MagicMock with .status and .read() -> JSON bytes.

    urlopen() itself is mocked to return a context manager whose __enter__
    yields this fake — matching `with urlopen(req, timeout=...) as resp:`.
    """
    fake = mock.MagicMock()
    fake.status = status
    fake.read.return_value = json.dumps(payload).encode()
    return fake


class ProbeServerTests(unittest.TestCase):
    def test_probe_success(self):
        fake = _fake_resp(200, {"object": "list", "data": [{"id": "llama3.2"}, {"id": "qwen2.5:7b"}]})
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            r = core.probe_server("http://127.0.0.1:11434/v1")
        self.assertTrue(r["ok"])
        self.assertEqual(r["http"], 200)
        self.assertEqual(r["models"], ["llama3.2", "qwen2.5:7b"])
        self.assertIsNone(r["error"])
        # URL is {base}/models and the request carries a browser User-Agent
        req = m.call_args.args[0]
        self.assertEqual(req.full_url, "http://127.0.0.1:11434/v1/models")
        self.assertIn("Mozilla", req.get_header("User-agent"))
        self.assertEqual(m.call_args.kwargs.get("timeout"), 3)

    def test_probe_strips_trailing_slash(self):
        fake = _fake_resp(200, {"data": [{"id": "tiny"}]})
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            r = core.probe_server("http://127.0.0.1:1234/v1/")
        self.assertTrue(r["ok"])
        self.assertEqual(m.call_args.args[0].full_url, "http://127.0.0.1:1234/v1/models")

    def test_probe_legacy_models_key(self):
        fake = _fake_resp(200, {"models": [{"id": "tiny"}, {"id": "small"}]})
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            r = core.probe_server("http://x/v1")
        self.assertEqual(r["models"], ["tiny", "small"])

    def test_probe_bare_list_payload(self):
        fake = _fake_resp(200, ["a", "b"])
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            r = core.probe_server("http://x/v1")
        self.assertEqual(r["models"], ["a", "b"])

    def test_probe_connection_refused(self):
        with mock.patch.object(core, "urlopen", side_effect=OSError("Connection refused")):
            r = core.probe_server("http://127.0.0.1:11434/v1")
        self.assertFalse(r["ok"])
        self.assertIsNone(r["http"])
        self.assertEqual(r["models"], [])
        self.assertIn("refused", r["error"].lower())

    def test_probe_http_error(self):
        # a REAL urllib.error.HTTPError instance, not a mock
        err = urllib.error.HTTPError(
            "http://127.0.0.1:11434/v1/models", 404, "Not Found", {}, io.BytesIO(b"")
        )
        with mock.patch.object(core, "urlopen", side_effect=err):
            r = core.probe_server("http://127.0.0.1:11434/v1")
        self.assertFalse(r["ok"])
        self.assertEqual(r["http"], 404)
        self.assertIn("404", r["error"])

    def test_probe_empty_base_url(self):
        r = core.probe_server("   ")
        self.assertFalse(r["ok"])
        self.assertIn("empty", r["error"])


class ProbeParsingEdgeTests(unittest.TestCase):
    """Edge-case payload parsing for Ollama / LM Studio / OpenAI /models responses."""

    def test_extract_model_ids_skips_invalid_rows(self):
        payload = {"data": [{"id": "a"}, {"name": "no-id"}, "b", 42, {"id": ""}, None]}
        self.assertEqual(core._extract_model_ids(payload), ["a", "b"])

    def test_extract_model_ids_mixed_shapes(self):
        self.assertEqual(core._extract_model_ids(None), [])
        self.assertEqual(core._extract_model_ids({"data": []}), [])
        self.assertEqual(core._extract_model_ids("nope"), [])
        self.assertEqual(core._extract_model_ids({"data": "not-a-list"}), [])
        self.assertEqual(core._extract_model_ids({"models": [{"id": "x"}]}), ["x"])

    def test_probe_invalid_json_reports_error(self):
        fake = mock.MagicMock()
        fake.status = 200
        fake.read.return_value = b"{broken json"
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            r = core.probe_server("http://127.0.0.1:11434/v1")
        self.assertFalse(r["ok"])
        self.assertEqual(r["models"], [])
        self.assertTrue(r["error"])

    def test_probe_json_string_payload_ok_with_no_models(self):
        # A quoted JSON string is valid JSON: parses, but yields no model ids.
        fake = _fake_resp(200, "just a string")
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            r = core.probe_server("http://127.0.0.1:11434/v1")
        self.assertTrue(r["ok"])
        self.assertEqual(r["models"], [])

    def test_probe_lmstudio_payload_shape(self):
        # LM Studio returns {"data": [{"id": "...", "object": "model", ...}]}
        fake = _fake_resp(200, {"data": [{"id": "gemma3-4b", "object": "model"}, {"id": "qwen2.5-7b"}]})
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            r = core.probe_server(core.LM_STUDIO_BASE_URL)
        self.assertEqual(r["models"], ["gemma3-4b", "qwen2.5-7b"])

    def test_probe_ollama_payload_shape(self):
        # Ollama /v1/models returns {"object":"list","data":[...]}
        fake = _fake_resp(200, {"object": "list", "data": [{"id": "llama3.2:3b"}]})
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            r = core.probe_server(core.OLLAMA_BASE_URL)
        self.assertEqual(r["models"], ["llama3.2:3b"])


class DetectServersExtraTests(unittest.TestCase):
    """detect_servers with extras, timeouts and degenerate inputs."""

    def test_detect_servers_with_custom_extra(self):
        fake = _fake_resp(200, {"data": [{"id": "custom-model"}]})
        extras = [{"id": "vllm", "name": "vLLM", "base_url": "http://127.0.0.1:8000/v1"}]
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            results = core.detect_servers(defaults=extras)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["server_id"], "vllm")
        self.assertEqual(results[0]["name"], "vLLM")
        self.assertTrue(results[0]["ok"])

    def test_detect_servers_forwards_timeout(self):
        fake = _fake_resp(200, {"data": []})
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            core.detect_servers(defaults=[{"id": "x", "base_url": "http://x/v1"}], timeout=1.5)
        self.assertEqual(m.call_args.kwargs.get("timeout"), 1.5)

    def test_detect_servers_empty_base_url_flagged_without_probe(self):
        with mock.patch.object(core, "urlopen") as m:
            results = core.detect_servers(defaults=[{"id": "bogus", "name": "Bogus", "base_url": "  "}])
        m.assert_not_called()  # probe_server short-circuits on empty base
        self.assertFalse(results[0]["ok"])
        self.assertIn("empty", results[0]["error"])


class ScanTextTests(unittest.TestCase):
    """/localmodels scan output format (scan_text)."""

    @staticmethod
    def _result(**kw):
        r = {"server_id": "x", "name": "X", "base_url": "http://x/v1",
             "ok": False, "http": None, "models": [], "error": None}
        r.update(kw)
        return r

    def test_scan_text_up_down_format(self):
        results = [
            self._result(server_id="ollama", name="Ollama", base_url=core.OLLAMA_BASE_URL,
                         ok=True, http=200, models=["llama3.2"]),
            self._result(server_id="lmstudio", name="LM Studio", base_url=core.LM_STUDIO_BASE_URL,
                         ok=False, error="Connection refused"),
        ]
        t = core.scan_text(results)
        self.assertIn("1 of 2", t)
        self.assertIn("UP    ollama", t)
        self.assertIn("models: llama3.2", t)
        self.assertIn("DOWN  lmstudio", t)
        self.assertIn("Connection refused", t)
        self.assertIn("usable: ollama", t)

    def test_scan_text_no_models_reported_placeholder(self):
        results = [self._result(server_id="ollama", ok=True, http=200, models=[])]
        t = core.scan_text(results)
        self.assertIn("(no models reported)", t)

    def test_scan_text_all_down_no_usable_line(self):
        results = [self._result(server_id="ollama", ok=False, error="refused")]
        t = core.scan_text(results)
        self.assertIn("0 of 1", t)
        self.assertNotIn("usable:", t)


class DetectServersTests(unittest.TestCase):
    def _side(self, fake):
        cm = mock.MagicMock()
        cm.__enter__.return_value = fake  # `with urlopen(...) as resp:` pattern
        def side_effect(req, timeout=3):
            if "11434" in req.full_url:  # ollama down
                raise OSError("Connection refused")
            return cm  # lmstudio up
        return side_effect

    def test_detect_servers_skips_down_servers(self):
        fake = _fake_resp(200, {"data": [{"id": "gemma3"}]})
        with mock.patch.object(core, "urlopen", side_effect=self._side(fake)):
            results = core.detect_servers()
        self.assertEqual(len(results), 2)  # both defaults reported
        down = next(r for r in results if r["server_id"] == "ollama")
        self.assertFalse(down["ok"])
        self.assertEqual(down["models"], [])
        self.assertEqual(down["base_url"], core.OLLAMA_BASE_URL)
        up = [r for r in results if r["ok"]]
        self.assertEqual(len(up), 1)  # the down server is skipped as usable
        self.assertEqual(up[0]["server_id"], "lmstudio")
        self.assertEqual(up[0]["models"], ["gemma3"])

    def test_detect_servers_default_arg_not_mutated(self):
        defaults = [{"id": "ollama", "name": "Ollama", "base_url": core.OLLAMA_BASE_URL}]
        with mock.patch.object(core, "urlopen", side_effect=OSError("refused")):
            core.detect_servers(defaults)
        self.assertEqual(defaults[0]["base_url"], core.OLLAMA_BASE_URL)  # deepcopy inside

    def test_detect_servers_accepts_string_urls(self):
        fake = _fake_resp(200, {"data": [{"id": "x"}]})
        with mock.patch.object(core, "urlopen") as m:
            m.return_value.__enter__.return_value = fake
            results = core.detect_servers(["http://127.0.0.1:9999/v1"])
        self.assertEqual(results[0]["server_id"], "127.0.0.1")
        self.assertTrue(results[0]["ok"])


class ConfigGenTests(unittest.TestCase):
    OLLAMA = {"id": "ollama", "name": "Ollama", "base_url": core.OLLAMA_BASE_URL}
    LMSTUDIO = {"id": "lmstudio", "name": "LM Studio", "base_url": core.LM_STUDIO_BASE_URL}

    def test_hermes_provider_block_ollama(self):
        block = core.hermes_provider_block(self.OLLAMA)
        self.assertIn(core.OLLAMA_BASE_URL, block)
        self.assertIn("provider: ollama", block)
        self.assertIn("key_env: local", block)

    def test_hermes_provider_block_lmstudio_and_model_hint(self):
        block = core.hermes_provider_block(self.LMSTUDIO, model_ids=["gemma3-4b"])
        self.assertIn(core.LM_STUDIO_BASE_URL, block)
        self.assertIn("# model: gemma3-4b", block)
        self.assertNotIn(core.OLLAMA_BASE_URL, block)

    def test_opencode_config_is_valid_json_with_base_url(self):
        cfg = core.opencode_config(self.OLLAMA, model_ids=["llama3.2", "qwen2.5"])
        parsed = json.loads(cfg)
        self.assertEqual(parsed["provider"]["ollama"]["options"]["baseURL"], core.OLLAMA_BASE_URL)
        self.assertEqual(parsed["provider"]["ollama"]["npm"], "@ai-sdk/openai-compatible")
        self.assertIn("llama3.2", parsed["provider"]["ollama"]["models"])

    def test_ollama_config_targets_any_server(self):
        cfg = core.ollama_config(self.LMSTUDIO)
        self.assertIn(core.LM_STUDIO_BASE_URL, cfg)
        self.assertNotIn(core.OLLAMA_BASE_URL, cfg)

    def test_config_text_bundle(self):
        text = core.config_text(self.OLLAMA, model_ids=["llama3.2"])
        self.assertIn("key_env: local", text)
        self.assertIn(core.OLLAMA_BASE_URL, text)
        self.assertIn("opencode.json provider block", text)
        self.assertIn('"baseURL": "http://127.0.0.1:11434/v1"', text)


class ConfigGenEdgeTests(unittest.TestCase):
    """Snippet generators: placeholders, defaults, JSON validity, custom servers."""

    def test_hermes_block_no_model_placeholder(self):
        block = core.hermes_provider_block(ConfigGenTests.OLLAMA)
        self.assertIn("# model: <id from /localmodels scan>", block)

    def test_hermes_block_empty_model_list_placeholder(self):
        block = core.hermes_provider_block(ConfigGenTests.OLLAMA, model_ids=[])
        self.assertIn("# model: <id from /localmodels scan>", block)

    def test_hermes_block_default_id_local(self):
        block = core.hermes_provider_block({"name": "Custom", "base_url": "http://127.0.0.1:8000/v1"})
        self.assertIn("provider: local", block)
        self.assertIn("Custom", block)
        self.assertIn("http://127.0.0.1:8000/v1", block)

    def test_opencode_config_placeholder_model_when_none(self):
        parsed = json.loads(core.opencode_config(ConfigGenTests.OLLAMA))
        prov = parsed["provider"]["ollama"]
        self.assertEqual(list(prov["models"].keys()), ["<model-id>"])
        self.assertEqual(prov["options"]["apiKey"], "local")

    def test_opencode_config_model_names_match_ids(self):
        parsed = json.loads(core.opencode_config(ConfigGenTests.OLLAMA, model_ids=["a", "b"]))
        models = parsed["provider"]["ollama"]["models"]
        self.assertEqual(models["a"]["name"], "a")
        self.assertEqual(models["b"]["name"], "b")

    def test_opencode_config_custom_server_id(self):
        server = {"id": "vllm", "name": "vLLM", "base_url": "http://127.0.0.1:8000/v1"}
        parsed = json.loads(core.opencode_config(server, model_ids=["deepseek-r1"]))
        prov = parsed["provider"]["vllm"]
        self.assertEqual(prov["name"], "vLLM")
        self.assertEqual(prov["options"]["baseURL"], "http://127.0.0.1:8000/v1")

    def test_ollama_and_opencode_configs_identical_wiring(self):
        self.assertEqual(
            core.ollama_config(ConfigGenTests.LMSTUDIO, model_ids=["x"]),
            core.opencode_config(ConfigGenTests.LMSTUDIO, model_ids=["x"]),
        )

    def test_config_text_includes_all_three_sections(self):
        text = core.config_text(ConfigGenTests.OLLAMA, model_ids=["llama3.2"])
        self.assertIn("local-models: Ollama", text)
        self.assertIn("opencode.json provider block", text)
        self.assertIn("canonical Ollama-shaped opencode block", text)
        # the embedded opencode JSON block must still parse
        section = text.split("opencode.json provider block:")[1].split("# canonical")[0].strip()
        parsed = json.loads(section)
        self.assertEqual(parsed["provider"]["ollama"]["options"]["baseURL"], core.OLLAMA_BASE_URL)


class ServersJsonTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "servers.json")
            extras = [{"id": "vllm", "name": "vLLM", "base_url": "http://127.0.0.1:8000/v1"}]
            core.save_servers(extras, path=p)
            self.assertEqual(core.load_servers(path=p), extras)

    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(core.load_servers(path=os.path.join(d, "nope.json")), [])

    def test_corrupt_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "servers.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertEqual(core.load_servers(path=p), [])

    def test_default_servers_deepcopy_isolation(self):
        a = core.default_servers()
        a[0]["base_url"] = "http://evil.invalid/v1"
        b = core.default_servers()
        self.assertEqual(b[0]["base_url"], core.OLLAMA_BASE_URL)

    def test_load_servers_dict_format(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "servers.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"servers": [{"id": "vllm", "base_url": "http://127.0.0.1:8000/v1"}]}, f)
            self.assertEqual(core.load_servers(path=p)[0]["id"], "vllm")

    def test_load_servers_unknown_shape_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "servers.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"nope": 1}, f)
            self.assertEqual(core.load_servers(path=p), [])

    def test_save_servers_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "nested", "deep", "servers.json")
            core.save_servers([{"id": "x"}], path=p)
            self.assertTrue(os.path.isfile(p))
            self.assertEqual(core.load_servers(path=p), [{"id": "x"}])


class WiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin = _load_init()

    def test_command_status_no_network(self):
        out = self.plugin._handle_localmodels("status")
        self.assertIn("ollama", out)
        self.assertIn(core.OLLAMA_BASE_URL, out)
        self.assertIn(core.LM_STUDIO_BASE_URL, out)

    def test_command_config_explicit_server(self):
        out = self.plugin._handle_localmodels("config lmstudio")
        self.assertIn(core.LM_STUDIO_BASE_URL, out)
        self.assertIn("key_env: local", out)

    def test_command_config_unknown_server(self):
        out = self.plugin._handle_localmodels("config nosuch")
        self.assertIn("unknown server", out)
        self.assertIn("ollama", out)  # lists known ids

    def test_command_config_defaults_to_ollama(self):
        out = self.plugin._handle_localmodels("config")
        self.assertIn(core.OLLAMA_BASE_URL, out)

    def test_command_unknown_subcommand(self):
        out = self.plugin._handle_localmodels("frobnicate")
        self.assertIn("unknown subcommand", out)

    def test_command_scan_probes_defaults_and_extras(self):
        canned = [
            {"server_id": "ollama", "name": "Ollama", "base_url": core.OLLAMA_BASE_URL,
             "ok": True, "http": 200, "models": ["llama3.2"], "error": None},
            {"server_id": "lmstudio", "name": "LM Studio", "base_url": core.LM_STUDIO_BASE_URL,
             "ok": False, "http": None, "models": [], "error": "Connection refused"},
        ]
        with mock.patch.object(self.plugin.core, "detect_servers", return_value=canned) as det:
            out = self.plugin._handle_localmodels("scan")
        # detect_servers got defaults + extras (deepcopied list of 2 dicts)
        self.assertEqual(len(det.call_args.args[0]), 2)
        self.assertIn("1 of 2", out)
        self.assertIn("llama3.2", out)
        self.assertIn("DOWN", out)

    def test_command_scan_output_format(self):
        canned = [
            {"server_id": "ollama", "name": "Ollama", "base_url": core.OLLAMA_BASE_URL,
             "ok": True, "http": 200, "models": ["llama3.2"], "error": None},
            {"server_id": "lmstudio", "name": "LM Studio", "base_url": core.LM_STUDIO_BASE_URL,
             "ok": False, "http": None, "models": [], "error": "refused"},
        ]
        with mock.patch.object(self.plugin.core, "detect_servers", return_value=canned):
            out = self.plugin._handle_localmodels("scan")
        self.assertIn("UP    ollama", out)
        self.assertIn("DOWN  lmstudio", out)
        self.assertIn("usable: ollama", out)
        self.assertIn("models: llama3.2", out)

    def test_tool_scan_routing(self):
        canned = [
            {"server_id": "ollama", "name": "Ollama", "base_url": core.OLLAMA_BASE_URL,
             "ok": True, "http": 200, "models": ["qwen2.5"], "error": None},
        ]
        with mock.patch.object(self.plugin.core, "detect_servers", return_value=canned):
            out = self.plugin._local_models_tool({"action": "scan"})
        self.assertIn("1 of 1", out)
        self.assertIn("qwen2.5", out)

    def test_tool_status_and_config_routing(self):
        out = self.plugin._local_models_tool({"action": "status"})
        self.assertIn(core.OLLAMA_BASE_URL, out)
        out = self.plugin._local_models_tool({"action": "config", "server": "lmstudio"})
        self.assertIn(core.LM_STUDIO_BASE_URL, out)
        out = self.plugin._local_models_tool({"action": "config"})
        self.assertIn(core.OLLAMA_BASE_URL, out)

    def test_tool_defaults_to_status_and_rejects_unknown(self):
        out = self.plugin._local_models_tool({})
        self.assertIn(core.OLLAMA_BASE_URL, out)  # missing action -> status
        out = self.plugin._local_models_tool({"action": "bogus"})
        self.assertIn("unknown action", out)

    def test_register_wires_command_and_tool(self):
        calls = {}

        class FakeCtx:
            def register_command(self, name, handler, description="", args_hint=""):
                calls.setdefault("cmd", []).append((name, handler, description, args_hint))

            def register_tool(self, name, toolset, schema, handler, **kw):
                calls["tool"] = (name, toolset, schema, handler, kw)

        self.plugin.register(FakeCtx())
        names = [c[0] for c in calls["cmd"]]
        self.assertIn("localmodels", names)
        self.assertIn("ollama", names)
        desc = next(d for n, h, d, a in calls["cmd"] if n == "localmodels")
        self.assertIn("status | scan | config", desc)
        self.assertEqual(calls["tool"][0], "local_models")
        self.assertEqual(calls["tool"][1], "local")
        schema = calls["tool"][2]
        self.assertEqual(schema["properties"]["action"]["enum"], ["status", "scan", "config"])
        self.assertEqual(schema["required"], ["action"])
        # the registered handler routes actions
        self.assertIn("unknown action", calls["tool"][3]({"action": "nope"}))


if __name__ == "__main__":
    unittest.main()
