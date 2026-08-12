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
    # U-SURF-3: pluggable voice backend registry (STT + TTS)
    "STT_BACKENDS",
    "TTS_BACKENDS",
    "BHARAT_LANGS",
    "SARVAM_LANG_CODES",
    "SARVAM_STT_URL",
    "SARVAM_TTS_URL",
    "BHASHINI_COMPUTE_URL",
    "ENV_SARVAM",
    "ENV_BHASHINI",
    "select_backend",
    "set_backend",
    "load_backend_config",
    "save_backend_config",
    "backend_config_path",
    "render_backends_table",
    "build_gemini_transcribe_payload",
    "build_sarvam_stt_payload",
    "build_sarvam_tts_payload",
    "build_bhashini_stt_payload",
    "build_bhashini_tts_payload",
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

# --------------------------------------------------------------------------- #
# U-SURF-3: pluggable voice backends — env vars are referenced by NAME only
# (values are read via _require_key/_api_key and never echoed anywhere).
# --------------------------------------------------------------------------- #

ENV_GOOGLE = "GOOGLE_API_KEY"
ENV_GEMINI = "GEMINI_API_KEY"
ENV_SARVAM = "SARVAM_API_KEY"
ENV_BHASHINI = "BHASHINI_API_KEY"

SARVAM_STT_URL = "https://api.sarvam.ai/v1/speech_to_text"
SARVAM_TTS_URL = "https://api.sarvam.ai/v1/text_to_speech"
BHASHINI_COMPUTE_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute"
DEFAULT_BHASHINI_PIPELINE_ID = "64392f96da7b500c55a0d0a2"
SARVAM_STT_MODEL = "saaras:v1"
SARVAM_TTS_MODEL = "bulbul:v1"
SARVAM_SPEAKER = "meera"

#: The eight bharat-pack languages (plugins/bharat-pack LANGUAGES): the
#: payload builders accept exactly these codes and fail loud on anything else.
BHARAT_LANGS = ("en", "hi", "mr", "ta", "te", "kn", "gu", "bn")

#: bharat-pack lang code -> Sarvam BCP-47 target_language_code.
SARVAM_LANG_CODES = {
    "en": "en-IN", "hi": "hi-IN", "mr": "mr-IN", "ta": "ta-IN",
    "te": "te-IN", "kn": "kn-IN", "gu": "gu-IN", "bn": "bn-IN",
}

SARVAM_HINT = (
    f"Set {ENV_SARVAM} in your environment or .env to use the sarvam backend "
    "(https://www.sarvam.ai/ — see docs/BHARAT-VOICE.md)."
)
BHASHINI_HINT = (
    f"Set {ENV_BHASHINI} in your environment or .env to use the bhashini "
    "backend (https://bhashini.gov.in/ — see docs/BHARAT-VOICE.md)."
)


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
    """Transcribe ``audio_path``. ``backend``: a registry name ('whisper-local',
    'gemini', 'sarvam'), a legacy name ('whisper'/'gemini'), or None = auto."""
    if not os.path.exists(audio_path):
        raise VoiceError(f"[voice-first] stt failed: audio file not found: {audio_path}")
    if backend is None or backend in STT_BACKENDS:
        # Registry path (U-SURF-3): auto-pick honors config overrides; explicit
        # registry names fail loud when unavailable.
        name = select_backend("stt", backend)
        return STT_BACKENDS[name]["transcribe"](audio_path)
    # Legacy names ('whisper' / 'gemini') — backward-compatible dispatch.
    name = detect_stt_backend(backend)
    if name == "whisper":
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


def _tts_edge(text: str, out_path: str, voice: str | None = None, timeout: float = 180) -> str:
    """edge-tts CLI synthesize (TTS_BACKENDS['edge']). Fail-loud."""
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
# U-SURF-3: pluggable voice backend registry
#
# STT_BACKENDS = {'whisper-local', 'gemini', 'sarvam'}
# TTS_BACKENDS = {'edge', 'sarvam', 'bhashini'}
#
# Every entry: {name, kind, available() -> bool (local binary/key check, NO
# network), transcribe(audio_path) | synthesize(text, out_path), priority,
# hint}. select_backend(kind, name|'auto') picks explicitly or auto-picks the
# first available in priority order, honoring config overrides:
#   env  VOICE_FIRST_STT_BACKEND / VOICE_FIRST_TTS_BACKEND  (or the dotted
#        voice_first.stt_backend / voice_first.tts_backend forms)
#   json <plugin>/.voice_first.json persisted by /voice set stt|tts <name>.
# Payload builders never embed key values: headers reference the env-var NAME
# (e.g. "env:SARVAM_API_KEY"); the live call path injects the value. Calling a
# builder without the required key set is a loud VoiceError naming the env var.
# --------------------------------------------------------------------------- #

def _post_json(url: str, headers: dict, body: dict,
               urlopen=urllib.request.urlopen, timeout: float = 60) -> dict:
    """POST JSON, parse the JSON response, wrap failures fail-loud."""
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers=headers, method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        raise VoiceError(
            f"[voice-first] {url} HTTP {exc.code} — {detail or exc.reason}. "
            "Fix: check the API key, endpoint availability, and quota."
        ) from exc
    except urllib.error.URLError as exc:
        raise VoiceError(
            f"[voice-first] {url} unreachable: {exc.reason}. "
            "Fix: check connectivity and that the endpoint is reachable."
        ) from exc
    except OSError as exc:
        raise VoiceError(f"[voice-first] {url} error: {exc}")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise VoiceError(f"[voice-first] {url} returned invalid JSON.") from exc


def _key_present(name: str) -> bool:
    """True iff the env var ``name`` is set (after .env loading). No network."""
    _load_env_files()
    return bool(os.environ.get(name, "").strip())


def _require_key(name: str) -> str:
    """Read ``name``; fail loud naming the env var and the fix when absent."""
    _load_env_files()
    value = os.environ.get(name, "").strip()
    if not value:
        raise VoiceError(
            f"[voice-first] {name} is not set. Fix: add {name}=<your-key> to "
            "your environment or .env (see docs/BHARAT-VOICE.md)."
        )
    return value


def _inject_key(headers: dict, env_name: str, api_key: str | None) -> dict:
    """Replace the ``env:<NAME>`` header placeholders with the real key value."""
    key = api_key or _require_key(env_name)
    out = dict(headers)
    for k, v in out.items():
        if v == f"env:{env_name}":
            out[k] = key
    return out


def _bharat_lang(lang: str) -> str:
    """Validate against the 8 bharat-pack languages; fail loud otherwise."""
    lang = (lang or "").strip().lower()
    if lang not in BHARAT_LANGS:
        raise VoiceError(
            f"[voice-first] unsupported language {lang!r}. Fix: use one of "
            f"{', '.join(BHARAT_LANGS)} (the bharat-pack language set)."
        )
    return lang


def _sarvam_code(lang: str, allow_auto: bool = False) -> str:
    """bharat-pack code -> Sarvam BCP-47 code ('auto' allowed for STT)."""
    if allow_auto and (lang or "").strip().lower() == "auto":
        return "auto"
    return SARVAM_LANG_CODES[_bharat_lang(lang)]


# --- payload builders (dry-run shape; keys by env NAME only) -----------------

def build_gemini_transcribe_payload(audio_path: str, key_env: str = ENV_GOOGLE) -> dict:
    """Dry-run Gemini STT payload shape. The key is referenced by env-var NAME
    only — the value is never read, embedded, or printed by this function."""
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
    return {
        "provider": "gemini",
        "kind": "stt",
        "method": "POST",
        "url": GEMINI_URL.format(model=GEMINI_MODEL),
        "key_env": key_env,  # env-var NAME only — never the value
        "query": {"key": f"env:{key_env}"},
        "body": body,
    }


def build_sarvam_stt_payload(audio_b64: str, lang: str = "auto",
                             api_key_env: str = ENV_SARVAM,
                             api_key: str | None = None):
    """``(url, headers, body)`` for Sarvam ``saaras:v1`` speech-to-text.

    ``lang``: one of BHARAT_LANGS or 'auto'. Fails loud (naming
    ``SARVAM_API_KEY``) when the key is absent and none is passed.
    """
    if api_key is None:
        _require_key(api_key_env)
    code = _sarvam_code(lang, allow_auto=True)
    headers = {"api-subscription-key": f"env:{api_key_env}",
               "Content-Type": "application/json"}
    body = {
        "audio": {"audio_content": audio_b64, "sample_rate": 16000, "encoding": "wav"},
        "model": SARVAM_STT_MODEL,
        "language_code": code,
    }
    return SARVAM_STT_URL, headers, body


def build_sarvam_tts_payload(text: str, lang: str,
                             api_key_env: str = ENV_SARVAM,
                             api_key: str | None = None):
    """``(url, headers, body)`` for Sarvam ``bulbul:v1`` TTS (speaker meera).

    Fails loud (naming ``SARVAM_API_KEY``) when the key is absent.
    """
    if api_key is None:
        _require_key(api_key_env)
    code = _sarvam_code(lang)
    headers = {"api-subscription-key": f"env:{api_key_env}",
               "Content-Type": "application/json"}
    body = {
        "model": SARVAM_TTS_MODEL,
        "inputs": [str(text)],
        "target_language_code": code,
        "speaker": SARVAM_SPEAKER,
    }
    return SARVAM_TTS_URL, headers, body


def build_bhashini_stt_payload(audio_b64: str, lang: str,
                               api_key_env: str = ENV_BHASHINI,
                               api_key: str | None = None,
                               pipeline_id: str | None = None):
    """``(url, headers, body)`` for Bhashini (MeitY ULCA) ASR.

    Fails loud (naming ``BHASHINI_API_KEY``) when the key is absent.
    """
    if api_key is None:
        _require_key(api_key_env)
    _bharat_lang(lang)
    headers = {"Authorization": f"Bearer env:{api_key_env}",
               "Content-Type": "application/json"}
    body = {
        "pipelineId": (pipeline_id or os.environ.get("BHASHINI_PIPELINE_ID")
                       or DEFAULT_BHASHINI_PIPELINE_ID),
        "input": [{"source": "audio",
                   "audio": [{"audioContent": audio_b64, "audioSource": "base64"}]}],
        "config": {"language": {"sourceLanguage": lang}},
    }
    return BHASHINI_COMPUTE_URL, headers, body


def build_bhashini_tts_payload(text: str, lang: str,
                               api_key_env: str = ENV_BHASHINI,
                               api_key: str | None = None,
                               pipeline_id: str | None = None):
    """``(url, headers, body)`` for Bhashini (MeitY ULCA) TTS.

    Fails loud (naming ``BHASHINI_API_KEY``) when the key is absent.
    """
    if api_key is None:
        _require_key(api_key_env)
    _bharat_lang(lang)
    headers = {"Authorization": f"Bearer env:{api_key_env}",
               "Content-Type": "application/json"}
    body = {
        "pipelineId": (pipeline_id or os.environ.get("BHASHINI_PIPELINE_ID")
                       or DEFAULT_BHASHINI_PIPELINE_ID),
        "input": [{"source": "text", "text": [{"input": str(text)}]}],
        "config": {"language": {"sourceLanguage": lang, "targetLanguage": lang}},
    }
    return BHASHINI_COMPUTE_URL, headers, body


# --- live backend implementations --------------------------------------------

def _stt_sarvam(audio_path: str) -> str:
    """Sarvam speech-to-text (auto language unless VOICE_SARVAM_LANG set)."""
    with open(audio_path, "rb") as fh:
        audio_b64 = base64.b64encode(fh.read()).decode("ascii")
    lang = os.environ.get("VOICE_SARVAM_LANG", "auto")
    url, headers, body = build_sarvam_stt_payload(audio_b64, lang)
    headers = _inject_key(headers, ENV_SARVAM, None)
    resp = _post_json(url, headers, body)
    text = resp.get("transcript") if isinstance(resp, dict) else None
    if not text:
        raise VoiceError(
            "[voice-first] stt failed: sarvam returned no transcript. "
            f"Fix: check {ENV_SARVAM} and the audio format (16 kHz wav)."
        )
    return str(text).strip()


def _stt_bhashini(audio_path: str) -> str:
    """Bhashini ASR via the MeitY ULCA model gateway."""
    with open(audio_path, "rb") as fh:
        audio_b64 = base64.b64encode(fh.read()).decode("ascii")
    lang = os.environ.get("VOICE_BHASHINI_LANG", "hi")
    url, headers, body = build_bhashini_stt_payload(audio_b64, lang)
    headers = _inject_key(headers, ENV_BHASHINI, None)
    resp = _post_json(url, headers, body)
    try:
        text = resp["output"][0]["audio"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise VoiceError(
            "[voice-first] stt failed: bhashini response missing "
            "'output[0].audio[0].text'. Fix: check BHASHINI_PIPELINE_ID and the audio format."
        )
    if not text:
        raise VoiceError("[voice-first] stt failed: bhashini returned an empty transcript.")
    return str(text).strip()


def _tts_sarvam(text: str, out_path: str, voice: str | None = None,
                timeout: float = 180) -> str:
    """Sarvam TTS (bulbul:v1, speaker meera). ``voice`` maps to the speaker."""
    lang = os.environ.get("VOICE_SARVAM_LANG",
                          "hi" if _NON_ASCII.search(text) else "en")
    url, headers, body = build_sarvam_tts_payload(text, lang)
    if voice:
        body = dict(body, speaker=voice)
    headers = _inject_key(headers, ENV_SARVAM, None)
    resp = _post_json(url, headers, body, timeout=timeout)
    audio_b64 = resp.get("audio") if isinstance(resp, dict) else None
    if not audio_b64:
        raise VoiceError(
            "[voice-first] tts failed: sarvam response missing 'audio'. "
            f"Fix: check {ENV_SARVAM} and the language code."
        )
    with open(out_path, "wb") as fh:
        fh.write(base64.b64decode(audio_b64))
    return out_path


def _tts_bhashini(text: str, out_path: str, voice: str | None = None,
                  timeout: float = 180) -> str:
    """Bhashini TTS via the MeitY ULCA model gateway."""
    lang = os.environ.get("VOICE_BHASHINI_LANG",
                          "hi" if _NON_ASCII.search(text) else "en")
    url, headers, body = build_bhashini_tts_payload(text, lang)
    headers = _inject_key(headers, ENV_BHASHINI, None)
    resp = _post_json(url, headers, body, timeout=timeout)
    try:
        audio_b64 = resp["output"][0]["audio"][0]["audioContent"]
    except (KeyError, IndexError, TypeError):
        raise VoiceError(
            "[voice-first] tts failed: bhashini response missing "
            "'output[0].audio[0].audioContent'. Fix: check BHASHINI_PIPELINE_ID and the text payload."
        )
    with open(out_path, "wb") as fh:
        fh.write(base64.b64decode(audio_b64))
    return out_path


# --- the registries ------------------------------------------------------------

STT_BACKENDS: dict = {
    "whisper-local": {
        "name": "whisper-local", "kind": "stt",
        "available": _whisper_importable,
        "transcribe": _stt_whisper,
        "priority": 1,
        "hint": WHISPER_HINT,
    },
    "gemini": {
        "name": "gemini", "kind": "stt",
        "available": lambda: bool(_api_key()),
        "transcribe": _stt_gemini,
        "priority": 2,
        "hint": GEMINI_HINT,
    },
    "sarvam": {
        "name": "sarvam", "kind": "stt",
        "available": lambda: _key_present(ENV_SARVAM),
        "transcribe": _stt_sarvam,
        "priority": 3,
        "hint": SARVAM_HINT,
    },
}

TTS_BACKENDS: dict = {
    "edge": {
        "name": "edge", "kind": "tts",
        "available": lambda: _find_tts_binary() is not None,
        "synthesize": _tts_edge,
        "priority": 1,
        "hint": ("Install edge-tts: `pip install edge-tts` (if using the Hermes "
                 "venv: `<hermes venv>/Scripts/pip install edge-tts`)."),
    },
    "sarvam": {
        "name": "sarvam", "kind": "tts",
        "available": lambda: _key_present(ENV_SARVAM),
        "synthesize": _tts_sarvam,
        "priority": 2,
        "hint": SARVAM_HINT,
    },
    "bhashini": {
        "name": "bhashini", "kind": "tts",
        "available": lambda: _key_present(ENV_BHASHINI),
        "synthesize": _tts_bhashini,
        "priority": 3,
        "hint": BHASHINI_HINT,
    },
}


def _registry(kind: str) -> dict:
    if kind == "stt":
        return STT_BACKENDS
    if kind == "tts":
        return TTS_BACKENDS
    raise VoiceError(
        f"[voice-first] unknown backend kind {kind!r}. Fix: use 'stt' or 'tts'."
    )


# --- selection + persistence -----------------------------------------------------

def backend_config_path() -> str:
    """Plugin config file where /voice set persists the backend choice."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        ".voice_first.json")


def load_backend_config() -> dict:
    """Persisted backend choices: ``{"stt_backend": ..., "tts_backend": ...}``."""
    try:
        with open(backend_config_path(), encoding="utf-8") as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def save_backend_config(cfg: dict) -> None:
    with open(backend_config_path(), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


def _configured_backend(kind: str) -> str | None:
    """Config override for ``kind``: env (dotted or VOICE_FIRST_*) then the
    persisted JSON. Returns None when nothing is configured (=> auto)."""
    _load_env_files()
    for env_name in (f"voice_first.{kind}_backend",
                     f"VOICE_FIRST_{kind.upper()}_BACKEND"):
        val = os.environ.get(env_name, "").strip()
        if val:
            return val
    return load_backend_config().get(f"{kind}_backend") or None


def select_backend(kind: str, name: str | None = None) -> str:
    """Pick a backend: explicit ``name``, else config override, else 'auto'.

    ``auto`` returns the first available backend in priority order
    (whisper-local -> gemini -> sarvam for STT; edge -> sarvam -> bhashini for
    TTS). Unknown names and unavailable-but-requested backends are loud
    VoiceErrors naming the valid set / the missing piece.
    """
    registry = _registry(kind)
    if name is None or name == "auto":
        name = _configured_backend(kind) or "auto"
    if name == "auto":
        for bname, entry in registry.items():  # insertion order = priority
            try:
                if entry["available"]():
                    return bname
            except VoiceError:
                continue
        lines = [f"[voice-first] no {kind} backend available. Fix one of:"]
        for bname, entry in registry.items():
            lines.append(f"  {bname}: {entry['hint']}")
        raise VoiceError("\n".join(lines))
    if name not in registry:
        raise VoiceError(
            f"[voice-first] unknown {kind} backend {name!r}. Fix: use one of "
            f"{', '.join(registry)} (or 'auto')."
        )
    try:
        available = registry[name]["available"]()
    except VoiceError:
        available = False
    if not available:
        raise VoiceError(
            f"[voice-first] {kind} backend {name!r} requested but unavailable. "
            f"{registry[name]['hint']}"
        )
    return name


def set_backend(kind: str, name: str) -> str:
    """Persist an explicit backend choice (``/voice set stt|tts <name>``).

    Unknown kind or backend -> loud VoiceError; nothing is written.
    """
    registry = _registry(kind)
    if name not in registry:
        raise VoiceError(
            f"[voice-first] unknown {kind} backend {name!r}. Fix: use one of "
            f"{', '.join(registry)} (or 'auto')."
        )
    cfg = load_backend_config()
    cfg[f"{kind}_backend"] = name
    save_backend_config(cfg)
    return name


def tts(text: str, out_path: str, voice: str | None = None,
        backend: str | None = None, timeout: float = 180) -> str:
    """Speak ``text`` into ``out_path`` via the selected TTS backend
    ('edge' | 'sarvam' | 'bhashini' | None = auto). Fail-loud."""
    text = str(text).strip()
    if not text:
        raise VoiceError("[voice-first] tts failed: empty text")
    name = select_backend("tts", backend)
    return TTS_BACKENDS[name]["synthesize"](text, out_path, voice=voice,
                                            timeout=timeout)


def render_backends_table() -> str:
    """``/voice backends`` table: kind, name, available, selected (no network)."""
    lines = ["[voice-first] voice backend registry "
             "(available = binary/key present locally, no network):"]
    for kind, registry in (("stt", STT_BACKENDS), ("tts", TTS_BACKENDS)):
        try:
            selected = select_backend(kind, None)
        except VoiceError:
            selected = None
        lines.append(f"  {kind.upper()} backends:")
        lines.append(f"    {'name':<14} {'available':<10} selected")
        for bname, entry in registry.items():
            try:
                ok = bool(entry["available"]())
            except Exception:
                ok = False
            mark = "*" if bname == selected else "-"
            lines.append(f"    {bname:<14} {'yes' if ok else 'no':<10} {mark}")
    return "\n".join(lines)


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
