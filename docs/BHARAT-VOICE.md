# BHARAT-VOICE — voice-native Bharat TTS/STT (plugin: `bharat-voice`)

Hindi + 5 regional languages (**hi, ta, te, kn, mr, gu**) text-to-speech and
speech-to-text over India-resident REST endpoints. Pure stdlib, zero hooks,
fail-loud, key-safe.

## Engines

| Engine | Provider | Endpoint | Used for | Env var |
|---|---|---|---|---|
| Sarvam | Sarvam AI | `https://api.sarvam.ai/v1/text_to_speech` | TTS (`bulbul:v1`, speaker `meera`) | `SARVAM_API_KEY` |
| Bhashini | MeitY ULCA | `https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute` | STT + TTS (pipeline-routed) | `BHASHINI_API_KEY` |
| edge-tts | local (`voice-first` plugin) | n/a | documented fallback | none |

Selection order (`pick_engine`): **Sarvam → Bhashini → edge-tts**. The
edge-tts branch just returns the string; the `voice-first` plugin provides
the actual local TTS.

## Env vars needed

```
SARVAM_API_KEY=<key>                          # Sarvam TTS
BHASHINI_API_KEY=<key>                        # Bhashini ASR/TTS
BHASHINI_PIPELINE_ID=<id>                     # optional; default 64392f96da7b500c55a0d0a2
```

Missing keys raise `BharatVoiceError` naming the env var **and** the fix;
key values are never printed/logged/included in error messages.

## Languages

| Code | Name | Sarvam code | Script |
|---|---|---|---|
| hi | Hindi | `hi-IN` | Devanagari |
| ta | Tamil | `ta-IN` | Tamil |
| te | Telugu | `te-IN` | Telugu |
| kn | Kannada | `kn-IN` | Kannada |
| mr | Marathi | `mr-IN` | Devanagari |
| gu | Gujarati | `gu-IN` | Gujarati |

## Usage

```python
from plugins.bharat_voice import core

audio = core.sarvam_tts("नमस्ते", "hi")        # TTS -> bytes (needs SARVAM_API_KEY)
text  = core.bhashini_stt(audio_b64, "hi")     # STT -> str (needs BHASHINI_API_KEY)
audio = core.bhashini_tts("ನಮಸ್ಕಾರ", "kn")     # TTS -> bytes
eng   = core.pick_engine("ta", has_sarvam_key=True, has_bhashini_key=False)  # 'sarvam'
print(core.render_convo([("user", "hello"), "assistant: नमस्ते"]))
```

All network failures raise `BharatVoiceError` naming the failing endpoint
and the fix. `core.available_engines()` reports which cloud engines have
keys present (no network). Test: `cd plugins/bharat-voice && python -m
unittest tests.test_core -q`.
