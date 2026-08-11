"""Scoring, stack-tag, symbol-parsing, cap and error-path tests for core.py."""
import os
import sys
import tempfile
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))  # plugins/ -> repomap pkg
sys.path.insert(0, os.path.dirname(_HERE))                   # repomap/ -> core

import core  # noqa: E402


class _TreeMixin:
    def _tree(self, files: dict[str, str]) -> str:
        d = tempfile.mkdtemp()
        for rel, content in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        return d


class ScoreFileTests(unittest.TestCase):
    """Unit-level checks of the _score_file relevance scoring rules."""

    def test_exact_symbol_match_scores_3(self):
        self.assertEqual(core._score_file("auth.py", ["login"], ["login"]), 3)
        self.assertEqual(core._score_file("auth.py", ["login", "logout"], ["login"]), 3)

    def test_filename_substring_scores_2(self):
        self.assertEqual(core._score_file("login_helper.py", ["x"], ["login"]), 2)

    def test_symbol_substring_scores_1(self):
        # term is only a substring of a symbol (no word boundary, no filename hit)
        self.assertEqual(core._score_file("misc.py", ["tokenizer"], ["token"]), 1)

    def test_word_boundary_blocks_exact_score(self):
        # "login" inside "login_success" is NOT a word-boundary match (+3),
        # but still counts as a plain substring (+1).
        self.assertEqual(core._score_file("auth.py", ["login_success"], ["login"]), 1)
        self.assertEqual(core._score_file("auth.py", ["login_success"], ["login_success"]), 3)

    def test_multiple_terms_combine(self):
        # exact symbol match (+3) + filename substring (+2) = 5
        self.assertEqual(core._score_file("auth.py", ["login"], ["login", "auth"]), 5)
        # two exact symbol matches = 6
        self.assertEqual(core._score_file("svc.py", ["login", "logout"], ["login", "logout"]), 6)

    def test_no_match_scores_zero(self):
        self.assertEqual(core._score_file("other.py", ["x"], ["zzz"]), 0)
        self.assertEqual(core._score_file("other.py", ["x"], []), 0)

    def test_case_insensitive_matching(self):
        self.assertEqual(core._score_file("auth.py", ["Login"], ["login"]), 3)
        self.assertEqual(core._score_file("auth.py", ["login"], ["LOGIN"]), 3)

    def test_filename_vs_symbol_priority(self):
        # symbol hit beats filename hit when both terms match different files
        self.assertEqual(core._score_file("auth.py", ["login"], ["login"]), 3)
        self.assertEqual(core._score_file("login_util.py", ["x"], ["login"]), 2)


class RankFilesExtendedTests(_TreeMixin, unittest.TestCase):
    def test_score_labels_and_multi_term_accumulation(self):
        d = self._tree({
            "auth.py": "def login():\n    pass\n",
            "auth_token.py": "def x():\n    pass\n",
            "other.py": "def y():\n    pass\n",
        })
        ranked = core.rank_files(d, "login auth")
        lines = ranked.splitlines()
        self.assertTrue(lines[0].startswith("5"), lines[0])  # 3 (symbol) + 2 (filename)
        self.assertIn("auth.py", lines[0])
        self.assertTrue(lines[1].startswith("2"), lines[1])  # auth_token.py: filename only
        self.assertEqual(len(lines), 2)

    def test_symbol_only_match_ranks_high(self):
        # match lives only in a symbol, not in the filename
        d = self._tree({"misc.py": "def tokenize():\n    pass\n"})
        ranked = core.rank_files(d, "tokenize")
        line = ranked.splitlines()[0]
        self.assertTrue(line.startswith("3"), line)
        self.assertIn("misc.py", line)

    def test_top_n_zero_returns_empty(self):
        d = self._tree({"auth.py": "def login():\n    pass\n"})
        self.assertEqual(core.rank_files(d, "login", top_n=0), "")

    def test_tie_break_shallower_depth_first(self):
        d = self._tree({
            "x.py": "def a():\n    pass\n",
            "sub/x.py": "def b():\n    pass\n",
        })
        ranked = core.rank_files(d, "x")
        names = [ln.split()[1] for ln in ranked.splitlines()]
        self.assertEqual(names, ["x.py", "sub/x.py"])  # depth 0 before depth 1

    def test_ranked_output_respects_char_cap(self):
        # long filename matches push the ranked output past DEFAULT_MAX_CHARS;
        # the cap must truncate at line granularity.
        files = {("t" * 250 + str(i) + ".py"): "def foo():\n    pass\n" for i in range(30)}
        d = self._tree(files)
        ranked = core.rank_files(d, "t" * 10, top_n=30)
        self.assertLessEqual(len(ranked), core.DEFAULT_MAX_CHARS + 300)
        self.assertLess(len(ranked.splitlines()), 30)  # some lines dropped by the cap

    def test_nonexistent_root_returns_empty(self):
        self.assertEqual(core.rank_files(os.path.join(tempfile.gettempdir(), "no-such-dir-xyz"), "login"), "")


class StackTagsExtendedTests(_TreeMixin, unittest.TestCase):
    def test_full_stack_detection_sorted(self):
        d = self._tree({
            "package.json": "{}\n",
            "app.py": "print(1)\n",
            "go.mod": "module x\n",
            "cargo.toml": "[package]\n",
            "pom.xml": "<project/>\n",
            "Gemfile": "source :rubygems\n",
            "Dockerfile": "FROM python\n",
            "page.php": "<?php\n",
            "schema.sql": "CREATE TABLE t (id int);\n",
            "util.c": "int main(void) { return 0; }\n",
            "util.cpp": "int main() { return 0; }\n",
        })
        self.assertEqual(
            core.stack_tags(d),
            ["c", "cpp", "docker", "go", "java", "node", "php", "python", "ruby", "rust", "sql"],
        )

    def test_skip_dirs_not_counted(self):
        d = self._tree({
            "venv/lib/site.py": "x = 1\n",
            ".git/hooks/x.py": "y = 2\n",
            "node_modules/pkg/a.js": "z = 3\n",
            "__pycache__/c.pyc": "",
        })
        self.assertEqual(core.stack_tags(d), [])

    def test_empty_dir_no_tags(self):
        self.assertEqual(core.stack_tags(tempfile.mkdtemp()), [])

    def test_nonexistent_root_no_tags(self):
        self.assertEqual(core.stack_tags(os.path.join(tempfile.gettempdir(), "no-such-dir-xyz")), [])


class SymbolParsingTests(_TreeMixin, unittest.TestCase):
    def test_oversize_file_skipped(self):
        with mock.patch.object(core, "MAX_FILE_BYTES", 100):
            d = self._tree({"big.py": "# " + "x" * 200 + "\ndef fn():\n    pass\n"})
            self.assertEqual(core._symbols_for(os.path.join(d, "big.py"), ".py"), [])
            self.assertNotIn("big.py", core.build_map(d))

    def test_missing_file_returns_empty_symbols(self):
        self.assertEqual(
            core._symbols_for(os.path.join(tempfile.gettempdir(), "no-such-file-xyz.py"), ".py"), []
        )

    def test_symbols_deduplicated(self):
        d = self._tree({"app.py": "def foo():\n    pass\ndef foo():\n    pass\nclass Bar:\n    pass\n"})
        m = core.build_map(d)
        self.assertIn("[foo, Bar]", m)
        self.assertNotIn("foo, foo", m)

    def test_symbol_overflow_plus_more(self):
        d = self._tree({"f.py": "".join(f"def fn{i}():\n    pass\n" for i in range(15))})
        m = core.build_map(d)
        self.assertIn("(+3 more)", m)  # 15 symbols, 12 listed
        self.assertIn("fn11", m)
        self.assertNotIn("fn12", m)  # hidden behind the +N more counter

    def test_c_header_alias_parsed_with_c_pattern(self):
        d = self._tree({"util.h": "int helper(void) {\n  return 1;\n}\n#define LIMIT 10\n"})
        m = core.build_map(d)
        self.assertIn("util.h", m)
        self.assertIn("[helper, LIMIT]", m)

    def test_vue_script_without_symbols_falls_back_to_component_name(self):
        d = self._tree({"Card.vue": "<script setup>import { ref } from 'vue'</script>\n"})
        m = core.build_map(d)
        self.assertIn("[Card]", m)


class BuildMapCapsTests(_TreeMixin, unittest.TestCase):
    def test_max_files_cap(self):
        d = self._tree({f"f{i}.py": f"def fn{i}():\n    pass\n" for i in range(10)})
        m = core.build_map(d, max_files=3)
        self.assertEqual(len(m.splitlines()), 3)

    def test_depth_sort_order(self):
        d = self._tree({
            "z.py": "def a():\n    pass\n",
            "sub/a.py": "def b():\n    pass\n",
        })
        m = core.build_map(d)
        self.assertLess(m.index("z.py"), m.index("sub/a.py"))

    def test_nonexistent_root_returns_empty(self):
        self.assertEqual(core.build_map(os.path.join(tempfile.gettempdir(), "no-such-dir-xyz")), "")


if __name__ == "__main__":
    unittest.main()
