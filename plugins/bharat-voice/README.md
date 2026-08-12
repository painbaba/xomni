# bharat-voice — voice-native Bharat TTS/STT

Hindi + 5 regional languages (**hi, ta, te, kn, mr, gu**) text-to-speech and
speech-to-text over India-resident REST endpoints. Pure stdlib (no pip
deps), **zero hooks**, fail-loud, key-safe: API keys are read from the
environment and **never** printed, logged, or included in error messages
(guarded by tests).

## Engines

| Engine | Provider | Endpoint | Used for | Key env var |
|---|---|---|---|---|
| Sarvam | Sarvam AI | `https://api.sarvam.ai/v1/text_to_speech` | TTS (`bulbul:v1`, speaker `meera`) | `SARVAM_API_KEY` |
| Bhashini | MeitY ULCA | `https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute` | STT + TTS (pipeline-routed) | `BHASHINI_API_KEY` |
| edge-tts | local (voice-first plugin) | n/a | documented fallback | none |

Engine selection (`pick_engine`): **Sarvam → Bhashini → edge-tts**. The
edge-tts branch returns the string only — the caller (e.g. the
`voice-first` plugin) supplies the actual local TTS.

## Environment variables

```
SARVAM_API_KEY=<your key>            # Sarvam TTS (required for sarvam_tts)
BHASHINI_API_KEY=<your key>          # Bhashini ASR/TTS (required for bhashini_*)
BHASHINI_PIPELINE_ID=<pipeline id>   # optional; default 64392f96da7b500c55a0d0a2
```

Missing keys raise `BharatVoiceError` naming the env var **and** the fix —
the key value itself is never echoed.

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
from core import sarvam_tts, bhashini_stt, bhashini_tts, pick_engine, render_convo

# TTS (Sarvam) -> bytes audio
audio = sarvam_tts("नमस्ते", "hi")          # needs SARVAM_API_KEY

# STT (Bhashini) -> recognized text
text = bhashini_stt(audio_b64, "hi")         # needs BHASHINI_API_KEY

# TTS (Bhashini) -> bytes audio
audio = bhashini_tts("ನಮಸ್ಕಾರ", "kn")

# Engine selection (no network)
engine = pick_engine("ta", has_sarvam_key=True, has_bhashini_key=False)  # 'sarvam'

# Transcript rendering
print(render_convo([("user", "hello"), "assistant: नमस्ते"]))
```

Every network failure raises `BharatVoiceError` with the failing endpoint
named and a fix hint — nothing is silently swallowed.

## Tests

```bash
cd plugins/bharat-voice && python -m unittest tests.test_core -q
```

16 methods: language table + Sarvam/Bhashini payload shapes, audio/text
parsing, server-error and missing-output fail-loud paths, missing-key
errors naming the env var, key-never-leaked guards, engine selection (all
4 combinations), `available_engines`, `render_convo`, zero-hooks guard.
