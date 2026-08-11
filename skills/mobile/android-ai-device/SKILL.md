---
name: android-ai-device
description: Use when making an Android fully AI or linking it via adb.
---

# Android AI Device (Project RAAM)

Turning the user's Android into a fully-AI device: offline brain + voice loop + system-wide automation + remote access to this PC. User delegated architecture decisions ("leaving upon u surprise me") — commit to a stack and build the kit, don't ask for permission on each piece.

## The decided stack (do not re-architect)
1. **Brain**: Ollama Android app (Play Store, official). Pull `qwen3:4b` (Hindi+English, good default); `gemma3:4b` alt. Needs 6GB+ RAM — on weaker phones drop to `qwen3:1.7b` / phi.
2. **Voice loop** (Termux): whisper-cpp (STT) → Ollama → piper (TTS). Fully offline once models downloaded. Commands in references/raam-kit.md.
3. **Automation**: Tasker + AutoVoice profiles — WhatsApp read-aloud, notification summaries via Ollama, shake/headset-button quick question, battery-saver suggestions.
4. **Wild card (Hermes Remote)**: SSH from Termux to this PC → run hermes CLI, check swarm, talk to me from anywhere. `termux-wake-lock` keeps the session alive.

## Kit location (built Aug 2026)
`C:\Users\HP\ai-workforce\phone-ai\` — `setup_termux.sh` (run INSIDE Termux on the phone) + `README.md` (full playbook). User's phones: test Android + personal 8602852438. Next session: finish setup when phone is in hand.

## Windows host tooling (this machine, verified)
- adb: `C:\Users\HP\AppData\Local\Android\Sdk\platform-tools\adb.exe` (pre-existing SDK — check there FIRST)
- scrcpy v4.1: `C:\Users\HP\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v4.1\scrcpy.exe`
- Install pattern: `winget install Google.PlatformTools` / `Genymobile.scrcpy` (user-level, no admin). choco needs admin — `Access to the path 'C:\ProgramData\chocolatey\lib-bad' is denied` → don't fight it, use winget.
- PATH gotcha: freshly winget-installed tools may not be on the current shell PATH — call by full path or export the WinGet\Links dir.

## Phone prep checklist (give user, in order)
1. Settings → About → tap build number 7x → Developer Options
2. USB debugging ON → plug into PC → `adb devices` → accept RSA prompt on phone
3. Install Termux from **F-Droid, NOT Play Store** (Play Store build is abandoned)
4. `termux-setup-storage` when prompted
5. Run `bash setup_termux.sh` inside Termux — prints SSH pubkey to add to PC's authorized_keys

## Pitfalls
- Play Store Termux is abandoned — F-Droid only. This is the #1 setup-killer.
- adb shows nothing until USB debugging is ON and the RSA prompt is accepted on the phone.
- choco fails without admin (lib-bad denied); winget is the user-level path.
- Small models only on low-RAM phones; 4B quantized needs ~6GB free.
- Keep voice commands exact (see reference) — whisper/piper package names differ between pkg and pip.

## References
- references/raam-kit.md — voice loop test commands, Ollama/Tasker specifics
