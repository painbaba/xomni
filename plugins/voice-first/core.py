"""voice-first core — optional hands-free voice mode for the Hermes CLI.

U10. Pure stdlib, zero hooks, fail-loud everywhere.

Pipeline: mic capture (ffmpeg dshow on Windows / arecord on POSIX) -> STT
(faster-whisper, or openai-whisper, or Gemini via the Google AI Studio REST
API) -> host round-trip (``hermes chat -q``) -> TTS (edge-tts CLI) -> repeat
in a session loop until the user (or the host) says "stop" or turns run out.

Fail-loud contract (per U3): every failure raises :class:`VoiceError` with an
explicit message that names the missing piece AND how to install/fix it.
Nothing is silently swallowed. API keys are read from the environment or the
user's ``.env`` files and are NEVER printed, logged, or included in error
messages (guarded by tests).
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

__all__ = [
    "VoiceError",
    "build_capture_cmd",
    "capture_audio",
    "detect_windows_mic",
    "detect_stt_backend",
    "stt",
    "build_tts_cmd",
    "tts",
    "pick_voice",
    "ask_host",
    "voice_session",
    "render_session",
    "is_stop",
    "_api_key",
]

_IS_WIN = sys.platform == "win32"

DEFAULT_MIC = "Microphone"                      # ffmpeg dshow fallback device name
WHISPER_MODEL = os.environ.get("VOICE_WHISPER_MODEL", "base")
TTS_DEFAULT_VOICE = "en-IN-PrabhatNeural"       # English (India) — default
TTS_HINDI_VOICE = "hi-IN-PrabhatNeural"         # Hindi (India) — bharat langs
GEMINI_MODEL = os.environ.get("VOICE_GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

WHISPER_HINT = (
    "Install a whisper runtime: `pip install faster-whisper` (recommended, "
    "CTranslate2, ~fast on CPU) or `pip install openai-whisper`."
)
GEMINI_HINT = (
    "Set GOOGLE_API_KEY (or GEMINI_API_KEY) in your environment or ~/.env "
    "to use the gemini STT backend (https://aistudio.google.com/apikey)."
)

STOP_RE = re.compile(r"\bstop\b", re.IGNORECASE)
_NON_ASCII = re.compile(r"[^\x00-\x7f]")


class VoiceError(Exception):
    """Fail-loud error: message names the failure AND the fix. Never silent."""


# --------------------------------------------------------------------------- #
# .env loading (keys only — values are never echoed anywhere)
# --------------------------------------------------------------------------- #

def _load_env_files() -> None:
    """Load KEY=VALUE lines from the user's .env candidates into os.environ.

    Only sets keys that are not already present (real env wins). Values are
    read into memory and never printed. Candidate order: repo root .env,
    plugin .env, ~/.env, ~/terminator/.env (machine-specific fallback).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(here, "..", "..", ".env"),      # <repo>/.env
        os.path.join(here, ".env"),                   # plugin-local .env
        os.path.join(home, ".env"),
        os.path.join(home, "terminator", ".env"),
    ]
    for path in candidates:
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except OSError:
            continue


def _api_key() -> str | None:
    """GOOGLE_API_KEY (spec) or GEMINI_API_KEY (machine reality). Never printed."""
    _load_env_files()
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or None


# --------------------------------------------------------------------------- #
# Capture: ffmpeg dshow (Windows) / arecord (POSIX)
# --------------------------------------------------------------------------- #

def detect_windows_mic(timeout: int = 15) -> str:
    """First dshow '(audio)' device via ``ffmpeg -list_devices``; else DEFAULT_MIC."""
    cmd = ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return DEFAULT_MIC
    blob = (proc.stdout or "") + (proc.stderr or "")
    match = re.search(r'"([^"]+)"\s+\(audio\)', blob)
    return match.group(1) if match else DEFAULT_MIC


def build_capture_cmd(duration_s: float, out_path: str, backend: str | None = None,
                      device: str | None = None) -> list[str]:
    """argv for mic capture: ffmpeg dshow (windows) or arecord (posix).

    ``backend``: 'windows' | 'posix' (auto by platform when None).
    ``device``:  explicit dshow device name; auto-detected when None (win).
    """
    backend = backend or ("windows" if _IS_WIN else "posix")
    if backend == "windows":
        dev = device or detect_windows_mic()
        return [
            "ffmpeg", "-y", "-f", "dshow", "-i", f"audio={dev}",
            "-t", str(int(duration_s)), "-ac", "1", "-ar", "16000", out_path,
        ]
    return [
        "arecord", "-d", str(int(duration_s)),
        "-f", "S16_LE", "-r", "16000", "-c", "1", out_path,
    ]


def capture_audio(duration_s: float, out_path: str, backend: str | None = None,
                  timeout: float | None = None) -> str:
    """Record ``duration_s`` seconds of mic audio to ``out_path``. Fail-loud."""
    backend = backend or ("windows" if _IS_WIN else "posix")
    if backend == "windows":
        binary = shutil.which("ffmpeg")
        if not binary:
            raise VoiceError(
                "[voice-first] capture failed: ffmpeg not found on PATH. Install it — "
                "Windows: `winget install ffmpeg` or https://ffmpeg.org/download.html; "
                "macOS: `brew install ffmpeg`; Debian/Ubuntu: `sudo apt install ffmpeg`."
            )
        hint = "is a microphone plugged in / enabled in Windows sound settings?"
    else:
        binary = shutil.which("arecord")
        if not binary:
            raise VoiceError(
                "[voice-first] capture failed: arecord not found (ALSA utils). Install — "
                "Debian/Ubuntu: `sudo apt install alsa-utils`; Arch: `sudo pacman -S alsa-utils`; "
                "macOS: `brew install portaudio`."
            )
        hint = "is a microphone plugged in / unmuted?"
    cmd = build_capture_cmd(duration_s, out_path, backend=backend)
    cmd[0] = binary
    timeout = timeout or max(int(duration_s) + 15, 20)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise VoiceError(
            f"[voice-first] capture failed: {cmd[0]} timed out after {timeout}s — {hint}"
        )
    except FileNotFoundError:
        raise VoiceError(f"[voice-first] capture failed: {cmd[0]} could not be executed — {hint}")
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        detail = "; ".join(tail) if tail else "no output"
        raise VoiceError(
            f"[voice-first] capture failed: {cmd[0]} exited rc={proc.returncode} ({detail}) — {hint}"
        )
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise VoiceError(
            f"[voice-first] capture failed: {cmd[0]} exited 0 but produced no audio at {out_path} — {hint}"
        )
    return out_path


# --------------------------------------------------------------------------- #
# STT: faster-whisper / openai-whisper / Gemini
# --------------------------------------------------------------------------- #

def _whisper_importable() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import whisper  # noqa: F401
        return True
    except ImportError:
        return False


def detect_stt_backend(preferred: str | None = None) -> str:
    """Pick the STT backend: 'whisper' | 'gemini'. Explicit preference honored; any
    unavailable requested backend or a totally empty toolbox is a loud error."""
    if preferred == "whisper":
        if _whisper_importable():
            return "whisper"
        raise VoiceError(f"[voice-first] stt failed: whisper requested but not importable. {WHISPER_HINT}")
    if preferred == "gemini":
        if _api_key():
            return "gemini"
        raise VoiceError(f"[voice-first] stt failed: gemini requested but no API key. {GEMINI_HINT}")
    if _whisper_importable():
        return "whisper"
    if _api_key():
        return "gemini"
    raise VoiceError(
        f"[voice-first] stt failed: no STT backend available — {WHISPER_HINT} {GEMINI_HINT}"
    )


def _stt_whisper(audio_path: str) -> str:
    model_size = os.environ.get("VOICE_WHISPER_MODEL", WHISPER_MODEL)
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(audio_path)
        text = "".join(seg.text for seg in segments).strip()
    except ImportError:
        try:
            import whisper  # openai-whisper fallback
            result = whisper.load_model(model_size).transcribe(audio_path)
            text = (result.get("text") or "").strip()
        except ImportError:
            raise VoiceError(f"[voice-first] stt failed: no whisper runtime importable. {WHISPER_HINT}")
        except Exception as exc:  # model download / load / inference
            raise VoiceError(f"[voice-first] stt failed: whisper ({model_size}) error: {exc}")
    except Exception as exc:
        raise VoiceError(f"[voice-first] stt failed: faster-whisper ({model_size}) error: {exc}")
    if not text:
        raise VoiceError("[voice-first] stt failed: whisper returned an empty transcript (silent or corrupt audio?)")
    return text


def _gemini_mime(path: str) -> str:
    return "audio/wav" if path.lower().endswith(".wav") else "audio/mpeg"


def _gemini_request(audio_path: str, key: str):
    """Build the generateContent POST. The key rides ONLY in the URL query —
    never in the JSON body, never in any error we raise."""
    with open(audio_path, "rb") as fh:
        data = base64.b64encode(fh.read()).decode("ascii")
    body = {
        "contents": [{
            "parts": [
                {"text": "Transcribe the audio verbatim. Reply with only the transcript, no commentary."},
                {"inline_data": {"mime_type": _gemini_mime(audio_path), "data": data}},
            ],
        }],
    }
    url = GEMINI_URL.format(model=GEMINI_MODEL) + "?key=" + key
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    return req


def _stt_gemini(audio_path: str) -> str:
    key = _api_key()
    if not key:
        raise VoiceError(f"[voice-first] stt failed: gemini backend has no key. {GEMINI_HINT}")
    try:
        req = _gemini_request(audio_path, key)
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise VoiceError(
            f"[voice-first] stt failed: gemini API HTTP {exc.code}"
            + (f" — {detail}" if detail else "")
        )
    except urllib.error.URLError as exc:
        raise VoiceError(f"[voice-first] stt failed: gemini API unreachable: {exc.reason}")
    except OSError as exc:
        raise VoiceError(f"[voice-first] stt failed: gemini API error: {exc}")
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError):
        raise VoiceError(
            f"[voice-first] stt failed: unexpected gemini response: {json.dumps(payload)[:300]}"
        )
    if not text:
        raise VoiceError("[voice-first] stt failed: gemini returned an empty transcript (silent or corrupt audio?)")
    return text


def stt(audio_path: str, backend: str | None = None) -> str:
    """Transcribe ``audio_path``. ``backend``: 'whisper' | 'gemini' | auto."""
    if not os.path.exists(audio_path):
        raise VoiceError(f"[voice-first] stt failed: audio file not found: {audio_path}")
    backend = detect_stt_backend(backend)
    if backend == "whisper":
        return _stt_whisper(audio_path)
    return _stt_gemini(audio_path)


# --------------------------------------------------------------------------- #
# TTS: edge-tts CLI
# --------------------------------------------------------------------------- #

def pick_voice(text: str) -> str:
    """hi-IN for bharat (non-ASCII) text, en-IN default otherwise."""
    return TTS_HINDI_VOICE if _NON_ASCII.search(text or "") else TTS_DEFAULT_VOICE


def _find_tts_binary() -> str | None:
    found = shutil.which("edge-tts")
    if found:
        return found
    exe_dir = os.path.dirname(sys.executable)
    for name in ("edge-tts", "edge-tts.exe", "edge-tts.cmd", "edge-tts.bat"):
        probe = os.path.join(exe_dir, name)
        if os.path.exists(probe):
            return probe
    base = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes",
                        "hermes-agent", "venv", "Scripts", "edge-tts")
    for suffix in ("", ".exe", ".cmd"):
        if os.path.exists(base + suffix):
            return base + suffix
    return None


def build_tts_cmd(text: str, out_path: str, voice: str | None = None) -> list[str]:
    return ["edge-tts", "--voice", voice or pick_voice(text),
            "--text", text, "--write-media", out_path]


def tts(text: str, out_path: str, voice: str | None = None, timeout: float = 180) -> str:
    """Speak ``text`` into an mp3 at ``out_path`` via the edge-tts CLI. Fail-loud."""
    text = str(text).strip()
    if not text:
        raise VoiceError("[voice-first] tts failed: empty text")
    binary = _find_tts_binary()
    if not binary:
        raise VoiceError(
            "[voice-first] tts failed: edge-tts CLI not found. Install: "
            "`pip install edge-tts` (if using the Hermes venv: "
            "`<hermes venv>/Scripts/pip install edge-tts`)."
        )
    cmd = build_tts_cmd(text, out_path, voice=voice)
    cmd[0] = binary
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise VoiceError(f"[voice-first] tts failed: edge-tts timed out after {timeout}s")
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        detail = "; ".join(tail) if tail else "no output"
        raise VoiceError(f"[voice-first] tts failed: edge-tts exited rc={proc.returncode} ({detail})")
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise VoiceError(f"[voice-first] tts failed: edge-tts exited 0 but produced no audio at {out_path}")
    return out_path


# --------------------------------------------------------------------------- #
# Host round-trip + session loop
# --------------------------------------------------------------------------- #

def _find_hermes() -> str | None:
    found = shutil.which("hermes")
    if found:
        return found
    exe_dir = os.path.dirname(sys.executable)
    for name in ("hermes", "hermes.exe", "hermes.cmd"):
        probe = os.path.join(exe_dir, name)
        if os.path.exists(probe):
            return probe
    base = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes",
                        "hermes-agent", "venv", "Scripts", "hermes")
    for suffix in ("", ".exe", ".cmd"):
        if os.path.exists(base + suffix):
            return base + suffix
    return None


def ask_host(prompt: str, hermes_home: str | None = None, timeout: float = 600) -> str:
    """One host round-trip: ``hermes chat -q <prompt>``. Fail-loud."""
    prompt = str(prompt).strip()
    if not prompt:
        raise VoiceError("[voice-first] session failed: empty prompt for host")
    binary = _find_hermes()
    if not binary:
        raise VoiceError(
            "[voice-first] session failed: hermes CLI not found on PATH or next to this "
            "python. Reinstall Hermes Agent to restore it."
        )
    env = dict(os.environ)
    if hermes_home:
        env["HERMES_HOME"] = hermes_home
    cmd = [binary, "chat", "-q", prompt]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise VoiceError(
            f"[voice-first] session failed: hermes chat timed out after {timeout}s "
            f"(prompt was {prompt[:60]!r})"
        )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
        detail = "; ".join(tail) if tail else "no output"
        raise VoiceError(f"[voice-first] session failed: hermes chat exited rc={proc.returncode} ({detail})")
    out = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    if not out:
        raise VoiceError("[voice-first] session failed: hermes chat returned an empty reply")
    return out


def is_stop(text: str) -> bool:
    """Session end-word: case-insensitive word 'stop'."""
    return bool(STOP_RE.search(text or ""))


def voice_session(turns: int = 5, duration_s: float = 4, backend: str | None = None,
                  out_dir: str | None = None, hermes_home: str | None = None,
                  on_event=None) -> list[dict]:
    """Hands-free loop: listen -> stt -> host -> tts, until 'stop' or turns run out.

    Every step fail-loud: a :class:`VoiceError` from capture/stt/host/tts
    propagates immediately (nothing is swallowed). Events are appended to a
    list (and optionally streamed to ``on_event``) for logging/tests.
    """
    turns = max(1, int(turns))
    out_dir = out_dir or tempfile.mkdtemp(prefix="voice-first-")
    os.makedirs(out_dir, exist_ok=True)
    events: list[dict] = []

    def emit(event: dict) -> None:
        events.append(event)
        if on_event is not None:
            on_event(event)

    for i in range(turns):
        wav = os.path.join(out_dir, f"turn{i:02d}.wav")
        emit({"event": "capture", "turn": i, "path": wav})
        capture_audio(duration_s, wav)
        text = stt(wav, backend=backend)
        emit({"event": "transcript", "turn": i, "text": text})
        if is_stop(text):
            emit({"event": "stop", "turn": i, "reason": "user said stop"})
            return events
        reply = ask_host(text, hermes_home=hermes_home)
        emit({"event": "reply", "turn": i, "text": reply})
        if is_stop(reply):
            emit({"event": "stop", "turn": i, "reason": "host said stop"})
            return events
        mp3 = os.path.join(out_dir, f"reply{i:02d}.mp3")
        tts(reply, mp3)
        emit({"event": "tts", "turn": i, "path": mp3})
    emit({"event": "stop", "reason": "turns exhausted"})
    return events


def render_session(events: list[dict]) -> str:
    """Human-readable session log for the /voice on command output."""
    lines = ["[voice-first] session log:"]
    for ev in events:
        turn = ev.get("turn")
        tag = f"turn {turn}" if turn is not None else "-----"
        kind = ev["event"]
        if kind == "capture":
            lines.append(f"  {tag} captured -> {ev['path']}")
        elif kind == "transcript":
            lines.append(f"  {tag} heard: {ev['text']}")
        elif kind == "reply":
            lines.append(f"  {tag} host: {ev['text']}")
        elif kind == "tts":
            lines.append(f"  {tag} spoken -> {ev['path']}")
        elif kind == "stop":
            lines.append(f"  {tag} stop: {ev['reason']}")
    return "\n".join(lines)
