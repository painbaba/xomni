# Project RAAM — kit detail (Aug 2026)

Kit on disk: `C:\Users\HP\ai-workforce\phone-ai\setup_termux.sh` + `README.md`.

## setup_termux.sh contents (run inside Termux)
Installs: termux-api, openssh, python, git, ffmpeg, curl, jq; whisper-cpp (or pip faster-whisper fallback); piper (or pip piper-tts); termux-setup-storage; generates ed25519 SSH key and prints the pubkey for PC's authorized_keys.

## Voice loop test commands (exact)
```bash
termux-microphone-record -d -f ~/say.wav          # record
whisper-cpp -m ~/ggml-base.bin -f ~/say.wav -otxt  # transcribe
cat ~/say.txt | ollama run qwen3:4b                # brain
ollama run qwen3:4b "say this in 1 sentence: <ans>" | piper --output_file ~/out.wav && termux-media-player play ~/out.wav
```

## Ollama on Android
- Official app on Play Store (separate from desktop ollama).
- `ollama pull qwen3:4b` — default brain, Hindi+English. Alt: gemma3:4b. Low-RAM: qwen3:1.7b.
- 6GB+ RAM required for 4B quantized comfortably.

## Tasker profile ideas (not yet built — offer XML if user wants)
- Incoming WhatsApp → TTS read aloud
- New notification → Ollama summary → TTS
- Headset button / shake → voice loop quick question
- Battery low → AI power-saving suggestions

## Hermes Remote (wild card)
```bash
ssh HP@<PC-LAN-IP>     # needs phone pubkey in PC authorized_keys
termux-wake-lock       # keep Termux alive as remote terminal
```
Then run hermes CLI, check survival-swarm heartbeat, read the city — from the phone.

## Install notes (this PC)
- winget worked for Google.PlatformTools + Genymobile.scrcpy; choco denied (needs admin, lib-bad path error).
- adb.exe pre-existed at AppData\Local\Android\Sdk\platform-tools\.
- scrcpy.exe under WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v4.1\.
- Fresh winget installs aren't on current bash PATH — use full paths.

## Status
Built Aug 9 2026. NOT yet applied to a phone (no device plugged in — `adb devices` empty). Next: user plugs phone in with USB debugging, then continue setup.
