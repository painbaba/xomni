#!/usr/bin/env python3
"""Parse Windows minidumps (.dmp) for exception code + faulting module.

Usage: python minidump_fault.py <file.dmp> [file2.dmp ...]   (glob patterns ok)

Pure stdlib, no deps. Handles WER dumps and Chromium/Electron Crashpad dumps
(e.g. %LOCALAPPDATA%\\Packages\\<pkg>\\LocalCache\\Roaming\\<app>\\Crashpad\\reports\\*.dmp).

Key interpretation notes:
- Fault address covered by NO loaded module + below 4GB => V8 JIT code
  (Electron/Chromium) => JS/env-level cause (check NODE_OPTIONS, GPU, sandbox),
  NOT a missing/bad DLL.
- Exception codes: 0xC0000005 access violation, 0xC0000409 fail-fast/CFG,
  0xC0000135 missing DLL (won't appear here - process never runs).
"""
import glob
import struct
import sys

MODULE_ENTRY = 108  # bytes per MINIDUMP_MODULE


def parse(path: str) -> None:
    data = open(path, "rb").read()
    if data[:4] != b"MDMP":
        print(f"{path}: not a minidump")
        return
    num_streams, dir_rva = struct.unpack_from("<II", data, 8)
    streams = {}
    for i in range(num_streams):
        stype, dsize, rva = struct.unpack_from("<III", data, dir_rva + i * 12)
        streams[stype] = (rva, dsize)

    exc_addr = None
    if 6 in streams:  # ExceptionStream
        rva, _ = streams[6]
        code, flags, _, addr = struct.unpack_from("<IIQI", data, rva + 8)
        print(f"ExceptionCode: 0x{code:08x}  ExceptionAddress: 0x{addr:x}")
        exc_addr = addr
    else:
        print("No exception stream")

    if 4 in streams:  # ModuleListStream
        rva, _ = streams[4]
        count = struct.unpack_from("<I", data, rva)[0]
        for i in range(count):
            off = rva + 4 + i * MODULE_ENTRY
            base, size, _, _, name_rva = struct.unpack_from("<QIIII", data, off)
            nlen = struct.unpack_from("<I", data, name_rva)[0]
            name = data[name_rva + 4 : name_rva + 4 + nlen].decode(
                "utf-16-le", "replace"
            ).rstrip("\x00")
            if exc_addr is not None and base <= exc_addr < base + size:
                print(f">>> FAULTING MODULE: {name} (offset 0x{exc_addr - base:x})")
            elif not name.lower().startswith(
                ("c:\\windows", "c:\\program files\\windowsapps\\microsoft")
            ):
                print(f"  loaded: {name}")

    if exc_addr is not None and exc_addr < 0x100000000:
        print(
            "NOTE: fault address in low memory (<4GB), not covered by any listed "
            "module -> V8 JIT region (Electron/Chromium). Suspect env-level cause "
            "(NODE_OPTIONS, GPU, sandbox) rather than a corrupted binary."
        )


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for pattern in sys.argv[1:]:
        for path in glob.glob(pattern):
            print(f"=== {path} ===")
            try:
                parse(path)
            except Exception as e:  # noqa: BLE001 - keep the script robust
                print("parse error:", e)
            print()


if __name__ == "__main__":
    main()
