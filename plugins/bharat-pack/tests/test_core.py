"""Tests for the Bharat Pack engine (core.py)."""
import unittest

import core


class StringsMapTests(unittest.TestCase):
    """Hindi/regional UI strings: completeness, parity, fallback."""

    def test_hi_and_en_present_and_parity(self):
        self.assertIn("hi", core.UI_STRINGS)
        self.assertIn("en", core.UI_STRINGS)
        self.assertEqual(set(core.UI_STRINGS["hi"]), set(core.UI_STRINGS["en"]))

    def test_all_langs_share_key_set(self):
        base = set(core.UI_STRINGS["en"])
        for code, s in core.UI_STRINGS.items():
            self.assertEqual(set(s), base, f"{code} key set differs from en")
            for key, val in s.items():
                self.assertTrue(val.strip(), f"{code}.{key} is empty")

    def test_hindi_uses_devanagari(self):
        hi = core.ui_strings("hi")
        self.assertEqual(hi["hello"], "नमस्ते")
        self.assertTrue(any("\u0900" <= ch <= "\u097f" for ch in hi["welcome"]))

    def test_ui_strings_fallback_to_english(self):
        self.assertEqual(core.ui_strings("xx"), core.UI_STRINGS["en"])
        self.assertEqual(core.ui_strings(""), core.UI_STRINGS["en"])


class IndianModelRegistryTests(unittest.TestCase):
    """Model-pool entries: 3-6, well-formed, source=spec, INR-market."""

    def test_registry_size_and_source_spec(self):
        self.assertGreaterEqual(len(core.INDIAN_MODELS), 3)
        self.assertLessEqual(len(core.INDIAN_MODELS), 6)
        self.assertTrue(all(m["source"] == "spec" for m in core.INDIAN_MODELS))

    def test_registry_entries_well_formed(self):
        ids = []
        for m in core.INDIAN_MODELS:
            for key in ("id", "vendor", "kind", "pricing", "source", "note"):
                self.assertIn(key, m, f"{m.get('id', '?')} missing key {key}")
            self.assertTrue(m["id"])
            ids.append(m["id"])
        self.assertEqual(len(ids), len(set(ids)), "duplicate model ids")

    def test_sarvam_krutrim_bhashini_covered(self):
        vendors = " ".join(m["vendor"] for m in core.INDIAN_MODELS)
        self.assertIn("Sarvam", vendors)
        self.assertIn("Krutrim", vendors)
        self.assertIn("Bhashini", vendors)

    def test_pricing_mentions_inr(self):
        for m in core.INDIAN_MODELS:
            p = m["pricing"]
            # sarvam → ₹ figures; krutrim → INR billing (per-token [UNVERIFIED]);
            # bhashini → free-to-register (gov-funded, pricing unverified).
            self.assertTrue(
                "₹" in p or "INR" in p or "free" in p,
                f"{m['id']} pricing not INR-market: {p}",
            )

    def test_sarvam_inr_rates_match_research(self):
        by_id = {m["id"]: m for m in core.INDIAN_MODELS}
        self.assertIn("₹4 in", by_id["sarvam-105b"]["pricing"])
        self.assertIn("₹16 out", by_id["sarvam-105b"]["pricing"])
        self.assertIn("₹2.5 in", by_id["sarvam-30b"]["pricing"])

class ProviderSnippetTests(unittest.TestCase):
    """Snippets: provider-pool block format + India facts."""

    def test_snippet_format_matches_provider_pool(self):
        self.assertEqual(set(core.PROVIDER_SNIPPETS), {"sarvam", "bhashini", "krutrim"})
        for name, snip in core.PROVIDER_SNIPPETS.items():
            self.assertIn("# --- xomni bharat-pack:", snip)
            self.assertIn(f"provider: {name}", snip)
            self.assertIn("model:", snip)
            self.assertIn("base_url:", snip)
            self.assertIn("key_env:", snip)

    def test_snippets_carry_india_facts(self):
        sarvam = core.provider_snippet("sarvam")
        self.assertIn("₹4", sarvam)
        self.assertIn("₹16", sarvam)
        self.assertIn("SARVAM_API_KEY", sarvam)
        self.assertIn("100 free credits", sarvam)
        bhashini = core.provider_snippet("bhashini")
        self.assertIn("approval-gated", bhashini)
        self.assertIn("BHASHINI_API_KEY", bhashini)
        krutrim = core.provider_snippet("krutrim")
        self.assertIn("data stays in India", krutrim)
        self.assertIn("UNVERIFIED", krutrim)
        self.assertIn("KRUTRIM_API_KEY", krutrim)

    def test_snippet_unknown_provider(self):
        self.assertIsNone(core.provider_snippet("bogus"))
        self.assertIsNone(core.provider_snippet(""))

if __name__ == "__main__":
    unittest.main()
