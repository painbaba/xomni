# Harvest forensics — complete-window harvest command set (c19, Aug 2026)

Validated on the Machine City Kali VM (`painbaba`, VBoxManage + paramiko from
Windows). Use AFTER all windows show `Done` lines — never mid-window.

## Per-log harvest one-liner (run over SSH)

```bash
cd ~/fuzz
for l in fuzz_avc_asan6.log fuzz_avc_patched_asan4.log fuzz_hevc_asan6.log fuzz_jpeg4.log; do
  echo "== $l"
  ls -la "$l" | awk '{print $5" bytes"}'
  echo "Done lines:";       grep -a '^Done ' "$l"
  echo "last cov line:";    grep -a 'cov:' "$l" | tail -1     # broad pattern, NOT 'pulse cov:'
  echo "raw format:";       grep -a 'pulse' "$l" | tail -1 | cat -A | cut -c1-160
  echo "ASAN-errors:";      grep -ac 'ERROR: AddressSanitizer' "$l"
  echo "libFuzzer-fatals:"; grep -ac 'ERROR: libFuzzer' "$l"
done
```

Grep facts that cost a cycle to learn:
- `grep -a 'pulse cov:'` (single space) returns NOTHING even when the log is
  full of pulses — libFuzzer writes `#N<TAB>pulse  cov: …` (TAB after `#N`,
  multi-space before `cov:`). The broad `'cov:'` pattern matches every pulse
  line; `cat -A` shows the `^I` tabs when you need the raw truth.
- `grep -ac '^Done '` per log == the authoritative completion marker;
  cross-check live procs with `pgrep -cf '[f]uzz_'` (0 = windows expired
  naturally).
- ASAN count 0 + libFuzzer-fatal count 0 on a 4.3MB debug-flood log and a
  10.9MB libjpeg-warning log = BOTH benign. Log SIZE is not a fault signal;
  only `ERROR: AddressSanitizer` + `Test unit written to` are.

## Completion poll loop (host side, before harvesting)

```python
# every ~45s until done or ~30min cap:
#   done = sum(grep -ac '^Done ' per log) == 4  and  pgrep -cf '[f]uzz_' == 0
# then harvest; then freeze:
#   VBoxManage controlvm 'kali hacker' savestate   # rc=0, then VMState="saved"
```

- Poll, don't assume: the c19 brief said the windows were "expired" ~16 min
  before the 3600s timers fired (seeded 18:29–18:31Z, `Done` ~19:30Z; the
  poll flipped at +944s from run start). Wall-clock arithmetic on launch times
  is a projection, not completion evidence.
- Never savestate over live fuzzers — SAVED freezes the processes mid-window.
  Freeze only at 4/4 Done + 0 live; verify rc=0 and `VMState="saved"` after.
- If the final-cov grep came up empty (separator mismatch): resume the VM,
  re-grep broad `'cov:'`, then savestate again — recovery is ~2 min and rc=0
  both ways, leaving the VM frozen exactly as intended.

## c19 evidence (4/4 windows complete, 272,104 runs, 0 ASAN errors)

| log | Done line | last cov pulse (`#N DONE`) | ASAN | bytes |
|---|---|---|---|---|
| fuzz_avc_asan6 | Done 6105 runs in 3605s | #6105 cov: 3985 ft: 23000 corp: 1064/40Mb | 0 | 29,696 |
| fuzz_avc_patched_asan4 | Done 17600 runs in 3602s | #17600 cov: 4955 ft: 24114 corp: 1295/22Mb | 0 | 4,277,255 |
| fuzz_hevc_asan6 | Done 5672 runs in 3604s | #5672 cov: 5221 ft: 29457 corp: 1450/35Mb | 0 | 20,849 |
| fuzz_jpeg4 | Done 242727 runs in 3601s | #242727 cov: 1028 ft: 4613 corp: 970/5023Kb | 0 | 10,929,909 |

Corpus deltas c18→c19: seeds_hevc 2778→2909, corpus_avc2 1724→1922,
corpus_patched 4746→5340, jpeg_seeds 5090→6116 (+1,949 files). Crash queue
unchanged 52 any-depth / 9 maxdepth-1 / 0 new — 2nd consecutive zero-crash
batch (~610k runs across c15+c18). hevc cov 5221 > c15-batch record 5172;
avc 3985 ≈ 3954 → coverage plateau signal for these decoder targets.
