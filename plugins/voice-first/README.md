# voice-first — optional hands-free voice mode

Voice-first mode: full conversation via TTS/STT — voice-in for the CLI makes
it hands-free. **Optional**: the existing text CLI is untouched. Zero hooks
(commands only). Fail-loud everywhere.

## Commands

| Command | What it does |
|---|---|
| `/voice test` | capture 3s from the mic, transcribe, print what was heard |
| `/voice ask <text>` | one spoken turn: send `<text>` to the host, speak the reply (TTS) |
| `/voice on [turns]` | hands-free session loop: listen → host → speak, until "stop" or turns run out |
| `/voice backends` | show the pluggable STT/TTS backend registry: available + selected |
| `/voice set stt\|tts <name>` | persist a backend choice (fails loud on unknown backends) |
| `/voice` | help |

Session loop state machine: `capture → stt → ask_host (hermes chat -q) → tts →`
repeat; breaks on the word "stop" (user **or** host) or when turns are
exhausted. Every step is fail-loud — a broken mic, missing binary, dead API,
or failed subprocess raises an explicit error naming the failure **and** the fix.

## Pluggable voice backends (U-SURF-3)

A backend registry in `core.py` with `available() -> bool` (local binary/key
check, **no network**), `transcribe(audio_path)` for STT, and
`synthesize(text, out_path)` for TTS:

| Kind | Backend | Priority | Available when |
|---|---|---|---|
| STT | `whisper-local` | 1 | `faster-whisper` (or `openai-whisper`) importable |
| STT | `gemini` | 2 | `GOOGLE_API_KEY` / `GEMINI_API_KEY` set |
| STT | `sarvam` | 3 | `SARVAM_API_KEY` set |
| TTS | `edge` | 1 | `edge-tts` CLI on PATH / next to the venv |
| TTS | `sarvam` | 2 | `SARVAM_API_KEY` set |
| TTS | `bhashini` | 3 | `BHASHINI_API_KEY` set |

- `select_backend(kind, name|'auto')`: explicit name, else config override,
  else auto-pick the first available in priority order. Unavailable-but-
  requested and unknown backends are loud `VoiceError`s naming the valid set
  and the missing piece.
- Config override (in priority order): env `voice_first.stt_backend` /
  `voice_first.tts_backend` (dotted) or `VOICE_FIRST_STT_BACKEND` /
  `VOICE_FIRST_TTS_BACKEND`, then the persisted plugin config
  `.voice_first.json` (written by `/voice set stt|tts <name>`).
- Payload builders (`build_gemini_transcribe_payload`,
  `build_sarvam_stt_payload`, `build_sarvam_tts_payload`,
  `build_bhashini_stt_payload`, `build_bhashini_tts_payload`) return the exact
  request shape for the documented endpoints; they **fail loud naming the
  missing env var** when the required key is absent. Keys are referenced by
  env-var NAME only in payloads (e.g. `env:SARVAM_API_KEY`) — values are never
  printed, logged, or included in error messages (guarded by tests).
- Sarvam/Bhashini cover the **8 bharat-pack languages**: `en, hi, mr, ta, te,
  kn, gu, bn` (Sarvam BCP-47: `en-IN … bn-IN`; Bhashini uses the plain code).
- Endpoints: Sarvam `POST https://api.sarvam.ai/v1/speech_to_text`
  (`saaras:v1`) and `/v1/text_to_speech` (`bulbul:v1`, speaker `meera`);
  Bhashini `POST https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute`
  (pipeline `64392f96da7b500c55a0d0a2`, override with `BHASHINI_PIPELINE_ID`).

## Pipeline & dependencies

| Step | Windows | POSIX | Missing → loud error says |
|---|---|---|---|
| capture | `ffmpeg -f dshow -i audio=<detected mic>` (16 kHz mono wav) | `arecord` (ALSA) | `winget install ffmpeg` / `apt install alsa-utils` |
| STT | `whisper-local` / `gemini` / `sarvam` (registry auto-pick) | same | `pip install faster-whisper` / set API key |
| TTS | `edge` / `sarvam` / `bhashini` (registry auto-pick) | same | `pip install edge-tts` / set API key |
| host | `hermes chat -q <prompt>` (subprocess) | same | reinstall Hermes |

- Gemini STT: `POST generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent`
  with inline base64 audio (`VOICE_GEMINI_MODEL` env overrides the model).
  Key from `GOOGLE_API_KEY` (or `GEMINI_API_KEY`)
  env / user `.env` files. **Never printed, logged, or echoed in errors.**
- TTS voice: `en-IN-PrabhatNeural` default; `hi-IN-PrabhatNeural` when the
  text contains non-ASCII (bharat) script.
- `VOICE_WHISPER_MODEL` env overrides the whisper model size (default `base`);
  `VOICE_SARVAM_LANG` / `VOICE_BHASHINI_LANG` override the default
  STT/TTS language for those backends.

## Tests

```bash
cd plugins/voice-first && python -m unittest tests.test_core -q
```

22 methods: capture argv + missing-binary/rc/timeout/no-output loud errors,
STT backend selection + whisper/gemini error paths, key-never-leaked guards,
TTS argv/voice pick + failures, session state machine (user-stop, host-stop,
exhaust, fail-loud propagation), `ask_host` argv/env, zero-hooks guard, and
the backend registry (tests 14-18): registry completeness, auto-pick with
mocked `available()`, explicit set + persistence, unknown-backend loud
errors, and payload builders (gemini key-by-env-name-only, sarvam/bhashini
for all 8 bharat-pack languages, edge synth payload, missing keys fail loud).
