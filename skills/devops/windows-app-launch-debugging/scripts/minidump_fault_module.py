#!/usr/bin/env python3
"""Parse a Windows minidump (.dmp) and report exception code/address + faulting module.

Usage:  python minidump_fault_module.py <file.dmp> [more.dmp ...]

Pure stdlib — no pip deps. (PyPI 'minidump' is a broken stub whose module has only
a 'name' attribute; 'minidump-parser' fails to import as expected — this script
is the reliable path.)

Output: exception code + address, and the loaded module containing that address.
A fault address in NO loaded module = executing JIT (V8) code (Chromium/Electron
allocate code ranges in the low 4GB, e.g. 0x2a549b9b) or control-flow corruption.

Dump layout used (MS minidump format):
  header:  'MDMP' + version + NumberOfStreams(4) + StreamDirectoryRva(4) + ...
  dir entry: <III  (stream type, data size, rva)
  ExceptionStream (type 6): rva+8 -> <IIQI exception code, flags, _, address
  ModuleListStream (type 4): rva -> count(4), then count x 108-byte entries:
      <QIIII  base, size, checksum, timestamp, nameRva  (+ 76 bytes skipped)
  module name at nameRva: Length(4, bytes incl null) + UTF-16LE text
"""
import struct
import sys


def analyze(path: str) -> None:
    data = open(path, "rb").read()
    if data[:4] != b"MDMP":
        print(f"{path}: not a minidump (bad signature)")
        return
    num_streams, dir_rva = struct.unpack_from("<II", data, 8)
    streams = {}
    for i in range(num_streams):
        stype, dsize, rva = struct.unpack_from("<III", data, dir_rva + i * 12)
        streams[stype] = (rva, dsize)

    addr = None
    if 6 in streams:  # ExceptionStream
        rva, _ = streams[6]
        code, flags, _, addr = struct.unpack_from("<IIQI", data, rva + 8)  # skip ThreadId(4)+pad(4)
        print(f"{path}: ExceptionCode=0x{code:08x}  Address=0x{addr:x}")
    else:
        print(f"{path}: no exception stream")

    mods = []
    if 4 in streams:  # ModuleListStream
        rva, _ = streams[4]
        count = struct.unpack_from("<I", data, rva)[0]
        for j in range(count):
            off = rva + 4 + j * 108
            base, size, _, _, nrva = struct.unpack_from("<QIIII", data, off)
            nlen = struct.unpack_from("<I", data, nrva)[0]
            name = data[nrva + 4 : nrva + 4 + nlen].decode("utf-16-le", "replace").rstrip("\x00")
            mods.append((base, size, name))

    if addr is not None:
        hit = next(((b, s, n) for b, s, n in mods if b <= addr < b + s), None)
        if hit:
            base, size, name = hit
            print(f"  >>> FAULTING MODULE: {name}  (base=0x{base:x} offset=0x{addr - base:x})")
        else:
            print(f"  address 0x{addr:x} in NO loaded module -> JIT (V8) code region or control-flow corruption")
        for b, s, n in mods:
            if not n.lower().startswith(("c:\\windows", "c:\\program files\\windowsapps\\microsoft")):
                print(f"  loaded: {n}  (base=0x{b:x} size=0x{s:x})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        try:
            analyze(p)
        except Exception as e:  # noqa: BLE001
            print(f"{p}: parse error: {e}")
        print()
