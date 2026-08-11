@echo off
REM ============================================================
REM  XOMNI launcher (Windows cmd)
REM  One agent. Every feature. Every free model.
REM  Starts the Hermes host with all 12 XOMNI plugins loaded.
REM  Usage:  run.cmd                (interactive chat)
REM          run.cmd chat -q "..."  (one-shot)
REM          run.cmd --continue     (resume last session)
REM ============================================================
echo [XOMNI] starting host + 12 plugins...
hermes %*
