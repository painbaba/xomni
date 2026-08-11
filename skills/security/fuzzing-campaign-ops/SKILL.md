---
name: fuzzing-campaign-ops
description: Manage libFuzzer/ASAN fuzz campaigns on a remote VM.
tags: [fuzzing, libfuzzer, asan, kali, ffmpeg, codec, security-research]
---

# Fuzzing Campaign Ops (libFuzzer + ASAN on remote VM)

Operate long-running libFuzzer/ASAN campaigns — status checks, artifact triage,
corpus expansion, multi-instance launches, rebuilds. Validated on the AOSP
codec audits (libavc H.264 / libhevc HEVC — Ittiam decoders) fuzzed on the
user's Kali VM from Windows.

## VM access (paramiko from Windows)

- Kali: `painbaba` @ `192.168.29.35` (fallback `192.168.56.101`), password auth.
- Helpers in `C:\Users\HP\ai-workforce\aosp-audit\`:
  - `kali_ssh.py "cmd" [timeout]` — run command, prints stdout/stderr, exit code.
  - `kali_xfer.py put|get local remote` — SFTP upload/download (keep SFTP in a
    SEPARATE file: sibling agents may rewrite shared helpers with a different CLI).
- Kali's default shell is **zsh**, not bash: inline bash functions/loops in an
  SSH command string fail (`command not found: gen`). Write a `.sh` script
  locally, `kali_xfer.py put` it, then run `bash /path/script.sh`. For short
  snippets, wrap inline instead: `bash -c '<script>'` (escape inner quotes).
- zsh does NOT word-split unquoted variables: `gcc $FLAGS` passes the whole
  string as ONE arg → cryptic errors like "argument to '-O' should be a
  non-negative integer". Any command with flag variables must run under
  `bash -c`, never bare zsh.
- **zsh glob failures ABORT the whole command chain** (not just that one
  command): `rm -f crash-*` with no matches → `zsh: no matches found:
  crash-*`, rc=1, and everything after it in the same SSH command silently
  never runs (a `nohup ... & echo STARTED` after a failing glob = no fuzzer
  launched). Wrap any command containing globs that may not match in
  `bash -c '...'` (bash globs to the literal pattern instead of aborting).
- `/usr/bin/time` is NOT installed on Kali. Use the bash builtin:
  `{ time timeout 20 ./harness "$f" >/dev/null 2>&1; } 2>/tmp/t.err` then read
  real/user/sys from the file. wall ≫ user+sys under load = scheduler
  starvation, not a busy loop; user+sys is the load-independent work measure.
- Re-read shared helper files right before use in multi-agent sessions — a
  sibling may have replaced the CLI (e.g. dropped --sftp-put support).
- **paramiko may only exist in ONE Windows Python.** On this host it is in
  `python` (3.11) but NOT `python3` (3.13) — `python -c "import paramiko"`
  before assuming; `pip install paramiko` into the interpreter that has it
  (or check `python` first, it's the one with the venv).
- Local source trees differ per platform: the Windows `hevc_dec_fuzzer.cpp`
  uses `_aligned_free` (won't compile on Linux) while the VM's copy uses
  `ivfree` and builds clean. When modifying a harness for a remote build,
  fetch/patch the VM's OWN copy (`sftp get`, patch, `sftp put`), not the
  local Windows file.
- **Heredocs through the terminal tool mangle escapes** (`\\\\n` in a
  `python3 - <<'EOF'` collapsed to a literal newline, breaking a string
  literal). Verify generated source locally (`cat -A` / grep the anchor)
  before upload, or write files with write_file instead of heredocs.
- **Best script-transfer trick: base64 ship-and-run, no SFTP needed.** Avoids
  ALL quoting layers (local bash → paramiko → remote zsh): `B64=$(base64 -w0
  script.sh) && python kali_ssh.py "echo $B64 | base64 -d > /tmp/script.sh &&
  bash /tmp/script.sh"`. Worked flawlessly for multi-line patch/launch/sweep
  scripts this session; also skips the `kali_xfer.py` helper entirely (immune
  to siblings rewriting its CLI).
- **Long builds survive a local SSH timeout — verify before relaunching.**
  The terminal tool's time cap kills the local paramiko client mid-read, but
  a no-pty `exec_command` build keeps running remotely (no controlling TTY →
  no SIGHUP). After a timed-out build SSH call: `pgrep -c clang++`, `tail
  /tmp/build.log`, and check the output binary's mtime — only relaunch if the
  compile is actually dead. The `( cmd > log 2>&1; echo RC=$? >> log )`
  subshell pattern survives teardown and records the exit code for later.
- **paramiko channel-read timeouts abort the WHOLE script — bound slow remote
  commands.** A `run_ssh` helper does `so.read()`, which blocks on the channel
  timeout (default 60s). A large `find ~/fuzz -name '*crash*'` right after
  boot (load spike ~10.00 from boot-time systemd) exceeded it →
  `paramiko.buffered_pipe.PipeTimeout` and the ENTIRE script died mid-mission
  (c15: recon done, relaunch block never reached, VM left booted-but-idle —
  a half-done state, not a clean abort). Fixes: (1) wrap expensive remote
  commands in a remote-side `timeout 30 …` so the channel always EOFs; (2)
  raise the Python-side read/channel timeout to ~90s for the recon loop; (3)
  EXPECT the first commands after boot to be slow — never give them tight
  timeouts. After such an abort, patch and RE-RUN rather than hand-restoring:
  a script whose VM-state check has an "already running → proceed to SSH"
  branch is idempotent, so the re-run completes the mission cleanly. Document
  both runs honestly in the report.

## Transfer & extract (tar bundle → SFTP)

- **Tar on Windows, but give the tarball a real Windows path** — git-bash
  `/tmp/foo.tgz` is invisible to Windows-native paramiko (`sftp.put` →
  `[WinError 2]`). Copy the tarball into the Windows workdir first
  (`cp /tmp/foo.tgz .` in git-bash), then `sftp.put(r'C:\Users\<u>\...\foo.tgz',
  remote)`. Verify remote byte count == local size after put.
- `tar -czf bundle.tgz -C libavc decoder common fuzzer` extracts to TOP-LEVEL
  `decoder/ common/ fuzzer/`, NOT under `libavc/`. Extract with
  `mkdir -p libavc && tar -xzf bundle.tgz -C libavc`. Same for seeds tarred
  with `-C seeds .` (contents extract into cwd — `mkdir -p seeds_avc` first).
  **Always `ls` right after extraction** — a wrong assumption here produced a
  silent empty dir this session.
- Confirm the harness exists before building:
  `ls libavc/fuzzer/avc_dec_fuzzer.cpp && grep -c LLVMFuzzerTestOneInput <it>`.

## Status check & progress verification

```
ps aux | grep fuzz_avc_asan | grep -v grep     # workers + `sh -c` wrappers when -jobs=N
tail -5 ~/fuzz/<fuzzer>.log
find ~/fuzz -maxdepth 1 -name 'artifact*' -o -maxdepth 1 -name '<prefix>_*'
```

- With `-jobs=8 -workers=8` expect 8 worker procs (`Rl`/`Sl`, ~40% CPU each) +
  `sh -c` wrappers. A `timeout 1800` wrapper means the run **auto-dies after
  30 min** — if PIDs differ from launch, someone/something relaunched it; check
  start times before concluding "still running".
- "Running" is not "progressing". Verify: corpus dir file count grows, and the
  log shows `NEW  cov: N ft: N corp: M/..` lines with fresh `NEW_FUNC` entries.
  `exec/s: 0` is normal when the box is oversubscribed (8 workers + extras).
- **libFuzzer pulse lines can LAG the log when stderr is redirected** (block
  buffering): process alive at 60% CPU, log growing, but `#N pulse` frozen for
  minutes. Don't conclude "stuck" — count EXECUTED INPUTS instead: a harness
  with a per-input dbg marker (`fprintf(stderr, "...create codec...")` /
  `grep -ac 'createCodec: entering' <log>`) gives the true progress; the final
  `stat::` block flushes at exit (`timeout` SIGTERM → graceful
  `libFuzzer: run interrupted; exiting` + `stat::number_of_executed_units` +
  `stat::new_units_added` via `-print_final_stats=1`).
- **`==NNNN== libFuzzer: run interrupted; exiting` at the log tail is the
  BENIGN signature of a `timeout N` wrapper expiring** (SIGTERM at N seconds)
  — NOT a crash and NOT an ASAN kill. Cross-check the wrapper's elapsed time
  (ps `etime`) against its `timeout` duration before concluding anything (Aug
  9: jpeg's 3600s wrapper expired cleanly mid-sweep — 361k runs, cov 1002,
  0 ASAN, no artifact write for it).
- **`Done N runs in M second(s)` = the CLEAN FULL-WINDOW completion signature
  (c17 harvest, all 4 c15 campaigns).** With `-max_total_time=3600` expect M ≈
  3601–3604 (window + teardown overhead), e.g. `Done 6937 runs in 3604
  second(s)`, `Done 304044 runs in 3601 second(s)`. The LAST pulse line IS the
  `#N DONE` line carrying the definitive cov/ft/corp (`#6937 DONE cov: 3954 ft:
  22592 corp: 1083/43Mb … exec/s: 1`) — **last pulse == DONE line = coverage
  finality, no divergence** → those are the trustworthy harvest numbers. `pgrep
  -af libFuzzer` → 0 + DONE lines everywhere = windows expired NATURALLY (the
  good case); `run interrupted; exiting` tails = killed (the c14 contrast). A
  campaign that shows `[dbg] fuzz: decode loop` at mid-cycle can still
  complete its window and finish with a `Done` line (c17: the patched-AVC run
  nobody was sure about finished 14898 runs, 0 ASAN) — always harvest from the
  log tail, never from an early read.
- **Pulse/DONE lines are TAB/multi-space field-separated — a single-space grep
  silently misses them (c19 harvest).** `grep -a 'pulse cov:'` returned
  NOTHING across 4 completed logs that each held 143–1120 pulse lines. Raw
  probe `grep -a 'pulse' <log> | tail -1 | cat -A` shows `#4096^Ipulse  cov:
  …` — `^I` is a TAB between `#N` and `pulse`, and `cov:` follows multi-space,
  not one space. Harvest with the broad `grep -a 'cov:' <log> | tail -1`
  (also catches the final `#N DONE cov: …` line), and verify with `cat -A`
  whenever a grep surprises you. c19 finals, all from each log's last
  `#N DONE` pulse: avc `cov: 3985 ft: 23000`, patched `cov: 4955 ft: 24114`,
  hevc `cov: 5221 ft: 29457`, jpeg `cov: 1028 ft: 4613`.
- **Poll for `Done` lines — never trust wall-clock window-expiry arithmetic
  (c19).** The mission brief called the 1-hour windows "expired" ~16 min
  before the `-max_total_time=3600` timers actually fired (seeded ~18:30Z,
  `Done` at ~19:30Z). Authoritative completion = `grep -ac '^Done '` per log
  == all windows AND `pgrep -cf '[f]uzz_'` == 0 — poll both every ~45s (hard
  cap ~30 min), then harvest. VM disposition (three-state policy: OFF kills /
  SAVED freezes / RUNNING hosts): freeze via `VBoxManage controlvm <vm>
  savestate` ONLY after completion; verify rc=0 and `VMState="saved"` after.
  Savestating a VM over live fuzzers freezes the campaign mid-window; if the
  cap hits incomplete, leave RUNNING and document why. (c19: poll flipped at
  +944s → 4/4 Done, 0 live → savestate rc=0, twice — the second time after a
  resume for final-cov recovery, re-frozen cleanly.) Full command set in
  `references/harvest-forensics.md`.
- **Dir file count ≠ log `corp:` number.** `ls ~/fuzz/seeds_hevc/ | wc -l`
  counts every file in the dir (2778); the log's `corp: 1501` counts live
  units libFuzzer loaded/wrote — the dir holds extra files the loader ignored.
  Report both as measured; do NOT try to reconcile them.
- **More benign log tails not to misread as errors:** `[dbg] fuzz: cleanup`
  (normal libFuzzer phase note from a harness with debug fprintf) and
  `Corrupt JPEG data: premature end of data segment` (libjpeg's expected
  complaint about mutated input — a parse note, not a crash). The ONLY crash
  signatures are `ERROR: AddressSanitizer` + a `Test unit written to` line.
- **`-artifact_prefix` is relative → artifacts land in the fuzzer's cwd (`~/fuzz`),
  unless an absolute prefix (`/home/painbaba/fuzz/`) is passed.

## Short-window verification runs & the plateau→pivot rule (c20)

- **When no harvest is due but the VM is SAVED with 0 live fuzzers, run a
  ~5-minute bounded verification instead of a full 4-window batch:**
  `<bin> -print_final_stats=1 -max_total_time=300 -artifact_prefix=crash_v20_ -rss_limit_mb=2048 <corpus> > fuzz_<t>_v20.log 2>&1 &`,
  poll for the `Done` line (~5 min), then harvest. This proves the savestate
  restored correctly, re-baselines the crash queue, and captures a CLEAN
  `stat::` block — `stat::number_of_executed_units`, `stat::average_exec_per_sec`,
  `stat::new_units_added`, `stat::slowest_unit_time_sec`, `stat::peak_rss_mb` —
  which is why c19 rec #2 (`-print_final_stats=1` on ALL future seeds) is now
  standard: the stat:: block beats last-pulse parsing at every harvest. c20
  evidence: `Done 10357 runs in 301 second(s)` on `fuzz_jpeg_asan`, stat:: block
  clean, 0 ASAN, 0 new crashes. Disposition after: `controlvm savestate` rc=0,
  verify `VMState="saved"`, `list runningvms` empty — never leave it running.
- **Binary auto-discovery before launch: never assume the fuzzer binary name.**
  `./jpeg_fuzzer` may not exist — discover first:
  `find ~/fuzz -maxdepth 2 -type f -perm -u+x -name '*jpeg*'` (or `-name '*hevc*'`),
  then launch the discovered path. Same discovery applies when inventorying
  candidate targets for a pivot.
- **Plateau→pivot rule: 3 consecutive zero-crash batches (~620k runs) with a
  frozen corpus set = the retire signal, not "one more batch".** cov flat +
  corpus growing + 0 ASAN (c20: jpeg cov stayed 1028 while `new_units_added: 20`)
  is a plateau, not a stall. Before recommending retirement, inventory the next
  target class ON the VM (`find ~/fuzz -maxdepth 2 -type f -perm -u+x` — c20
  found the unpatched-HEVC family, vpx, yuv, O0, exact_alloc already built): a
  pivot is zero-build-time if the binaries exist. Report the plateau (negative)
  and the pivot inventory (positive path) in the same cycle.

## Full sweep + status report (all fuzzers at once)

Validated Aug 2026: enumerate EVERYTHING (ps, all logs, artifacts, per-log
stats) in one pass, then triage artifacts in a second pass. Reusable scripts:
`scripts/sweep_collect.sh` (enumeration) and `scripts/sweep_reports.sh`
(per-artifact triage). Upload via `kali_xfer.py put`, run with
`bash /tmp/...`, capture with `> file 2>&1`.

- **DO NOT pipe SSH output through `head` / `tee | head`** — when head exits,
  SIGPIPE kills the whole capture mid-stream and you silently LOSE the tail of
  the output (the LOGTAIL section was exactly what got cut). Redirect the full
  output to a file, then page it locally.
- **`grep -oE '[0-9]+ exec/s'` is WRONG** — it matches the max_len limit in
  `lim: 60000 exec/s: 0` and reports "60000 exec/s" as the rate. Use
  `grep -oE 'exec/s: [0-9]+' | tail -1`. Same trap: `corp: N/Mb` — include the
  `Mb` in the regex or the trailing digits get dropped.
- Artifact name hash IS the input's sha1: libFuzzer names are
  `<prefix>(crash|timeout|slow-unit|leak)-<40-hex-of-input>`. So the
  "is it a seed?" test = compare the name hash against `sha1sum` of seed/corpus
  files. Build the seed hash index ONCE
  (`find <seeddirs> -maxdepth 1 -type f -exec sha1sum {} + > /tmp/seed_hashes.txt`),
  then `grep -m1 "^<sha1> "` per artifact — never re-hash thousands of seeds
  per artifact.
- Map artifact→log: `grep -q "Test unit written to.*<name>" ~/fuzz/*.log`.
  Extract its stack with `grep -B45 "Test unit written to.*<name>" <log> | tail -50`
  (the ASAN/timeout report immediately precedes the write line).
- Repro a candidate single-input on the ASAN build:
  `timeout 30 ./fuzz_avc_asan <file> -runs=1 -timeout=25` — rc=0 + "Executed in
  N ms" means NO crash, regardless of a filename saying "crash". Manual
  `*_crash_*.bin` saves from sibling agents are often UBSAN/plain-build
  artifacts that do NOT fire ASAN (all 8 verified rc=0 in the Aug 9 sweep).
- Mirror to Windows with descriptive names: `<fuzzer>_timeout_<hash8>.bin`
  (e.g. `avc2_timeout_e78fc738.bin`), `hevc2_timeout_<hash8>.bin`; dedupe by
  sha1 BEFORE downloading (timeout-X and slow-unit-X with the same hash =
  same input).
- `-jobs=N` runs: the parent log (e.g. `fuzz_avc_asan3.log`, shows "pulse...")
  is NOT the whole story — some workers die of startup timeouts (their log
  stops at low #N with `SUMMARY: libFuzzer: timeout` + `Job exited with exit
  code 70`) while others keep finding NEW coverage. Check every `fuzz-N.log`,
  and remember a `timeout 1800` wrapper kills the whole run at 30 min even if
  workers are alive.
- Box state drives timeout triage: with 10+ ASAN processes on a 9 GB box,
  exec/s drops to ~0 and seeds themselves trip `-timeout=10` (21 of 26
  artifacts in one sweep were sha1-identical to seeds/corpus members → benign).
  Treat a timeout as a real hang ONLY after the plain-harness discriminator.
- Sweep reporting: per-fuzzer rows need binary, corpus (+files loaded from the
  log's `N files found in <corpus>/` line), last `#N` run counter, last
  cov/ft/corp, real exec/s, ASAN error count, artifacts. Cross-check the ps
  section against log mtimes — "log exists" ≠ "fuzzer running"; the HEVC
  fuzzers had logs but were interrupted hours ago.

## Artifact triage: crash vs timeout

- **Crash (real bug):** log contains `ERROR: AddressSanitizer`. Grab the stack;
  top frames in `libavc/...` or `libavc/common/...` with file:line = bug location.
  SFTP the artifact to the Windows audit dir and identify the bug class
  (e.g. OOB WRITE — the class ASAN catches that Windows UBSAN builds miss).
- **Artifact file with NO matching `Test unit written to` line in ANY log** =
  sibling-agent/manual save, not a fuzzer write — repro it anyway on the ASAN
  build (rc=0 → benign). Aug 9: `jpeg_crash-4e5c616e` (7718B) existed with a
  "crash" name but the jpeg log had 0 ASAN and no write line; single-input
  repro ran 37ms rc=0 ("Corrupt JPEG data" only). A crash-named file is never
  evidence by itself — the repro rc is.
- **Known READ bugs can be ASAN-invisible through the official harness — don't
  block the campaign on them.** The documented libavc exp-Golomb OOB read
  (`ih264d_uev`, CWE-125, 11-byte SEI trigger `0000000106000000020000`) does
  NOT fire ASAN through `avc_dec_fuzzer.cpp`, even with an exact-size
  `malloc(n)` repro driver (all 5 prior `*_crash_*.bin` files rc=0). Two
  reasons: (1) the harness's `decodeHeader()` phase consumes short SEI-only
  inputs before frame decode ever sees them; (2) libFuzzer input buffers carry
  capacity slack, so small OOB reads past logical end stay inside the
  allocation — ASAN only fires on block-boundary crossings. Implication: a
  "known bug doesn't reproduce" is NOT evidence the bug is fixed or that the
  hunt is broken — it's the expected ASAN blind spot for small reads. Note it
  and keep fuzzing for WRITES/UAF (the class ASAN actually catches). Quick
  check: exact-alloc driver pattern (`malloc(n)` exactly, copy input, call
  LLVMFuzzerTestOneInput) distinguishes harness-buffer-slack masking from a
  genuinely fixed bug.
  **CLOSED (Aug 9, bound-check patch probe): the uev over-read is FINAL
  not-ASAN-detectable.** Patching `ih264d_uev` with an early-return bound
  check (`u4_ofst + 32 > u4_max_ofst → -1`), rebuilding, and fuzzing the
  patched tree 30 min (21k execs on the merged corpus incl. all known
  triggers): 0 ASAN, 0 artifacts — the read stays inside the decoder's own
  zero-padded 256KB bitstream buffer, never crossing an ASAN redzone. The
  check-fires proof (gc-sections unit probe) + full recipe live in
  `asan-libfuzzer-verification` §4c /
  `references/bounds-check-probe-uev-case.md`.
- **Timeout / slow-unit (`*_timeout-*`, `*_slow-unit-*`):** NOT memory bugs.
  Class = hang/DoS-by-hang — but MOST resolve as fuzzer-config artifacts, not
  real hangs. Triage in this order (full recipe + libavc plain-build in
  `references/timeout-triage-methodology.md`):

  1. **Is it the fuzzer's own seed?** libFuzzer artifact names are
     `<kind>-<sha1-of-content>` — the hash IS the file's SHA1. Run
     `sha1sum ~/fuzz/<seeds> ~/fuzz/*.h264` and compare to the artifact
     filename. Seeds tripping a too-tight `-timeout` (wall-clock limit on an
     ASAN build on an overloaded box) is the #1 cause: 2 of the first libavc
     timeouts were byte-identical to the seed files, 3 more were 1-byte
     mutants of seeds. Identical hash = conclusive, no further repro needed.
  2. **Structural sanity:** scan start codes (00 00 00 01 / 00 00 01), count
     NAL types (7=SPS, 8=PPS, 5=IDR, 1=slice, 9=AUD), and parse SPS
     dimensions with a small Exp-Golomb reader (skip scaling lists for
     High/100 profile). Normal structure + tiny dims (≤480p here) rules out
     the missing-slice / corrupt-SPS-huge-allocation pathology.
  3. **Decisive test — plain (non-ASAN) harness:** rebuild the same sources
     without sanitizers, then `time` one decode per artifact. If EVERY input
     completes rc=0 in <4 s CPU, there is no hang — ASAN (~2–4×) + scheduler
     starvation inflated wall time over the limit. Only a unit that never
     completes in the plain build is a real hang/DoS candidate worth
     stack-level digging.
- Startup timeouts on legitimate seeds ("slow-unit" during
  `ReadAndExecuteSeedCorpora`) are benign — libFuzzer logs and continues.

## Expanding the corpus (ffmpeg seeds)

Use `scripts/gen_h264_seeds.sh` (validated): varies resolution (96x96→480x270),
framerate, GOP (`-g 5..250`), profile (baseline/main), bitrate. Key rules:

1. **Keep every seed under `-max_len`** (e.g. 200000) — libFuzzer truncates
   oversize inputs. `stat -c%s` each file; re-encode oversize at lower bitrate.
2. **libx264 silently downgrades profiles.** `-profile:v main` with
   `-preset ultrafast` emits Baseline (profile_idc=66) because no main-only
   features are used. Force real Main with
   `-x264-params "cabac=1:bframes=3:ref=2"` → profile_idc=77.
3. **Verify SPS profile bytes, not ffprobe strings** (ffprobe reports
   "Constrained Baseline" misleadingly even for Main). Sniff the SPS NAL:
   `python3 -c "d=open(f,'rb').read(); i=d.find(b'\x67'); print(d[i+1])"`
   (66=Baseline, 77=Main, 100=High).
4. Validate a sample with `ffprobe -show_entries stream=codec_name,width,height`.

## Launching / relaunching instances

```bash
cd ~/fuzz && setsid nohup ./fuzz_avc_asan <corpus>/ -max_len=200000 -timeout=10 \
  -rss_limit_mb=3000 -artifact_prefix=<pfx>_ > <log> 2>&1 < /dev/null &
```

- **`setsid nohup ... < /dev/null &` is REQUIRED.** Plain `nohup ... &` over a
  paramiko channel got reaped ~1 min after launch (process-group teardown when
  the sibling agent relaunched the other instance). `setsid` detaches the
  process group; verify with `ps` after 30–60 s AND confirm the log shows
  `N files found in <corpus>/`.
- **`nohup … & disown` alone suffices when the launch is the SSH command's
  FINAL statement** (validated c15: 4 campaigns survived the script exit —
  same PIDs, growing `etime`, via a fresh SSH at t+90s). `setsid` remains
  belt-and-braces when sibling agents may tear down process groups mid-window.
  After ANY launch, verify persistence TWICE: in-script at t+30s (pulse line)
  AND post-script via fresh SSH (same PIDs, `etime` growing, `#N` pulse
  higher, cov strictly increasing — c15: avc 2974→3466, hevc 3289→3438 at
  pulse #64→#128). Count the full windows, don't eyeball:
  `ps -eo args | grep -c 'max_total_time=3600'`.
- **Corpus bloat stalls relaunches — use a FRESH curated corpus, not the
  grown one.** After campaign 1 grew `corpus_avc/` to 800+ units/34 MB, a
  `-jobs=8` relaunch on it spent nearly all time on RELOAD (workers stalled at
  #128–#512, exec/s ~0, one worker never even logged). Relaunch against a new
  dir seeded from the ORIGINAL curated seeds (`mkdir corpus_avc3 && cp
  seeds_avc/* corpus_avc3/`), and trim `-max_len` to ~60000 when the biggest
  seed is ≤58 KB — campaign 3/4 (fresh seeds, 60000) kept finding NEW coverage
  at ~4× the unit rate of the bloated-corpus run. The grown corpus's VALUE is
  preserved as a seed source for later merges; it's just a bad live corpus.
  NUANCE (Aug 9 closing sweep): the bloat-stall is a MULTI-WORKER problem. A
  single worker (no `-jobs`) loaded a grown 704-file/59MB corpus in seconds
  and fuzzed immediately (exec/s 2-10, corpus still finding NEW) — only
  `-jobs=N` runs choke on RELOAD. So relaunching a single worker against the
  grown corpus is fine; the fresh-curated-corpus rule targets multi-worker
  relaunches.
- Second instances: single worker (no `-jobs`), so load impact is one core.
- **Never point a second fuzzer at a LIVE corpus dir another instance is
  writing.** libFuzzer writes new coverage units back into the corpus dir it
  was given at launch; two writers clobber each other's state files. Copy the
  seeds per instance (`cp -r seeds_hevc seeds_hevc_420p`) and launch the
  variant against its private copy — a multi-thousand-file cp is seconds.
- **Relaunch conditionals: check `ps` BEFORE relaunching.** If the target
  process is alive, its log mtime is fresh, and it's still emitting `NEW`
  lines, SKIP the relaunch and report why — do not kill a progressing instance
  just to apply a config tweak (Aug 9: hevc3 was alive at cov 4798, so the
  planned hevc4 relaunch was correctly skipped even though hevc3 still ran the
  old `-timeout=10`; only the dead libavc run was relaunched as avc3).
- **After launching, add the new log to your sweep's log list.** A hardcoded
  LOGS list silently omits freshly created logs — the Aug 9 sweep missed
  `fuzz_avc_asan3.log` (the relaunch's own log) and the status table had to be
  re-checked with a follow-up script. Build the list dynamically
  (`ls ~/fuzz/*.log`) or append the new name in the same step as the launch.
- **`-artifact_prefix` directory must pre-exist** — `mkdir -p art_asan/` or
  libFuzzer dies instantly with `ERROR: The required directory "art_asan/"
  does not exist` (silently swallowed when launched via nohup; check the log
  after 5 s or you've wasted the window).
- **Quick verification campaigns need a SMALL curated corpus.** `-runs=1` on
  a 1400-file corpus dir HANGS during corpus init (one slow seed decodes for
  minutes before any fuzzing starts) — you'll see the process alive with no
  `#N` stats. For reachability probes (e.g. "does any input execute this
  write?"), seed 3–6 known triggers + real seeds into a fresh dir. When a
  probe finishes, the log shows `Done N runs in N second(s)` — grep for that
  line to confirm completion, don't assume from `pgrep`.
- Watch RSS: 8 workers × ~400 MB + extras on a 9 GB box is near the limit;
  `-rss_limit_mb=3000` per worker is fine but monitor `free -h`.

## Rebuild recipe (libavc, Linux — VALIDATED Aug 2026)

```bash
cd ~/fuzz && clang++ -O1 -g -msse4.1 -fsanitize=address,fuzzer -fno-omit-frame-pointer \
  -I libavc -I libavc/decoder -I libavc/common -I libavc/fuzzer \
  -I libavc/common/x86 -I libavc/decoder/x86 \
  libavc/fuzzer/avc_dec_fuzzer.cpp -x c libavc/decoder/*.c libavc/common/*.c \
  libavc/decoder/x86/*.c libavc/common/x86/*.c \
  -o fuzz_avc_asan
```

- **The x86 include dirs + x86/*.c sources are REQUIRED on x86_64** — without
  `-I libavc/common/x86 -I libavc/decoder/x86` every TU dies with
  `fatal error: 'ih264_platform_macros.h' file not found` (the AOSP cmake adds
  those dirs + the ssse3/sse42 sources on non-ARM; mirror it). Exclude `arm/`,
  `armv8/`, `riscv/` subdirs — the top-level `*.c` globs skip them anyway.
- **No `_aligned_free`→`free` sed needed on Linux** — the harness's
  `iv_aligned_free` already calls plain `free()` outside `#if defined(_WIN32)`
  and the posix_memalign shim is Windows-guarded too; it builds clean as-is.
- If the harness carries debug `fprintf(stderr, "[dbg] ...")` spam (per-input
  fflush destroys exec/s), build from a stripped copy, KEEP the original for
  repro: `sed '/\[dbg\]/d' avc_dec_fuzzer.cpp > avc_dec_fuzzer_nodbg.cpp`.
- Binary is fine unless dead; only rebuild when the fuzzer is dead/missing.
- **Fast harness-iteration pattern: compile the decoder once, relink often.**
  `clang -O1 -g -fsanitize=<same-suite> ... -c decoder/*.c decoder/x86/*.c
  common/*.c common/x86/*.c` into `obj/`, then each variant is a ~30 s link:
  `clang++ -fsanitize=<same-suite> -DDISABLE_AVX2 -I... obj/*.o <harness_variant>.cpp
  hevc_one_main.cpp -o fuzz_variant`. Sanitizer flags MUST match between the
  .o compile and the link (mix -fsanitize=null objects with an ASAN link =
  undefined references). This turns a 4–5 min per-variant full rebuild into
  minutes total for a whole variant matrix (ASAN / null-UBSAN / -O0 /
  instrumented fmt_conv). For single-shot binaries (tiny main calling
  LLVMFuzzerTestOneInput) use `-fsanitize=address` WITHOUT `,fuzzer` — and do
  NOT drop `-msse4.1` from the recipe: the common/x86 SIMD files then die with
  `always_inline function '_mm_cvtepu8_epi16' requires target feature
  'sse4.1'` (got bitten rebuilding the single-shot harness without it).
- Quick `-fsanitize=fuzzer` availability probe: compile a TU with NO main
  (`echo 'int foo(){return 0;}' | clang++ -x c++ - -fsanitize=fuzzer -o
  /tmp/t`) — link success = libFuzzer runtime present. A "multiple definition
  of main" error against `libclang_rt.fuzzer.a` is ALSO proof the runtime
  links (FuzzerMain.o defines main); the real harness has no main so it
  builds fine. The stock fuzz_hevc_asan/fuzz_avc_asan are libFuzzer binaries
  (`strings <bin> | grep __start___libfuzzer_extra_counters`).

## Output-format variant harnesses (codec fmt_conv coverage)

AOSP codec fuzzer harnesses (hevc_dec_fuzzer.cpp, avc_dec_fuzzer.cpp) pick the
decoder's output color format from an input byte — libhevc uses
`data[6] % 6` over `{IV_YUV_420P, IV_YUV_420SP_UV, IV_YUV_420SP_VU,
IV_YUV_422ILE, IV_RGB_565, IV_RGBA_8888}` — so any given format gets only ~1/6
of mutation effort, and the harness's buffer layout follows the format. The
420SP path (2 buffers: Y + interleaved UV, bufs[2]=NULL by design) leaves the
420P fmt_conv branch (`ihevcd_fmt_conv_420sp_to_420p`, which WRITES
`pu1_v_dst`) dead/unreachable. To sweep format-specific paths (VALIDATED Aug 9,
libhevc 420P variant):

1. **Check whether the stock harness ALREADY contains the target path** under
   an input-selected knob before writing a new decoder — libhevc's allocFrame
   had a correct 3-buffer 420P case; it was just rarely selected. The patch is
   usually a pin, not new code.
2. **Copy the tree** (`cp -r libhevc libhevc_420p`) — carries any triage
   patches in decoder sources into the variant (keep them unless the task
   says strip).
3. **Pin the format** in LLVMFuzzerTestOneInput:
   `IV_COLOR_FORMAT_T colorFormat = IV_YUV_420P;` (enum in common/iv.h:
   420P=0x1, 420SP_UV=0xb, 420SP_VU=0xc) instead of the byte-6 lookup, and
   force allocFrame() to the 3-buffer layout (sizes W*H / W*H>>2 / W*H>>2,
   num_bufs=3, one iv_aligned_malloc per plane).
4. **Verify the chain before trusting the variant:** create_ip
   `e_output_format` → `ps_codec->e_chroma_fmt` (ihevcd_api.c:1212) → fmt_conv
   dispatch. Grep the dispatch to confirm your format hits the function you
   think it does (e.g. 420P → 420sp_to_420p → pu1_v_dst write at fmt_conv.c
   ~855-891).
5. **Smoke-test** on a real seed (`-runs=1`) for rc=0 before launching.
6. **Confirm new surface by cov delta:** a working variant climbs past the
   stock run's cov ceiling (420P hit cov 4761 vs 4336 max on 420SP = +425
   edges). That delta IS the dead-path-now-live evidence; report it.

## References

- `references/libavc-campaign-notes.md` — campaign state, hang finding, corpus
  layout for the libavc/libhevc audits.
- `references/libhevc-420p-variant.md` — the Aug 9 420P format-pin variant:
  exact 2-hunk harness diff (pin IV_YUV_420P + 3-buffer allocFrame), enum
  values, e_output_format→e_chroma_fmt chain, build/launch commands, cov
  delta evidence (4761 vs 4336), 0-ASAN result.
- `references/timeout-triage-methodology.md` — full timeout/slow-unit triage
  recipe: artifact-vs-seed hash check, NAL/SPS analysis, plain-harness
  discriminator, libavc plain build, evidence from the Aug 2026 libavc case.
- `references/harvest-forensics.md` — complete-window harvest command set
  (per-log one-liner, completion poll loop, savestate timing), the
  TAB/multi-space pulse-format pitfall, and c19 evidence (4/4 windows,
  272k runs, 0 ASAN, corpus +1,949 files, hevc cov record 5221).
- `scripts/build_avc_plain_harness.sh` — builds the plain (non-ASAN) libavc
  decoder harness on the VM (`bash ~/fuzz/build_avc_plain.sh` → binary in
  `~/fuzz/build_avc_plain/avc_dec_plain`); the decisive hang-vs-artifact tool.
- `scripts/sweep_collect.sh` — full-campaign enumeration (ps, logs, recent
  files, artifact scan, per-log tail/ASAN count/stats). Run before any status
  report or artifact hunt.
- `scripts/sweep_reports.sh` — per-artifact triage: sha1 + seed-match vs
  prebuilt hash index, artifact→log mapping, stack extraction, single-input
  ASAN repros, real exec/s.
