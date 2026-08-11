# Disclosure-readiness audit — verify upstream fix status BEFORE filing (2026-08-09)

When a fuzzing/audit campaign produces findings, they are NOT reportable until
each one is mapped against: the audited AOSP copy (commit/date), AOSP `main`
HEAD, every release branch, and the CANONICAL upstream repo. Produced
`DISCLOSURE_READINESS.md` for 5 AOSP decoder findings — the technique below.

## The live-audit recipe (from the Kali VM — it has internet; Windows curl is
blocked on googlesource, the VM is not)

1. **Full clones, all branches** (googlesource rate-limits rapid `?format=TEXT`
   fetches with 404 bursts — spacing + full clones avoids the whole class):
   ```bash
   git clone https://android.googlesource.com/platform/external/libhevc   # AOSP
   git clone https://github.com/ittiam-systems/libhevc                     # upstream maintainer
   git clone https://git.code.sf.net/p/giflib/code                         # canonical giflib
   git -C <repo> branch -r | grep release   # android13/14/15-release branches
   ```
2. **Per-finding line check**: grep the exact bug line in (a) AOSP main HEAD,
   (b) each android<NN>-release branch, (c) upstream main. Record: fixed?
   `git -C <repo> log -1 --format='%H %cd'` gives the audited copy's date.
3. **Upstream fix hunt**: for each finding, search upstream history for the
   fixing commit (`git log -S 'guard string' -- <file>`). giflib's fix = 6.1.3
   tag (`edff4ae`, 2026-04-12) adds `if (GifFile->ImageCount <= 0)` in
   DGifDecreaseImageCounter; Ittiam partially fixed the shift-UB via
   `(UWORD32)value << ...` (commit 5ad6b713) — NOT in AOSP.
4. **Produce the table** (the deliverable shape):
   | Finding (file:line) | Audited AOSP copy (version/commit/date) | Fixed in AOSP main? | Android branches affected | Fixed upstream? |
   Every finding gets a row. Supporting facts section: per-file last-touch
   dates (`git log -1 -- <file>`), AOSP-never-upgraded notes (AOSP main HEAD ==
   audited commit → every release branch ships the bug).
5. **Report-path recommendations** (what the table implies):
   - Android Security Rewards (`g.co/androidsecurityreport`) + AOSP Issue
     Tracker — primary for all AOSP-shipped bugs; one report per library,
     citing audited commit + exact line + ASAN/UBSAN evidence + branches affected.
   - Upstream maintainers (e.g. Ittiam github) — secondary; AOSP only mirrors
     their code, so fixes must land upstream first to propagate.
   - If upstream ALREADY fixed: report is a vendor-lag sync request (nothing to
     invent). If upstream UNFIXED: coordinated-disclosure candidate — the
     highest-value report ("no fix exists anywhere").
   - Order by impact × fixability (e.g. remotely-reachable + unfixed-everywhere
     first).

## Pitfalls hit
- googlesource `?format=TEXT` rate-limits into 404 bursts — full git clones
  instead; space the fetches if you must use TEXT.
- Wrong-`cd` / 2-byte greps gave bogus "0 counts" for release branches —
  re-verify from the CORRECT repo; all bug lines were confirmed present in
  android13/14/15-release.
- Dead upstream URLs: `TeamHypersomnia/giflib` and `gitlab.com/limx/giflib`
  are 404 — canonical giflib is SourceForge `git.code.sf.net/p/giflib/code`.
- Conservative flags: a "partial fix" (e.g. Ittiam's cast that fixes the
  signed-overflow but not the shift-count edge) → mark PARTIAL, note the
  residual edge was not re-reproduced.
- No CVEs assigned yet = pre-disclosure; say so in the doc.

## Deliverable
`aosp-audit/DISCLOSURE_READINESS.md` (2026-08-09) — the 5-finding table +
supporting facts + report-path recommendations. Reuse this exact structure for
any future campaign's disclosure phase.
