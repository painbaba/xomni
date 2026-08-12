"""Tests for the provider pool engine (core.py)."""
import json
import os
import tempfile
import unittest

from unittest import mock

import core


class ProviderPoolTests(unittest.TestCase):
    def test_registry_has_25_verified_models(self):
        self.assertEqual(len(core.GATEWAY_MODELS), 25)
        ids = [m["id"] for m in core.GATEWAY_MODELS]
        self.assertIn("deepseek-v4-flash", ids)
        self.assertIn("minimax-m3", ids)
        # no duplicate ids
        self.assertEqual(len(ids), len(set(ids)))

    def test_recommendations_exist_in_registry(self):
        ids = {m["id"] for m in core.GATEWAY_MODELS}
        for role, model in core.RECOMMENDED.items():
            self.assertIn(model, ids, f"recommended {role}={model} not in registry")

    def test_vision_flag_only_minimax_m3(self):
        vision = [m["id"] for m in core.GATEWAY_MODELS if m["vision"]]
        self.assertEqual(vision, ["minimax-m3"])  # the only verified-vision model

    def test_filter_by_tag(self):
        fast = core.filter_by_tag("fast")
        self.assertIn("deepseek-v4-flash", fast)
        self.assertIn("qwen3.7-plus", fast)
        coding = core.filter_by_tag("coding")
        self.assertIn("kimi-k2.7-code", coding)
        self.assertNotIn("minimax-m3", coding)

    def test_recommend(self):
        self.assertEqual(core.recommend("coding"), "kimi-k2.7-code")
        self.assertEqual(core.recommend("bogus"), core.RECOMMENDED["default"])
        self.assertEqual(core.recommend(), "deepseek-v4-flash")

    def test_gateway_health_success(self):
        fake = mock.MagicMock()
        fake.status = 200
        fake.read.return_value = json.dumps({"data": [{"id": "a"}, {"id": "b"}]}).encode()
        fake.__enter__.return_value = fake  # `with urlopen(...) as resp` must yield the SAME object
        with mock.patch.object(core.urllib.request, "urlopen", return_value=fake):
            h = core.gateway_health(key="k")
        self.assertTrue(h["ok"])
        self.assertEqual(h["model_count"], 2)
        self.assertEqual(h["models"], ["a", "b"])
        self.assertIsNone(h["error"])

    def test_gateway_health_http_error(self):
        from urllib.error import HTTPError

        err = HTTPError(core.GATEWAY_URL + "/models", 403, "Forbidden", {}, None)
        with mock.patch.object(core.urllib.request, "urlopen", side_effect=err):
            h = core.gateway_health(key="k")
        self.assertFalse(h["ok"])
        self.assertEqual(h["http"], 403)
        self.assertIn("403", h["error"])

    def test_gateway_health_network_error(self):
        with mock.patch.object(core.urllib.request, "urlopen", side_effect=OSError("boom")):
            h = core.gateway_health(key="k")
        self.assertFalse(h["ok"])
        self.assertIsNone(h["http"])
        self.assertIn("boom", h["error"])

    def test_load_key_from_env(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write("OPENCODE_GO_API_KEY=sk-abc123\nOTHER=zzz\n")
            with mock.patch.object(core.os.path, "expanduser", return_value=env):
                self.assertEqual(core.load_key("OPENCODE_GO_API_KEY"), "sk-abc123")

    def test_load_key_missing_returns_empty(self):
        with mock.patch.object(core.os.path, "expanduser", return_value="/nonexistent-dir"):
            self.assertEqual(core.load_key("OPENCODE_GO_API_KEY"), "")

    def test_agent_configs_all_have_gateway_url(self):
        for agent in core.AGENT_CONFIGS:
            cfg = core.agent_config(agent)
            self.assertIsNotNone(cfg)
            self.assertIn(core.GATEWAY_URL, cfg)
            self.assertIn(core.KEY_ENV, cfg)

    def test_agent_config_unknown(self):
        self.assertIsNone(core.agent_config("bogus"))

    def test_hermes_block_has_fallback_chain(self):
        self.assertIn("fallback_model", core.HERMES_PROVIDER_BLOCK)
        self.assertIn(core.GATEWAY_URL, core.HERMES_PROVIDER_BLOCK)

    def test_models_text_lists_all(self):
        t = core.models_text()
        self.assertIn("25 free models", t)
        self.assertIn("deepseek-v4-flash", t)
        self.assertIn("[VISION-verified]", t)

    def test_models_text_filter(self):
        t = core.models_text("coding")
        self.assertIn("kimi-k2.7-code", t)
        self.assertNotIn("  minimax-m3", t)  # not in the filtered list (header mention is fine)

    def test_channels_text_has_all_channels(self):
        t = core.channels_text()
        for ch in core.FREE_CHANNELS:
            self.assertIn(ch["name"], t)
        self.assertIn("wired", t)

    def test_channels_text_format(self):
        t = core.channels_text()
        for ch in core.FREE_CHANNELS:
            self.assertIn(f"key: {ch['key_env']}", t)
            self.assertIn(ch["note"], t)
        self.assertIn(str(len(core.GATEWAY_MODELS)), t)  # wired channel model count


class AgentSnippetGenTests(unittest.TestCase):
    """Config snippet generation for all 5 agent formats (Hermes + 4 in AGENT_CONFIGS)."""

    def test_all_five_formats_covered(self):
        self.assertEqual(len(core.AGENT_CONFIGS), 4)  # opencode, codex, aider, goose
        for agent in ("opencode", "codex", "aider", "goose"):
            self.assertIn(agent, core.AGENT_CONFIGS)
        # 5th format: the Hermes YAML block
        self.assertIn("model:", core.HERMES_PROVIDER_BLOCK)

    def test_opencode_snippet_is_valid_json(self):
        cfg = core.agent_config("opencode")
        # snippet carries a `//` comment header line; the JSON document itself must parse
        parsed = json.loads(cfg[cfg.index("{"):])
        prov = parsed["provider"]["opencode-zen"]
        self.assertEqual(prov["npm"], "@ai-sdk/openai-compatible")
        self.assertEqual(prov["name"], "OpenCode Zen")
        self.assertEqual(prov["options"]["baseURL"], core.GATEWAY_URL)
        self.assertEqual(prov["options"]["apiKey"], "{env:OPENCODE_GO_API_KEY}")
        self.assertIn("deepseek-v4-flash", prov["models"])
        self.assertIn("minimax-m3", prov["models"])

    def test_codex_snippet_toml_shape(self):
        cfg = core.agent_config("codex")
        self.assertIn('model_provider = "opencode-zen"', cfg)
        self.assertIn('model = "deepseek-v4-flash"', cfg)
        self.assertIn("[model_providers.opencode-zen]", cfg)
        self.assertIn('env_key = "OPENCODE_GO_API_KEY"', cfg)
        self.assertIn('wire_api = "chat"', cfg)

    def test_aider_snippet_cli_flags(self):
        cfg = core.agent_config("aider")
        self.assertIn("--model openai/deepseek-v4-flash", cfg)
        self.assertIn("--openai-api-base", cfg)
        self.assertIn("--openai-api-key $OPENCODE_GO_API_KEY", cfg)
        self.assertIn(core.GATEWAY_URL, cfg)

    def test_goose_snippet_cli_flags(self):
        cfg = core.agent_config("goose")
        self.assertIn("goose configure --provider openai", cfg)
        self.assertIn("--base-url", cfg)
        self.assertIn("--api-key $OPENCODE_GO_API_KEY", cfg)
        self.assertIn(core.GATEWAY_URL, cfg)

    def test_hermes_block_provider_lines(self):
        b = core.HERMES_PROVIDER_BLOCK
        self.assertIn("provider: opencode-go", b)
        self.assertIn("model: deepseek-v4-flash", b)
        self.assertIn("key_env: OPENCODE_GO_API_KEY", b)
        self.assertIn(core.GATEWAY_URL, b)
        self.assertIn("openrouter", b)  # documented fallback chain

    def test_waba_block_documented_shape(self):
        """WABA agent block (WhatsApp B2B mode) documents the Cloud API env
        vars and stays OUT of AGENT_CONFIGS (it is not an LLM endpoint)."""
        b = core.WABA_AGENT_BLOCK
        self.assertIn("WHATSAPP_CLOUD_PHONE_NUMBER_ID", b)
        self.assertIn("WHATSAPP_CLOUD_ACCESS_TOKEN", b)
        self.assertIn("WHATSAPP_CLOUD_VERIFY_TOKEN", b)
        self.assertIn(core.GATEWAY_URL, b)  # same free-model brain
        self.assertIn("COMPLIANCE", b)  # compliance rule is part of the shape
        self.assertNotIn("waba", core.AGENT_CONFIGS)


class ModelListParsingTests(unittest.TestCase):
    """models_text / filter_by_tag formatting and filtering."""

    def test_every_model_has_required_fields(self):
        for m in core.GATEWAY_MODELS:
            self.assertIn("id", m)
            self.assertTrue(m["id"])
            self.assertIn("tags", m)
            self.assertIsInstance(m["tags"], list)
            self.assertIn("vision", m)
            self.assertIsInstance(m["vision"], bool)

    def test_filter_by_tag_unknown_tag_empty(self):
        self.assertEqual(core.filter_by_tag("no-such-tag"), [])

    def test_filter_by_tag_vision_only_minimax(self):
        self.assertEqual(core.filter_by_tag("vision"), ["minimax-m3"])

    def test_models_text_lists_every_registry_id(self):
        t = core.models_text()
        for m in core.GATEWAY_MODELS:
            self.assertIn("\n  " + m["id"], t, f"model {m['id']} missing from /models text")

    def test_models_text_unknown_tag_header_only(self):
        t = core.models_text("bogus-tag")
        self.assertIn("25 free models", t)
        self.assertNotIn("\n  deepseek-v4-flash", t)  # no model rows for unknown tag

    def test_models_text_filter_excludes_other_tags(self):
        t = core.models_text("fast")
        self.assertIn("qwen3.7-plus", t)
        self.assertNotIn("\n  kimi-k2.7-code", t)  # coding/heavy model not in fast list

    def test_models_text_recommended_line(self):
        t = core.models_text()
        self.assertIn("default=deepseek-v4-flash", t)
        self.assertIn("vision=minimax-m3", t)


class HealthCheckResultTests(unittest.TestCase):
    """gateway_health result handling: headers, payload shapes, failures."""

    def _fake(self, status: int, body: bytes):
        fake = mock.MagicMock()
        fake.status = status
        fake.read.return_value = body
        fake.__enter__.return_value = fake
        return fake

    def test_sends_auth_header_when_key_given(self):
        with mock.patch.object(core.urllib.request, "urlopen", return_value=self._fake(200, b'{"data": []}')) as m:
            core.gateway_health(key="sk-xyz")
        req = m.call_args.args[0]
        self.assertEqual(req.get_header("Authorization"), "Bearer sk-xyz")
        self.assertIn("Mozilla", req.get_header("User-agent"))

    def test_no_auth_header_without_key(self):
        with mock.patch.object(core.urllib.request, "urlopen", return_value=self._fake(200, b'{"data": []}')) as m:
            core.gateway_health(key="")
        req = m.call_args.args[0]
        self.assertIsNone(req.get_header("Authorization"))

    def test_missing_data_key_counts_zero(self):
        with mock.patch.object(core.urllib.request, "urlopen", return_value=self._fake(200, b'{"object": "list"}')):
            h = core.gateway_health(key="k")
        self.assertTrue(h["ok"])
        self.assertEqual(h["model_count"], 0)
        self.assertEqual(h["models"], [])

    def test_bad_json_reports_error(self):
        with mock.patch.object(core.urllib.request, "urlopen", return_value=self._fake(200, b"{not json")):
            h = core.gateway_health(key="k")
        self.assertFalse(h["ok"])
        self.assertIsNone(h["http"])
        self.assertTrue(h["error"])  # JSONDecodeError message captured

    def test_timeout_forwarded(self):
        with mock.patch.object(core.urllib.request, "urlopen", return_value=self._fake(200, b'{"data": []}')) as m:
            core.gateway_health(key="k", timeout=7)
        self.assertEqual(m.call_args.kwargs.get("timeout"), 7)

    def test_load_key_quoted_value(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write('OPENCODE_GO_API_KEY="sk-quoted"\n')
            with mock.patch.object(core.os.path, "expanduser", return_value=env):
                self.assertEqual(core.load_key("OPENCODE_GO_API_KEY"), "sk-quoted")


if __name__ == "__main__":
    unittest.main()
