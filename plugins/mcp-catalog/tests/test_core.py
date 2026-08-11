"""Tests for mcp-catalog core (core.py) — catalog parsing, validation,
formatting, JSON-RPC message shapes, and state round-trip."""
import json
import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
