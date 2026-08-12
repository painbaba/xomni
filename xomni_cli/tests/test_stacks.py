"""U1 — one-command vertical stacks: `xomni add <stack>`.

Validates the 4 stack defs in data/stacks/ against data/curated-skills.json and
data/mcp/catalog.json, the non-interactive config-write path (temp config only —
never the live host config), unknown-stack handling, and dry-run no-write.

Run:  cd repo && python -m unittest xomni_cli.tests.test_stacks -v
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import xomni_cli  # noqa: E402

STACKS = ("trading-stack", "data-science", "web-dev", "home-automation")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _run_add(stack, *flags, config=None):
    """Call cmd_add in a subprocess-free way with an isolated host config."""
    old = os.environ.get("XOMNI_HERMES_CONFIG")
    if config is not None:
        os.environ["XOMNI_HERMES_CONFIG"] = config
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = xomni_cli.cmd_add(stack, dry_run="--dry-run" in flags,
                                   smoke="--smoke" in flags)
    finally:
        if old is None:
            os.environ.pop("XOMNI_HERMES_CONFIG", None)
        else:
            os.environ["XOMNI_HERMES_CONFIG"] = old
    return rc, buf.getvalue()


class TestStackDefs(unittest.TestCase):
    def setUp(self):
        self.stacks = {name: _load(os.path.join(xomni_cli.STACKS_DIR, name + ".json"))
                       for name in STACKS}
        self.skills = {s["name"] for s in _load(xomni_cli.CURATED_SKILLS)}
        self.catalog = xomni_cli._load_catalog()

    def test_all_four_stacks_present_and_parse(self):
        self.assertEqual(sorted(self.stacks), sorted(STACKS))
        for name, s in self.stacks.items():
            for key in ("name", "description", "skills", "mcp_servers",
                        "config", "smoke_test"):
                self.assertIn(key, s, f"{name}: missing key {key!r}")
            self.assertIsInstance(s["skills"], list)
            self.assertIsInstance(s["mcp_servers"], list)

    def test_stack_name_matches_filename(self):
        for name, s in self.stacks.items():
            self.assertEqual(s["name"], name)

    def test_stack_has_content(self):
        for name, s in self.stacks.items():
            self.assertGreater(len(s["description"]), 10, name)
            self.assertGreater(len(s["skills"]), 0, name)
            self.assertGreater(len(s["mcp_servers"]), 0, name)

    def test_skills_exist_in_curated_db(self):
        for name, s in self.stacks.items():
            for sk in s["skills"]:
                self.assertIn(sk, self.skills,
                              f"{name}: skill {sk!r} not in curated-skills.json")

    def test_mcps_exist_in_catalog(self):
        for name, s in self.stacks.items():
            for mcp in s["mcp_servers"]:
                self.assertIn(mcp, self.catalog,
                              f"{name}: MCP {mcp!r} not in catalog.json")

    def test_mcps_resolve_to_noninteractive_config(self):
        for name, s in self.stacks.items():
            for mcp in s["mcp_servers"]:
                cfg = xomni_cli._resolve_mcp(mcp, self.catalog)
                self.assertTrue(cfg.get("command") or cfg.get("url"),
                                f"{name}: {mcp} resolved to empty entry {cfg}")
                self.assertTrue(cfg.get("enabled"), f"{name}: {mcp} not enabled")

    def test_smoke_tests_defined(self):
        for name, s in self.stacks.items():
            st = s["smoke_test"]
            self.assertTrue(st.get("command"), f"{name}: no smoke command")
            self.assertTrue(st.get("expect"), f"{name}: no smoke expect")

    def test_trading_stack_uses_finance_mcps(self):
        trading = self.stacks["trading-stack"]
        for mcp in trading["mcp_servers"]:
            self.assertEqual(self.catalog[mcp]["category"], "FINANCE",
                             f"trading-stack MCP {mcp!r} not in FINANCE category")


class TestCliBehavior(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="xomni_stacks_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _config(self, text=None):
        path = os.path.join(self.tmp, "config.yaml")
        if text is None:
            text = ("model:\n  provider: opencode-go\n  model: deepseek-v4-flash\n"
                    "mcp_servers:\n"
                    "  ffmpeg:\n"
                    "    command: npx\n"
                    "    args:\n"
                    "      - -y\n"
                    "      - ffmpeg-mcp\n"
                    "    enabled: false\n"
                    "gateways:\n"
                    "  telegram:\n"
                    "    - hermes-telegram\n")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_unknown_stack_rejected(self):
        rc, out = _run_add("does-not-exist", config=self._config())
        self.assertEqual(rc, 1)
        self.assertIn("unknown stack", out)

    def test_dry_run_does_not_write(self):
        cfg = self._config()
        before = open(cfg, encoding="utf-8").read()
        for name in STACKS:
            rc, out = _run_add(name, "--dry-run", config=cfg)
            self.assertEqual(rc, 0, f"{name} dry-run failed:\n{out}")
            self.assertIn("DRY-RUN", out)
        self.assertEqual(open(cfg, encoding="utf-8").read(), before)

    def test_add_appends_and_preserves_existing_config(self):
        cfg = self._config()
        rc, out = _run_add("trading-stack", config=cfg)
        self.assertEqual(rc, 0, out)
        text = open(cfg, encoding="utf-8").read()
        # appended entries present
        for mcp in ("mcp-yfinance", "tradingview-mcp", "coingecko-mcp",
                    "alphavantage-mcp", "PolymarketScan"):
            self.assertIn(mcp + ":", text, mcp)
        self.assertIn("enabled: true", text)
        # existing entries + other sections preserved
        self.assertIn("ffmpeg:", text)
        self.assertIn("ffmpeg-mcp", text)
        self.assertIn("model: deepseek-v4-flash", text)
        self.assertIn("hermes-telegram", text)
        # result parses as valid YAML with all 5 servers
        import yaml
        with open(cfg, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        servers = data["mcp_servers"]
        self.assertIn("mcp-yfinance", servers)
        self.assertEqual(servers["mcp-yfinance"]["command"], "uvx")
        self.assertEqual(servers["mcp-yfinance"]["args"], ["mcp-yfinance"])
        self.assertEqual(servers["ffmpeg"]["enabled"], False)
        self.assertIn("url", servers["PolymarketScan"])

    def test_add_is_idempotent(self):
        cfg = self._config()
        rc1, out1 = _run_add("web-dev", config=cfg)
        self.assertEqual(rc1, 0, out1)
        rc2, out2 = _run_add("web-dev", config=cfg)
        self.assertEqual(rc2, 0, out2)
        self.assertIn("wrote 0", out2)
        self.assertIn("skipped 5", out2)
        text = open(cfg, encoding="utf-8").read()
        self.assertEqual(text.count("playwright:"), 1)

    def test_add_creates_mcp_servers_block_when_absent(self):
        cfg = self._config("model:\n  provider: opencode-go\n  model: deepseek-v4-flash\n")
        rc, out = _run_add("data-science", config=cfg)
        self.assertEqual(rc, 0, out)
        text = open(cfg, encoding="utf-8").read()
        self.assertIn("mcp_servers:", text)
        self.assertIn("arxiv-mcp-server:", text)
        self.assertIn("model: deepseek-v4-flash", text)

    def test_missing_config_fails_loudly_with_fix(self):
        missing = os.path.join(self.tmp, "nope.yaml")
        rc, out = _run_add("trading-stack", config=missing)
        self.assertEqual(rc, 1)
        self.assertIn("config.yaml not found", out)
        self.assertIn("Fix:", out)

    def test_remote_mcp_writes_url_entry(self):
        cfg = self._config()
        rc, out = _run_add("trading-stack", config=cfg)
        self.assertEqual(rc, 0, out)
        import yaml
        with open(cfg, encoding="utf-8") as f:
            servers = yaml.safe_load(f)["mcp_servers"]
        self.assertTrue(servers["PolymarketScan"]["url"].startswith("https://"))

    def test_parse_install_command_forms(self):
        self.assertEqual(xomni_cli._parse_install_command("uvx mcp-yfinance"),
                         {"command": "uvx", "args": ["mcp-yfinance"]})
        self.assertEqual(xomni_cli._parse_install_command("npx -y @coingecko/coingecko-mcp"),
                         {"command": "npx", "args": ["-y", "@coingecko/coingecko-mcp"]})
        self.assertEqual(xomni_cli._parse_install_command("pip install tradingview-mcp-server"),
                         {"command": "uvx", "args": ["tradingview-mcp-server"]})
        self.assertEqual(xomni_cli._parse_install_command(
            "hermes mcp add stripe --url https://mcp.stripe.com --auth oauth"),
            {"url": "https://mcp.stripe.com"})
        self.assertEqual(xomni_cli._parse_install_command(
            "npx -y @smithery/cli mcp add https://polymarketscan--jordan-s648.run.tools"),
            {"url": "https://polymarketscan--jordan-s648.run.tools"})
        for bad in ("see repo", "git clone https://x && npm install",
                    "hermes mcp add plaid --auth oauth"):
            with self.assertRaises(ValueError):
                xomni_cli._parse_install_command(bad)

    def test_stacks_command_lists_all(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = xomni_cli.cmd_stacks()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        for name in STACKS:
            self.assertIn(name, out)
        for pat in ("skills", "MCPs"):
            self.assertIn(pat, out)


if __name__ == "__main__":
    unittest.main()
