"""Tests for the Bharat Pack engine (core.py)."""
import json
import os
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


class RegionalLanguagePackTests(unittest.TestCase):
    """mr/ta/te/kn/gu packs: non-empty strings, greet carries the language."""

    def _assert_pack(self, code: str) -> None:
        s = core.ui_strings(code)
        self.assertIsNot(s, core.UI_STRINGS["en"], f"{code} fell back to English")
        for key, val in s.items():
            self.assertTrue(val.strip(), f"{code}.{key} is empty")
        self.assertIn(code, core.greet(code))
        self.assertIn(code, [lang["code"] for lang in core.LANGUAGES])

    def test_marathi_pack(self):
        self._assert_pack("mr")

    def test_tamil_pack(self):
        self._assert_pack("ta")

    def test_telugu_pack(self):
        self._assert_pack("te")

    def test_kannada_pack(self):
        self._assert_pack("kn")

    def test_gujarati_pack(self):
        self._assert_pack("gu")


class SarvamTtsPreviewTests(unittest.TestCase):
    """Dry-run TTS payload: correct shape per language, key referenced not printed."""

    def test_tts_preview_payload_shape_per_lang(self):
        for code, tlc in core.SARVAM_TTS_LANGS.items():
            p = core.tts_preview("नमस्ते XOMNI", code)
            self.assertEqual(p["mode"], "dry-run", code)
            self.assertEqual(p["method"], "POST", code)
            self.assertEqual(p["url"], "https://api.sarvam.ai/v1/tts", code)
            self.assertEqual(p["body"]["model"], "bulbul/v1", code)
            self.assertEqual(p["body"]["target_language_code"], tlc, code)
            self.assertEqual(p["body"]["input"], "नमस्ते XOMNI", code)
            self.assertEqual(p["target_language_code"], tlc, code)
            self.assertEqual(p["text_chars"], len("नमस्ते XOMNI"), code)
            self.assertIn("https://api.sarvam.ai/v1/tts", p["curl"], code)
            self.assertIn(core.SARVAM_API_KEY_ENV, p["curl"], code)
            self.assertIn(tlc, p["curl"], code)
        # unknown lang falls back to hi-IN (never errors, still dry-run)
        fb = core.tts_preview("hello", "xx")
        self.assertEqual(fb["target_language_code"], "hi-IN")
        self.assertEqual(fb["mode"], "dry-run")

    def test_tts_preview_key_env_referenced_not_printed(self):
        secret = "sk-sarvam-super-secret-12345"
        os.environ[core.SARVAM_API_KEY_ENV] = secret
        try:
            p = core.tts_preview("hello", "hi")
            rendered = core.tts_preview_text("hello", "hi")
            # env-var NAME is referenced in the shape and the render...
            self.assertEqual(p["key_env"], core.SARVAM_API_KEY_ENV)
            self.assertEqual(
                p["headers"]["api-subscription-key"],
                f"env:{core.SARVAM_API_KEY_ENV}",
            )
            self.assertIn(core.SARVAM_API_KEY_ENV, rendered)
            # ...but its VALUE is never read or printed (dry-run, no leak).
            self.assertNotIn(secret, json.dumps(p, ensure_ascii=False))
            self.assertNotIn(secret, rendered)
        finally:
            os.environ.pop(core.SARVAM_API_KEY_ENV, None)


if __name__ == "__main__":
    unittest.main()
