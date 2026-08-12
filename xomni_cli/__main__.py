"""Allow `python -m xomni_cli` — same entry point as the installed `xomni` script."""
import sys

from . import main

if __name__ == "__main__":
    sys.exit(main())
