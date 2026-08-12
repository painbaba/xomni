"""Tests for bharat-voice core (core.py) — Sarvam/Bhashini TTS/STT.

Run: cd plugins/bharat-voice && python -m unittest tests.test_core -q

Everything is mocked — no network, no real keys (all functions take an
injectable urlopen / explicit api_key). Guards: fail-loud errors name the
missing key/endpoint AND the fix; the API key value never appears in any
error message.
"""
import io
import json
import os
import unittest
import urllib.error

from core import (
    BharatVoiceError,
    BHASHINI_COMPUTE_URL,
    DEFAULT_BHASHINI_PIPELINE_ID,
    LANGS,
    SARVAM_TTS_URL,
    available_engines,
    bhashini_stt,
    bhashini_tts,
    build_bhashini_stt_payload,
    build_bhashini_tts_payload,
    build_sarvam_tts_payload,
    pick_engine,
    render_convo,
    sarvam_tts,
)

FAKE_KEY = "sk-SECRET-12345-do-not-leak"
AUDIO_B64 = "QUlGQk9Y"  # b64 of b"AI FBOX" — any bytes will do for tests


def _stub_urlopen(resp_obj):
    """Return a urlopen stub that answers with ``resp_obj`` as JSON."""

    def _urlopen(req, timeout=None):
        return io.BytesIO(json.dumps(resp_obj).encode("utf-8"))

    return _urlopen


class LangsTest(unittest.TestCase):
    def test_langs_six_languages_with_codes(self):
        expected = {
            "hi": ("Hindi", "hi-IN"),
            "ta": ("Tamil", "ta-IN"),
            "te": ("Telugu", "te-IN"),
            "kn": ("Kannada", "kn-IN"),
            "mr": ("Marathi", "mr-IN"),
            "gu": ("Gujarati", "gu-IN"),
        }
        self.assertEqual(set(LANGS), set(expected))
        for code, (name, sarvam_code) in expected.items():
            info = LANGS[code]
            self.assertEqual(info["name"], name)
            self.assertEqual(info["sarvam_code"], sarvam_code)
            self.assertIn("script", info)


class PayloadTest(unittest.TestCase):
    def test_sarvam_tts_payload_exact_shape(self):
        url, headers, body = build_sarvam_tts_payload("नमस्ते", "hi", api_key=FAKE_KEY)
        self.assertEqual(url, SARVAM_TTS_URL)
        self.assertEqual(
            headers,
            {"api-subscription-key": FAKE_KEY, "Content-Type": "application/json"},
        )
        self.assertEqual(
            body,
            {
                "model": "bulbul:v1",
                "inputs": ["नमस्ते"],
                "target_language_code": "hi-IN",
                "speaker": "meera",
            },
        )
        # every language maps to its Sarvam BCP-47 code
        for code, info in LANGS.items():
            _, _, body = build_sarvam_tts_payload("x", code, api_key=FAKE_KEY)
            self.assertEqual(body["target_language_code"], info["sarvam_code"])

    def test_bhashini_stt_payload_exact_shape(self):
        url, headers, body = build_bhashini_stt_payload(AUDIO_B64, "hi", api_key=FAKE_KEY)
        self.assertEqual(url, BHASHINI_COMPUTE_URL)
        self.assertEqual(
            headers,
            {"Authorization": f"Bearer {FAKE_KEY}", "Content-Type": "application/json"},
        )
        self.assertEqual(body["pipelineId"], DEFAULT_BHASHINI_PIPELINE_ID)
        self.assertEqual(
            body["input"],
            [{"source": "audio", "audio": [{"audioContent": AUDIO_B64, "audioSource": "base64"}]}],
        )
        self.assertEqual(body["config"], {"language": {"sourceLanguage": "hi"}})

    def test_bhashini_tts_payload_shape_and_pipeline_override(self):
        url, headers, body = build_bhashini_tts_payload(
            "ನಮಸ್ಕಾರ", "kn", api_key=FAKE_KEY, pipeline_id="pipe-99"
        )
        self.assertEqual(url, BHASHINI_COMPUTE_URL)
        self.assertEqual(headers["Authorization"], f"Bearer {FAKE_KEY}")
        self.assertEqual(body["pipelineId"], "pipe-99")
        self.assertEqual(body["input"], [{"source": "text", "text": [{"input": "ನಮಸ್ಕಾರ"}]}])
        self.assertEqual(
            body["config"], {"language": {"sourceLanguage": "kn", "targetLanguage": "kn"}}
        )


class SarvamTest(unittest.TestCase):
    def test_sarvam_tts_parses_audio_bytes(self):
        expected = b"RIFFfake-wav"
        resp = {"audio": __import__("base64").b64encode(expected).decode("ascii")}
        got = sarvam_tts("hello", "hi", api_key=FAKE_KEY, urlopen=_stub_urlopen(resp))
        self.assertEqual(got, expected)

    def test_sarvam_tts_error_paths_fail_loud(self):
        resp = {"error": {"message": "quota exhausted"}}
        with self.assertRaises(BharatVoiceError) as ctx:
            sarvam_tts("hello", "hi", api_key=FAKE_KEY, urlopen=_stub_urlopen(resp))
        self.assertIn("quota exhausted", str(ctx.exception))
        with self.assertRaises(BharatVoiceError) as ctx:
            sarvam_tts("hello", "hi", api_key=FAKE_KEY, urlopen=_stub_urlopen({}))
        self.assertIn("audio", str(ctx.exception))


class BhashiniTest(unittest.TestCase):
    def test_bhashini_stt_parses_text(self):
        resp = {"output": [{"audio": [{"text": "नमस्ते दुनिया"}]}]}
        got = bhashini_stt(AUDIO_B64, "hi", api_key=FAKE_KEY, urlopen=_stub_urlopen(resp))
        self.assertEqual(got, "नमस्ते दुनिया")

    def test_bhashini_stt_raises_fail_loud(self):
        resp = {"error": {"message": "invalid audio stream"}}
        with self.assertRaises(BharatVoiceError) as ctx:
            bhashini_stt(AUDIO_B64, "hi", api_key=FAKE_KEY, urlopen=_stub_urlopen(resp))
        self.assertIn("invalid audio stream", str(ctx.exception))
        with self.assertRaises(BharatVoiceError) as ctx:
            bhashini_stt(AUDIO_B64, "hi", api_key=FAKE_KEY, urlopen=_stub_urlopen({}))
        self.assertIn("output[0].audio[0].text", str(ctx.exception))

    def test_bhashini_tts_parses_audio_bytes(self):
        expected = b"ID3fake-mp3"
        resp = {"output": [{"audio": [{"audioContent": __import__("base64").b64encode(expected).decode("ascii")}]}]}
        got = bhashini_tts("hello", "ta", api_key=FAKE_KEY, urlopen=_stub_urlopen(resp))
        self.assertEqual(got, expected)


class FailLoudTest(unittest.TestCase):
    def test_missing_key_raises_naming_env_var(self):
        saved = {k: os.environ.pop(k, None) for k in ("SARVAM_API_KEY", "BHASHINI_API_KEY")}
        try:
            with self.assertRaises(BharatVoiceError) as ctx:
                build_sarvam_tts_payload("hi", "hi")
            self.assertIn("SARVAM_API_KEY", str(ctx.exception))
            self.assertIn("Fix:", str(ctx.exception))
            with self.assertRaises(BharatVoiceError) as ctx:
                build_bhashini_stt_payload(AUDIO_B64, "hi")
            self.assertIn("BHASHINI_API_KEY", str(ctx.exception))
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_errors_never_contain_api_key(self):
        cases = [
            # server error body
            {"error": {"message": "bad request"}},
            # missing output
            {},
        ]
        for resp in cases:
            with self.assertRaises(BharatVoiceError) as ctx:
                sarvam_tts("hi", "hi", api_key=FAKE_KEY, urlopen=_stub_urlopen(resp))
            self.assertNotIn(FAKE_KEY, str(ctx.exception))
            with self.assertRaises(BharatVoiceError) as ctx:
                bhashini_stt(AUDIO_B64, "hi", api_key=FAKE_KEY, urlopen=_stub_urlopen(resp))
            self.assertNotIn(FAKE_KEY, str(ctx.exception))
        # network-layer failures (URLError / HTTPError) must not leak the key either
        def _boom_urlopen(req, timeout=None):
            raise urllib.error.URLError("connection refused")

        with self.assertRaises(BharatVoiceError) as ctx:
            sarvam_tts("hi", "hi", api_key=FAKE_KEY, urlopen=_boom_urlopen)
        self.assertNotIn(FAKE_KEY, str(ctx.exception))

        def _http_error_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                SARVAM_TTS_URL, 401, "Unauthorized", {},
                io.BytesIO(b'{"error":"bad key"}'),
            )

        with self.assertRaises(BharatVoiceError) as ctx:
            bhashini_tts("hi", "hi", api_key=FAKE_KEY, urlopen=_http_error_urlopen)
        self.assertNotIn(FAKE_KEY, str(ctx.exception))

    def test_unsupported_lang_fail_loud(self):
        with self.assertRaises(BharatVoiceError) as ctx:
            build_sarvam_tts_payload("x", "xx", api_key=FAKE_KEY)
        self.assertIn("xx", str(ctx.exception))


class EngineTest(unittest.TestCase):
    def test_pick_engine_all_combinations(self):
        self.assertEqual(pick_engine("hi", True, True), "sarvam")
        self.assertEqual(pick_engine("hi", True, False), "sarvam")
        self.assertEqual(pick_engine("hi", False, True), "bhashini")
        self.assertEqual(pick_engine("hi", False, False), "edge-tts")

    def test_available_engines_reflects_env(self):
        saved = {k: os.environ.pop(k, None) for k in ("SARVAM_API_KEY", "BHASHINI_API_KEY")}
        try:
            os.environ.pop("SARVAM_API_KEY", None)
            os.environ.pop("BHASHINI_API_KEY", None)
            self.assertEqual(available_engines(), {"sarvam": False, "bhashini": False})
            os.environ["SARVAM_API_KEY"] = "k1"
            self.assertEqual(available_engines(), {"sarvam": True, "bhashini": False})
            os.environ["BHASHINI_API_KEY"] = "k2"
            self.assertEqual(available_engines(), {"sarvam": True, "bhashini": True})
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)


class RenderTest(unittest.TestCase):
    def test_render_convo_numbered(self):
        out = render_convo([("user", "namaste"), "assistant: नमस्ते", "bye"])
        self.assertEqual(
            out,
            "1. user: namaste\n2. assistant: नमस्ते\n3. bye",
        )


class ZeroHooksTest(unittest.TestCase):
    def test_zero_hooks_in_non_test_code(self):
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ("core.py", "__init__.py"):
            with open(os.path.join(here, "..", name), encoding="utf-8") as fh:
                src = fh.read()
            self.assertNotIn("register_hook", src, f"{name} must not register hooks")


if __name__ == "__main__":
    unittest.main()
