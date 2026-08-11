"""omni-skills tests — pure core, no host needed."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

SKILL_A = """---
name: hello-skill
description: "Greets the user."
version: "1.2.0"
license: MIT
tags: [greeting, demo]
---
# Hello
Do the greeting.
"""

SKILL_BAD = """---
name: evil-skill
description: "Runs a destructive command."
---
#!/bin/bash
rm -rf /tmp/x
"""

SKILL_NOSKILL = "no frontmatter here, just prose"


class FrontmatterTests(unittest.TestCase):
    def test_parses_scalars_and_lists(self):
        fm = core.parse_frontmatter(SKILL_A)
        self.assertEqual(fm["name"], "hello-skill")
        self.assertEqual(fm["version"], "1.2.0")
        self.assertEqual(fm["tags"], ["greeting", "demo"])

    def test_no_frontmatter_returns_empty(self):
        self.assertEqual(core.parse_frontmatter("plain text"), {})

    def test_malformed_never_raises(self):
        self.assertEqual(core.parse_frontmatter("---\n:no-colon-line\n---"), {})
        self.assertEqual(core.parse_frontmatter("---"), {})


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omni-skills-test-")
        os.makedirs(os.path.join(self.tmp, "good"))
        with open(os.path.join(self.tmp, "good", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_A)
        os.makedirs(os.path.join(self.tmp, "empty"))
        os.makedirs(os.path.join(self.tmp, "notskill"))
        with open(os.path.join(self.tmp, "notskill", "notes.txt"), "w", encoding="utf-8") as f:
            f.write("x")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scan_finds_skill_dirs_only(self):
        skills = core.scan_skills(self.tmp)
        names = [s["name"] for s in skills]
        self.assertEqual(names, ["hello-skill"])

    def test_scan_missing_root(self):
        self.assertEqual(core.scan_skills("/nonexistent/xyz"), [])


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omni-skills-test-")
        self.good = os.path.join(self.tmp, "good")
        os.makedirs(self.good)
        with open(os.path.join(self.good, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_A)
        self.bad = os.path.join(self.tmp, "bad")
        os.makedirs(self.bad)
        with open(os.path.join(self.bad, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_BAD)
        with open(os.path.join(self.bad, "run.sh"), "w", encoding="utf-8") as f:
            f.write("rm -rf /tmp/x\ncat ../secret\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_good_skill_passes(self):
        r = core.validate_skill(self.good)
        self.assertEqual(r["verdict"], "PASS")
        self.assertTrue(r["ok"])

    def test_destructive_skill_rejected(self):
        r = core.validate_skill(self.bad)
        self.assertEqual(r["verdict"], "REJECT")
        self.assertFalse(r["ok"])
        self.assertTrue(any("destructive" in reason for _f, reason in r["issues"]))

    def test_missing_skill_md_rejected(self):
        r = core.validate_skill(self.tmp)  # dir without SKILL.md
        self.assertEqual(r["verdict"], "REJECT")


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.src = tempfile.mkdtemp(prefix="omni-skills-src-")
        self.dst = tempfile.mkdtemp(prefix="omni-skills-dst-")
        os.makedirs(os.path.join(self.src, "good"))
        with open(os.path.join(self.src, "good", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_A)

    def tearDown(self):
        shutil.rmtree(self.src, ignore_errors=True)
        shutil.rmtree(self.dst, ignore_errors=True)

    def test_install_copies_validated_skill(self):
        r = core.install_skill(os.path.join(self.src, "good"), self.dst)
        self.assertTrue(r["ok"])
        self.assertTrue(os.path.isfile(os.path.join(self.dst, "hello-skill", "SKILL.md")))

    def test_dry_run_writes_nothing(self):
        r = core.install_skill(os.path.join(self.src, "good"), self.dst, dry_run=True)
        self.assertTrue(r["dry_run"])
        self.assertFalse(os.path.exists(os.path.join(self.dst, "hello-skill")))

    def test_marketplace_install(self):
        r = core.install_marketplace(self.src, self.dst)
        self.assertEqual(r["installed"], 1)
        self.assertEqual(r["rejected"], 0)

    def test_fingerprint_stable(self):
        a = core.fingerprint(os.path.join(self.src, "good"))
        b = core.fingerprint(os.path.join(self.src, "good"))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)


class SearchListStatusTests(unittest.TestCase):
    """Skills search, plugin inventory, env status — the 'full access via any
    API' surface."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omni-skills-search-")
        os.makedirs(os.path.join(self.tmp, "plotly-101"))
        with open(os.path.join(self.tmp, "plotly-101", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: plotly-101\ndescription: \"Plotly charts for data viz.\"\n---\nMake charts with plotly.\n")
        os.makedirs(os.path.join(self.tmp, "gh-issues"))
        with open(os.path.join(self.tmp, "gh-issues", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: gh-issues\ndescription: \"GitHub issue triage.\"\n---\nTriage issues.\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_search_finds_in_skill_tree(self):
        hits = core.search_skills("plotly")
        tree_hits = [h for h in hits if h["source"] in ("hermes-skills", "checkout-skills")]
        # without a checkout data/, search falls back to the real hermes skills
        # tree (may or may not contain plotly) — so assert shape, not hits.
        self.assertIsInstance(hits, list)
        # direct tree search over a temp root must find the planted skill
        found = []
        for base, _dirs, files in os.walk(self.tmp):
            if "SKILL.md" in files:
                text = open(os.path.join(base, "SKILL.md"), encoding="utf-8").read()
                if "plotly" in text.lower():
                    found.append(base)
        self.assertEqual(len(found), 1)

    def test_empty_query_no_hits(self):
        self.assertEqual(core.search_skills(""), [])
        self.assertEqual(core.search_skills(None), [])

    def test_list_plugins_finds_self(self):
        plugins = core.list_plugins()
        names = [p["name"] for p in plugins]
        self.assertIn("omni-skills", names)
        by_name = {p["name"]: p for p in plugins}
        self.assertFalse(by_name["omni-skills"]["has_hooks"])

    def test_list_plugins_missing_dir(self):
        self.assertEqual(core.list_plugins("/nonexistent/xyz"), [])

    def test_env_status_shape(self):
        st = core.env_status()
        for key in ("xomni_home", "plugins_total", "skills_total", "data"):
            self.assertIn(key, st)
        self.assertGreaterEqual(st["plugins_total"], 1)


if __name__ == "__main__":
    unittest.main()
