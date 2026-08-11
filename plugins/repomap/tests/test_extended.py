"""Extended tests: new-language symbol extraction, relevance ranking, query routing."""
import os
import sys
import tempfile
import unittest

# Make both the plugin package (parent dir) and core.py (plugin dir) importable
# regardless of how the suite is launched.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))  # plugins/ -> repomap pkg
sys.path.insert(0, os.path.dirname(_HERE))                   # repomap/ -> core

import core
import repomap  # plugin __init__: tool + command handlers


class ExtendedSymbolTests(unittest.TestCase):
    def _tree(self, files: dict[str, str]) -> str:
        d = tempfile.mkdtemp()
        for rel, content in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        return d

    def test_new_language_symbols(self):
        d = self._tree({
            "Main.kt": (
                "package app\n\n"
                "class Server\n\n"
                "fun main() {}\n\n"
                "interface Handler\n\n"
                "object Registry\n\n"
                "class Wrapper {\n"
                "    companion object Factory\n"
                "}\n"
            ),
            "App.swift": (
                "import Foundation\n\n"
                "class User {}\n\n"
                "struct Point {}\n\n"
                "enum Color {}\n\n"
                "protocol Drawable {}\n\n"
                "func render() {}\n\n"
                "extension Array {}\n"
            ),
            "main.dart": (
                "void main() {}\n\n"
                "class Api {}\n\n"
                "Future<void> fetch() async {}\n\n"
                "Stream<int> ticks() {}\n\n"
                "enum Status {}\n\n"
                "typedef Compare = int Function(int a, int b);\n"
            ),
            "App.scala": (
                "package app\n\n"
                "class Service\n\n"
                "object Registry {}\n\n"
                "trait Loggable {}\n\n"
                "def helper(): Unit = {}\n"
            ),
            "main.lua": (
                "local function helper()\n"
                "end\n\n"
                "function M.run()\n"
                "end\n"
            ),
            "analysis.r": (
                "add <- function(a, b) {\n"
                "  a + b\n"
                "}\n\n"
                "setClass(\"Person\")\n"
            ),
            "main.tf": (
                'resource "aws_instance" "web_server" {\n'
                "}\n\n"
                'data "aws_ami" "ubuntu" {\n'
                "}\n\n"
                'variable "region" {\n'
                "}\n\n"
                'output "public_ip" {\n'
                "}\n\n"
                'module "vpc" {\n'
                "}\n"
            ),
            "App.vue": (
                "<template>\n"
                '  <div class="app">hi</div>\n'
                "</template>\n\n"
                "<script setup>\n"
                "import { ref } from 'vue'\n\n"
                "const count = ref(0)\n\n"
                "function increment() {\n"
                "  count.value++\n"
                "}\n"
                "</script>\n"
            ),
        })
        m = core.build_map(d)
        self.assertIn("[Server, main, Handler, Registry, Wrapper, Factory]", m)
        self.assertIn("[User, Point, Color, Drawable, render, Array]", m)
        self.assertIn("[main, Api, fetch, ticks, Status, Compare]", m)
        self.assertIn("[Service, Registry, Loggable, helper]", m)
        self.assertIn("[helper, M.run]", m)
        self.assertIn("[add, Person]", m)
        self.assertIn("[web_server, ubuntu, region, public_ip, vpc]", m)
        self.assertIn("[count, increment]", m)

    def test_vue_component_name_fallback(self):
        d = self._tree({"Card.vue": "<template><p>hi</p></template>\n"})
        m = core.build_map(d)
        self.assertIn("Card.vue", m)
        self.assertIn("[Card]", m)

    def test_shell_pattern_unchanged(self):
        d = self._tree({"run.sh": "#!/bin/sh\n\nstart_server() {\n  echo hi\n}\n"})
        m = core.build_map(d)
        self.assertIn("start_server", m)


class RankFilesTests(unittest.TestCase):
    def _tree(self, files: dict[str, str]) -> str:
        d = tempfile.mkdtemp()
        for rel, content in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        return d

    def test_rank_files_scoring_order(self):
        d = self._tree({
            "auth.py": "def login():\n    pass\n",
            "login_helper.py": "def do_thing():\n    pass\n",
            "tokenizer.py": "def parse():\n    pass\n",
            "misc.py": "def tokenize():\n    pass\n",
        })
        ranked = core.rank_files(d, "login token")
        lines = ranked.splitlines()
        # exact symbol match (auth.login, +3) > filename substring
        # (login_helper.py, +2) > symbol substring (misc.tokenize, +1)
        self.assertEqual(
            [ln.split()[1] for ln in lines],
            ["auth.py", "login_helper.py", "tokenizer.py", "misc.py"],
        )
        self.assertTrue(lines[0].startswith("3"), lines[0])
        self.assertTrue(lines[1].startswith("2"), lines[1])
        self.assertTrue(lines[2].startswith("2"), lines[2])
        self.assertTrue(lines[3].startswith("1"), lines[3])
        # unmatched files are omitted entirely
        self.assertEqual(len(lines), 4)

    def test_rank_files_single_term_and_top_n(self):
        d = self._tree({
            "auth.py": "def login():\n    pass\n",
            "login_helper.py": "def do_thing():\n    pass\n",
            "other.py": "def x():\n    pass\n",
        })
        single = core.rank_files(d, "login")
        self.assertEqual(single.splitlines()[0].split()[1], "auth.py")
        self.assertEqual(len(single.splitlines()), 2)  # other.py unmatched
        top = core.rank_files(d, "login", top_n=1)
        self.assertEqual(len(top.splitlines()), 1)
        self.assertIn("auth.py", top)
        # case-insensitive matching
        upper = core.rank_files(d, "LOGIN")
        self.assertEqual(upper.splitlines()[0].split()[1], "auth.py")

    def test_rank_files_blank_query(self):
        d = self._tree({"a.py": "def x():\n    pass\n"})
        self.assertEqual(core.rank_files(d, ""), "")
        self.assertEqual(core.rank_files(d, "   "), "")


class RoutingTests(unittest.TestCase):
    def _tree(self, files: dict[str, str]) -> str:
        d = tempfile.mkdtemp()
        for rel, content in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        return d

    def test_tool_query_routing(self):
        d = self._tree({
            "auth.py": "def login():\n    pass\n",
            "other.py": "def x():\n    pass\n",
        })
        # no query -> plain map, exactly as before
        plain = repomap._repomap_tool({"path": d})
        self.assertIn("auth.py", plain)
        self.assertIn("other.py", plain)
        # query present -> ranked relevant files
        ranked = repomap._repomap_tool({"path": d, "query": "login"})
        first = ranked.splitlines()[0]
        self.assertTrue(first.startswith("3"), first)
        self.assertIn("auth.py", first)
        self.assertNotIn("other.py", ranked)  # score 0 -> omitted
        # root alias still works, empty query still plain
        self.assertIn("other.py", repomap._repomap_tool({"root": d, "query": ""}))
        # not-a-directory guard unchanged
        self.assertIn("not a directory", repomap._repomap_tool({"path": os.path.join(d, "nope")}))

    def test_tool_schema_declares_query(self):
        captured = {}

        class FakeCtx:
            def register_tool(self, name, toolset=None, schema=None, handler=None, description=None, emoji=None):
                captured["schema"] = schema
                captured["handler"] = handler

            def register_command(self, name, handler=None, description=None, args_hint=None):
                captured["cmd_handler"] = handler
                captured["args_hint"] = args_hint

        repomap.register(FakeCtx())
        self.assertIn("query", captured["schema"]["properties"])
        self.assertEqual(captured["schema"]["properties"]["query"]["type"], "string")
        self.assertEqual(captured["args_hint"], "<directory> [query words...]")

    def test_command_query_parsing(self):
        d = self._tree({
            "auth.py": "def login():\n    pass\n",
            "other.py": "def x():\n    pass\n",
        })
        out = repomap._handle_repomap(f"{d} login")
        self.assertIn("query: login", out)
        lines = out.splitlines()
        self.assertTrue(lines[1].startswith("3"), lines[1])  # ranked line after header
        self.assertIn("auth.py", lines[1])
        self.assertNotIn("other.py", out)
        # dir only -> plain map with the old header (backward compatible)
        plain = repomap._handle_repomap(d)
        self.assertNotIn("query:", plain)
        self.assertIn("auth.py", plain)
        self.assertIn("other.py", plain)
        # multi-word query: first arg dir, rest = query
        out2 = repomap._handle_repomap(f"{d} login token")
        self.assertIn("query: login token", out2)


if __name__ == "__main__":
    unittest.main()
