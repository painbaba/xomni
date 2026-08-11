# Case study: ChatGPT desktop app crashes on launch (Aug 2026)

Machine: HP laptop, Windows 11 22H2 build 22621.4249 (last hotfix Oct 2024 — 22 months stale),
i5-12450H, KIOXIA NVMe healthy, daily Kernel-Power 41 hard resets, SECOCL64 crash-looping hourly.

## Symptom
"ChatGPT app won't open." No process via Start menu / AppsFolder; direct exe launch exits
-1073741819 (0xC0000005) in under 1s, deterministic at the same address every run.

## Evidence trail (in order found — mirrors the diagnostic ladder in SKILL.md)

1. No "ChatGPT" anywhere by name, but `OpenAI.Codex` package present with DisplayName **ChatGPT**,
   exe `app\ChatGPT.exe` (read from AppxManifest.xml). OpenAI's Store listing 9PLM9XGG6VKS
   ("ChatGPT" — its apps.microsoft.com page embeds packageFamilyNames) ships the OpenAI.Codex
   package family. winget msstore "already installed" / "Successfully installed" = entitlement
   view, not deployment.
2. `explorer.exe shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App` -> "This command cannot be run
   completely because the system cannot find all the information required" = broken registration.
   `Add-AppxPackage -Register` fixed the shell error; app still crashed.
3. Event log: SECOCL64.exe (Sound Research / HP audio DRM, parent service `SECOMNService`)
   fail-fast crash-looping 0xC0000409 all day (dumps 10:49, 14:22, 14:41, 15:11, 15:19, 15:47,
   22:56). RED HERRING: disabling SECOMNService did NOT fix the app (verify via control experiment).
4. Control: WhatsApp Desktop (Electron Store app) launches fine -> problem is app-specific.
5. Crashpad dumps at `%LOCALAPPDATA%\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Roaming\Codex\web\Codex\Crashpad\reports\*.dmp`
   (note the app's internal product dir is "Codex"). Fault 0xC0000005 at 0x2a549b9b in NO loaded
   module -> V8/JIT code region.
6. Fresh reinstall + cache wipe + `--disable-gpu` + `--no-sandbox`: no change.
7. SMOKING GUN — launch with `--enable-logging=stderr --v=1`, RedirectStandardError to file:
   `electron: --openssl-legacy-provider is not allowed in NODE_OPTIONS`
8. `[Environment]::GetEnvironmentVariable('NODE_OPTIONS','Machine')` = `--openssl-legacy-provider`
   (set system-wide by some Node dev tool). Modern Electron disallows it -> startup failure.
   Older Electron (WhatsApp) ignores it -> why only ChatGPT died.

## Fix applied
1. UAC script FILE (nested `-Command` quoting silently failed once; file-based worked):
   `[Environment]::SetEnvironmentVariable('NODE_OPTIONS',$null,'Machine')` +
   WM_SETTINGCHANGE broadcast (`SendMessageTimeout(0, 0x1A, 0, "Environment", 2, 5000, ...)`).
2. Verified Machine NODE_OPTIONS == "".
3. Launched via AppsFolder with clean env -> 16 processes, ~1GB, stable.
4. Also disabled `SECOMNService` (Sound Research) — was crash-looping hourly.

## Error strings to grep for
- `electron: --openssl-legacy-provider is not allowed in NODE_OPTIONS`
- `This command cannot be run completely because the system cannot find all the information required`
- `Started MSStore package execution. ProductId: 9PLM9XGG6VKS PackageFamilyName: OpenAI.Codex_2p2nqsd0c76g0`
  (winget logs: `%LOCALAPPDATA%\Packages\Microsoft.DesktopAppInstaller_8wekyb3d8bbwe\LocalState\DiagOutputDir\*.log`)

## Minidump parse core (stdlib, full script in scripts/minidump_fault_module.py)
```python
data = open(path,'rb').read()                 # b'MDMP' at 0
num, drva = struct.unpack_from('<II', data, 8)
# directory: <III (type, size, rva) x num
# exception stream type 6: rva+8 -> <IIQI code, flags, _, addr
# module list type 4: rva -> count, then count x 108-byte entries:
#   <QIIII base, size, _, _, nameRva ; name = UTF-16LE at nameRva+4
```
