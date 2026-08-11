@echo off
REM ============================================================
REM  XOMNI launcher (Windows cmd)
REM  One agent. Every feature. Every free model.
REM  Starts the Hermes host with all 16 XOMNI plugins loaded.
REM  Usage:  run.cmd                (interactive chat)
REM          run.cmd chat -q "..."  (one-shot)
REM          run.cmd --continue     (resume last session)
REM ============================================================
set XOMNI_HOME=%~dp0
REM Best-effort: ensure the bundled Ollama runtime is up so LOCAL
REM models work with zero extra installs (never blocks chat).
if exist "%~dp0ollama\start-ollama.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ollama\start-ollama.ps1" >nul 2>&1
)
echo [XOMNI] starting host + 17 plugins...
hermes %*
