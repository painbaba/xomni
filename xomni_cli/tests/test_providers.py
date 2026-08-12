"""xomni providers add — one-command LLM-provider connect tests."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from xomni_cli import cmd_providers_add, _env_path, _config_path, _provider_block

BASE_CONFIG = """# host config
providers:
  opencode-go:
    request_timeout_seconds: 120
toolsets:
  - hermes-cli
model:
  default: deepseek-v4-flash
"""


class ProvidersAddTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="xomni-providers-")
        self.config = os.path.join(self.tmp, "config.yaml")
        with open(self.config, "w", encoding="utf-8") as f:
            f.write(BASE_CONFIG)
        self.env = os.path.join(self.tmp, ".env")
        self._old_env = dict(os.environ)
        os.environ["XOMNI_HERMES_CONFIG"] = self.config

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _patch_env_path(self):
        # redirect .env writes to the temp .env
        import xomni_cli
        xomni_cli._env_path = lambda: self.env
        self.addCleanup(lambda: setattr(xomni_cli, "_env_path", _env_path))

    def test_add_writes_block_and_env_placeholder(self):
        self._patch_env_path()
        rc = cmd_providers_add(["my-openai", "https://api.openai.com/v1",
                                "--key-env", "MY_OPENAI_API_KEY", "--yes"])
        self.assertEqual(rc, 0)
        text = open(self.config, encoding="utf-8").read()
        self.assertIn("  my-openai:", text)
        self.assertIn("base_url: https://api.openai.com/v1", text)
        self.assertIn("api_type: openai", text)
        self.assertIn("env_key: MY_OPENAI_API_KEY", text)
        self.assertIn("opencode-go:", text)  # pre-existing block preserved
        self.assertIn("toolsets:", text)     # other sections preserved
        self.assertIn("MY_OPENAI_API_KEY=", open(self.env, encoding="utf-8").read())
        # config stays valid YAML
        import yaml
        yaml.safe_load(open(self.config, encoding="utf-8"))

    def test_add_with_models_and_anthropic(self):
        self._patch_env_path()
        rc = cmd_providers_add(["claude-test", "https://api.anthropic.com",
                                "--api-type", "anthropic",
                                "--models", "claude-x,claude-y", "--yes"])
        self.assertEqual(rc, 0)
        text = open(self.config, encoding="utf-8").read()
        self.assertIn("api_type: anthropic", text)
        self.assertIn("    models:", text)
        self.assertIn("      - claude-x", text)
        self.assertIn("      - claude-y", text)

    def test_idempotent(self):
        self._patch_env_path()
        self.assertEqual(cmd_providers_add(["dup", "https://x.example/v1", "--yes"]), 0)
        before = open(self.config, encoding="utf-8").read()
        self.assertEqual(cmd_providers_add(["dup", "https://x.example/v1", "--yes"]), 0)
        self.assertEqual(open(self.config, encoding="utf-8").read(), before)

    def test_dry_run_writes_nothing(self):
        self._patch_env_path()
        rc = cmd_providers_add(["dry", "https://x.example/v1", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertNotIn("dry:", open(self.config, encoding="utf-8").read())
        self.assertFalse(os.path.isfile(self.env))

    def test_invalid_name(self):
        self.assertEqual(cmd_providers_add(["Bad Name!", "https://x.example/v1"]), 1)

    def test_invalid_url(self):
        self.assertEqual(cmd_providers_add(["ok", "not-a-url"]), 1)
        self.assertEqual(cmd_providers_add(["ok", "ftp://x.example/v1"]), 1)

    def test_invalid_env_var(self):
        self.assertEqual(cmd_providers_add(["ok", "https://x.example/v1",
                                            "--key-env", "bad-name"]), 1)

    def test_invalid_api_type(self):
        self.assertEqual(cmd_providers_add(["ok", "https://x.example/v1",
                                            "--api-type", "grok"]), 1)

    def test_missing_config(self):
        os.environ["XOMNI_HERMES_CONFIG"] = os.path.join(self.tmp, "nope.yaml")
        self.assertEqual(cmd_providers_add(["ok", "https://x.example/v1"]), 1)

    def test_config_dir_fails_loud(self):
        os.environ["XOMNI_HERMES_CONFIG"] = self.tmp  # a directory -> OSError
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_providers_add(["ok", "https://x.example/v1", "--yes"])
        self.assertEqual(rc, 1)
        self.assertIn("FAILED", buf.getvalue())

    def test_default_env_key_derived_from_name(self):
        self._patch_env_path()
        self.assertEqual(cmd_providers_add(["my-provider", "https://x.example/v1",
                                            "--yes"]), 0)
        self.assertIn("MY_PROVIDER_API_KEY=",
                      open(self.env, encoding="utf-8").read())

    def test_block_render(self):
        block = _provider_block("b", "https://b.example/v1", "B_API_KEY",
                                "openai", ["m1", "m2"])
        self.assertIn("  b:", block)
        self.assertIn("    models:", block)
        self.assertIn("      - m1", block)
        self.assertIn("env_key: B_API_KEY", block)


if __name__ == "__main__":
    unittest.main()
