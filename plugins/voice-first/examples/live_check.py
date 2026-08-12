"""Live verification for U10 voice-first (runs on THIS machine, real hardware/APIs)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

tmp = tempfile.mkdtemp(prefix="vf-live-")
print("key present:", bool(core._api_key()), "(never printed)")
wav = os.path.join(tmp, "live.wav")
print("capture ->", core.capture_audio(3, wav))
print("wav bytes:", os.path.getsize(wav))
text = core.stt(wav, backend="gemini")
print("TRANSCRIPT:", repr(text))
mp3 = os.path.join(tmp, "live.mp3")
core.tts("voice first is online", mp3)
print("tts ->", mp3, os.path.getsize(mp3), "bytes")
