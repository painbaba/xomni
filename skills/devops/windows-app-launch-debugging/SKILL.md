---
name: windows-app-launch-debugging
description: Use when a Windows app won't open or crashes on launch.
---

# Windows App Launch Debugging

Diagnose "app won't open / crashes instantly on launch" on Windows (Store/MSIX, desktop, Electron/Chromium apps). Terminal runs git-bash on this host — use POSIX syntax, PowerShell only via `powershell -NoProfile -Command`.

## Quick wins (do these first, ~2 min)

1. **Is it installed at all?** `powershell -NoProfile -Command "Get-AppxPackage | Select-Object Name,Version,InstallLocation | Format-List"`.
   PITFALL: package Name != display name. OpenAI's "ChatGPT" Store app is packaged as `OpenAI.Codex` (DisplayName: ChatGPT, exe `app/ChatGPT.exe`). Search *openai*, *chatgpt*, *codex* and read `AppxManifest.xml` DisplayName/Executable before concluding "not installed".

2. **Stale wedged process?** `tasklist | grep -i <app>` / `Get-Process -Name <app>`. PITFALL: `Get-Process` returns an ARRAY when the app runs (Electron spawns 10-20 processes) — use `$q.Count`, index it, or `Measure-Object WorkingSet64 -Sum`; calling `.WorkingSet64` on the array throws.

3. **Application event log, last 15 min** (Application Error 1000 / WER 1001):
   ```powershell
   Get-WinEvent -LogName Application -MaxEvents 300 | Where-Object {$_.TimeCreated -gt (Get-Date).AddMinutes(-15) -and $_.Id -in 1000,1001} | fl TimeCreated,ProviderName,Message
   ```
   PITFALL: filter by TIME WINDOW, not app name — the faulting process may be an injected agent (e.g. SECOCL64.exe) while your app is the victim. Report.wer files are UTF-16: `iconv -f UTF-16LE -t UTF-8 Report.wer | grep -E "^(Sig\[|Fault)"`.

## Exit-code mapping (launch the exe directly)

Store apps live under `C:\Program Files\WindowsApps\<pkg>` (files readable even if dir listing is denied). Launch the exe directly to capture the real exit code:
```powershell
$p = Start-Process $exe -PassThru; Start-Sleep 10
if (Get-Process -Name <App>) {'RUNNING'} else {'exit ' + $p.ExitCode}
```
- `-1073741819` = 0xC0000005 access violation. Deterministic SAME address across runs = same code path every launch (not random corruption).
- `-1073741515` = 0xC0000135 missing DLL (different code).
- `0xC0000409` (also -1073740791) = fail-fast / stack-buffer-overrun (seen as BEX64).

## Registration vs deployment (Store/MSIX)

- winget msstore "Successfully installed" does NOT mean deployed — it can be entitlement-only. Verify with Get-AppxPackage AND `Test-Path` on the exe.
- Launch via AUMID: `explorer.exe 'shell:AppsFolder\<PackageFamilyName>!<AppId>'` (AppId from AppxManifest.xml `Applications.Application.Id`).
- Error "This command cannot be run completely because the system cannot find all the information required" = broken registration. Fix:
  ```powershell
  Add-AppxPackage -Register "<InstallLocation>\AppxManifest.xml" -DisableDevelopmentMode
  ```
- Full reinstall: `Get-AppxPackage -Name '<Name>' | Remove-AppxPackage`, then `winget install --id <StoreId> --source msstore --accept-package-agreements --accept-source-agreements --force`.

## Isolate app-specific vs system-wide

Control experiment: launch a similar app of the SAME runtime family (e.g. another Electron Store app like WhatsApp Desktop). Runs fine → app-specific problem (env var, app build, its own data). Also crashes → look system-wide (audio-DRM injection, HVCI, kernel drivers, failing disk, stale OS).

## Electron/Chromium apps

1. **Get the app's own error — highest-value move.** Launch with logging redirected:
   ```powershell
   Start-Process $exe -ArgumentList '--enable-logging=stderr','--v=1' -RedirectStandardError "$env:TEMP\app_err.log" -PassThru
   ```
   This caught the root cause in one shot after hours of dump-diving.

2. **NODE_OPTIONS kills modern Electron.** If the log says `electron: --openssl-legacy-provider is not allowed in NODE_OPTIONS` (or any flag on Electron's disallowed list), an env var is set machine/user-wide:
   ```powershell
   [Environment]::GetEnvironmentVariable('NODE_OPTIONS','Machine')  # HKLM
   [Environment]::GetEnvironmentVariable('NODE_OPTIONS','User')     # HKCU
   ```
   Older Electron ignores it (WhatsApp runs) while new builds die at startup with an AV in a V8-region address. Fix: remove machine-wide + broadcast (below). If the user needs the flag for old Node builds, set it per-project, never system-wide.

3. **Crashpad dumps** (when the app collects its own): `%LOCALAPPDATA%\Packages\<pkg>\LocalCache\Roaming\<app>\Crashpad\reports\*.dmp` (+ `_sidecar.json`, ptype tells main vs renderer). Parse with `scripts/minidump_fault_module.py` (stdlib-only; PyPI `minidump` is a broken stub, `minidump-parser` fails to import). Fault address in NO loaded module = V8/JIT code region (low 4GB, e.g. 0x2a549b9b) or control-flow corruption.
4. Windows minidumps also land in `%LOCALAPPDATA%\CrashDumps\` — check for the app AND for injected agents (e.g. `SECOCL64.exe.<pid>.dmp`) crashing at the same moment.

## Changing machine env vars (needs admin)

- Nested quoting inside `Start-Process powershell -Verb RunAs -ArgumentList '...'` SILENTLY BREAKS (once the fix never applied). Write a `.ps1` with write_file, then:
  ```powershell
  Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\path\fix.ps1' -Wait
  ```
- Always broadcast so Explorer/new processes pick it up: `SendMessageTimeout(0, 0x1A /*WM_SETTINGCHANGE*/, 0, "Environment", 2, 5000, out r)`.
- Verify by reading the var back with `[Environment]::GetEnvironmentVariable(...,'Machine')`.

## HP audio-DRM stack (crash-loop suspect on HP laptops)

Sound Research SECOMN64/SECOCL64 (service `SECOMNService`), Dolby DAX, B&O (BOAudio) — known to fail-fast crash-loop (0xC0000409, dumps every hour) and inject into processes. If their crash events correlate with app crashes: `sc config SECOMNService start= disabled` (admin, UAC) + kill processes. Audio-DRM only — normal sound unaffected. NOTE: can be a long red herring; verify with the control experiment before chasing it.

## Other system checks (when app-specific fixes fail)

- Disk: `Get-PhysicalDisk` HealthStatus — dying SSD = deterministic same-address crashes from corrupted file reads.
- System log: WHEA events = hardware faults; Kernel-Power 41 (daily) = hard resets; volmgr 161 = dump file write failed (no BSOD dump available).
- Core Isolation/HVCI: `Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard Win32_DeviceGuard` (SecurityServicesRunning {2} = HVCI).
- OS servicing age: `Get-HotFix | Sort InstalledOn -Desc | Select -First 3` — a build >1 year stale can break new Chromium-based apps. EOL check: Win11 22H2 went end-of-support Oct 2025 — WU saying "You're up to date" on an EOL build means NO updates ever again; the fix is a feature update (24H2/25H2, needs ~20GB free). Free space least-invasive first: temp/caches → VM disk images (`du -sh` on `VirtualBox VMs`/Docker dirs — 100GB+ of stale VM copies is common) → hiberfil (disable hibernate, frees ~RAM size) → pagefile (fixed 8GB, frees ~15GB on 16GB-RAM machines). Never delete user files or VMs without showing sizes and asking.

## Feature updates & servicing repair (EOL builds)

- **Installation Assistant silent-exit**: the official assistant (`go.microsoft.com/fwlink/?linkid=2171764` ~4MB; Media Creation Tool = linkid=2156295) can exit with NO window, NO process, NO consent.exe when the servicing stack is damaged — it hands off to Windows Update and dies if WU is broken. Do NOT relaunch it in a loop: repair first, then retry:
  `DISM /Online /Cleanup-Image /RestoreHealth` then `sfc /scannow` (elevated .ps1, 15–40 min, log to a stable path, run a background watcher grepping for a DONE marker).
- TPM check: `Get-Tpm` can return BLANK on machines with a working TPM 2.0. Confirm via `Get-PnpDevice -Class SecurityDevices` (expect "Trusted Platform Module 2.0", Status OK). Missing/disabled TPM (BIOS Intel PTT) is a real upgrade blocker; a blank Get-Tpm is not.
- VM disks are usually the biggest space win. Proper removal: `VBoxManage unregistervm "<name>" --delete` (VBoxManage at `C:\Program Files\Oracle\VirtualBox\`) — removes registry entry + disk files. Check `list runningvms` first; never delete a running VM. `unregistervm` WITHOUT `--delete` leaves a stale `<inaccessible>` entry.
- git-bash `curl -o` can fail with exit 23 writing to Windows paths → use `powershell -NoProfile -Command "Invoke-WebRequest -Uri <url> -OutFile <path>"` instead.

## Pitfalls quick list
- winget msstore "Successfully installed" != deployed
- package Name != display name (check AppxManifest.xml)
- git-bash: `/tmp` doesn't exist → use `$HOME`; backticks inside double-quoted `powershell -Command` get eaten by bash
- `Get-WinEvent ... -match '<appname>'` misses crashes attributed to other exes — filter by time
- Recursive `du` / `Get-ChildItem -Recurse` over C:\Users\HP or C:\Windows TIMES OUT (>300s) on this host — target known paths with `du -sh` per folder instead
- This user: explain the multi-step plan up front and show sizes/details BEFORE suggesting deletions — they ask for both anyway
- Report.wer / .dmp are binary to read_file — use iconv / the script
- `rm -rf %TEMP%/*` (disk cleanup) deletes YOUR OWN helper .ps1 placed there — put working scripts/logs OUTSIDE Temp (e.g. `C:\Users\<user>\win_repair.ps1`). If an elevated script "never ran", verify the file still exists AND the log file appeared BEFORE blaming UAC dismissal (this cost 3 wasted repair attempts)
- `Start-Process -Verb RunAs`: no target process right after launch is NORMAL (UAC pending on secure desktop); if it never appears and there's no `consent.exe` either, the elevated child failed to start — check the script path/log first

## Support files
- `scripts/minidump_fault_module.py` — parse .dmp → exception code/address + faulting module (stdlib only)
- `references/windows-app-launch-case-studies.md` — ChatGPT desktop crash case: evidence trail + exact error strings to grep for
