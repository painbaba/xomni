"""bharat-voice — voice-native Bharat TTS/STT (Sarvam + Bhashini), zero hooks.

M3. Hindi + 5 regional languages (ta, te, kn, mr, gu) text-to-speech and
speech-to-text over India-resident REST endpoints:

* Sarvam AI — https://api.sarvam.ai/v1/text_to_speech (TTS, bulbul:v1)
* Bhashini  — https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute
              (MeitY ULCA ASR/TTS model gateway, pipeline-id routed)

Pure stdlib, fail-loud, key-safe: API keys are read from the environment and
never printed, logged, or included in error messages. No hooks are registered
(spec: zero hooks) — call the functions in :mod:`core` directly.
"""
from . import core

__version__ = "0.1.0"

__all__ = ["core", "__version__"]
