"""OmniDesign plugin tests — pure core, no host needed."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

SLOPPY_HTML = """<!DOCTYPE html>
<html><head><style>
body{background:linear-gradient(135deg,#6d5dfc,#7c3aed,#4f46e5);font-family:Inter,sans-serif}
.card{border-left:5px solid #6d5dfc;backdrop-filter:blur(10px)}
.stat{font-size:96px;text-align:center}
</style></head><body>
<div style="text-align:center"><svg></svg></div><h2>One</h2><p>desc</p>
<div style="text-align:center"><svg></svg></div><h2>Two</h2><p>desc</p>
<div style="text-align:center"><svg></svg></div><h2>Three</h2><p>desc</p>
<div style="text-align:center"><svg></svg></div><h2>Four</h2><p>desc</p>
</body></html>"""

CLEAN_HTML = """<!DOCTYPE html>
<html><head><style>
:root{--accent:#00E5A0}
body{background:#050607;color:#E8EAED;font-family:ui-sans-serif,system-ui,sans-serif}
</style></head><body><main><h1>Title</h1><p>Body text.</p></main></body></html>"""


class TokenPresetTests(unittest.TestCase):
    def test_all_presets_have_required_keys(self):
        for name, preset in core.TOKEN_PRESETS.items():
            self.assertIn(name, ("xomni-dark", "xomni-light", "terminal-emerald", "plasma-cyan"))
            missing = core.REQUIRED_TOKEN_KEYS - set(preset)
            self.assertEqual(missing, set(), f"{name} missing {missing}")

    def test_css_tokens_renders_accent(self):
        css = core.css_tokens("xomni-dark")
        self.assertIn("#00E5A0", css)
        self.assertIn("--ease-out-expo", css)
        self.assertIn("--font-mono", css)


class SlopAuditTests(unittest.TestCase):
    def test_sloppy_html_scores_high(self):
        r = core.slop_score(SLOPPY_HTML)
        self.assertGreaterEqual(r["score"], 5)
        self.assertGreaterEqual(len(r["tell_keys"]), 6)
        self.assertIn("generic-indigo", r["tell_keys"])
        self.assertIn("unearned-blur", r["tell_keys"])

    def test_clean_html_scores_low(self):
        r = core.slop_score(CLEAN_HTML)
        self.assertLessEqual(r["score"], 2)
        self.assertIn("repair", r)

    def test_repair_register_maps(self):
        r = core.slop_score(SLOPPY_HTML)
        self.assertTrue(any("re-layout" in x for x in r["repair"]))
        self.assertTrue(any("recolor" in x for x in r["repair"]))


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omni-design-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_generates_landing(self):
        path = core.generate_artifact("a landing page for a terminal AI agent",
                                      preset="xomni-dark", out_dir=self.tmp)
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as f:
            html = f.read()
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("<style>", html)
        self.assertIn("#00E5A0", html)
        self.assertIn("@media (prefers-reduced-motion: reduce)", html)
        self.assertIn('name="viewport"', html)
        self.assertNotIn("{TOKENS}", html)
        self.assertNotIn("{BODY}", html)

    def test_generates_deck_and_lab(self):
        p1 = core.generate_artifact("a deck presentation", out_dir=self.tmp)
        self.assertIn("deck", open(p1, encoding="utf-8").read().lower())
        p2 = core.generate_artifact("a component lab ui kit", out_dir=self.tmp)
        self.assertIn("component lab", open(p2, encoding="utf-8").read().lower())

    def test_surface_picking(self):
        self.assertEqual(core.pick_surface("status dashboard for metrics"),
                         "Monitor")
        self.assertEqual(core.pick_surface("landing page for a product"),
                         "Decide/Learn")
        self.assertEqual(core.pick_surface("a settings wizard"), "Configure")


if __name__ == "__main__":
    unittest.main()
