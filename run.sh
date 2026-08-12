#!/usr/bin/env bash
# ============================================================
#  XOMNI launcher (git-bash / POSIX)
#  One agent. Every feature. Every free model.
#  Starts the Hermes host with all 16 XOMNI plugins loaded.
#  Usage:  ./run.sh                (interactive chat)
#          ./run.sh chat -q "..."  (one-shot)
#          ./run.sh --continue     (resume last session)
# ============================================================
export XOMNI_HOME="$(cd "$(dirname "$0")" && pwd)"
# Best-effort: ensure a local Ollama runtime is reachable so LOCAL
# models work with zero extra installs (never blocks chat).
if command -v ollama >/dev/null 2>&1 && ! curl -sf --max-time 2 http://127.0.0.1:11434/v1/models >/dev/null 2>&1; then
    (ollama serve >/dev/null 2>&1 &)
    for _ in $(seq 1 30); do
        curl -sf --max-time 2 http://127.0.0.1:11434/v1/models >/dev/null 2>&1 && break
        sleep 2
    done
fi
echo "[XOMNI] starting standalone XOMNI profile + 22 plugins..."
export HERMES_HOME="${HERMES_HOME:-$HOME/AppData/Local/hermes/profiles/xomni}"
hermes "$@"
