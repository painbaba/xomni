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


if __name__ == "__main__":
    unittest.main()
