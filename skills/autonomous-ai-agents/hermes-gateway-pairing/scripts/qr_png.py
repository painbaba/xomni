#!/usr/bin/env python3
"""Render a scannable PNG from a raw QR payload (e.g. Baileys WhatsApp pairing).

Usage:
    python qr_png.py "<raw payload>" [output.png] [size_px]
    echo "<payload>" | python qr_png.py

The payload may be wrapped across lines (PTY output) — all whitespace and
newlines are stripped before encoding (the WhatsApp pairing payload is one
continuous string; the commas are part of the data, do NOT remove them).
Writes qr.png (or the given output path) at 500px by default.

Deps: python3 -m pip install qrcode pillow   # use python3 -m pip, NOT bare
pip — on Windows they can target different interpreters.
"""
import sys

try:
    import qrcode
except ImportError as e:
    sys.exit(f"qrcode not installed: {e}\nRun: python3 -m pip install qrcode pillow")

def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] != "-":
        raw = sys.argv[1]
    else:
        raw = sys.stdin.read()
    out = sys.argv[2] if len(sys.argv) >= 3 else "qr.png"
    size = int(sys.argv[3]) if len(sys.argv) >= 4 else 500

    # PTY output wraps the payload; strip ALL whitespace/newlines.
    payload = "".join(raw.split())
    if not payload:
        sys.exit("empty payload")

    img = qrcode.make(payload)
    if size != img.size[0]:
        img = img.resize((size, size))
    img.save(out)
    print(f"saved {out} ({size}x{size})")

if __name__ == "__main__":
    main()
