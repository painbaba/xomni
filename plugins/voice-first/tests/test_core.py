"""Tests for voice-first core (core.py) — capture, STT, TTS, session loop.

Run: cd plugins/voice-first && python -m unittest tests.test_core -q

Everything is mocked — no mic, no network, no hermes subprocess required.
Guards: fail-loud errors carry install hints; the API key never appears in
any error message or request body (it rides only in the URL query).
"""
import io
import json
import os
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


def _write_fake_wav() -> str:
    tmp = tempfile.mkdtemp(prefix="vf-wav-")
    path = os.path.join(tmp, "sample.wav")
    with open(path, "wb") as fh:
        fh.write(b"RIFF" + b"\x00" * 100)
    return path


if __name__ == "__main__":
    unittest.main()
