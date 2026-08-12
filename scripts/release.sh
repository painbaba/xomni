#!/usr/bin/env bash
# XOMNI release script — DRY-RUN BY DEFAULT.
# Usage: bash scripts/release.sh          # dry-run: no tag, no push, no publish
#        bash scripts/release.sh --do-tag # additionally creates the git tag
set -euo pipefail

cd "$(dirname "$0")/.."

# --- version from pyproject.toml ---
VERSION=$(python -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
echo "[release] version: $VERSION"

# --- working tree check ---
DIRTY=$(git status --porcelain)
if [ -n "$DIRTY" ]; then
  echo "!!! [release] WARNING: working tree is NOT clean — do not tag a dirty tree. Continuing in dry-run:"
  echo "$DIRTY"
else
  echo "[release] working tree clean"
fi

# --- changelog ---
python scripts/changelog.py

# --- tag / push (dry-run unless --do-tag) ---
DO_TAG=0
if [ "${1:-}" = "--do-tag" ]; then
  DO_TAG=1
fi

if [ "$DO_TAG" = "1" ]; then
  echo "[release] creating tag v$VERSION"
  git tag "v$VERSION"
  echo "[release] tag created: v$VERSION (push it yourself: git push origin v$VERSION)"
else
  echo "[release] DRY-RUN — would run: git tag v$VERSION && git push origin v$VERSION"
  echo "[release] (pass --do-tag to actually create the tag; push/publish are never run here)"
fi

# --- PyPI publish dry-run: build wheel, print manual twine step ---
mkdir -p .tmp/dist
echo "[release] building wheel (--no-deps)..."
if ! python -m pip wheel . -w .tmp/dist --no-deps; then
  echo "[release] ERROR: wheel build failed" >&2
  exit 1
fi
WHEEL=$(ls .tmp/dist/*.whl)
echo "[release] wheel built: $WHEEL"
echo "[release] manual step (twine not installed by this script): twine check .tmp/dist/*.whl"
echo "[release] dry-run complete — no tag, no push, no publish."
