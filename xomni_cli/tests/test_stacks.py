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

    def test_e2e_trading_stack_temp_config_install_parse(self):
        """E2E: install trading-stack into a temp host config -> parse the
        result -> assert all 5 servers with the right launch shape, the hosted
        PolymarketScan remote as a url: entry, and every pre-existing section
        (model / ffmpeg / gateways) preserved byte-for-byte semantics."""
        cfg = self._config()
        rc, out = _run_add("trading-stack", config=cfg)
        self.assertEqual(rc, 0, out)
        self.assertIn("wrote 5 MCP server(s)", out)
        import yaml
        with open(cfg, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        servers = data["mcp_servers"]
        # the 5 stack servers appended, pre-existing ffmpeg untouched
        self.assertEqual(
            sorted(servers),
            ["PolymarketScan", "alphavantage-mcp", "coingecko-mcp", "ffmpeg",
             "mcp-yfinance", "tradingview-mcp"],
        )
        # stdio launch lines derived from install_command
        self.assertEqual(servers["mcp-yfinance"]["command"], "uvx")
        self.assertEqual(servers["mcp-yfinance"]["args"], ["mcp-yfinance"])
        self.assertEqual(servers["coingecko-mcp"]["command"], "npx")
        self.assertEqual(servers["coingecko-mcp"]["args"],
                         ["-y", "@coingecko/coingecko-mcp"])
        self.assertEqual(servers["tradingview-mcp"]["command"], "uvx")
        self.assertEqual(servers["alphavantage-mcp"]["command"], "uvx")
        # hosted remote -> url entry only, enabled by default
        self.assertTrue(servers["PolymarketScan"]["url"].startswith("https://"))
        self.assertNotIn("command", servers["PolymarketScan"])
        for name in ("mcp-yfinance", "tradingview-mcp", "coingecko-mcp",
                     "alphavantage-mcp", "PolymarketScan"):
            self.assertTrue(servers[name]["enabled"])
        # pre-existing sections preserved
        self.assertEqual(data["model"]["model"], "deepseek-v4-flash")
        self.assertEqual(servers["ffmpeg"]["enabled"], False)
        self.assertEqual(data["gateways"]["telegram"], ["hermes-telegram"])
        # second install is a no-op (idempotent), config unchanged
        rc2, out2 = _run_add("trading-stack", config=cfg)
        self.assertEqual(rc2, 0, out2)
        self.assertIn("wrote 0", out2)
        self.assertIn("skipped 5", out2)
        with open(cfg, encoding="utf-8") as f:
            self.assertEqual(yaml.safe_load(f), data)

    def test_add_expands_empty_inline_mcp_servers(self):
        """`mcp_servers: {}` / `mcp_servers: []` (valid YAML idioms) must stay
        valid YAML after `xomni add` — the inline container is expanded to a
        block mapping instead of producing a ParserError."""
        import yaml
        for empty in ("mcp_servers: {}", "mcp_servers: []"):
            cfg = self._config(
                "model:\n  provider: opencode-go\n" + empty + "\n"
                "gateways:\n  telegram:\n    - hermes-telegram\n"
            )
            rc, out = _run_add("web-dev", config=cfg)
            self.assertEqual(rc, 0, out)
            with open(cfg, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self.assertGreaterEqual(len(data["mcp_servers"]), 4)
            self.assertEqual(data["model"]["provider"], "opencode-go")
            self.assertEqual(data["gateways"]["telegram"], ["hermes-telegram"])

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

    def test_all_four_stacks_install_cleanly(self):
        """CLI-level install for EVERY stack into a temp host config: rc 0,
        no ERROR output, valid YAML, and every declared MCP server present
        and enabled (covers the other 3 stacks end-to-end, not just
        trading-stack)."""
        import yaml
        for name in STACKS:
            cfg = self._config()
            rc, out = _run_add(name, config=cfg)
            self.assertEqual(rc, 0, f"{name}: {out}")
            self.assertNotIn("ERROR", out, name)
            with open(cfg, encoding="utf-8") as f:
                servers = yaml.safe_load(f)["mcp_servers"]
            for mcp in xomni_cli._load_stack(name)["mcp_servers"]:
                self.assertIn(mcp, servers, f"{name}: missing {mcp}")
                self.assertTrue(servers[mcp].get("enabled"),
                                f"{name}: {mcp} not enabled")


class TestCliValidation(unittest.TestCase):
    """cmd_add's validation path: a stack def that fails validation must be
    rejected with rc=1 and a clear ERROR line, and must never touch config.
    Uses a temp STACKS_DIR so bad defs never enter the real data/stacks/."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="xomni_stacks_bad_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self._old_dir = xomni_cli.STACKS_DIR
        self._old_cfg = os.environ.get("XOMNI_HERMES_CONFIG")
        xomni_cli.STACKS_DIR = self.tmp
        self.cfg = os.path.join(self.tmp, "config.yaml")
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write("model:\n  provider: opencode-go\n  model: deepseek-v4-flash\n")
        os.environ["XOMNI_HERMES_CONFIG"] = self.cfg

    def tearDown(self):
        xomni_cli.STACKS_DIR = self._old_dir
        if self._old_cfg is None:
            os.environ.pop("XOMNI_HERMES_CONFIG", None)
        else:
            os.environ["XOMNI_HERMES_CONFIG"] = self._old_cfg

    def _write_stack(self, name, **over):
        sdef = {"name": name, "description": "x" * 20, "skills": ["xlsx"],
                "mcp_servers": ["coingecko-mcp"], "config": {},
                "smoke_test": {"command": "echo ok", "expect": "ok"}}
        sdef.update(over)
        with open(os.path.join(self.tmp, name + ".json"), "w",
                  encoding="utf-8") as f:
            json.dump(sdef, f)

    def test_unknown_skill_rejected(self):
        self._write_stack("bad-skill", skills=["xlsx", "no-such-skill"])
        rc, out = _run_add("bad-skill")
        self.assertEqual(rc, 1)
        self.assertIn("skill not in data/curated-skills.json: 'no-such-skill'",
                      out)

    def test_unknown_mcp_rejected(self):
        self._write_stack("bad-mcp", mcp_servers=["coingecko-mcp", "no-such-mcp"])
        rc, out = _run_add("bad-mcp")
        self.assertEqual(rc, 1)
        self.assertIn("unknown MCP server in catalog: 'no-such-mcp'", out)

    def test_missing_smoke_test_rejected(self):
        self._write_stack("no-smoke", smoke_test={})
        rc, out = _run_add("no-smoke")
        self.assertEqual(rc, 1)
        self.assertIn("smoke_test must define command + expect", out)

    def test_unparseable_install_command_rejected(self):
        # temp catalog whose entry needs manual setup (e.g. "see repo")
        cat_path = os.path.join(self.tmp, "catalog.json")
        old_cat = xomni_cli.MCP_CATALOG
        xomni_cli.MCP_CATALOG = cat_path
        self.addCleanup(setattr, xomni_cli, "MCP_CATALOG", old_cat)
        with open(cat_path, "w", encoding="utf-8") as f:
            json.dump([{"name": "manual-mcp",
                        "install_command": "see repo for setup"}], f)
        self._write_stack("manual-mcp", mcp_servers=["manual-mcp"])
        rc, out = _run_add("manual-mcp")
        self.assertEqual(rc, 1)
        self.assertIn("cannot auto-install non-interactively", out)

    def test_rejected_stack_never_writes_config(self):
        self._write_stack("bad-skill", skills=["no-such-skill"])
        before = open(self.cfg, encoding="utf-8").read()
        rc, _ = _run_add("bad-skill")
        self.assertEqual(rc, 1)
        self.assertEqual(open(self.cfg, encoding="utf-8").read(), before)


if __name__ == "__main__":
    unittest.main()
