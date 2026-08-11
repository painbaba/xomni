"""Tests for the aider-style repo map engine (core.py)."""
import os
import tempfile
import unittest

import core


class RepoMapTests(unittest.TestCase):
    def _tree(self, files: dict[str, str]) -> str:
        d = tempfile.mkdtemp()
        for rel, content in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        return d

    def test_python_symbols(self):
        d = self._tree({
            "app.py": "import os\n\ndef main():\n    pass\n\nclass Server:\n    pass\n\nasync def fetch():\n    pass\n",
            "util.py": "class Helper:\n    pass\n",
        })
        m = core.build_map(d)
        self.assertIn("app.py", m)
        self.assertIn("main", m)
        self.assertIn("Server", m)
        self.assertIn("fetch", m)
        self.assertIn("util.py", m)
        self.assertIn("Helper", m)

    def test_go_and_rust_symbols(self):
        d = self._tree({
            "main.go": "package main\n\nfunc main() {}\n\ntype Config struct{}\n",
            "lib.rs": "pub fn parse() {}\npub struct Token {}\nenum Kind {}\n",
        })
        m = core.build_map(d)
        self.assertIn("main.go", m)
        self.assertIn("[main, Config]", m)  # map lists symbols, not source lines
        self.assertIn("lib.rs", m)
        self.assertIn("[parse, Token, Kind]", m)

    def test_js_ts_symbols(self):
        d = self._tree({
            "a.ts": "export interface User {}\nexport function load() {}\nexport class API {}\n",
            "b.js": "function helper() {}\nexport const VALUE = 1;\n",
        })
        m = core.build_map(d)
        self.assertIn("User", m)
        self.assertIn("load", m)
        self.assertIn("API", m)
        self.assertIn("helper", m)
        self.assertIn("VALUE", m)

    def test_skips_node_modules_and_build(self):
        d = self._tree({
            "src/index.js": "function real() {}\n",
            "node_modules/lib/index.js": "function fake() {}\n",
            "dist/bundle.js": "function fake2() {}\n",
        })
        m = core.build_map(d)
        self.assertIn("real", m)
        self.assertNotIn("fake", m)

    def test_output_size_capped(self):
        d = self._tree({f"f{i}.py": f"def fn{i}():\n    pass\n" for i in range(200)})
        m = core.build_map(d, max_files=60, max_chars=1000)
        self.assertLessEqual(len(m), 1000 + 200)  # cap enforced at line granularity

    def test_stack_tags(self):
        d = self._tree({
            "requirements.txt": "django\n",
            "go.mod": "module x\n",
            "Dockerfile": "FROM python\n",
            "ignored/node_modules/x.js": "",
        })
        tags = core.stack_tags(d)
        self.assertIn("python", tags)
        self.assertIn("go", tags)
        self.assertIn("docker", tags)
        self.assertNotIn("node", tags)  # node_modules skipped


if __name__ == "__main__":
    unittest.main()
