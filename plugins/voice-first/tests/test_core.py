"""Tests for voice-first core (core.py) — capture, STT, TTS, session loop.

Run: cd plugins/voice-first && python -m unittest tests.test_core -q

Everything is mocked — no mic, no network, no hermes subprocess required.
Guards: fail-loud errors carry install hints; the API key never appears in
any error message or request body (it rides only in the URL query).
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

import core

FAKE_KEY = "sekret123abc"  # a fake key used to prove non-leakage


class CaptureTests(unittest.TestCase):
    def test_build_capture_cmd_windows(self):
        """Windows: ffmpeg dshow with detected device by default, override honored."""
        with mock.patch.object(core, "detect_windows_mic", return_value="Microphone"):
            cmd = core.build_capture_cmd(3, r"C:\tmp\out.wav", backend="windows")
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("-f", cmd) and self.assertIn("dshow", cmd)
        self.assertIn("audio=Microphone", cmd)
        self.assertIn("-t", cmd) and self.assertIn("3", cmd)
        self.assertIn("-ar", cmd) and self.assertIn("16000", cmd)
        self.assertEqual(cmd[-1], r"C:\tmp\out.wav")
        cmd2 = core.build_capture_cmd(3, "out.wav", backend="windows",
                                      device="Headset (pTron BT)")
        self.assertIn("audio=Headset (pTron BT)", cmd2)

    def test_build_capture_cmd_posix_arecord(self):
        """POSIX: arecord with S16_LE 16 kHz mono."""
        cmd = core.build_capture_cmd(3, "/tmp/out.wav", backend="posix")
        self.assertEqual(cmd, ["arecord", "-d", "3", "-f", "S16_LE",
                               "-r", "16000", "-c", "1", "/tmp/out.wav"])

    def test_capture_missing_binary_loud(self):
        """Missing ffmpeg/arecord -> loud VoiceError with an install hint."""
        with mock.patch.object(core, "_IS_WIN", True), \
             mock.patch("shutil.which", return_value=None):
            with self.assertRaises(core.VoiceError) as ctx:
                core.capture_audio(3, "out.wav")
        msg = str(ctx.exception)
        self.assertIn("ffmpeg", msg) and self.assertIn("winget", msg)
        with mock.patch.object(core, "_IS_WIN", False), \
             mock.patch("shutil.which", return_value=None):
            with self.assertRaises(core.VoiceError) as ctx:
                core.capture_audio(3, "out.wav")
        msg = str(ctx.exception)
        self.assertIn("arecord", msg) and self.assertIn("alsa-utils", msg)

    def test_capture_run_failures_loud(self):
        """Nonzero rc / timeout / zero-byte output -> loud VoiceError."""
        with mock.patch.object(core, "_IS_WIN", True), \
             mock.patch.object(core, "detect_windows_mic", return_value="Microphone"), \
             mock.patch("shutil.which", return_value="ffmpeg"):
            proc = mock.Mock(returncode=1, stderr="could not open audio device",
                             stdout="")
            with mock.patch("core.subprocess.run", return_value=proc):
                with self.assertRaises(core.VoiceError) as ctx:
                    core.capture_audio(3, "out.wav")
            self.assertIn("rc=1", str(ctx.exception))
            self.assertIn("could not open audio device", str(ctx.exception))

            with mock.patch("core.subprocess.run",
                            side_effect=subprocess_timeout()):
                with self.assertRaises(core.VoiceError) as ctx:
                    core.capture_audio(3, "out.wav")
            self.assertIn("timed out", str(ctx.exception))

            proc_ok = mock.Mock(returncode=0, stderr="", stdout="")
            with mock.patch("core.subprocess.run", return_value=proc_ok), \
                 mock.patch("os.path.exists", return_value=False):
                with self.assertRaises(core.VoiceError) as ctx:
                    core.capture_audio(3, "out.wav")
            self.assertIn("produced no audio", str(ctx.exception))

    def test_detect_windows_mic_parses_device_list(self):
        """ffmpeg -list_devices output -> first '(audio)' device name."""
        stderr = (
            '[in#0 @ x] "Microphone Array (2- Intel STT)" (audio)\n'
            '  Alternative name "@device_cm_..._wave_..."\n'
            '[in#0 @ x] "Headset (pTron BT)" (audio)\n'
        )
        proc = mock.Mock(returncode=1, stdout="", stderr=stderr)
        with mock.patch("core.subprocess.run", return_value=proc):
            self.assertEqual(core.detect_windows_mic(),
                             "Microphone Array (2- Intel STT)")
        with mock.patch("core.subprocess.run", return_value=mock.Mock(
                returncode=1, stdout="", stderr="no devices")):
            self.assertEqual(core.detect_windows_mic(), core.DEFAULT_MIC)


def subprocess_timeout():
    return core.subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=20)


class STTTests(unittest.TestCase):
    def test_stt_backend_selection(self):
        """Auto: whisper preferred; gemini fallback; none -> loud error."""
        with mock.patch.object(core, "_whisper_importable", return_value=True):
            self.assertEqual(core.detect_stt_backend(), "whisper")
        with mock.patch.object(core, "_whisper_importable", return_value=False), \
             mock.patch.object(core, "_api_key", return_value=FAKE_KEY):
            self.assertEqual(core.detect_stt_backend(), "gemini")
        with mock.patch.object(core, "_whisper_importable", return_value=False), \
             mock.patch.object(core, "_api_key", return_value=None):
            with self.assertRaises(core.VoiceError) as ctx:
                core.detect_stt_backend()
            msg = str(ctx.exception)
            self.assertIn("faster-whisper", msg)
            self.assertIn("GOOGLE_API_KEY", msg)
            self.assertNotIn(FAKE_KEY, msg)

    def test_stt_whisper_unimportable_loud(self):
        """Explicit whisper backend with no runtime -> loud pip hint."""
        with mock.patch.dict(sys.modules, {"faster_whisper": None, "whisper": None}):
            with self.assertRaises(core.VoiceError) as ctx:
                core.detect_stt_backend("whisper")
        self.assertIn("pip install faster-whisper", str(ctx.exception))

    def test_stt_gemini_success(self):
        """Gemini: transcript parsed; key in URL only, never in the body."""
        payload = {"candidates": [{"content": {"parts": [
            {"text": "hello voice world"}]}}]}
        resp = mock.MagicMock()
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        resp.__enter__.return_value = resp
        urlopen = mock.MagicMock(return_value=resp)
        wav = _write_fake_wav()
        with mock.patch.object(core, "_api_key", return_value=FAKE_KEY), \
             mock.patch("urllib.request.urlopen", urlopen):
            text = core.stt(wav, backend="gemini")
        self.assertEqual(text, "hello voice world")
        req = urlopen.call_args[0][0]
        self.assertIn("key=" + FAKE_KEY, req.full_url)
        body = json.loads(req.data.decode("utf-8"))
        self.assertNotIn(FAKE_KEY, json.dumps(body))

    def test_stt_gemini_failures_loud_and_key_not_leaked(self):
        """HTTP error / empty transcript -> loud VoiceError; key never echoed."""
        wav = _write_fake_wav()
        http_err = urllib.error.HTTPError(
            "https://x", 403, "Forbidden", None,
            io.BytesIO(b'{"error":{"message":"quota exceeded"}}'))
        with mock.patch.object(core, "_api_key", return_value=FAKE_KEY), \
             mock.patch("urllib.request.urlopen", side_effect=http_err):
            with self.assertRaises(core.VoiceError) as ctx:
                core.stt(wav, backend="gemini")
        msg = str(ctx.exception)
        self.assertIn("403", msg)
        self.assertNotIn(FAKE_KEY, msg)

        empty = {"candidates": [{"content": {"parts": [{"text": "  "}]}}]}
        resp = mock.MagicMock()
        resp.read.return_value = json.dumps(empty).encode("utf-8")
        resp.__enter__.return_value = resp
        with mock.patch.object(core, "_api_key", return_value=FAKE_KEY), \
             mock.patch("urllib.request.urlopen", return_value=resp):
            with self.assertRaises(core.VoiceError) as ctx:
                core.stt(wav, backend="gemini")
        self.assertIn("empty transcript", str(ctx.exception))
        self.assertNotIn(FAKE_KEY, str(ctx.exception))

    def test_stt_missing_file_loud(self):
        with self.assertRaises(core.VoiceError) as ctx:
            core.stt(r"C:\nonexistent\no.wav")
        self.assertIn("not found", str(ctx.exception))


class TTSTests(unittest.TestCase):
    def test_build_tts_cmd_and_pick_voice(self):
        """Default en-IN voice; hi-IN for bharat (non-ASCII) text."""
        cmd = core.build_tts_cmd("Hello there", "out.mp3")
        self.assertEqual(cmd, ["edge-tts", "--voice", "en-IN-PrabhatNeural",
                               "--text", "Hello there", "--write-media", "out.mp3"])
        self.assertEqual(core.pick_voice("नमस्ते दुनिया"), "hi-IN-PrabhatNeural")
        cmd2 = core.build_tts_cmd("नमस्ते", "out.mp3")
        self.assertEqual(cmd2[2], "hi-IN-PrabhatNeural")

    def test_tts_failures_loud(self):
        """Missing edge-tts / nonzero rc -> loud VoiceError with install hint."""
        with mock.patch.object(core, "_find_tts_binary", return_value=None):
            with self.assertRaises(core.VoiceError) as ctx:
                core.tts("hello", "out.mp3")
        msg = str(ctx.exception)
        self.assertIn("edge-tts", msg) and self.assertIn("pip install edge-tts", msg)
        proc = mock.Mock(returncode=1, stderr="network error", stdout="")
        with mock.patch.object(core, "_find_tts_binary", return_value="edge-tts"), \
             mock.patch("core.subprocess.run", return_value=proc):
            with self.assertRaises(core.VoiceError) as ctx:
                core.tts("hello", "out.mp3")
        self.assertIn("rc=1", str(ctx.exception))

    def test_tts_success_writes_file(self):
        """rc 0 + non-empty file -> returns out_path."""
        tmp = tempfile.mkdtemp(prefix="vf-tts-")
        out = os.path.join(tmp, "out.mp3")
        with open(out, "wb") as fh:
            fh.write(b"ID3")
        proc = mock.Mock(returncode=0, stderr="", stdout="")
        with mock.patch.object(core, "_find_tts_binary", return_value="edge-tts"), \
             mock.patch("core.subprocess.run", return_value=proc):
            self.assertEqual(core.tts("hello", out), out)


class SessionTests(unittest.TestCase):
    def _run_session(self, turns=3, stt_texts=("hello",), replies=("hi there",),
                     capture_error=None):
        tmp = tempfile.mkdtemp(prefix="vf-sess-")
        stt_iter = iter(stt_texts)
        reply_iter = iter(replies)

        def fake_stt(path, backend=None):
            return next(stt_iter)

        def fake_ask(prompt, hermes_home=None):
            return next(reply_iter)

        patches = [
            mock.patch.object(core, "capture_audio",
                              side_effect=capture_error or (lambda *a, **k: None)),
            mock.patch.object(core, "stt", side_effect=fake_stt),
            mock.patch.object(core, "ask_host", side_effect=fake_ask),
            mock.patch.object(core, "tts", return_value="reply00.mp3"),
        ]
        started = [p.start() for p in patches]
        try:
            events = core.voice_session(turns=turns, out_dir=tmp)
        finally:
            for p in reversed(patches):
                p.stop()
        ask_mock, tts_mock = started[2], started[3]
        return events, ask_mock, tts_mock

    def test_session_state_machine(self):
        """User stop -> early exit; host stop -> no tts; exhaustion -> final stop."""
        events, ask_host, tts = self._run_session(
            turns=5, stt_texts=("stop now",))
        self.assertEqual(events[-1]["reason"], "user said stop")
        ask_host.assert_not_called()
        tts.assert_not_called()

        events, ask_host, tts = self._run_session(
            turns=5, stt_texts=("hello there",), replies=("we should stop here",))
        self.assertEqual(events[-1]["reason"], "host said stop")
        tts.assert_not_called()
        self.assertEqual(len([e for e in events if e["event"] == "reply"]), 1)

        events, ask_host, tts = self._run_session(
            turns=1, stt_texts=("hi",), replies=("hello!",))
        self.assertEqual(events[-1]["reason"], "turns exhausted")
        self.assertEqual(len([e for e in events if e["event"] == "tts"]), 1)
        self.assertIn("spoken ->", core.render_session(events))

    def test_session_fail_loud_propagates(self):
        """A capture failure must propagate (fail-loud), never be swallowed."""
        with self.assertRaises(core.VoiceError) as ctx:
            self._run_session(capture_error=core.VoiceError(
                "[voice-first] capture failed: ffmpeg not found on PATH. Install it"))
        self.assertIn("ffmpeg not found", str(ctx.exception))

    def test_ask_host_command_and_env(self):
        """hermes chat -q <prompt> argv; HERMES_HOME set when provided; rc loud."""
        proc = mock.Mock(returncode=0, stdout="the reply\n", stderr="")
        with mock.patch.object(core, "_find_hermes", return_value=r"C:\x\hermes.exe"), \
             mock.patch("core.subprocess.run", return_value=proc) as run:
            out = core.ask_host("hello host", hermes_home=r"C:\hermes-home")
        self.assertEqual(out, "the reply")
        cmd, kwargs = run.call_args
        self.assertEqual(cmd[0], [r"C:\x\hermes.exe", "chat", "-q", "hello host"])
        self.assertEqual(kwargs["env"]["HERMES_HOME"], r"C:\hermes-home")
        proc_bad = mock.Mock(returncode=2, stdout="", stderr="boom")
        with mock.patch.object(core, "_find_hermes", return_value="hermes"), \
             mock.patch("core.subprocess.run", return_value=proc_bad):
            with self.assertRaises(core.VoiceError) as ctx:
                core.ask_host("hi")
        self.assertIn("rc=2", str(ctx.exception))


class ZeroHooksGuardTests(unittest.TestCase):
    def test_zero_hooks_rule(self):
        """No register_hook anywhere in the plugin (spec: zero hooks)."""
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ("__init__.py", "core.py"):
            with open(os.path.join(here, "..", name), encoding="utf-8") as fh:
                self.assertNotIn("register_hook", fh.read(),
                                 f"{name} must register zero hooks")


class BackendRegistryTests(unittest.TestCase):
    """U-SURF-3: pluggable voice backend registry — tests 14-18.

    Registry completeness, auto-pick with mocked available(), explicit set +
    persistence, unknown-backend loud errors, and payload builders (gemini key
    by env name only, sarvam/bhashini for all 8 bharat-pack languages, edge
    synth payload, missing keys fail loud).
    """

    def setUp(self):
        # Isolate persistence: /voice set writes to a temp config file.
        self._tmp = tempfile.mkdtemp(prefix="vf-cfg-")
        patcher = mock.patch.object(
            core, "backend_config_path",
            return_value=os.path.join(self._tmp, ".voice_first.json"))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_registry_complete_and_shapes(self):
        """STT {'whisper-local','gemini','sarvam'}, TTS {'edge','sarvam',
        'bhashini'}; every entry carries name/kind/available + transcribe or
        synthesize; availability is a local bool check (no network)."""
        self.assertEqual(set(core.STT_BACKENDS),
                         {"whisper-local", "gemini", "sarvam"})
        self.assertEqual(set(core.TTS_BACKENDS),
                         {"edge", "sarvam", "bhashini"})
        for name, entry in core.STT_BACKENDS.items():
            self.assertEqual(entry["name"], name)
            self.assertEqual(entry["kind"], "stt")
            self.assertTrue(callable(entry["available"]))
            self.assertTrue(callable(entry["transcribe"]))
        for name, entry in core.TTS_BACKENDS.items():
            self.assertEqual(entry["name"], name)
            self.assertEqual(entry["kind"], "tts")
            self.assertTrue(callable(entry["available"]))
            self.assertTrue(callable(entry["synthesize"]))
        for entry in list(core.STT_BACKENDS.values()) + list(core.TTS_BACKENDS.values()):
            self.assertIsInstance(entry["available"](), bool)
        # edge synth payload shape (edge-tts argv).
        self.assertEqual(core.build_tts_cmd("Hello there", "out.mp3"),
                         ["edge-tts", "--voice", "en-IN-PrabhatNeural",
                          "--text", "Hello there", "--write-media", "out.mp3"])

    def test_auto_pick_first_available(self):
        """auto returns the first available backend in priority order; when
        nothing is available the error is loud and lists every backend."""
        reg = {
            "whisper-local": {"name": "whisper-local", "kind": "stt",
                              "available": lambda: False, "hint": "w"},
            "gemini": {"name": "gemini", "kind": "stt",
                       "available": lambda: True, "hint": "g"},
            "sarvam": {"name": "sarvam", "kind": "stt",
                       "available": lambda: False, "hint": "s"},
        }
        with mock.patch.dict(core.STT_BACKENDS, reg, clear=True):
            self.assertEqual(core.select_backend("stt", "auto"), "gemini")
        all_down = {k: dict(v, available=lambda: False) for k, v in reg.items()}
        with mock.patch.dict(core.STT_BACKENDS, all_down, clear=True):
            with self.assertRaises(core.VoiceError) as ctx:
                core.select_backend("stt", "auto")
        msg = str(ctx.exception)
        self.assertIn("no stt backend available", msg)
        self.assertIn("whisper-local", msg) and self.assertIn("sarvam", msg)

    def test_explicit_set_and_persistence(self):
        """/voice set persists to the plugin config; auto honors config and env
        overrides; /voice backends renders the live table."""
        self.assertEqual(core.set_backend("stt", "gemini"), "gemini")
        self.assertEqual(core.load_backend_config().get("stt_backend"), "gemini")
        with mock.patch.object(core, "_api_key", return_value=FAKE_KEY):
            self.assertEqual(core.select_backend("stt", None), "gemini")
        core.set_backend("tts", "edge")
        self.assertEqual(core.load_backend_config().get("tts_backend"), "edge")
        # env override (dotted + VOICE_FIRST_*) wins over persisted config.
        with mock.patch.dict(os.environ, {"voice_first.stt_backend": "gemini"}), \
             mock.patch.object(core, "_api_key", return_value=FAKE_KEY):
            self.assertEqual(core.select_backend("stt", None), "gemini")
        with mock.patch.dict(os.environ, {"VOICE_FIRST_STT_BACKEND": "sarvam"}):
            with self.assertRaises(core.VoiceError) as ctx:
                core.select_backend("stt", None)  # sarvam has no key -> loud
            self.assertIn("SARVAM_API_KEY", str(ctx.exception))
        # /voice commands surface the registry and persist choices.
        vf = _import_voice_first()
        table = vf._handle_voice("backends")
        self.assertIn("STT backends", table) and self.assertIn("TTS backends", table)
        self.assertIn("whisper-local", table) and self.assertIn("bhashini", table)
        self.assertIn("available", table) and self.assertIn("selected", table)
        out = vf._handle_voice("set tts gemini")  # bad name for tts
        self.assertIn("ERROR", out) and self.assertIn("gemini", out)
        out2 = vf._handle_voice("set stt sarvam")
        self.assertIn("sarvam", out2)
        self.assertEqual(core.load_backend_config().get("stt_backend"), "sarvam")

    def test_unknown_backend_loud(self):
        """Unknown backend/kind -> loud VoiceError naming the valid set; the
        /voice set handler surfaces it as a [voice] ERROR."""
        with self.assertRaises(core.VoiceError) as ctx:
            core.select_backend("stt", "bogus")
        msg = str(ctx.exception)
        self.assertIn("bogus", msg) and self.assertIn("whisper-local", msg)
        with self.assertRaises(core.VoiceError) as ctx:
            core.set_backend("tts", "bogus")
        self.assertIn("edge", str(ctx.exception))
        with self.assertRaises(core.VoiceError) as ctx:
            core.select_backend("video", "edge")
        self.assertIn("stt", str(ctx.exception))  # names the valid kinds
        vf = _import_voice_first()
        out = vf._handle_voice("set stt bogus")
        self.assertIn("[voice] ERROR", out) and self.assertIn("bogus", out)

    def test_payload_builders_all_backends(self):
        """Gemini: key by env NAME only, never the value. Sarvam/bhashini:
        payloads for all 8 bharat-pack languages. Missing keys -> loud error
        naming the env var."""
        wav = _write_fake_wav()
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": FAKE_KEY}):
            p = core.build_gemini_transcribe_payload(wav)
        self.assertEqual(p["provider"], "gemini")
        self.assertEqual(p["kind"], "stt")
        self.assertIn("generateContent", p["url"])
        self.assertEqual(p["key_env"], "GOOGLE_API_KEY")
        self.assertEqual(p["query"], {"key": "env:GOOGLE_API_KEY"})
        self.assertNotIn(FAKE_KEY, json.dumps(p))  # env NAME only, never value
        self.assertIn("inline_data", json.dumps(p["body"]))
        self.assertEqual(p["body"]["contents"][0]["parts"][1]["inline_data"]["mime_type"],
                         "audio/wav")
        # sarvam + bhashini builders cover all 8 bharat-pack languages.
        with mock.patch.dict(os.environ,
                             {"SARVAM_API_KEY": FAKE_KEY,
                              "BHASHINI_API_KEY": FAKE_KEY}):
            for lang in core.BHARAT_LANGS:
                text = "hello" if lang == "en" else "नमस्ते"
                url, headers, body = core.build_sarvam_tts_payload(text, lang)
                self.assertEqual(body["target_language_code"],
                                 core.SARVAM_LANG_CODES[lang])
                self.assertEqual(body["model"], "bulbul:v1")
                self.assertIn("api-subscription-key", headers)
                url, headers, body = core.build_sarvam_stt_payload("QUJD", lang)
                self.assertEqual(body["language_code"], core.SARVAM_LANG_CODES[lang])
                url, headers, body = core.build_bhashini_stt_payload("QUJD", lang)
                self.assertEqual(body["config"]["language"]["sourceLanguage"], lang)
                url, headers, body = core.build_bhashini_tts_payload(text, lang)
                self.assertEqual(body["config"]["language"]["targetLanguage"], lang)
                self.assertNotIn(FAKE_KEY, json.dumps(body))
        # sarvam STT accepts 'auto' language; a bad language is loud.
        with mock.patch.dict(os.environ, {"SARVAM_API_KEY": FAKE_KEY}):
            url, headers, body = core.build_sarvam_stt_payload("QUJD", "auto")
            self.assertEqual(body["language_code"], "auto")
            with self.assertRaises(core.VoiceError) as ctx:
                core.build_sarvam_tts_payload("hello", "xx")
            self.assertIn("xx", str(ctx.exception))
        # Missing keys -> loud error naming the env var (never a key value).
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(core.VoiceError) as ctx:
                core.build_sarvam_tts_payload("hello", "hi")
            self.assertIn("SARVAM_API_KEY", str(ctx.exception))
            with self.assertRaises(core.VoiceError) as ctx:
                core.build_bhashini_tts_payload("hello", "hi")
            self.assertIn("BHASHINI_API_KEY", str(ctx.exception))
            with self.assertRaises(core.VoiceError) as ctx:
                core.build_sarvam_stt_payload("QUJD", "hi")
            self.assertIn("SARVAM_API_KEY", str(ctx.exception))
            with self.assertRaises(core.VoiceError) as ctx:
                core.build_bhashini_stt_payload("QUJD", "hi")
            self.assertIn("BHASHINI_API_KEY", str(ctx.exception))


def _import_voice_first():
    """Load the plugin package, reusing the already-imported ``core`` module
    (sys.modules['voice_first.core'] = core) so mock patches on ``core`` stay
    effective inside the /voice command handler."""
    import importlib.util
    if "voice_first" in sys.modules:
        return sys.modules["voice_first"]
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.modules["voice_first.core"] = core
    spec = importlib.util.spec_from_file_location(
        "voice_first", os.path.join(parent, "__init__.py"),
        submodule_search_locations=[parent])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["voice_first"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_fake_wav() -> str:
    tmp = tempfile.mkdtemp(prefix="vf-wav-")
    path = os.path.join(tmp, "sample.wav")
    with open(path, "wb") as fh:
        fh.write(b"RIFF" + b"\x00" * 100)
    return path


if __name__ == "__main__":
    unittest.main()
