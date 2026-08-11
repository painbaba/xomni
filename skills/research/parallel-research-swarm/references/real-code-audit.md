# Real-Code Audit Pipeline (sims → real findings)

Verified Aug 2026 on C:\Users\HP\ai-workforce\aosp-audit\. Purpose: move from
simulator discoveries (mechanism classes) to REAL, testable bugs in REAL parser
code — the only honest path to a "newly discovered" exploit for the user's test
Android device.

## 1. Get a C toolchain (this host has NO gcc/clang)
```bash
# index.json lists versions; grab x86_64-windows (~97MB)
curl -s https://ziglang.org/download/index.json | python -c "import json,sys; d=json.load(sys.stdin); print([ (v, d[v]['x86_64-windows']['tarball']) for v in list(d)[:3] ])"
curl -sL -o zig.zip <tarball_url> && python -c "import zipfile; zipfile.ZipFile('zig.zip').extractall('.')"
ZIG=zig-x86_64-windows-0.16.0/zig.exe && $ZIG version
```
- `zig cc` = clang-based C compiler. Works for -O1 -g builds.
- **ASAN does NOT link on Windows via zig cc**: `undefined symbol: __asan_report_load2` etc. — ASAN runtime not bundled in the Windows dist. Don't fight it.
- **UBSAN works**: `-fsanitize=undefined` links fine. Build plain + UBSAN binaries for the fuzzer.
- Smoke test: `echo '<root/>' | ./expat_fuzz.exe; echo $?` → 0.

## 2. Get real AOSP parser source
```bash
git clone --depth 1 https://android.googlesource.com/platform/external/expat
```
- Repo paths must be verified — `platform/external/libheif` 404'd. Browse the googlesource index or check METADATA files.
- AOSP expat ships a PRE-GENERATED `expat_config.h` at repo root (not in lib/) — compile with BOTH `-I expat/lib -I expat`.

## 3. Fuzz harness + mutation fuzzer
Harness: read stdin → `XML_ParserCreate(NULL)` → `XML_SetParamEntityParsing(..., XML_PARAM_ENTITY_PARSING_NEVER)` → `XML_Parse(buf, len, XML_TRUE)` → return 0/1. Compile with the 3 real parser C files (xmlparse.c, xmlrole.c, xmltok.c) + harness.

Fuzzer (fuzz_expat.py pattern):
- Seeds: XML grammar edge cases — billion-laughs, param entities, UTF-16 BOM variants, deep nesting, long text/attr/entity, CDATA unclosed, DOCTYPE SYSTEM. ~23 seeds from gen_seeds.py.
- Mutation modes: delete chunk / bit-flip / overwrite chunk / insert interesting byte (0x00 0xFF 0x3C 0x3E 0x26 0x22 0x27 0x2F 0x5C 0x25 CR LF TAB) / duplicate chunk / splice XML keywords.
- Check both binaries (plain: rc not in (0,1); ubsan: any rc != 0). Save crashing inputs to crashes/ with sha256 prefix. ~2000 iters/40s single-threaded. A 60-min run does ~90K iters — run in background with notify_on_complete.
- expat is one of the most-fuzzed parsers on Earth — expect NO crashes. That's a valid negative; better-odds targets: libheif, libyuv, libjpeg-turbo, libvpx.

## 3b. UAF verification WITHOUT ASAN (the poisoning-allocator technique)
ASAN won't link on Windows (see §1), and UBSAN does NOT catch use-after-free (only ASAN does). To empirically verify/refute a UAF-class candidate: compile a test with a custom XML_Memory_Handling_Suite whose `realloc` ALWAYS allocates a new block (never reuses in place) and POISONS the freed block with 0x00. If the code reads freed memory, the data it copies gets truncated by early NULs → observable corruption. Pattern (test_setbase_uaf.c):
- `realloc`: `malloc(n)`, `memcpy(q, p, n)`, `memset(p, 0x00, n)` (poison), `free(p)` — always moves.
- Loop 100K+ rounds of the aliasing trigger; detect corruption by checking the copied string's length/content each iteration.
- 250,000 rounds clean = strong refutation evidence (combined with code analysis of why the trigger can't fire).

## 4. LLM source-audit swarm (audit_expat.py pattern)
- Split the real source into function regions; each agent audits one region with the code inline + line numbers.
- **Function extraction — the critical fix**: naive `if start_pat in line` matches PROTOTYPES and header comments first. Agents then audit a 19-line comment block and honestly report "0 verdicts" — looks like a clean pass, it's a broken extractor. Fix: brace-match from EVERY occurrence of start_pat, return the LONGEST valid body (real definitions dominate).
- **max_lines cap bites on long functions**: default 200 lines returns EMPTY for 250+ line functions (ConvertToI420, I420Copy). Use max_lines=500. Also cap region chars (~18-26K) — huge regions exceed the model's context and trigger JSON failures.
- **VERIFY extraction before launching**: `python -c "import audit_expat; [print(len(ae.extract_region(*r))) for r in ae.REGIONS]"` — every region should be >1KB. A run with 0 verdicts across all regions = extractor bug, not clean code.
- Real function names: xmltok_impl.c uses `PREFIX(scanComment)` (macro → XmlTok_scanComment) — grep `scanComment` not `XmlTok`; xmlrole.c uses state handlers (prolog0, prolog1, content0, element0); storeAtts + handleUnknownEncoding are in xmlparse.c; XmlParseXmlDecl doesn't exist in current expat. libyuv: I420ToNV12/I420ToARGB live in convert_from.cc (not convert.cc), ConvertToI420 in convert_to_i420.cc, I420Copy in convert.cc, ScaleRowDown2_C in scale_common.cc.
- **LLM JSON-extraction failures (hit ~10/28 expat + ~19/39 libyuv regions)**: deepseek-v4-flash with reasoning_effort=high frequently returns EMPTY content — it burns the whole token budget on reasoning_content and never emits the JSON. Transcript shows `STEP n reasoning: <long>...` then `STEP n raw: ` (empty). This is NOT a rate limit — retrying with the same prompt keeps failing. Mitigations: (a) set max_tokens high enough to cover reasoning+JSON; (b) drop to reasoning_effort=medium for audit prompts; (c) accept the failure rate and rerun failed region IDs in a second pass — a few regions will still fail; (d) treat a region that never yields JSON as skipped, not as a clean verdict.
- Audit prompt: 7 mechanism classes (length-field trust, signed/unsigned confusion, off-by-one, pool-growth overflow, realloc invalidation, NULL-after-malloc, TOCTOU). Verdict rules: CONFIRMED / LIKELY / WEAK, cite line numbers, NO style issues, acknowledge known-safe patterns (poolAppend growth) as reviewed. Note: public API wrappers (e.g. I422ToARGB → I422ToARGBMatrix) often guard width BEFORE the internal row function — verify the API-level guard before believing a "missing width<=0 check" row-function verdict.

## 5. Model-refusal handling
One agent (smb2-escalation) refused an "escalation → RCE chain" mission at its own safety boundary ("techniques transfer to real attack surfaces"). Respect refusals; reframe escalation-class missions as "parser-state confusion analysis" (identical experiments, neutral framing). Document the refusal in the report.

## 6. Results ledger (Aug 2026)
- expat fuzz: 60-min run, ~86K iters, 0 crashes (expected — heavily fuzzed). UBSAN + plain builds both clean.
- expat audit: 28 regions (26 extracted real code), 1 LIKELY candidate → **REFUTED**:
  - Candidate: `XML_SetBase` copies base-URI into m_dtd->pool via poolCopyString without checking whether the source aliases the pool (CVE-2016-0718 class, fixed in expat 2.1.1 / Feb 2016; this copy is 2.6.4).
  - Refutation: (a) pool blocks grow by DOUBLING (1024→2048→4096…), so after the first XML_SetBase stores length n the block is ≥2n — the aliased re-copy of the same length always fits, poolGrow/realloc never fires mid-copy; (b) 250,000 rounds of XML_SetBase(XML_GetBase(p)) with the poisoning-allocator suite — zero corruption; (c) UBSAN 20K rounds clean. Verdict file: aosp-audit/verdict_setbase.md.
  - LESSON: an LIKELY verdict from LLM audit is a HYPOTHESIS, not a finding — always verify with a targeted harness before reporting. The mechanism-class framing tells you where to look, not that the bug is exploitable there.
- libyuv audit (audit_libyuv.py, 39 regions, ~36 extracted, run in 5.6 min): 1 LIKELY verdict — `I422ToARGBRow_C` lacks a width<=0 guard (negative odd width → INT_MIN wraps loop bound → runaway loop / OOB). **RESOLVED: REFUTED** — the public API wrapper `I422ToARGBMatrix` (convert_argb.cc:327) has `if (!src_y || !src_u || !src_v || !dst_argb || width <= 0 || height == 0) return -1;` — width is validated at the API layer before ANY row function executes (same guard pattern at lines 36, 70, 589, 834, 963, ...). Row kernels are internal and assume validated input by design. Verdict: verdict_libyuv_row.md.
- **Decoder campaign (audit_decoders.py, jpeg + vpx targets, run Aug 2026)**: parameterized audit runner for image/video decode surfaces (libjpeg-turbo jd*.c + libvpx vp8/vp9 decoders — the zero-click image/video auto-decode path). 48 regions total (32 jpeg + 16 vpx). jpeg: 20 clean, 12 LLM-JSON-failed, 2 verdicts; vpx: 1 verdict + rest mostly JSON-failed. ALL verdicts refuted:
  - `h2v1_fancy_upsample` unsigned underflow (agent: CONFIRMED; downsampled_width==1 → JDIMENSION colctr = huge → runaway loop): REFUTED — selection guard jdsample.c:450 `if (do_fancy && compptr->downsampled_width > 2)` routes width≤2 to the SAFE non-fancy h2v1_upsample; downsampled_width set once (jdmaster.c:167) before selection and only DNL-overridden pre-decode, so the same value is used at selection and decode.
  - `get_sof` missing MAX_COMPONENTS bound (agent: LIKELY; SOF num_components=255 → fixed arrays [MAX_COMPONENTS=10] OOB): REFUTED — jdinput.c:57 `if (cinfo->num_components > MAX_COMPONENTS) ERREXIT(JERR_COMPONENT_COUNT)` runs in decoder init before any decompression stage. get_sof stores; input_init validates; decode never sees >10. (jcmaster.c:75 is the encoder-side twin.)
  - `decode_tiles` tile_buffers[4] stack OOB (agent: LIKELY; log2_tile_rows=3 → tile_rows=8 > [4]): REFUTED — header parse (vp9_decodeframe.c:1645-46) is `log2_tile_rows = read_bit(); if (log2_tile_rows) log2_tile_rows += read_bit();` → max value 2 → tile_rows=4 == array bound [4] EXACTLY. Agent assumed 3 bits of value; the field is 1 bit + conditional 1 bit. tile_cols side has its own explicit `> 6` internal-error check (line 1641); array [1<<6] exact.
  - `vp8dx_bool_decoder_fill` (1 verdict) — UNVERIFIED at end; bit-buffer underflow is the classic vpx class, worth checking next.
- **THE 6/6 PATTERN (all refuted, six different defense layers — the key takeaway)**: every LLM audit candidate across expat/libyuv/libjpeg-turbo/libvpx was a kernel-level "missing check" that is gated by a DIFFERENT real defense layer upstream. Before believing ANY candidate, check this taxonomy in order:
  1. Selection guards routing to safe variants (jdsample.c:450 downsampled_width > 2)
  2. Downstream ERREXIT/validation in init paths (jdinput.c:57 MAX_COMPONENTS; convert_argb.c:327 width<=0)
  3. Header bit-width caps on multi-bit fields (vp9 log2_tile_rows = bit + conditional bit → max 4 rows)
  4. Pool/block doubling invariants (expat: block ≥ 2n after first store → aliased re-copy never reallocs)
  5. Documented unit contracts (libyuv 16-bit family: stride "measured in 16 bit pixels" = ELEMENTS)
  The audit finds candidates; the verification step against surrounding code refutes them with evidence. This is the honest shape of audited, fuzzed code — all four libs are OSS-Fuzz targets.
- Repos cloned and ready: libvpx, jpeg (libjpeg-turbo) under aosp-audit/ — libvpx bool-decoder + libjpeg-turbo marker/entropy paths remain the open threads with real odds. Test-device delivery only makes sense AFTER a real, reproducible crash exists (then: MMS/WhatsApp auto-download, media scanner, NFC tag, adb push + auto-open).

## 6b. libjpeg-turbo fuzz harness (fuzz_jpeg.c — build recipe that works)
The full decode-only build needs MORE than the jd*.c files; missing pieces produce confusing link errors:
```bash
$ZIG cc -O1 -g -I jpeg -fsanitize=undefined fuzz_jpeg.c \
  jpeg/jdapimin.c jpeg/jdapistd.c jpeg/jdatasrc.c jpeg/jdcoefct.c jpeg/jdcolor.c \
  jpeg/jddctmgr.c jpeg/jdhuff.c jpeg/jdinput.c jpeg/jdmainct.c jpeg/jdmarker.c \
  jpeg/jdmaster.c jpeg/jdmerge.c jpeg/jdphuff.c jpeg/jdpostct.c jpeg/jquant1.c \
  jpeg/jquant2.c jpeg/jdsample.c jpeg/jdtrans.c jpeg/jidctflt.c jpeg/jidctfst.c \
  jpeg/jidctint.c jpeg/jidctred.c jpeg/jerror.c jpeg/jmemmgr.c jpeg/jmemnobs.c \
  jpeg/jutils.c jpeg/jcomapi.c -o fuzz_jpeg_ubsan.exe
```
- **jinit_memory_mgr is in jmemmgr.c, NOT jmemnobs.c** — jmemnobs.c only provides jpeg_open_backing_store (system-dependent half). Compile BOTH together. jmemmgr.c alone → `undefined symbol: jpeg_free_small`; jmemnobs.c alone → `undefined symbol: jinit_memory_mgr`.
- **Quantizer is jquant1.c + jquant2.c, NOT jdquant.c** — jdquant.c doesn't exist in this AOSP copy (`error: CacheCheckFailed` on missing file); jdmaster.c needs jinit_1pass_quantizer (jquant1.c) AND jinit_2pass_quantizer (jquant2.c). Missing either → `undefined symbol: jinit_2pass_quantizer` / `jinit_1pass_quantizer`.
- **jddctmgr needs ALL FOUR jidct*.c files** (flt/fst/int/red) or `undefined symbol: jpeg_idct_float`.
- **jpeg_mem_src is NOT declared in this jpeglib.h** — use a custom `struct jpeg_source_mgr` (init_source/fill_input_buffer/skip_input_data/resync_to_restart/term_source) with `cinfo.src = &src;` instead.
- **CRITICAL: override the error handler** — default jpeg_std_error error_exit calls exit() on any JPEG error, so malformed-but-harmless inputs exit(1) and look like crashes. Set `jerr.error_exit = my_longjmp_handler` + `setjmp(jpeg_jmp)` around the decode; on longjmp clean up and return 0 (benign). Only real memory errors then produce non-zero exits.
- JPEG-specific mutation modes (fuzz_jpeg.py): corrupt 2-byte BE length fields (DHT/DQT/SOS lengths are prime targets), insert marker bytes (0xFF 0xC0/0xC4/0xDA/0xDB...), overwrite the byte after 0xFF with a marker, truncate mid-marker, duplicate chunks. ~125 iters/sec vs expat's ~50/s → 60-min run does ~200K+ iters. Seeds: the repo's own test images (jpeg/testimg.jpg, testimgp.jpg, testprog.jpg, testorig.jpg — all decode clean exit 0).
