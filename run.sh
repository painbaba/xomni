#!/usr/bin/env bash
# ============================================================
#  XOMNI launcher (git-bash / POSIX)
#  One agent. Every feature. Every free model.
#  Starts the Hermes host with all 14 XOMNI plugins loaded.
#  Usage:  ./run.sh                (interactive chat)
#          ./run.sh chat -q "..."  (one-shot)
#          ./run.sh --continue     (resume last session)
# ============================================================
echo "[XOMNI] starting host + 12 plugins..."
hermes "$@"
