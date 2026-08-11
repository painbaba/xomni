# Case study: "ChatGPT app not opening" (Aug 2026, user's HP laptop)

## Symptom
ChatGPT desktop app icon wouldn't open. Nothing happened; no error dialog.

## What it actually was
Machine-wide `NODE_OPTIONS=--openssl-legacy-provider` (HKLM env, set by Node dev tooling)
made the ChatGPT app's Electron runtime hard-exit at startup. Older Electron apps
(WhatsApp Desktop) ignored the flag → only ChatGPT died. Disabled Sound Research
SECOMNService (HP audio DRM, crash-looping hourly) as a bonus fix.

## Diagnostic path that worked (in order)
1. `winget search chatgpt` → official app = msstore `9PLM9XGG6VKS`. First install said
   "already installed / no upgrade". `Get-AppxPackage -Name OpenAI.Codex` → DisplayName
   **ChatGPT**, exe `app\ChatGPT.exe` — package family name is a legacy internal name.
2. `shell:AppsFolder` launch failed ("cannot be run completely...") → re-registered:
   `Add-AppxPackage -Register "<InstallLocation>\AppxManifest.xml" -DisableDevelopmentMode`.
   Still crashed.
3. Direct exe launch: exit code **-1073741819 = 0xC0000005** (access violation) within
   ~1s. No WER event for ChatGPT, but SECOCL64.exe (Sound Research audio DRM) was
   faulting (0xc0000409) at the exact same second — red herring; it was crash-looping
   all day on its own (dumps every hour in `%LOCALAPPDATA%\CrashDumps\`).
4. Control test: WhatsApp Desktop (Electron, Store) launched fine → system-level
   Electron breakage ruled out → app/env-specific.
5. Crashpad dumps at `%LOCALAPPDATA%\Packages\OpenAI.Codex_*\LocalCache\Roaming\Codex\web\Codex\Crashpad\reports\*.dmp`
   → parsed with pure-Python minidump parser: 0xC0000005 at 0x2a549b9b, an address in
   NO loaded module, below 4GB → V8 JIT region → JS/env-level cause.
6. `--enable-logging=stderr` capture printed:
   `electron: --openssl-legacy-provider is not allowed in NODE_OPTIONS` — smoking gun.
7. `[Environment]::GetEnvironmentVariable('NODE_OPTIONS','Machine')` → `--openssl-legacy-provider`.
   Removed via elevated script (a .ps1 file + `Start-Process powershell -Verb RunAs -File ...`),
   broadcast WM_SETTINGCHANGE. App launched: 16 processes, ~1GB, stable.

## Distractions that cost time (avoid)
- Fixating on SECOCL64 (audio DRM) — correlated but not causal.
- Wiping the app's LocalCache — no effect (not a cache problem).
- `--disable-gpu` / `--no-sandbox` — no effect.
- Fresh reinstall of the Store package — no effect (same broken env).
- `pip install minidump` — that PyPI package is a broken stub (only has `name`).
  `minidump-parser` also didn't install. Write the ~40-line parser instead
  (see `scripts/minidump_fault.py`).

## Same session, adjacent fixes
- Windows 11 22H2 (build 22621.4317) was EOL (Oct 2025) — WU said "up to date" with
  no updates since Oct 2024. WU COM search found only Defender + HP driver updates;
  OSUpgrade category = 0. Installation Assistant + MCT both exited silently on this
  build. Working path: MCT → ISO (6.45GB Windows.iso, 25H2 V2) → `Mount-DiskImage` →
  `explorer.exe D:\setup.exe` → keep files+apps.
- Disk space: VMs were the hog — 5 Kali VMs = ~106GB. `VBoxManage unregistervm "<name>" --delete`
  per VM; `savestate` for the in-use one (preserves exact state).
- Daily Kernel-Power 41 (hard resets) + SECOCL64 crash-looping → disabled
  SECOMNService (UAC-elevated `sc config SECOMNService start= disabled`).
- TPM scare: `Get-Tpm` returned empty, but `Get-PnpDevice -Class SecurityDevices`
  showed "Trusted Platform Module 2.0 OK" — TPM was never the problem.
