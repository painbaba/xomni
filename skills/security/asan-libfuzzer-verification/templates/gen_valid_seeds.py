#!/usr/bin/env python3
"""Generate diverse VALID seeds so the fuzzer explores beyond a known-crash seed.

Lesson: a corpus containing only the crash trigger keeps mutations in the crash
neighborhood (low coverage). Add structurally diverse valid files: multi-frame,
interlaced, local colormaps, extensions, transparency, multiple sizes.
Adapt the writers to whatever format you're fuzzing (this one makes GIFs).
"""
import struct, os

OUT = "gif_seeds"
os.makedirs(OUT, exist_ok=True)

def gif_header(ver=b"89a"):
    return b"GIF" + ver

def screen_desc(w, h, gct_flag, bg=0):
    packed = (0xF0 | 0x00) if gct_flag else 0  # GCT present, 2 colors
    return struct.pack("<HHBBB", w, h, packed, bg, 0)

def gct(colors):
    return b"".join(bytes(c) for c in colors)

def gce(delay=10, transparent=None):
    packed = 0x01 if transparent is not None else 0
    return b"\x21\xF9\x04" + bytes([packed, delay & 0xFF, (delay >> 8) & 0xFF,
                                    transparent if transparent is not None else 0]) + b"\x00"

def image_desc(left, top, w, h, lct_flag=False, interlaced=False):
    packed = (0x80 | 0x00) if lct_flag else 0
    if interlaced:
        packed |= 0x40
    return b"\x2C" + struct.pack("<HHHH", left, top, w, h) + bytes([packed])

def lzw_min_code(ncolors):
    return max(2, (ncolors - 1).bit_length())

def lzw_data_blocks(pixel_bytes, min_code):
    """Trivial-but-valid LZW: clear code + literal codes + end code, sub-blocked."""
    clear = 1 << min_code
    end = clear + 1
    codes = [clear] + list(pixel_bytes) + [end]
    out = bytearray()
    acc, nbits = 0, 0
    for c in codes:
        acc |= c << nbits
        nbits += min_code + 1
        while nbits >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            nbits -= 8
    if nbits:
        out.append(acc & 0xFF)
    blocks = bytearray()
    for i in range(0, len(out), 255):
        chunk = out[i:i+255]
        blocks.append(len(chunk))
        blocks += chunk
    blocks.append(0)
    return bytes(blocks)

def make(name, frames, header_ver=b"89a", w=10, h=10, gct_colors=None):
    data = bytearray(gif_header(header_ver))
    data += screen_desc(w, h, gct_colors is not None)
    if gct_colors:
        data += gct(gct_colors)
    for f in frames:
        if f.get("delay") is not None or f.get("transparent") is not None:
            data += gce(f.get("delay", 10), f.get("transparent"))
        data += image_desc(0, 0, w, h, lct_flag=f.get("local", False),
                           interlaced=f.get("interlaced", False))
        if f.get("local"):
            data += gct(f["palette"])
        ncolors = len(f.get("palette", gct_colors or [(0,0,0),(255,255,255)]))
        mc = lzw_min_code(ncolors)
        data += bytes([mc]) + lzw_data_blocks(f["pixels"], mc)
    data += b"\x3B"
    with open(os.path.join(OUT, name), "wb") as fh:
        fh.write(bytes(data))
    print(f"{name}: {len(data)} bytes")

G = [(0,0,0), (255,255,255)]
make("seed_1x1_87a.gif", [{"pixels": b"\x00", "local": True, "palette": G}], header_ver=b"87a", w=1, h=1, gct_colors=G)
make("seed_10x10_checker.gif", [{"pixels": bytes([(x+y) & 1 for y in range(10) for x in range(10)])}], w=10, h=10, gct_colors=G)
make("seed_3frame.gif", [
    {"pixels": b"\x00"*100, "delay": 10},
    {"pixels": b"\x01"*100, "delay": 20},
    {"pixels": b"\x00\x01"*50, "delay": 30},
], w=10, h=10, gct_colors=G)
make("seed_interlaced.gif", [{"pixels": bytes([(x*3+y*7) & 1 for y in range(10) for x in range(10)]), "interlaced": True}], w=10, h=10, gct_colors=G)
make("seed_localct.gif", [{"pixels": bytes([(x+y) % 4 for y in range(10) for x in range(10)]), "local": True,
                           "palette": [(255,0,0),(0,255,0),(0,0,255),(255,255,0)]}], w=10, h=10, gct_colors=G)
make("seed_transparent.gif", [{"pixels": bytes([(x+y) % 4 for y in range(10) for x in range(10)]), "delay": 5, "transparent": 3}], w=10, h=10,
     gct_colors=[(255,0,0),(0,255,0),(0,0,255),(255,255,0)])
make("seed_64x64.gif", [{"pixels": bytes([(x*8//64 + y*8//64) % 8 for y in range(64) for x in range(64)])}], w=64, h=64,
     gct_colors=[(i*32, i*16, i*8) for i in range(8)])
print("done")
