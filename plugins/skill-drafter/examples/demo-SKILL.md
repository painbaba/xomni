---
name: set-up-python-package
description: "Set up a Python package and prove it installs"
version: "1.0.0"
author: "xomni"
tags: [drafted, auto-skill]
---

# Set Up Python Package

Set up a Python package and prove it installs

Auto-drafted from a successful session (6 successful tool calls).

## Procedure

1. Run `mkdir -p src/demo_pkg && printf '__version__ = "0.1.0"\n' > src/demo_pkg/__init__.py` (via terminal).
2. Run `git init -b main` (via terminal).
3. Run `pyproject.toml` (via write_file).
4. Run `python -m pip install -e . --quiet` (via terminal).
5. Run `python -c "import demo_pkg; print(demo_pkg.__version__)"` (via terminal).
6. Run `git add -A && git commit -m "feat: initial package"` (via terminal).

## Verification

The originating session completed 6 tool calls successfully, ending with: Run `git add -A && git commit -m "feat: initial package"` (via terminal)..
