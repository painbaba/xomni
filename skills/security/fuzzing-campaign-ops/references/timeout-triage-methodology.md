# Timeout / slow-unit triage methodology (libFuzzer + ASAN)

Validated Aug 2026 on the libavc H.264 campaign (Kali VM, `~/fuzz`). Outcome:
all 8 timeout units + 11 slow-units were the fuzzer's own seeds or 1-byte
mutants of them tripping `-timeout=10` — NOT a hang, NOT a DoS.

## Why timeouts happen (the mental model)

libFuzzer's `-timeout=N` is a **wall-clock** limit per input. Wall time is
inflated by: (a) ASAN instrumentation (~2–4×), (b) scheduler starvation when
the box is oversubscribed (this VM: 8 cores, load avg 19–24, 11 concurrent
fuzzer processes, `exec/s: 0` pulses), (c) harness per-input overhead
(codec create/teardown, up to 100 decode calls). Decodes that take <4 s CPU
natively can exceed 10 s wall under these conditions — so the fuzzer
re-discovers its own corpus seeds as "timeouts" repeatedly (same artifact
hashes across runs is the tell).

## Step 1 — artifact filename hash == content SHA1

libFuzzer names artifacts `<kind>-<sha1>` where the hash is SHA1 of the file
content. Compare directly:

```bash
cd ~/fuzz && sha1sum timeout-* avc2_timeout-* | head
sha1sum real_*.h264 seed_*.264
```

Identical hash → the "timeout unit" is byte-identical to a seed file.
Conclusive, no repro needed. Mutants: compare byte distance with python
(`sum(1 for i in range(min(len(a),len(b))) if a[i]!=b[i])`) — the libavc
mutants were 1 differing byte, same length.

## Step 2 — NAL structure scan (python)

Scan start codes `00 00 00 01` / `00 00 01`; NAL type = byte after start
code & 0x1F (7=SPS, 8=PPS, 5=IDR, 1=non-IDR slice, 9=AUD). Healthy stream:
SPS/PPS/SEI/IDR then slices, 15–120 NALs. Red flags that WOULD support a
real hang: hundreds of AUDs, truncated/missing slices, absurd SPS dims.

Parse SPS dims with an Exp-Golomb bit reader: profile_idc(8) +
constraints/level(8+8) + ue seq_parameter_set_id; for profiles 100/110/122/
244/44/83/86/118/128/138/139/134/135 also skip chroma/bit-depth/scaling-list
fields (scaling list: 8 lists of 16, or 12 of 64 if chroma==3, skipping
delta-scales) before pic_width_in_mbs_minus1 / pic_height_in_map_units_minus1.
libavc units were all 128×96…480×272 → no huge-allocation vector.

## Step 3 — decisive test: plain (non-ASAN) harness

Rebuild the same sources without sanitizers (see
`scripts/build_avc_plain_harness.sh`), then time one decode per artifact:

```bash
cd ~/fuzz
for f in timeout-* avc2_timeout-* avc2_slow-unit-*; do
  { time timeout 20 ./build_avc_plain/avc_dec_plain "$f" >/dev/null 2>&1; } 2>/tmp/t.err
  echo "$f rc=$? $(grep -E 'real|user|sys' /tmp/t.err | tr '\n' ' ')"
done
```

Interpretation:
- ALL inputs rc=0 in <4 s CPU → **no hang exists**. Verdict: fuzzer
  artifact (too-tight timeout for ASAN+load). Report as NOT a DoS.
- Any unit still running after `timeout 30` in the plain build → real
  hang/DoS candidate; investigate with gdb/strace and the alarm stack.

## Step 4 — ASAN repro (for the record)

```bash
timeout 20 env ASAN_OPTIONS=detect_leaks=0 ./fuzz_avc_asan -runs=1 \
  -timeout=10 -rss_limit_mb=3000 <artifact>
```

- rc=0 + "Done 1 runs" → completes under limit now (borderline; was >10 s
  under heavier load).
- rc=70 + "ERROR: libFuzzer: timeout" → reproducibly exceeds the limit.
  NOTE: rc=70 means libFuzzer's alarm fired mid-decode, NOT a hang — check
  `user`/`sys` CPU from the builtin `time`: 8+ s CPU consumed = real work in
  progress that would finish if given more time.

## Evidence table (libavc case, Aug 2026)

| Artifact | Size | Finding |
|---|---|---|
| timeout-f310df47 | 28603 B | byte-identical to seed real_baseline_176x144.h264 |
| timeout-b9c5eae1 | 11089 B | byte-identical to seed real_main_128x96.h264 |
| timeout-0337e306 | 28603 B | 1-byte mutant of baseline seed |
| timeout-857ef714 / c2648240 | 57979 B each | 1-byte mutants of real_high_352x288 seed |
| timeout-426b29bd | 11089 B | 1-byte mutant of main seed |
| avc2_timeout-e78fc738 | 94681 B | valid 256×144, 120 slices (longer capture) |
| avc2_slow-unit-24eb4a3f | 167427 B | valid 480×272, 60 slices |
| slow-unit-96430bdc | 200000 B (=max_len) | junk NALs; decodes natively in 0.37 s |

Plain-harness wall times (load-20 box): 0.1–3.6 s per input, all rc=0.
ASAN: 11 KB unit 6.8 s rc=0; 94 KB unit timed out at 12 s (user 4.7 + sys
3.7 s CPU — real work, completes natively in ~3 s).

## Follow-up recommendation for the campaign

Bump `-timeout=30` (or reduce concurrent workers) so the campaign stops
re-discovering its own seeds as timeouts and burning cycles on alarm dumps.
