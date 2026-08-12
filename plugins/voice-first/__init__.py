"""voice-first — Hermes plugin wiring (ZERO hooks, commands only).

U10. Optional voice-first mode: full conversation via TTS/STT — voice-in for
the CLI makes it hands-free. The existing text CLI is untouched.

Commands:
    /voice test                 capture 3s from the mic, transcribe, print what was heard
    /voice ask <text>           one spoken turn: send <text> to the host, speak the reply (TTS)
    /voice on [turns]           hands-free session loop: listen -> host -> speak, until 'stop' or turns
    /voice                      show help

No hooks are registered (spec: zero hooks). Every step is fail-loud: capture,
STT, host round-trip, and TTS failures surface as explicit "[voice] ERROR: ..."
messages with install/fix hints — never silent.
"""
from __future__ import annotations

import os
import tempfile

from . import core

_CTX = None

HELP = (
    "/voice test                 capture 3s from the mic, transcribe, print what was heard\n"
    "/voice ask <text>           one spoken turn: send <text> to the host, speak the reply (TTS)\n"
    "/voice on [turns]           hands-free session loop: listen -> host -> speak, until 'stop' or turns\n"
    "/voice                      show this help"
)


def _handle_voice(args: str | None) -> str:
    parts = (args or "").split(None, 1)
    sub = (parts[0] or "").lower()
    try:
        if sub == "test":
            tmp = tempfile.mkdtemp(prefix="voice-test-")
            wav = os.path.join(tmp, "capture.wav")
            core.capture_audio(3, wav)
            text = core.stt(wav)
            return f"[voice] captured {wav}\n[voice] heard: {text}"
        if sub == "ask":
            text = parts[1].strip() if len(parts) > 1 else ""
            if not text:
                return HELP
            reply = core.ask_host(text)
            tmp = tempfile.mkdtemp(prefix="voice-ask-")
            mp3 = os.path.join(tmp, "reply.mp3")
            core.tts(reply, mp3)
            return f"[voice] host: {reply}\n[voice] spoken -> {mp3}"
        if sub == "on":
            rest = parts[1].strip() if len(parts) > 1 else ""
            turns = int(rest) if rest.isdigit() else 5
            events = core.voice_session(turns=turns)
            return core.render_session(events)
    except core.VoiceError as exc:
        # Fail-loud: the user sees exactly what broke and how to fix it.
        return f"[voice] ERROR: {exc}"
    return HELP


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "voice",
        handler=_handle_voice,
        description=(
            "voice-first: optional hands-free mode — mic capture (ffmpeg/arecord), "
            "STT (faster-whisper or Gemini), TTS (edge-tts), /voice session loop. "
            "Zero hooks."
        ),
        args_hint="[test|ask <text>|on [turns]]",
    )
