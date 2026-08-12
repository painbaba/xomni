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
| `/voice` | help |

Session loop state machine: `capture → stt → ask_host (hermes chat -q) → tts →`
repeat; breaks on the word "stop" (user **or** host) or when turns are
exhausted. Every step is fail-loud — a broken mic, missing binary, dead API,
or failed subprocess raises an explicit error naming the failure **and** the fix.

## Pipeline & dependencies

| Step | Windows | POSIX | Missing → loud error says |
|---|---|---|---|
| capture | `ffmpeg -f dshow -i audio=<detected mic>` (16 kHz mono wav) | `arecord` (ALSA) | `winget install ffmpeg` / `apt install alsa-utils` |
| STT | `faster-whisper` (fallback `openai-whisper`) **or** Gemini | same | `pip install faster-whisper` / set API key |
| TTS | `edge-tts` CLI | same | `pip install edge-tts` |
| host | `hermes chat -q <prompt>` (subprocess) | same | reinstall Hermes |

- STT backend auto: whisper if importable, else Gemini if a key is present,
  else a loud error listing both options. Override with `backend=` in core.
- Gemini STT: `POST generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent`
  with inline base64 audio (`VOICE_GEMINI_MODEL` env overrides the model).
  Key from `GOOGLE_API_KEY` (or `GEMINI_API_KEY`)
  env / user `.env` files. **Never printed, logged, or echoed in errors.**
- TTS voice: `en-IN-PrabhatNeural` default; `hi-IN-PrabhatNeural` when the
  text contains non-ASCII (bharat) script.
- `VOICE_WHISPER_MODEL` env overrides the whisper model size (default `base`).

## Tests

```bash
cd plugins/voice-first && python -m unittest tests.test_core -q
```

16 methods: capture argv + missing-binary/rc/timeout/no-output loud errors,
STT backend selection + whisper/gemini error paths, key-never-leaked guards,
TTS argv/voice pick + failures, session state machine (user-stop, host-stop,
exhaust, fail-loud propagation), `ask_host` argv/env, zero-hooks guard.
