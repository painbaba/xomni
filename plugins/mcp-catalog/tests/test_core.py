"""Tests for mcp-catalog core (core.py) — catalog parsing, validation,
formatting, JSON-RPC message shapes, state round-trip, and the U2
marketplace install path (host-config append, badges, /mcp add <name>)."""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

import core

SAMPLE = [
    {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:/data"],
        "env": {"NODE_NO_WARNINGS": "1"},
        "description": "files and directories",
    },
    {
        "name": "fetch",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
        "description": "fetch urls as markdown",
    },
]

NOPE = "mcp-catalog-definitely-not-installed-xyz"


class ParseCatalogTests(unittest.TestCase):
    def test_happy_path_parses_and_canonicalizes(self):
        servers = core.parse_catalog(json.dumps(SAMPLE))
        self.assertEqual(len(servers), 2)
        self.assertEqual(
            servers[0],
            {
                "name": "filesystem",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:/data"],
                "env": {"NODE_NO_WARNINGS": "1"},
                "description": "files and directories",
            },
        )
        # defaults: args -> [], env -> {}, description -> ""
        minimal = core.parse_catalog('[{"name": "s", "command": "npx"}]')
        self.assertEqual(
            minimal,
            [{"name": "s", "command": "npx", "args": [], "env": {}, "description": ""}],
        )

    def test_accepts_already_decoded_list(self):
        servers = core.parse_catalog(SAMPLE)
        self.assertEqual([s["name"] for s in servers], ["filesystem", "fetch"])

    def test_unknown_keys_dropped(self):
        servers = core.parse_catalog(
            '[{"name": "s", "command": "npx", "bogus": 42, "nested": {"x": 1}}]'
        )
        self.assertEqual(
            servers[0], {"name": "s", "command": "npx", "args": [], "env": {}, "description": ""}
        )

    def test_bad_json_raises_clear_message(self):
        with self.assertRaises(core.CatalogError) as cm:
            core.parse_catalog("{not json")
        self.assertIn("invalid JSON", str(cm.exception))

    def test_non_list_raises(self):
        with self.assertRaises(core.CatalogError) as cm:
            core.parse_catalog('{"name": "s"}')
        self.assertIn("must be a JSON array", str(cm.exception))

    def test_missing_name_raises(self):
        with self.assertRaises(core.CatalogError) as cm:
            core.parse_catalog('[{"command": "npx"}]')
        self.assertIn("missing or invalid 'name'", str(cm.exception))
        self.assertIn("catalog entry 1", str(cm.exception))

    def test_missing_command_raises(self):
        with self.assertRaises(core.CatalogError) as cm:
            core.parse_catalog('[{"name": "s"}]')
        self.assertIn("missing or invalid 'command'", str(cm.exception))
        self.assertIn("'s'", str(cm.exception))

    def test_bad_args_and_env_types_raise(self):
        with self.assertRaises(core.CatalogError) as cm:
            core.parse_catalog('[{"name": "s", "command": "npx", "args": "nope"}]')
        self.assertIn("'args' must be a list of strings", str(cm.exception))
        with self.assertRaises(core.CatalogError) as cm:
            core.parse_catalog('[{"name": "s", "command": "npx", "env": {"K": 1}}]')
        self.assertIn("'env' must be an object mapping string to string", str(cm.exception))

    def test_duplicate_names_rejected(self):
        doc = json.dumps([SAMPLE[0], {"name": "filesystem", "command": "uvx"}])
        with self.assertRaises(core.CatalogError) as cm:
            core.parse_catalog(doc)
        self.assertIn("duplicate server name", str(cm.exception))
        self.assertIn("'filesystem'", str(cm.exception))

    def test_command_not_on_path_when_checkable(self):
        doc = json.dumps([{"name": "s", "command": NOPE}])
        with self.assertRaises(core.CatalogError) as cm:
            core.parse_catalog(doc, check_path=True)
        self.assertIn("command not found on PATH", str(cm.exception))
        self.assertIn(NOPE, str(cm.exception))
        # check_path=False skips the PATH check
        servers = core.parse_catalog(doc, check_path=False)
        self.assertEqual(servers[0]["command"], NOPE)

    def test_validate_catalog_collects_all_errors(self):
        doc = json.dumps(
            [
                {"command": "npx"},                                    # missing name
                {"name": "a", "command": ""},                          # missing command
                {"name": "dup", "command": "npx"},                     # ok
                {"name": "dup", "command": NOPE},                      # duplicate + bad path
                {"name": "ok", "command": "npx"},                      # ok
            ]
        )
        errors = core.validate_catalog(doc)
        self.assertEqual(len(errors), 4)  # name, command, duplicate, path
        self.assertTrue(any("duplicate server name" in e for e in errors))
        self.assertTrue(any("command not found on PATH" in e for e in errors))
        # valid doc -> no errors
        self.assertEqual(core.validate_catalog(json.dumps(SAMPLE)), [])
        self.assertTrue(core.validate_catalog("not json at all")[0].startswith("invalid JSON"))


class FormattingTests(unittest.TestCase):
    def test_list_tools_text_contains_names_launch_and_descriptions(self):
        servers = core.parse_catalog(json.dumps(SAMPLE))
        text = core.list_tools_text(servers)
        self.assertIn("mcp://filesystem", text)
        self.assertIn("mcp://fetch", text)
        self.assertIn("@modelcontextprotocol/server-filesystem", text)
        self.assertIn("files and directories", text)
        self.assertIn("mcp__fetch__<tool>", text)
        self.assertIn("2 server(s)", text)

    def test_list_tools_text_empty(self):
        self.assertEqual(core.list_tools_text([]), "no MCP servers in catalog.")

    def test_list_catalog_text_shows_env(self):
        servers = core.parse_catalog(json.dumps(SAMPLE))
        text = core.list_catalog_text(servers)
        self.assertIn("filesystem", text)
        self.assertIn("NODE_NO_WARNINGS=1", text)

    def test_format_tool_list_tuples_and_dicts(self):
        out = core.format_tool_list(
            "fetch", [("fetch", "fetch a url"), {"name": "search", "description": "search web"}]
        )
        self.assertIn("server 'fetch': 2 tool(s)", out)
        self.assertIn("mcp__fetch__fetch", out)
        self.assertIn("mcp__fetch__search", out)
        self.assertIn("search web", out)
        self.assertIn("no tools", core.format_tool_list("x", []))


class JsonRpcShapeTests(unittest.TestCase):
    def test_initialize_message_shape(self):
        msg = core.initialize_message(
            client_name="my-client", client_version="9.9", request_id=0
        )
        self.assertEqual(
            msg,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": core.MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "my-client", "version": "9.9"},
                },
            },
        )

    def test_initialized_notification_has_no_id(self):
        msg = core.initialized_notification()
        self.assertEqual(msg, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertNotIn("id", msg)

    def test_list_tools_message_shape(self):
        self.assertEqual(
            core.list_tools_message(request_id=1),
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )

    def test_call_tool_message_shape_with_and_without_arguments(self):
        self.assertEqual(
            core.call_tool_message("read_file", {"path": "/a"}, request_id=2),
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "read_file", "arguments": {"path": "/a"}},
            },
        )
        no_args = core.call_tool_message("ping", request_id=3)
        self.assertEqual(no_args["params"], {"name": "ping"})
        self.assertNotIn("arguments", no_args["params"])

    def test_rpc_envelope_is_newline_delimited_json(self):
        line = core.rpc_envelope(core.list_tools_message(1))
        self.assertTrue(line.endswith("\n"))
        self.assertEqual(json.loads(line), core.list_tools_message(1))

    def test_default_ids_follow_handshake_sequence(self):
        ids = [
            core.initialize_message()["id"],
            core.list_tools_message()["id"],
            core.call_tool_message("t")["id"],
        ]
        self.assertEqual(ids, [0, 1, 2])


class StateRoundTripTests(unittest.TestCase):
    def test_parse_dump_parse_round_trip(self):
        servers = core.parse_catalog(json.dumps(SAMPLE))
        again = core.round_trip(servers)
        self.assertEqual(again, servers)

    def test_file_save_and_load_round_trip(self):
        servers = core.parse_catalog(json.dumps(SAMPLE))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "catalog.json")
            core.save_catalog_file(path, servers)
            self.assertTrue(os.path.isfile(path))
            loaded = core.load_catalog_file(path)
            self.assertEqual(loaded, servers)

    def test_load_all_catalogs_merges_and_skips_broken(self):
        servers = core.parse_catalog(json.dumps(SAMPLE))
        with tempfile.TemporaryDirectory() as tmp:
            core.save_catalog_file(os.path.join(tmp, "a.json"), servers[:1])
            core.save_catalog_file(os.path.join(tmp, "b.json"), servers[1:])
            with open(os.path.join(tmp, "broken.json"), "w", encoding="utf-8") as f:
                f.write("{broken")
            merged = core.load_all_catalogs(tmp)
            self.assertEqual([s["name"] for s in merged], ["filesystem", "fetch"])
        self.assertEqual(core.load_all_catalogs(os.path.join(tmp, "nope")), [])

    def test_default_catalog_dir_and_env_override(self):
        import unittest.mock as mock

        with mock.patch.dict(os.environ, {}, clear=True):
            d = core.default_catalog_dir()
            self.assertTrue(d.endswith(os.path.join(".hermes-mcp", "catalogs")))
        with mock.patch.dict(os.environ, {"HERMES_MCP_CATALOG_DIR": "C:/tmp/cats"}):
            self.assertEqual(core.default_catalog_dir(), "C:/tmp/cats")

    def test_find_server(self):
        servers = core.parse_catalog(json.dumps(SAMPLE))
        self.assertEqual(core.find_server(servers, "fetch")["command"], "uvx")
        self.assertIsNone(core.find_server(servers, "ghost"))


class InstallServerTests(unittest.TestCase):
    """U2 marketplace install path: launch derivation, host config append
    (idempotent + loud failures), badge rendering."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = os.path.join(self.tmp, "config.yaml")
        self.catalog = [
            {
                "name": "mcp-yfinance",
                "install_command": "uvx mcp-yfinance",
                "connect_steps": ["1. uvx mcp-yfinance"],
                "description": "yahoo finance data",
                "stars": 1,
                "verified": True,
                "source": "pypi",
            },
            {
                "name": "browser-use-mcp",
                "install_command": "pip install browser-use && uvx browser-use",
                "connect_steps": ["2. Add to config.yaml mcp_servers: command=uvx, args=['browser-use']"],
                "description": "browser agent",
                "stars": 108796,
                "verified": True,
                "source": "github",
            },
            {
                "name": "plaid-mcp",
                "install_command": "hermes mcp add plaid --url https://mcp.plaid.com/mcp --auth oauth",
                "connect_steps": ["hosted"],
                "description": "plaid finance api",
                "stars": 28,
                "verified": True,
                "source": "github",
            },
            {
                "name": "equibles-mcp",
                "install_command": "see repo",
                "connect_steps": ["1. read the repo README"],
                "description": "stock market data",
                "stars": None,
                "verified": False,
                "source": "blog:6 Best Stock Market MCP Servers",
            },
            {
                "name": "secret-srv",
                "install_command": "uvx secret-srv",
                "connect_steps": ["set SECRET_API_KEY env var"],
                "description": "needs API key",
                "stars": 500,
                "verified": False,
                "source": "reddit:top-15",
            },
        ]

    def tearDown(self):
        if os.path.exists(self.cfg):
            try:
                os.chmod(self.cfg, 0o644)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_cfg(self, text):
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write(text)

    def test_install_server_appends_block_and_preserves_rest(self):
        self._write_cfg(
            "session_reset:\n"
            "  at_hour: 4\n"
            "mcp_servers:\n"
            "  ffmpeg:\n"
            "    command: npx\n"
            "    args:\n"
            "      - -y\n"
            "      - ffmpeg-mcp\n"
            "plugins:\n"
            "  enabled: []\n"
        )
        result = core.install_server("mcp-yfinance", self.cfg, self.catalog)
        self.assertTrue(result["written"])
        self.assertEqual(result["block"], {"command": "uvx", "args": ["mcp-yfinance"]})
        with open(self.cfg, encoding="utf-8") as f:
            text = f.read()
        self.assertIn(
            "  mcp-yfinance:\n    command: uvx\n    args:\n      - mcp-yfinance", text
        )
        # untouched sections + ordering (block inserted inside mcp_servers)
        self.assertIn("session_reset:\n  at_hour: 4", text)
        self.assertIn("  ffmpeg:", text)
        self.assertIn("plugins:\n  enabled: []", text)
        self.assertLess(text.index("mcp-yfinance"), text.index("plugins:"))

    def test_install_server_idempotent_skips_existing(self):
        self._write_cfg(
            "mcp_servers:\n"
            "  mcp-yfinance:\n"
            "    command: uvx\n"
            "    args:\n"
            "      - mcp-yfinance\n"
        )
        result = core.install_server("mcp-yfinance", self.cfg, self.catalog)
        self.assertFalse(result["written"])
        self.assertEqual(result["path"], self.cfg)
        with open(self.cfg, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(text.count("mcp-yfinance:"), 1)  # no duplicate block

    def test_install_server_creates_section_when_missing(self):
        self._write_cfg("session_reset:\n  at_hour: 4\n")
        result = core.install_server("mcp-yfinance", self.cfg, self.catalog)
        self.assertTrue(result["written"])
        with open(self.cfg, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("mcp_servers:\n  mcp-yfinance:\n    command: uvx", text)
        self.assertIn("session_reset:\n  at_hour: 4", text)

    def test_install_server_missing_config_raises_loud(self):
        missing = os.path.join(self.tmp, "nope.yaml")
        with self.assertRaises(core.CatalogError) as cm:
            core.install_server("mcp-yfinance", missing, self.catalog)
        msg = str(cm.exception)
        self.assertIn(missing, msg)
        self.assertIn("config", msg.lower())

    def test_install_server_read_only_raises_loud(self):
        self._write_cfg("mcp_servers: {}\n")
        os.chmod(self.cfg, 0o444)
        try:
            with self.assertRaises(core.CatalogError) as cm:
                core.install_server("mcp-yfinance", self.cfg, self.catalog)
            msg = str(cm.exception)
            self.assertIn(self.cfg, msg)
            self.assertTrue(
                "read-only" in msg.lower() or "permission" in msg.lower()
            )
        finally:
            os.chmod(self.cfg, 0o644)

    def test_install_server_unknown_server_raises(self):
        with self.assertRaises(core.CatalogError) as cm:
            core.install_server("no-such-server", self.cfg, self.catalog)
        msg = str(cm.exception)
        self.assertIn("no-such-server", msg)
        self.assertIn("not found", msg)

    def test_install_server_no_launch_raises_with_manual_steps(self):
        with self.assertRaises(core.CatalogError) as cm:
            core.install_server("equibles-mcp", self.cfg, self.catalog)
        msg = str(cm.exception)
        self.assertIn("equibles-mcp", msg)
        self.assertIn("see repo", msg)
        self.assertIn("read the repo README", msg)  # connect_steps surfaced

    def test_launch_config_derives_command_args_url_and_none(self):
        self.assertEqual(
            core.launch_config(self.catalog[0]),
            {"command": "uvx", "args": ["mcp-yfinance"]},
        )
        # shell install prefix stripped: 'pip install X && uvx browser-use'
        self.assertEqual(
            core.launch_config(self.catalog[1]),
            {"command": "uvx", "args": ["browser-use"]},
        )
        # hosted HTTP server -> url block
        self.assertEqual(
            core.launch_config(self.catalog[2]),
            {"url": "https://mcp.plaid.com/mcp"},
        )
        # 'see repo' -> None
        self.assertIsNone(core.launch_config(self.catalog[3]))
        # npx launcher keeps flags
        self.assertEqual(
            core.launch_config(
                {"install_command": "npx -y @modelcontextprotocol/server-filesystem C:/data"}
            ),
            {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:/data"]},
        )

    def test_security_badge_helpers_keyless_and_verdict(self):
        self.assertTrue(core.keyless(self.catalog[0]))    # no secret hints
        self.assertFalse(core.keyless(self.catalog[4]))   # API key + env var hints
        self.assertEqual(core.security_verdict(self.catalog[0]), "VERIFIED")    # pypi+verified
        self.assertEqual(core.security_verdict(self.catalog[2]), "VERIFIED")    # github+verified
        self.assertEqual(core.security_verdict(self.catalog[4]), "UNVERIFIED")  # not verified
        # verified but secondary source -> REVIEW
        review = dict(self.catalog[4], verified=True)
        self.assertEqual(core.security_verdict(review), "REVIEW")

    def test_format_badges_and_badged_list_render(self):
        badges = core.format_badges(self.catalog[1])  # 108796★, keyless, github
        self.assertIn("★108.8k", badges)
        self.assertIn("keyless", badges)
        self.assertIn("VERIFIED", badges)
        no_stars = core.format_badges(self.catalog[3])
        self.assertIn("★-", no_stars)
        self.assertIn("UNVERIFIED", no_stars)
        listing = core.list_catalog_badged(self.catalog)
        self.assertIn("5 server(s)", listing)
        self.assertIn("mcp-yfinance  [", listing)
        self.assertIn("install: uvx mcp-yfinance", listing)


class InstallWiringTests(unittest.TestCase):
    """/mcp add <name> [--yes] handler routing — the --yes install path and the
    plan-without-confirmation path. __init__.py loads via the importlib
    package recipe (its `from . import core` cannot run as a plain module)."""

    @classmethod
    def setUpClass(cls):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg = types.ModuleType("pkg")
        pkg.__path__ = [plugin_dir]
        sys.modules["pkg"] = pkg
        spec = importlib.util.spec_from_file_location(
            "pkg.__init__", os.path.join(plugin_dir, "__init__.py")
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["pkg.__init__"] = mod
        spec.loader.exec_module(mod)
        cls.mod = mod

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = os.path.join(self.tmp, "config.yaml")
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write("session_reset:\n  at_hour: 4\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_add_install_yes_path_calls_install_server(self):
        mod = self.mod
        with mock.patch.object(mod, "_host_config_path", return_value=self.cfg), mock.patch.object(
            mod.core,
            "install_server",
            return_value={
                "name": "mcp-yfinance",
                "block": {"command": "uvx", "args": ["mcp-yfinance"]},
                "written": True,
                "path": self.cfg,
            },
        ) as inst:
            out = mod._handle_mcp("add mcp-yfinance --yes")
        inst.assert_called_once()
        self.assertEqual(inst.call_args.args[0], "mcp-yfinance")
        self.assertIn("installed", out)
        self.assertIn("mcp-yfinance", out)

    def test_add_install_without_yes_prints_plan_and_asks(self):
        mod = self.mod
        with mock.patch.object(mod, "_host_config_path", return_value=self.cfg), mock.patch.object(
            mod.core, "install_server"
        ) as inst, mock.patch.object(
            mod.core,
            "load_rich_catalog",
            return_value=[
                {
                    "name": "mcp-yfinance",
                    "install_command": "uvx mcp-yfinance",
                    "connect_steps": ["run it"],
                    "description": "d",
                    "stars": 1,
                    "verified": True,
                    "source": "pypi",
                }
            ],
        ):
            out = mod._handle_mcp("add mcp-yfinance")
        inst.assert_not_called()
        self.assertIn("plan:", out)
        self.assertIn("--yes", out)
        self.assertIn("uvx mcp-yfinance", out)


if __name__ == "__main__":
    unittest.main()
