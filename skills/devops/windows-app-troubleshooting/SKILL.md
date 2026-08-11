---
name: windows-app-troubleshooting
description: Use when a Windows app won't launch or needs OS/VM fixes.
---

# Windows App & OS Troubleshooting (this host)

Class-level playbook for fixing apps that won't start, diagnosing crashes, running Windows feature upgrades, and managing VirtualBox VMs on the user's Windows 11 machine. Session case study: `references/chatgpt-nodeoptions-case.md`. Minidump parser: `scripts/minidump_fault.py`.

## 0. CRITICAL HOST QUIRK — GUI visibility
Apps launched directly from this terminal (PowerShell `Start-Process`, bash) render on a **hidden desktop — the user cannot see them**. They also often exit silently when they wait for clicks that never come.
- **To put a window on the user's screen: launch via Explorer**: `explorer.exe "C:\path\app.exe"` (or `explorer.exe 'shell:AppsFolder\<AUMID>!App'` for Store apps).
- UAC prompts DO reach the user (secure desktop), so elevated scripts work — but the elevated app's own window is still on the hidden desktop.
- If a user says "nothing popped up" after you launched a GUI tool, this is why. Relaunch via explorer.exe.
- Verify what the user can see by asking; process-alive ≠ user-visible.

## 1. Electron/Chromium app won't start — check NODE_OPTIONS FIRST
Modern Electron (2025+) hard-exits at startup when `NODE_OPTIONS` contains disallowed flags. The killer seen in the wild: `--openssl-legacy-provider` (set machine-wide by Node dev tooling). Symptom: instant crash with 0xC0000005, no useful WER event, older Electron apps (WhatsApp) work fine.
- Check: `[Environment]::GetEnvironmentVariable('NODE_OPTIONS','Machine')` and `'User'`.
- Fix: remove machine-wide: elevated `[Environment]::SetEnvironmentVariable('NODE_OPTIONS',$null,'Machine')`, then broadcast WM_SETTINGCHANGE (`SendMessageTimeout` HWND_BROADCAST, 0x1A, 'Environment').
- Confirm via stderr: launch exe with `--enable-logging=stderr` and capture stderr — Electron prints `electron: <flag> is not allowed in NODE_OPTIONS` before dying.
- Other disallowed NODE_OPTIONS flags (per Electron): `--openssl-legacy-provider`, `--force-fips`, `--enable-fips`, `--jitless`... treat any NODE_OPTIONS as suspect first.

## 2. Crash diagnosis ladder (in order)
1. **Direct exe launch + exit code**: `Start-Process <exe> -PassThru`, wait 8-10s, check `$p.ExitCode`. Hex it: 0xC0000005 = access violation, 0xC0000409 = fail-fast (stack corruption / CFG), 0xC0000135 = missing DLL.
2. **Event logs**: `Get-WinEvent -LogName Application -MaxEvents 400` filter Id 1000/1001 — faulting module is in the message. Note: WER events may name a DIFFERENT exe than the app (e.g. an injected agent crashing) — correlate timestamps.
3. **Crashpad dumps** (Electron/Chromium): `%LOCALAPPDATA%\Packages\<pkg>\LocalCache\Roaming\<app>\Crashpad\reports\*.dmp` — parse with `scripts/minidump_fault.py`.
4. **Windows CrashDumps**: `%LOCALAPPDATA%\CrashDumps\*.dmp`, and WER archive `C:\ProgramData\Microsoft\Windows\WER\ReportArchive\` (Report.wer is UTF-16 — `iconv -f UTF-16 -t UTF-8`).
5. **Same-architecture control test**: launch another Electron app (e.g. WhatsApp Desktop). If it works, the system isn't broken — it's app/env-specific.

Minidump fault-address reading: an address NOT covered by any loaded module, below 4GB, is V8 JIT code (Electron/Chromium) — points at a JS/env-level cause, not a bad DLL.

## 3. MSIX/Store app management
- **Package family name ≠ display name.** OpenAI's ChatGPT desktop app ships as package `OpenAI.Codex` (DisplayName "ChatGPT", exe `app\ChatGPT.exe`). Find the real identity: `Get-AppxPackage | select Name,InstallLocation`, then read `AppxManifest.xml` for DisplayName/Executable.
- winget msstore `--force install` can report "Successfully installed" while deploying nothing (stale entitlement). Verify deployment with `Get-AppxPackage` + check the exe exists on disk.
- Re-register broken registration (shell:AppsFolder launch fails, no Start menu tile): `Add-AppxPackage -Register "<InstallLocation>\AppxManifest.xml" -DisableDevelopmentMode`.
- Full reset: `Remove-AppxPackage <name>` then `winget install --id <storeid> -e --source msstore --accept-...`.
- Launch via `explorer.exe 'shell:AppsFolder\<PackageFamilyName>!<AppId>'` — and remember section 0.

## 4. Windows Update & feature upgrades
- **"You're up to date" ≠ supported.** 22H2 went EOL Oct 2025; consumer WU then offers nothing. Check build: `(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion')` DisplayVersion/CurrentBuild/UBR + `Get-HotFix | sort InstalledOn`.
- WU COM search works from CLI: `New-Object -ComObject Microsoft.Update.Session` → `CreateUpdateSearcher().Search('IsInstalled=0 and IsHidden=0')`. `Type='Upgrade'` is NOT a valid criterion (0x80240032). On EOL builds the OSUpgrade category returns 0 → no feature update via WU.
- The Installation Assistant and MCT both exit silently on EOL builds (they expect WU to offer the upgrade). Don't fight them — go straight to **MCT → ISO** (works, official, user clicks through wizard; ISO ~6.5GB multi-edition, current release e.g. 25H2).
- **In-place upgrade**: mount ISO (`Mount-DiskImage`), `explorer.exe "<drive>:\setup.exe"` (section 0!), keep "Keep personal files and apps". Needs ~20GB free; check `Get-PSDrive C` first.
- Repair the update stack first if the machine is unstable/behind: DISM `/Online /Cleanup-Image /RestoreHealth` then `sfc /scannow` — write results to a log OUTSIDE Temp (see pitfall below).

## 5. VirtualBox VM ops
- `"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"` (not on PATH).
- Delete a VM cleanly: `unregistervm "<name>" --delete` (removes registry entry + files). Deleting the folder manually leaves a stale `<inaccessible>` entry — remove with `unregistervm <uuid>` (no --delete).
- Shut down safely preserving work: `controlvm "<name>" savestate` (saved VMs still appear in `list runningvms` — don't be fooled, they consume nothing).
- VM disk usage: `du -sh "C:\Users\HP\VirtualBox VMs/"*/` — du on the VM folder, never recursive full-disk scans.

## Pitfalls
- **NEVER `rm -rf` a temp dir you're also using**: deleting `%TEMP%\*` wiped my own repair script that lived there → "UAC dismissed" was actually "script file gone". Keep working scripts at `C:\Users\HP\<name>.ps1`, not in Temp.
- **Full-disk recursive scans time out** (du on C:\Windows etc. > 300s). Use targeted `du -sh` on known paths, or PowerShell `Get-ChildItem -Include` on likely dirs only.
- **curl write failures (exit 23) on Windows** → use `powershell Invoke-WebRequest -OutFile` instead (MSYS curl quirks). Same for MSI/exe downloads.
- **Backticks inside PS one-liners passed through bash break** — avoid `` ` `` (use `[Environment]::NewLine` or no splitting); quote JSON bodies carefully.
- **Windows logs (Report.wer, PowerShell Out-File utf16) are UTF-16** — `iconv -f UTF-16 -t UTF-8` before grep.
- Machine instability signals worth flagging: daily Kernel-Power 41 (event 41 = hard reboot), a third-party agent crash-looping all day (e.g. Sound Research SECOCL64 — HP audio DRM; fix = disable its service `SECOMNService`), Chrome/SnippingTool crashing — all point to a broken driver/OS, and repairs + feature updates are the cure.
- Win11 feature update refusal often misread as TPM failure: verify `Get-PnpDevice -Class SecurityDevices` (TPM 2.0 OK) before blaming hardware.
