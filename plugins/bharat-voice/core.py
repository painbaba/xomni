"""bharat-voice core — voice-native Bharat TTS/STT via Sarvam + Bhashini REST.

M3. Hindi + 5 regional languages (ta, te, kn, mr, gu) text-to-speech and
speech-to-text through two India-resident providers:

* Sarvam AI — ``POST https://api.sarvam.ai/v1/text_to_speech`` (TTS, bulbul:v1,
  speaker meera). Key from ``SARVAM_API_KEY``.
* Bhashini  — ``POST https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute``
  (MeitY ULCA model gateway; ASR/TTS routed by pipeline id from
  ``BHASHINI_PIPELINE_ID``, default ``64392f96da7b500c55a0d0a2``). Key from
  ``BHASHINI_API_KEY``.

Pure stdlib (urllib.request / json / base64 / os). Zero hooks. Fail-loud:
every failure raises :class:`BharatVoiceError` naming the missing piece AND
the fix. API keys are read from the environment and are NEVER printed,
logged, or included in error messages (guarded by tests).
"""
from __future__ import annotations

import base64
import json
import os

__all__ = [
    "BharatVoiceError",
    "LANGS",
    "SARVAM_TTS_URL",
    "BHASHINI_COMPUTE_URL",
    "DEFAULT_BHASHINI_PIPELINE_ID",
    "available_engines",
    "pick_engine",
    "build_sarvam_tts_payload",
    "sarvam_tts",
    "build_bhashini_stt_payload",
    "bhashini_stt",
    "build_bhashini_tts_payload",
    "bhashini_tts",
    "render_convo",
]

#: The six supported languages: Hindi + 5 regional (Dravidian + Marathi + Gujarati).
LANGS = {
    "hi": {"name": "Hindi", "sarvam_code": "hi-IN", "script": "Devanagari"},
    "ta": {"name": "Tamil", "sarvam_code": "ta-IN", "script": "Tamil"},
    "te": {"name": "Telugu", "sarvam_code": "te-IN", "script": "Telugu"},
    "kn": {"name": "Kannada", "sarvam_code": "kn-IN", "script": "Kannada"},
    "mr": {"name": "Marathi", "sarvam_code": "mr-IN", "script": "Devanagari"},
    "gu": {"name": "Gujarati", "sarvam_code": "gu-IN", "script": "Gujarati"},
}

SARVAM_TTS_URL = "https://api.sarvam.ai/v1/text_to_speech"
BHASHINI_COMPUTE_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute"
DEFAULT_BHASHINI_PIPELINE_ID = "64392f96da7b500c55a0d0a2"

_ENV_DOC = "see docs/BHARAT-VOICE.md"


class BharatVoiceError(Exception):
    """Fail-loud error: the message names the missing key/endpoint AND the fix.

    API keys never appear in these messages — by construction (they are only
    read from the environment and placed in headers) and by test guard.
    """


# ---------------------------------------------------------------------------
# Key handling (key-safe: the value is never echoed anywhere)
# ---------------------------------------------------------------------------

def _api_key(name: str) -> str:
    """Read ``name`` from the environment; fail loud (naming the var + fix) if absent."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise BharatVoiceError(
            f"Missing API key: environment variable {name} is not set. "
            f"Fix: add '{name}=<your-key>' to your environment / .env file "
            f"({_ENV_DOC})."
        )
    return value


def _lang_code(lang: str) -> str:
    """Validate ``lang`` against LANGS and return its Sarvam BCP-47 code."""
    info = LANGS.get(lang)
    if info is None:
        raise BharatVoiceError(
            f"Unsupported language '{lang}'. Fix: use one of "
            f"{', '.join(sorted(LANGS))} (Hindi + 5 regional: ta, te, kn, mr, gu)."
        )
    return info["sarvam_code"]


def _server_message(resp: dict) -> str:
    """Extract a human-readable message from a provider error response."""
    if not isinstance(resp, dict):
        return str(resp)
    err = resp.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)
    return str(err) if err else ""


# ---------------------------------------------------------------------------
# HTTP plumbing (injectable urlopen; urllib errors wrapped fail-loud)
# ---------------------------------------------------------------------------

def _post_json(url: str, headers: dict, body: dict, urlopen) -> dict:
    """POST JSON to ``url``, return the parsed JSON response, fail loud."""
    # Lazy import: urllib costs ~100ms cold on Windows; the import gate
    # (<90ms) is measured on module import, so defer it to first use.
    import urllib.error
    import urllib.request

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        raise BharatVoiceError(
            f"HTTP {exc.code} {exc.reason} from {url}. "
            f"Fix: check the API key, endpoint availability, and quota. "
            f"Server said: {detail or '(no body)'}"
        ) from exc
    except urllib.error.URLError as exc:
        raise BharatVoiceError(
            f"Network error calling {url}: {exc.reason}. "
            f"Fix: check connectivity and that the endpoint is reachable."
        ) from exc
    except OSError as exc:
        raise BharatVoiceError(
            f"Network error calling {url}: {exc}. "
            f"Fix: check connectivity and that the endpoint is reachable."
        ) from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise BharatVoiceError(
            f"Invalid JSON response from {url}. "
            f"Fix: verify the endpoint is the expected REST API."
        ) from exc


# ---------------------------------------------------------------------------
# Sarvam TTS
# ---------------------------------------------------------------------------

def build_sarvam_tts_payload(text: str, lang: str, api_key: str | None = None):
    """Return ``(url, headers, body)`` for Sarvam ``bulbul:v1`` TTS."""
    key = api_key or _api_key("SARVAM_API_KEY")
    code = _lang_code(lang)
    headers = {"api-subscription-key": key, "Content-Type": "application/json"}
    body = {
        "model": "bulbul:v1",
        "inputs": [text],
        "target_language_code": code,
        "speaker": "meera",
    }
    return SARVAM_TTS_URL, headers, body


def sarvam_tts(
    text: str,
    lang: str,
    api_key: str | None = None,
    urlopen=None,
) -> bytes:
    """Synthesize speech with Sarvam TTS; return the raw audio bytes.

    Response: ``{"audio": "<base64>"}`` (see build_sarvam_tts_payload).
    """
    if urlopen is None:
        import urllib.request

        urlopen = urllib.request.urlopen
    url, headers, body = build_sarvam_tts_payload(text, lang, api_key=api_key)
    resp = _post_json(url, headers, body, urlopen)
    if resp.get("error"):
        raise BharatVoiceError(
            f"Sarvam TTS error: {_server_message(resp)}. "
            f"Fix: check SARVAM_API_KEY and the language code ({_ENV_DOC})."
        )
    audio_b64 = resp.get("audio") if isinstance(resp, dict) else None
    if not audio_b64:
        raise BharatVoiceError(
            "Sarvam TTS response missing the 'audio' field. "
            f"Fix: verify the request reached api.sarvam.ai (server said: "
            f"{_server_message(resp) or '(no error message)'})."
        )
    return base64.b64decode(audio_b64)


# ---------------------------------------------------------------------------
# Bhashini (MeitY ULCA gateway) — STT and TTS
# ---------------------------------------------------------------------------

def _bhashini_pipeline_id(pipeline_id: str | None) -> str:
    return (
        pipeline_id
        or os.environ.get("BHASHINI_PIPELINE_ID")
        or DEFAULT_BHASHINI_PIPELINE_ID
    )


def build_bhashini_stt_payload(
    audio_b64: str,
    lang: str,
    api_key: str | None = None,
    pipeline_id: str | None = None,
):
    """Return ``(url, headers, body)`` for Bhashini ASR (speech-to-text)."""
    key = api_key or _api_key("BHASHINI_API_KEY")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {
        "pipelineId": _bhashini_pipeline_id(pipeline_id),
        "input": [
            {"source": "audio", "audio": [{"audioContent": audio_b64, "audioSource": "base64"}]}
        ],
        "config": {"language": {"sourceLanguage": lang}},
    }
    return BHASHINI_COMPUTE_URL, headers, body


def bhashini_stt(
    audio_b64: str,
    lang: str,
    api_key: str | None = None,
    pipeline_id: str | None = None,
    urlopen=None,
) -> str:
    """Transcribe base64 audio with Bhashini ASR; return the recognized text.

    Walks ``resp["output"][0]["audio"][0]["text"]``; raises
    :class:`BharatVoiceError` (with the server message) on ``error`` or a
    malformed/missing output.
    """
    if urlopen is None:
        import urllib.request

        urlopen = urllib.request.urlopen
    url, headers, body = build_bhashini_stt_payload(
        audio_b64, lang, api_key=api_key, pipeline_id=pipeline_id
    )
    resp = _post_json(url, headers, body, urlopen)
    if resp.get("error"):
        raise BharatVoiceError(
            f"Bhashini STT error: {_server_message(resp)}. "
            f"Fix: check BHASHINI_API_KEY and BHASHINI_PIPELINE_ID ({_ENV_DOC})."
        )
    try:
        return resp["output"][0]["audio"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise BharatVoiceError(
            "Bhashini STT response missing 'output[0].audio[0].text'. "
            f"Fix: check BHASHINI_PIPELINE_ID and the audio format. "
            f"Server said: {_server_message(resp) or '(no error message)'}."
        ) from exc


def build_bhashini_tts_payload(
    text: str,
    lang: str,
    api_key: str | None = None,
    pipeline_id: str | None = None,
):
    """Return ``(url, headers, body)`` for Bhashini TTS (text-to-speech)."""
    key = api_key or _api_key("BHASHINI_API_KEY")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {
        "pipelineId": _bhashini_pipeline_id(pipeline_id),
        "input": [{"source": "text", "text": [{"input": text}]}],
        "config": {"language": {"sourceLanguage": lang, "targetLanguage": lang}},
    }
    return BHASHINI_COMPUTE_URL, headers, body


def bhashini_tts(
    text: str,
    lang: str,
    api_key: str | None = None,
    pipeline_id: str | None = None,
    urlopen=None,
) -> bytes:
    """Synthesize speech with Bhashini TTS; return the raw audio bytes.

    Reads ``resp["output"][0]["audio"][0]["audioContent"]`` (base64).
    """
    if urlopen is None:
        import urllib.request

        urlopen = urllib.request.urlopen
    url, headers, body = build_bhashini_tts_payload(
        text, lang, api_key=api_key, pipeline_id=pipeline_id
    )
    resp = _post_json(url, headers, body, urlopen)
    if resp.get("error"):
        raise BharatVoiceError(
            f"Bhashini TTS error: {_server_message(resp)}. "
            f"Fix: check BHASHINI_API_KEY and BHASHINI_PIPELINE_ID ({_ENV_DOC})."
        )
    try:
        audio_b64 = resp["output"][0]["audio"][0]["audioContent"]
    except (KeyError, IndexError, TypeError) as exc:
        raise BharatVoiceError(
            "Bhashini TTS response missing 'output[0].audio[0].audioContent'. "
            f"Fix: check BHASHINI_PIPELINE_ID and the text payload. "
            f"Server said: {_server_message(resp) or '(no error message)'}."
        ) from exc
    return base64.b64decode(audio_b64)


# ---------------------------------------------------------------------------
# Engine selection & helpers
# ---------------------------------------------------------------------------

def pick_engine(lang: str, has_sarvam_key: bool, has_bhashini_key: bool) -> str:
    """Choose the TTS/STT engine: prefer Sarvam, then Bhashini, else edge-tts.

    ``edge-tts`` is the documented fallback (the voice-first plugin's local
    Microsoft Edge TTS) — this function only returns the string; the caller
    decides what to do with it.
    """
    _lang_code(lang)  # fail loud on unknown languages
    if has_sarvam_key:
        return "sarvam"
    if has_bhashini_key:
        return "bhashini"
    return "edge-tts"


def available_engines() -> dict:
    """Report which cloud engines have keys present in the env (no network)."""
    return {
        "sarvam": bool(os.environ.get("SARVAM_API_KEY", "").strip()),
        "bhashini": bool(os.environ.get("BHASHINI_API_KEY", "").strip()),
    }


def render_convo(lines) -> str:
    """Render a transcript as numbered lines: ``1. <line>``.

    Each line may be a plain string or a ``(speaker, text)`` pair, in which
    case it renders as ``1. speaker: text``.
    """
    out = []
    for idx, line in enumerate(lines, 1):
        if isinstance(line, (tuple, list)) and len(line) == 2:
            out.append(f"{idx}. {line[0]}: {line[1]}")
        else:
            out.append(f"{idx}. {line}")
    return "\n".join(out)
