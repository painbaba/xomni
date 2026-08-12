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

# A small marketplace-style catalog document (CRLF, 1-space entry indent) used
# to exercise byte-for-byte preservation when user-added entries are appended.
SAMPLE_CATALOG_TEXT = (
    "[\r\n"
    " {\r\n"
    "  \"name\": \"filesystem\",\r\n"
    "  \"install_command\": \"npx -y @modelcontextprotocol/server-filesystem C:/data\",\r\n"
    "  \"verified\": true,\r\n"
    "  \"source\": \"github\"\r\n"
    " },\r\n"
    " {\r\n"
    "  \"name\": \"fetch\",\r\n"
    "  \"install_command\": \"uvx mcp-server-fetch\",\r\n"
    "  \"verified\": true,\r\n"
    "  \"source\": \"pypi\"\r\n"
    " }\r\n"
    "]"
)


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
    (idempotent + loud failures), badge rendering, and U-SURF-1
    self-cataloging (auto-index into the catalog json)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = os.path.join(self.tmp, "config.yaml")
        # U-SURF-1: isolate the auto-index catalog target from the real
        # data/mcp/catalog.json so install tests never touch the repo file.
        self.catalog_file = os.path.join(self.tmp, "catalog.json")
        with open(self.catalog_file, "w", encoding="utf-8", newline="") as f:
            f.write(SAMPLE_CATALOG_TEXT)
        os.environ["HERMES_MCP_CATALOG_FILE"] = self.catalog_file
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
            {
                "name": "PolymarketScan",
                "install_command": "npx -y @smithery/cli mcp add https://polymarketscan--jordan-s648.run.tools",
                "connect_steps": ["hosted remote endpoint"],
                "description": "polymarket analytics",
                "stars": 39501,
                "verified": True,
                "source": "smithery",
            },
        ]

    def tearDown(self):
        os.environ.pop("HERMES_MCP_CATALOG_FILE", None)
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

    def test_launch_config_smithery_remote_writes_url(self):
        """Smithery-hosted remotes (`npx -y @smithery/cli mcp add <url>`) are
        HTTP servers — resolve to a `url:` block, never a stdio npx launcher."""
        self.assertEqual(
            core.launch_config(self.catalog[5]),
            {"url": "https://polymarketscan--jordan-s648.run.tools"},
        )

    def test_install_server_writes_url_block_for_hosted_remote(self):
        """Full install loop for a hosted remote: `url:` block written inside
        mcp_servers, `mcp_servers: {}` expanded so the file stays valid YAML,
        and the rest of the config preserved."""
        self._write_cfg(
            "session_reset:\n  at_hour: 4\n"
            "mcp_servers: {}\n"
            "plugins:\n  enabled: []\n"
        )
        result = core.install_server("PolymarketScan", self.cfg, self.catalog)
        self.assertTrue(result["written"])
        self.assertEqual(
            result["block"], {"url": "https://polymarketscan--jordan-s648.run.tools"}
        )
        with open(self.cfg, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("url: 'https://polymarketscan--jordan-s648.run.tools'", text)
        self.assertNotIn("command:", text)
        self.assertIn("session_reset:\n  at_hour: 4", text)
        self.assertIn("plugins:\n  enabled: []", text)
        import yaml
        with open(self.cfg, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertEqual(
            data["mcp_servers"]["PolymarketScan"]["url"],
            "https://polymarketscan--jordan-s648.run.tools",
        )

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
        self.assertIn(f"{len(self.catalog)} server(s)", listing)
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
        # U-SURF-1: point the self-catalog target at a temp file so e2e wiring
        # tests never touch the real data/mcp/catalog.json.
        self.catalog_file = os.path.join(self.tmp, "catalog.json")
        with open(self.catalog_file, "w", encoding="utf-8", newline="") as f:
            f.write(SAMPLE_CATALOG_TEXT)
        os.environ["HERMES_MCP_CATALOG_FILE"] = self.catalog_file

    def tearDown(self):
        os.environ.pop("HERMES_MCP_CATALOG_FILE", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _catalog_names(self):
        with open(self.catalog_file, encoding="utf-8", newline="") as f:
            return [e["name"] for e in json.load(f)]

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

    def test_search_command_returns_badged_results(self):
        mod = self.mod
        rich = [
            {
                "name": "mcp-yfinance",
                "install_command": "uvx mcp-yfinance",
                "connect_steps": [],
                "description": "yahoo finance data",
                "purpose": "quotes and history",
                "stars": 1,
                "verified": True,
                "source": "pypi",
            },
            {
                "name": "browser-use-mcp",
                "install_command": "uvx browser-use",
                "connect_steps": [],
                "description": "browser agent",
                "purpose": "browser automation",
                "stars": 2,
                "verified": True,
                "source": "github",
            },
        ]
        with mock.patch.object(mod.core, "load_rich_catalog", return_value=rich):
            out = mod._handle_mcp("search finance")
        self.assertIn("1 match(es) for 'finance'", out)
        self.assertIn("mcp-yfinance", out)
        self.assertIn("VERIFIED", out)
        with mock.patch.object(mod.core, "load_rich_catalog", return_value=rich):
            out = mod._handle_mcp("search zzz-none")
        self.assertIn("no matches for 'zzz-none'", out)

    def test_status_surfaces_marketplace_gap(self):
        mod = self.mod
        with mock.patch.object(
            mod.core, "load_rich_catalog", return_value=[{"name": "x"}, {"name": "y"}]
        ), mock.patch.object(
            mod, "_host_config_servers", return_value={"ffmpeg": {"enabled": False}}
        ):
            out = mod._cmd_status([])
        self.assertIn("marketplace: 2 server(s) in data/mcp/catalog.json", out)
        self.assertIn("1 registered (0 enabled)", out)
        self.assertIn("gap: 1 catalog server(s) not registered", out)


class SearchTests(unittest.TestCase):
    """U2 /mcp search: keyword search over name/description/purpose with
    badged results, and the marketplace-vs-host gap line (/mcp status)."""

    def setUp(self):
        self.catalog = [
            {
                "name": "browser-use-mcp",
                "description": "browser-use MCP (PyPI, 108k★). The popular AI browser agent",
                "purpose": "LLM-driven browser agent: plan + execute multi-step web tasks",
                "install_command": "uvx browser-use",
                "stars": 108796,
                "verified": True,
                "source": "github",
            },
            {
                "name": "tavily",
                "description": "AI-optimized web search with citations",
                "purpose": "search the web",
                "install_command": "uvx tavily",
                "stars": 500,
                "verified": True,
                "source": "pypi",
            },
            {
                "name": "firecrawl-mcp-server",
                "description": "Web scraping & search",
                "purpose": "scrape and crawl sites",
                "install_command": "see repo",
                "stars": None,
                "verified": False,
                "source": "blog:top-20",
            },
            {
                "name": "filesystem",
                "description": "secure local file operations",
                "purpose": "file access",
                "install_command": "npx -y @modelcontextprotocol/server-filesystem",
                "stars": 1000,
                "verified": True,
                "source": "github",
            },
        ]

    def test_search_by_name(self):
        matches = core.search_catalog(self.catalog, "tavily")
        self.assertEqual([m["name"] for m in matches], ["tavily"])

    def test_search_by_description_keyword_case_insensitive(self):
        matches = core.search_catalog(self.catalog, "BROWSER")
        self.assertEqual([m["name"] for m in matches], ["browser-use-mcp"])
        # 'web' hits browser-use-mcp's purpose plus both search descriptions
        matches = core.search_catalog(self.catalog, "web")
        self.assertEqual(
            [m["name"] for m in matches],
            ["browser-use-mcp", "tavily", "firecrawl-mcp-server"],
        )
        # description-only hit, not present anywhere in the other entries
        matches = core.search_catalog(self.catalog, "citations")
        self.assertEqual([m["name"] for m in matches], ["tavily"])

    def test_search_name_matches_rank_first(self):
        catalog = [
            {"name": "search-helper", "description": "generic utility", "purpose": "x"},
            {"name": "plain", "description": "a search service for docs", "purpose": "search"},
            {"name": "alpha-search", "description": "search anything", "purpose": "y"},
        ]
        matches = core.search_catalog(catalog, "search")
        # name hits first (catalog order), then description-only hits
        self.assertEqual(
            [m["name"] for m in matches], ["search-helper", "alpha-search", "plain"]
        )

    def test_search_all_tokens_must_match(self):
        matches = core.search_catalog(self.catalog, "citations")
        self.assertEqual([m["name"] for m in matches], ["tavily"])
        # 'firecrawl search' → both tokens in the firecrawl entry's name+desc
        matches = core.search_catalog(self.catalog, "firecrawl search")
        self.assertEqual([m["name"] for m in matches], ["firecrawl-mcp-server"])

    def test_search_no_match_and_empty_query(self):
        self.assertEqual(core.search_catalog(self.catalog, "zzz-none"), [])
        self.assertEqual(core.search_catalog(self.catalog, ""), [])
        self.assertEqual(core.search_catalog(self.catalog, "   "), [])

    def test_format_search_results_header_and_badges(self):
        matches = core.search_catalog(self.catalog, "web")
        text = core.format_search_results(matches, "web", len(self.catalog))
        self.assertIn("search: 3 match(es) for 'web' in MCP catalog (4 servers)", text)
        self.assertIn("  browser-use-mcp  [", text)
        self.assertIn("★108.8k", text)       # stars badge
        self.assertIn("  tavily  [", text)
        self.assertIn("★500", text)          # stars badge
        self.assertIn("VERIFIED", text)
        self.assertIn("install: uvx tavily", text)
        self.assertIn("  firecrawl-mcp-server  [", text)
        self.assertIn("★-", text)            # no stars → placeholder
        self.assertIn("UNVERIFIED", text)
        self.assertIn("install: see repo", text)

    def test_format_search_results_no_match_message(self):
        text = core.format_search_results([], "zzz", 311)
        self.assertIn("no matches for 'zzz'", text)
        self.assertIn("311", text)

    def test_gap_line_matches_and_differs(self):
        line = core.gap_line(311, {"ffmpeg": {"enabled": False}, "yfinance": {}})
        self.assertIn("marketplace: 311 server(s) in data/mcp/catalog.json", line)
        self.assertIn("host config mcp_servers: 2 registered (1 enabled)", line)
        self.assertIn("gap: 309 catalog server(s) not registered", line)
        self.assertIn("/mcp add <name> --yes", line)
        # no gap when counts agree
        same = core.gap_line(2, {"a": {}, "b": {}})
        self.assertNotIn("gap", same)
        self.assertIn("2 registered (2 enabled)", same)
        # all-disabled hosts still count as registered, just not enabled
        disabled = core.gap_line(1, {"a": {"enabled": False}})
        self.assertIn("1 registered (0 enabled)", disabled)
        self.assertNotIn("gap", disabled)


class SelfCatalogTests(unittest.TestCase):
    """U-SURF-1 core: catalog_add / register_server — user-added auto-indexing
    into the catalog json (idempotent, byte-preserving, loud failures),
    auto-index on install, badges + source for user-added entries."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.catalog_file = os.path.join(self.tmp, "catalog.json")
        with open(self.catalog_file, "w", encoding="utf-8", newline="") as f:
            f.write(SAMPLE_CATALOG_TEXT)
        os.environ["HERMES_MCP_CATALOG_FILE"] = self.catalog_file
        self.cfg = os.path.join(self.tmp, "config.yaml")
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write("session_reset:\n  at_hour: 4\n")

    def tearDown(self):
        os.environ.pop("HERMES_MCP_CATALOG_FILE", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _catalog(self):
        with open(self.catalog_file, encoding="utf-8", newline="") as f:
            return json.load(f)

    def test_catalog_add_appends_user_entry_preserving_rest_byte_for_byte(self):
        result = core.catalog_add(
            "my-srv", {"install_command": "uvx my-srv"}, catalog_path=self.catalog_file
        )
        self.assertTrue(result["written"])
        self.assertEqual(result["path"], self.catalog_file)
        entry = result["entry"]
        self.assertEqual(entry["name"], "my-srv")
        self.assertEqual(entry["install_command"], "uvx my-srv")
        self.assertEqual(entry["source"], "user-added")
        self.assertEqual(entry["security"], "REVIEW")
        self.assertEqual(entry["badges"], {"keyless": True})
        self.assertTrue(entry["added_at"])
        # the rest of the catalog is preserved byte-for-byte (CRLF, indents,
        # key order, final ']'): everything before the closing ']' appears
        # verbatim, followed by ',' + the new entry + ']'
        with open(self.catalog_file, encoding="utf-8", newline="") as f:
            text = f.read()
        preserved = SAMPLE_CATALOG_TEXT[:-1].rstrip()  # original minus ']'
        self.assertTrue(text.startswith(preserved + ","))
        self.assertTrue(text.endswith("]"))
        data = self._catalog()
        self.assertEqual([e["name"] for e in data], ["filesystem", "fetch", "my-srv"])
        # file style matches the marketplace document (1-space entry brace,
        # 2-space keys, CRLF)
        self.assertIn(" {\r\n", text)
        self.assertIn('  "name": "my-srv",\r\n', text)

    def test_catalog_add_idempotent_skips_existing(self):
        first = core.catalog_add(
            "my-srv", {"install_command": "uvx my-srv"}, catalog_path=self.catalog_file
        )
        self.assertTrue(first["written"])
        with open(self.catalog_file, encoding="utf-8", newline="") as f:
            before = f.read()
        second = core.catalog_add(
            "my-srv", {"install_command": "uvx my-srv"}, catalog_path=self.catalog_file
        )
        self.assertFalse(second["written"])
        self.assertEqual(second["entry"]["source"], "user-added")
        with open(self.catalog_file, encoding="utf-8", newline="") as f:
            after = f.read()
        self.assertEqual(before, after)  # byte-for-byte unchanged on re-add
        names = [e["name"] for e in self._catalog()]
        self.assertEqual(names.count("my-srv"), 1)

    def test_catalog_add_rejects_bad_shape_loudly(self):
        with self.assertRaises(core.CatalogError) as cm:
            core.catalog_add("x", {}, catalog_path=self.catalog_file)
        self.assertIn("needs 'install_command', 'command'", str(cm.exception))
        with self.assertRaises(core.CatalogError):
            core.catalog_add("", {"install_command": "uvx x"}, catalog_path=self.catalog_file)
        with self.assertRaises(core.CatalogError):
            core.catalog_add("x", {"install_command": "   "}, catalog_path=self.catalog_file)
        with self.assertRaises(core.CatalogError):
            core.catalog_add("x", {"command": "uvx", "args": "not-a-list"}, catalog_path=self.catalog_file)
        with self.assertRaises(core.CatalogError):
            core.catalog_add("x", "uvx x", catalog_path=self.catalog_file)
        # file untouched by rejected adds
        with open(self.catalog_file, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), SAMPLE_CATALOG_TEXT)

    def test_catalog_add_accepts_config_shapes_and_creates_missing_file(self):
        # stdio config shape (command/args) and hosted url shape both index
        stdio = core.catalog_add(
            "srv-a", {"command": "npx", "args": ["-y", "srv-a"], "env": {}}, catalog_path=self.catalog_file
        )
        self.assertTrue(stdio["written"])
        self.assertEqual(stdio["entry"]["install_command"], "npx -y srv-a")
        url = core.catalog_add(
            "srv-b", {"url": "https://example.com/mcp"}, catalog_path=self.catalog_file
        )
        self.assertTrue(url["written"])
        self.assertEqual(
            url["entry"]["install_command"], "hermes mcp add srv-b --url https://example.com/mcp"
        )
        # env vars flip the keyless badge
        keyed = core.catalog_add(
            "srv-c", {"command": "uvx", "args": ["srv-c"], "env": {"API_KEY": "x"}},
            catalog_path=self.catalog_file,
        )
        self.assertEqual(keyed["entry"]["badges"], {"keyless": False})
        # missing catalog file: created with just the entry
        missing = os.path.join(self.tmp, "fresh.json")
        created = core.catalog_add("solo", {"install_command": "uvx solo"}, catalog_path=missing)
        self.assertTrue(created["written"])
        with open(missing, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual([e["name"] for e in data], ["solo"])
        self.assertEqual(data[0]["source"], "user-added")

    def test_install_server_auto_indexes_into_catalog(self):
        catalog = [{"name": "mcp-yfinance", "install_command": "uvx mcp-yfinance",
                    "connect_steps": [], "description": "d", "stars": 1,
                    "verified": True, "source": "pypi"}]
        result = core.install_server("mcp-yfinance", self.cfg, catalog)
        self.assertTrue(result["written"])
        self.assertTrue(result["indexed"])
        self.assertEqual(result["catalog_path"], self.catalog_file)
        data = self._catalog()
        entry = next(e for e in data if e["name"] == "mcp-yfinance")
        self.assertEqual(entry["source"], "user-added")
        self.assertEqual(entry["install_command"], "uvx mcp-yfinance")
        self.assertEqual(entry["security"], "REVIEW")
        self.assertEqual(entry["badges"], {"keyless": True})
        # untouched entries still present, catalog still valid JSON
        self.assertEqual([e["name"] for e in data[:2]], ["filesystem", "fetch"])
        # host config got the block too
        with open(self.cfg, encoding="utf-8") as f:
            self.assertIn("mcp-yfinance:\n    command: uvx", f.read())

    def test_install_server_auto_index_idempotent(self):
        catalog = [{"name": "mcp-yfinance", "install_command": "uvx mcp-yfinance",
                    "connect_steps": [], "stars": 1, "verified": True, "source": "pypi"}]
        first = core.install_server("mcp-yfinance", self.cfg, catalog)
        self.assertTrue(first["indexed"])
        with open(self.catalog_file, encoding="utf-8", newline="") as f:
            before = f.read()
        second = core.install_server("mcp-yfinance", self.cfg, catalog)
        self.assertFalse(second["written"])     # already registered
        self.assertFalse(second["indexed"])     # already in catalog
        with open(self.catalog_file, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), before)  # catalog untouched
        self.assertEqual([e["name"] for e in self._catalog()].count("mcp-yfinance"), 1)

    def test_install_server_backfills_catalog_when_already_registered(self):
        # a server already in host config (imported from a config entry) is
        # still auto-indexed into the catalog on touch
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write("mcp_servers:\n  mcp-yfinance:\n    command: uvx\n    args:\n      - mcp-yfinance\n")
        catalog = [{"name": "mcp-yfinance", "install_command": "uvx mcp-yfinance",
                    "connect_steps": [], "stars": 1, "verified": True, "source": "pypi"}]
        result = core.install_server("mcp-yfinance", self.cfg, catalog)
        self.assertFalse(result["written"])
        self.assertTrue(result["indexed"])
        names = [e["name"] for e in self._catalog()]
        self.assertEqual(names.count("mcp-yfinance"), 1)
        self.assertEqual(
            next(e for e in self._catalog() if e["name"] == "mcp-yfinance")["source"],
            "user-added",
        )

    def test_register_server_writes_host_config_and_catalog(self):
        result = core.register_server(
            "my-new-srv", {"command": "uvx", "args": ["my-new-srv"]}, self.cfg
        )
        self.assertTrue(result["written"])
        self.assertTrue(result["indexed"])
        self.assertEqual(result["catalog_path"], self.catalog_file)
        with open(self.cfg, encoding="utf-8") as f:
            self.assertIn("my-new-srv:\n    command: uvx\n    args:\n      - my-new-srv", f.read())
        entry = next(e for e in self._catalog() if e["name"] == "my-new-srv")
        self.assertEqual(entry["source"], "user-added")
        self.assertEqual(entry["install_command"], "uvx my-new-srv")
        # url block variant
        url_result = core.register_server("hosted-srv", {"url": "https://example.com/mcp"}, self.cfg)
        self.assertTrue(url_result["written"])
        with open(self.cfg, encoding="utf-8") as f:
            self.assertIn("hosted-srv:\n    url: 'https://example.com/mcp'", f.read())

    def test_register_server_bad_block_raises_loud(self):
        with self.assertRaises(core.CatalogError) as cm:
            core.register_server("", {"command": "x"}, self.cfg)
        self.assertIn("non-empty string", str(cm.exception))
        with self.assertRaises(core.CatalogError) as cm:
            core.register_server("x", {}, self.cfg)
        self.assertIn("needs 'url' (hosted) or 'command'", str(cm.exception))
        with self.assertRaises(core.CatalogError):
            core.register_server("x", {"command": "  "}, self.cfg)
        with self.assertRaises(core.CatalogError):
            core.register_server("x", {"url": "  "}, self.cfg)
        with open(self.cfg, encoding="utf-8") as f:
            self.assertNotIn("x:", f.read())

    def test_user_added_entry_badges_and_render(self):
        entry = {
            "name": "solo",
            "install_command": "uvx solo",
            "badges": {"keyless": True},
            "security": "REVIEW",
            "source": "user-added",
            "added_at": "2026-08-13T00:00:00+00:00",
        }
        self.assertEqual(core.security_verdict(entry), "REVIEW")
        badges = core.format_badges(entry)
        self.assertIn("★-", badges)     # no stars for user-added
        self.assertIn("keyless", badges)
        self.assertIn("REVIEW", badges)
        listing = core.list_catalog_badged([entry])
        self.assertIn("solo  [", listing)
        self.assertIn("install: uvx solo", listing)
        keyed = dict(entry, badges={"keyless": False})
        self.assertIn("needs-key", core.format_badges(keyed))


class SelfCatalogWiringTests(unittest.TestCase):
    """/mcp add <name> <url-or-command> and /mcp catalog-add routing —
    self-catalog e2e (temp host config + temp catalog), loud failures, and
    the zero-hooks rule. Loads __init__.py via the package recipe."""

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
        cls.plugin_dir = plugin_dir

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = os.path.join(self.tmp, "config.yaml")
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write("session_reset:\n  at_hour: 4\n")
        self.catalog_file = os.path.join(self.tmp, "catalog.json")
        with open(self.catalog_file, "w", encoding="utf-8", newline="") as f:
            f.write(SAMPLE_CATALOG_TEXT)
        os.environ["HERMES_MCP_CATALOG_FILE"] = self.catalog_file
        # isolate the catalog-dir import target too (file-import tests)
        self.catalog_dir = os.path.join(self.tmp, "catalogs")
        os.environ["HERMES_MCP_CATALOG_DIR"] = self.catalog_dir

    def tearDown(self):
        os.environ.pop("HERMES_MCP_CATALOG_FILE", None)
        os.environ.pop("HERMES_MCP_CATALOG_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _catalog_names(self):
        with open(self.catalog_file, encoding="utf-8", newline="") as f:
            return [e["name"] for e in json.load(f)]

    def test_mcp_add_self_catalog_e2e_stdio(self):
        mod = self.mod
        with mock.patch.object(mod, "_host_config_path", return_value=self.cfg):
            out = mod._handle_mcp("add my-new-srv uvx my-new-srv")
        self.assertIn("added 'my-new-srv'", out)
        with open(self.cfg, encoding="utf-8") as f:
            self.assertIn("my-new-srv:\n    command: uvx\n    args:\n      - my-new-srv", f.read())
        self.assertIn("my-new-srv", self._catalog_names())
        with open(self.catalog_file, encoding="utf-8") as f:
            data = json.load(f)
        added = next(e for e in data if e["name"] == "my-new-srv")
        self.assertEqual(added["source"], "user-added")
        self.assertEqual(added["security"], "REVIEW")
        self.assertEqual(added["install_command"], "uvx my-new-srv")

    def test_mcp_add_self_catalog_e2e_url_and_yes_flag(self):
        mod = self.mod
        with mock.patch.object(mod, "_host_config_path", return_value=self.cfg):
            out = mod._handle_mcp("add hosted-srv https://example.com/mcp --yes")
        self.assertIn("added 'hosted-srv'", out)
        with open(self.cfg, encoding="utf-8") as f:
            self.assertIn("hosted-srv:\n    url: 'https://example.com/mcp'", f.read())
        with open(self.catalog_file, encoding="utf-8") as f:
            data = json.load(f)
        added = next(e for e in data if e["name"] == "hosted-srv")
        self.assertEqual(
            added["install_command"], "hermes mcp add hosted-srv --url https://example.com/mcp"
        )

    def test_mcp_catalog_add_catalog_only(self):
        mod = self.mod
        out = mod._handle_mcp("catalog-add solo-srv uvx solo-srv")
        self.assertIn("indexed 'solo-srv'", out)
        self.assertIn("user-added", out)
        with open(self.cfg, encoding="utf-8") as f:
            self.assertNotIn("solo-srv", f.read())  # host config untouched
        with open(self.catalog_file, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("solo-srv", [e["name"] for e in data])
        # idempotent re-add
        out2 = mod._handle_mcp("catalog-add solo-srv uvx solo-srv")
        self.assertIn("already in catalog", out2)
        # usage when the install command is missing
        self.assertIn("usage:", mod._handle_mcp("catalog-add solo-srv"))

    def test_mcp_add_self_catalog_loud_failure(self):
        mod = self.mod
        with mock.patch.object(mod, "_host_config_path", return_value=self.cfg):
            out = mod._handle_mcp("add nospec")  # single token → marketplace install of unknown server
        self.assertIn("FAILED", out)
        self.assertIn("not found in MCP catalog", out)
        # single token that is not a marketplace server → loud FAILED, never silent
        with mock.patch.object(mod, "_host_config_path", return_value=self.cfg):
            out2 = mod._handle_mcp("add onlyname")
        self.assertIn("FAILED", out2)
        self.assertIn("onlyname", out2)
        # missing name / missing install command → usage
        self.assertIn("usage:", mod._handle_mcp("add"))
        self.assertIn("usage:", mod._handle_mcp("catalog-add"))
        self.assertIn("usage:", mod._handle_mcp("catalog-add solo-srv"))

    def test_mcp_add_marketplace_install_auto_indexes(self):
        """/mcp add <real-catalog-name> --yes e2e: block lands in host config
        AND a user-added entry lands in the catalog json."""
        mod = self.mod
        with mock.patch.object(mod, "_host_config_path", return_value=self.cfg):
            out = mod._handle_mcp("add mcp-yfinance --yes")
        self.assertIn("installed 'mcp-yfinance'", out)
        with open(self.cfg, encoding="utf-8") as f:
            self.assertIn("mcp-yfinance:\n    command: uvx", f.read())
        with open(self.catalog_file, encoding="utf-8") as f:
            data = json.load(f)
        added = next(e for e in data if e["name"] == "mcp-yfinance")
        self.assertEqual(added["source"], "user-added")
        self.assertEqual(added["install_command"], "uvx mcp-yfinance")
        # second run: no-op on config AND catalog (idempotent)
        with mock.patch.object(mod, "_host_config_path", return_value=self.cfg):
            out2 = mod._handle_mcp("add mcp-yfinance --yes")
        self.assertIn("already registered", out2)
        with open(self.catalog_file, encoding="utf-8") as f:
            names = [e["name"] for e in json.load(f)]
        self.assertEqual(names.count("mcp-yfinance"), 1)

    def test_mcp_add_file_import_auto_indexes(self):
        """/mcp add <path> import: servers land in the catalog dir AND are
        auto-indexed into the catalog json as user-added entries."""
        mod = self.mod
        import_file = os.path.join(self.tmp, "import.json")
        with open(import_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    [
                        {"name": "imp-a", "command": "uvx", "args": ["imp-a"], "env": {}, "description": "a"},
                        {"name": "imp-b", "command": "npx", "args": ["-y", "imp-b"], "env": {}, "description": "b"},
                    ]
                )
            )
        out = mod._handle_mcp(f"add {import_file}")
        self.assertIn("added 2 server(s)", out)
        self.assertIn("Self-cataloged 2 new server(s)", out)
        self.assertIn("imp-a", self._catalog_names())
        self.assertIn("imp-b", self._catalog_names())

    def test_plugin_registers_no_hooks(self):
        """Zero-hooks rule: the plugin registers only a command and a tool —
        no hooks, no event handlers."""
        mod = self.mod
        with open(os.path.join(self.plugin_dir, "__init__.py"), encoding="utf-8") as f:
            src = f.read()
        for banned in ("register_hook", "add_hook", "on_event", "subscribe"):
            self.assertNotIn(banned, src)
        class RecordingCtx:
            def __init__(self):
                self.calls = []
            def register_command(self, *a, **k):
                self.calls.append(("command", a[0] if a else "?"))
            def register_tool(self, *a, **k):
                self.calls.append(("tool", a[0] if a else "?"))
            def register_hook(self, *a, **k):
                self.calls.append(("hook", a))
        ctx = RecordingCtx()
        mod.register(ctx)
        kinds = [c[0] for c in ctx.calls]
        self.assertEqual(kinds, ["command", "tool"])
        self.assertNotIn("hook", kinds)
        self.assertEqual(ctx.calls[0][1], "mcp")


if __name__ == "__main__":
    unittest.main()
