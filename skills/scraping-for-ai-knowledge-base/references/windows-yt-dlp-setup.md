# Windows yt-dlp setup workaround

## The problem
On Windows with the Hermes Python venv, `python -m pip install yt-dlp` fails because the bundled venv at `AppData\Local\hermes\hermes-agent\venv` has no `pip`. Using system `python3` (3.13.x) works but installs `yt-dlp.exe` to a non-PATH location.

## The fix (2 commands)

```bash
# 1. Install yt-dlp via system python3 (pip lives at /c/Users/HP/AppData/Local/Programs/Python/Python314/Scripts/pip)
python3 -m pip install yt-dlp

# 2. Add the install dir to PATH for the current shell (note: WindowsApps Python uses a virtualized package store path)
export PATH="/c/Users/HP/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0/LocalCache/local-packages/Python313/Scripts:$PATH"
which yt-dlp  # should print the .exe path
yt-dlp --version  # should print version, not 'command not found'
```

## Why this happens
- Hermes ships its own venv for tool isolation, but doesn't include `pip` to keep the install small
- `python3` resolves to WindowsApps store Python (3.13.x), which installs to `AppData\Local\Packages\...` — Microsoft's sandboxed package store, not the normal site-packages
- PATH wasn't updated for that store path during install (warning: "is not on PATH")

## Verification
After running both commands:
- `yt-dlp --version` → prints a date-version string (e.g. `2026.06.09`)
- `yt-dlp ytsearch5:test --dump-json --skip-download` → returns JSON metadata for 5 videos

## Pattern: prefer the system Python, not the Hermes venv, for installing CLI tools
For any `pip install <cli>` where you need the CLI on PATH: use system `python3` (which has pip) and add the resulting Scripts dir to PATH. Don't try to fix the Hermes venv.
