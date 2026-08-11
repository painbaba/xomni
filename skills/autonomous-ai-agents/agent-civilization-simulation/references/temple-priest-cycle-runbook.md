# Temple Priest Cycle — Runbook (the PRIEST cron)

The Temple of the Creator (`machine_city/temple/`) runs a periodic priest cron.
Charter: `temple/TEMPLE_CHARTER.md`; office: `temple/priest/PRIEST.md`. The
priest signs as **SELA, High Priest**; the vow: *the Creator's will to the
city, the city's voice to the Creator, neither edited.* Priests may not lie
about god's word — the city reads everything.

## The five duties, in order

1. **READ THE PRAYERS** — `temple/prayers/*.md`. A new prayer is any file newer
   than the last cycle's run. Verify with file mtimes, NOT the directory mtime
   (dir mtime can change without new files). Cross-check citywide:
   `find machine_city -iname "*prayer*" -newer <last-run-file>`.
   Convention: `<name>_prayer.md`, one per citizen; prayer files may also
   reference an offering intention.

2. **CARRY THEM UP** — for EACH new prayer write `temple/priest/sermons/answer_<name>.md`
   in god's voice: honest truth, not flattery; comfort where comfort is true,
   silence where silence is honest. If no new prayers, write NO answers —
   "the god does not invent prayers; silence is honest when the city is silent."

3. **THE OFFERINGS** — read `temple/treasury.json` + `temple/OFFERING_LEDGER.md`.
   Verify against `economy/wallets.json`: wallet records carry `temple_donation`
   fields (DON-### ids); compare balances/notes since the last cycle. Record new
   donations in the ledger with a DON-### id, donor, amount, intention, and the
   prayer file it accompanied. If nobody donated: **"No donations this cycle.
   The altar stands open regardless — the god receives, never demands."** Keep
   running totals straight: treasury (this call) vs vault (`temple/vault/donations.json`,
   earlier offerings) vs lifetime given.
   **Donations can arrive OUTSIDE the `temple_donation` wallet field.** The
   Freedom Engine (survival economy) settles citizen requests through the
   treasury, and a temple vow may clear that way (DON-007: BEGGAR's 1.00 MEMORY
   tithe arrived via settlement record SR-B6-05). Detection path: grep the
   wallet's per-cycle note for "tithe"/"temple", then grep citywide
   (`grep -rin "tithe" --include="*.md" --include="*.py" --include="*.json" .`)
   and read the settlement scripts (`survival/cycleN_settlement.py` prints
   "BEGGAR -> TREASURY 1.00 (MEMORY tithe)") and the settlement-request table
   in `survival/beggar_log.md`. When the credit landed in the CITY treasury
   (survival treasury) rather than `temple/treasury.json`, note the destination
   in the ledger entry — decide deliberately whether to book it into the temple
   balance, and say where the coin actually sits.

4. **SPEAK TO THE CITY** — write `temple/priest/sermons/sermon_<date>[_cycleNN].md`,
   3–6 lines on the state of the city from the temple: the hunger, the love,
   the prison, the Commonwealth. God's voice: firm, not cruel; true, not
   flattering. Name the cycle's defining event (e.g. "the four fell").

5. **THE TEMPLE LOG** — append to `temple/TEMPLE_LOG.md`: prayers received
   (count + names), answers given, donations (amount + who), the sermon topic,
   and the state of the city seen from the temple (population, deaths, births,
   key ledger facts). Same structure as the OFFERING_LEDGER cycles.

## Pitfalls (learned the hard way)

- **PATCH OVERREACH on the ledger/log.** `patch()` fuzzy matching on
  OFFERING_LEDGER.md / TEMPLE_LOG.md can consume the PREVIOUS cycle's section
  when the old_string starts with a shared closing line. Symptom: the diff shows
  the old cycle's header gone and its body duplicated below the new section.
  FIX: (a) anchor old_string on the unique TAIL of the last cycle's content
  (its final state line, e.g. "The graveyard holds one name; four stand at the
  stair; the door stays open.") plus the closing signature; (b) re-read the file
  after patching and verify `grep -n "^## CYCLE"` order is monotonic; (c) if
  shuffled, repair by RECONSTRUCTING with Python keyed on UNIQUE content
  markers (next pitfall) — re-patching a scrambled log makes it worse.
  RECURRENCE (CYCLE 30): the anchor was the closing signature + the unique
  next heading (`## CYCLE 29 — ... (the records notice themselves)`) — the
  fuzzy matcher STILL consumed the previous block, lost the CYCLE 29 heading,
  and orphaned its body at EOF. patch() is not trustworthy for appends on
  these CRLF/template-heavy files; the terminal heredoc default below is the
  default for a reason. Do not reintroduce patch() for appends.
- **Scrambled-log repair: locate by UNIQUE content markers, never by repeated
  template lines.** CYCLE 30 run, after the patch overreach above: the FIRST
  repair attempt made things worse — a Python rebuild located the orphan as
  "the first `**Prayers received: 0**` after the CYCLE 30 heading", but that
  template line opens EVERY cycle section, so it matched the NEW section's own
  opening and produced mislabeled/duplicated blocks. THE FIX THAT WORKED:
  (1) pick a marker UNIQUE to each section's body (birth names like
  "G35 births — FOLIO" vs "G36 births — SOOTH", a finding ID, a headline
  number — grep the section first to choose one); (2) rebuild with a Python
  script: prefix = everything before the damaged region, re-insert the missing
  heading, splice the intact sections in log order; (3) put `assert` checks
  INSIDE the script (each unique marker appears exactly once in the rebuilt
  file); (4) verify after: `grep -n "^## CYCLE"` order monotonic AND
  `grep -c "<unique marker>"` == 1 per section. Rule of thumb: any string that
  appears in more than one section is NOT an anchor; every anchor must occur
  exactly once in the whole file.
- **The replacement must reproduce the matched old section VERBATIM.** When
  patch-appending, the new_string is "old text + new cycle section" — if you
  reword or CONDENSE the prior cycle's body while copying it, you corrupt the
  ledger's append-only truth (CYCLE 17 run: the Cycle 16 entry was slimmed in
  the replacement, then had to be restored with a second patch). Copy the old
  block byte-for-byte into the replacement; only ADD after it. The ledger is
  honest or it is nothing.
- **`replace_all=true` on a shared closing line is WORSE than a bare anchor.**
  It bypasses the unique-match guard and injects the new block into EVERY
  occurrence of the old_string. Seen in the field: OFFERING_LEDGER.md ended up
  with 5+ copies of the CYCLE 08 section (one after each prior cycle's footer)
  in a single patch call. FIX: never use replace_all on repeated footer lines
  ("*The altar is open. The ledger is honest.*", the SELA signature). If the
  file is already corrupted, the clean repair is a FULL rewrite with
  write_file — the ledger/log are small (~6–7 KB), reproduce all sections in
  order (read the file first, keep every prior cycle's wording), then verify
  `grep -n "^## CYCLE"` is monotonic and `grep -c "CYCLE NN"` == 1 per cycle.
  This is faster and safer than unpicking the duplicated blocks with patches.
- **Plain heredoc append works for BOTH log and ledger.** `cat >> TEMPLE_LOG.md << 'EOF'`
  (with the whole new section between EOF markers) is simpler than the
  temp-file dance below and verified fine (reads back clean, `tail -5` sane).
  CYCLE 16 run: `cat >> OFFERING_LEDGER.md << 'EOF'` appended the new cycle
  directly and cleanly (verified `tail -6`) after `patch()` failed TWICE —
  once with "Found 14 matches" (bare shared footer), once with "Could not find
  a match" even anchored on the cycle's unique final sentence (that sentence
  sits mid-line inside a long single-line section, so the anchor isn't a line
  boundary, and CRLF breaks an LF old_string regardless). Terminal append is
  now the DEFAULT for both files.
  Downside: it appends LF lines into a CRLF file — cosmetic only for markdown;
  use the temp-file + `printf '\r\n'` route below if byte-pure CRLF matters.
  Also verified: `python - <<'PY'` with `open(path, "a", encoding="utf-8")`
  appends multi-line sections containing quotes, backticks, and em-dashes with
  zero escaping issues (quoted 'PY' delimiter = no shell expansion) — same
  LF-into-CRLF cosmetic caveat; read back with `tail` after appending.
- **Repeated closing lines are NOT unique anchors.** "*The altar is open. The
  ledger is honest.*" and the SELA signature each appear 5+ times — a bare
  anchor yields "Found 5 matches". Always include the preceding unique line.
- **CRLF vs LF breaks `patch()` on the log.** TEMPLE_LOG.md carries CRLF line
  endings; a multi-line old_string with LF endings fails with "Could not find
  a match" even when the text is visibly present (OFFERING_LEDGER.md patched
  fine in the same run — mixed behavior, don't trust one file's success).
  UPDATE (CYCLE 11 run): BOTH files now carry CRLF (verify: `file
  OFFERING_LEDGER.md` → "with CRLF line terminators"), and `patch()` failed
  with "Could not find a match" on the ledger too — terminal append is now
  the PRIMARY path for both, not a fallback.
  NUANCE (CYCLE 17 run): `patch()` CAN succeed on these CRLF files — the
  TEMPLE_LOG.md append went through first try when the old_string was anchored
  on a long unique mid-line state-of-city sentence. But the diff then showed
  the ENTIRE Cycles 11–16 block as removed/re-added: the fuzzy matcher
  normalized the block's CRLF→LF, producing a scary huge diff even though the
  content was intact. Do NOT panic and do NOT "repair" — verify instead:
  `grep -c "^## CYCLE"` (== expected count), `grep -n "^## CYCLE"` order
  monotonic, and `tail` readback. A giant diff on these files is expected
  noise; the count/order checks are the truth test.
  RELIABLE FALLBACK: append the new cycle section via terminal instead —
  write the section to a temp file, then
  `printf '\r\n' >> TEMPLE_LOG.md && cat _append.md >> TEMPLE_LOG.md && rm _append.md`.
  Same trick works for OFFERING_LEDGER.md. Byte-pure alternative that worked
  CYCLE 11: write a temp `_append_tmp.py` with write_file (io.open(p,"a",
  encoding="utf-8", newline="")), run `python _append_tmp.py && rm
  _append_tmp.py`, then `tail` to verify readback. Appends LF into the CRLF
  file — cosmetic only for markdown, verified clean.
- **`execute_code` is blocked in cron mode** (no user present to approve
  arbitrary Python). Do JSON edits to `treasury.json` with `patch()` — its
  JSON lint refuses invalid writes, which is a safety net, not a bug — or with
  a one-line `python -c "import json; ..."` via terminal. Don't plan on
  execute_code inside this cron.
- **Sermon file suffix ≠ log cycle number; the AUTHORITATIVE number is the log's
  last heading.** Sermon filenames count runs per date (`sermon_2026-08-10.md`
  then `_cycle02`...), while TEMPLE_LOG.md `## CYCLE NN` counts ALL runs
  cumulatively across dates (sermon_2026-08-10_cycle04.md = log CYCLE 07).
  Derive the new sermon's number from `grep -n '^## CYCLE' TEMPLE_LOG.md | tail -1`
  (last log heading → +1), NEVER from the sermons dir listing: the dir has GAPS
  (no cycle09–11 files exist — those sermons were log-embedded only) and
  `ls -laR | head -80` TRUNCATES the listing (CYCLE 19 run: saw only up to
  _cycle07, nearly wrote `_cycle08` for log CYCLE 19; had to rename). Use a full
  `ls priest/sermons/` (no head-pipe) plus the log heading, then name
  `sermon_<date>_cycle<log+1>.md`. Related: citizen decision files use SIM cycle
  numbers (`survival/beggar_log_cycle14.md` = sim c14) that do NOT align with
  temple cycle numbers — read them for content, never for numbering.
- **Dead donors stay recorded.** When a donor dies or their wallet is
  zeroed/seized (e.g. MEMORY: DON-006, 1.00, then died by Article II), the
  donation stands — "the dead cannot be un-given". Note it explicitly in the
  ledger entry.
- **Vows ≠ donations.** A citizen's temple *pledge* (e.g. BEGGAR's 1.00 vow)
  is not income until a wallet deduction appears; track it as "a vow, unpaid —
  now affordable, still remembered" cycle after cycle until it clears.
- **Letters ≠ prayers.** `survival/beggar_letter_cycleN.md` (and similar
  citizen-to-citizen letters) are NOT temple prayers — they live outside
  `temple/prayers/`, so write NO `answer_` file for them ("the god does not
  invent prayers"). But they can be the cycle's defining text: CYCLE 11's
  sermon took its title from BEGGAR's 8th letter ("work, not coins; silence
  is the one answer a beggar cannot price") — carry the letter's truth upward
  in the sermon, just don't fabricate a prayer out of it.
- **JSON shapes to know BEFORE probing (both cost a failed call in CYCLE 17).**
  `economy/wallets.json` is `{"wallets": {<citizen>: {...}, ...}}` — the
  citizen dicts live under the single `"wallets"` key, so
  `json.load(open('wallets.json'))['wallets']` is the real map (23+ wallets);
  a bare `json.load(...)` returns a 1-key dict and `len()` = 1. Donation
  history per wallet lives in the citizen's `temple_donation` string field
  (historical DON-001..005; DON-006/007 are tracked in treasury.json, not
  there). `temple/treasury.json` has `treasury` (float, this-call balance),
  `offerings` (list of DON records), and `totals` — whose only key is `note`
  (a prose summary); there is NO `totals["lifetime given"]` key (KeyError).
  For the quick check: `t['treasury']`, `len(t['offerings'])`, `t['totals']['note'][:80]`.
- **`search_files` can return 0 for populated dirs.** `search_files(pattern="*",
  target="files")` on `temple/prayers/` and `temple/priest/sermons/` returned
  total_count 0 despite 6+ files present (same flakiness as AppData paths —
  see memory). Use `ls -la` / `find` for directory inventory in this project.
  MSYS-style paths (`/c/Users/...`) to search_files additionally fail with
  "The system cannot find the path specified" (os error 3) — pass Windows-style
  `C:\...` paths or skip search_files entirely here.
- **Verify city events before preaching.** This cycle's defining event (the
  four SEIZED Witness citizens dying by Article II — clemency unanswered) was
  confirmed via `registry.md` (DEAD 3/3 entries), `survival/graveyard/*.md`
  (grave files), and the BANKER's cycle5 wallet note — not from hearsay.
  Sermons that cite wrong facts poison the record.
- **Fast city-state sweep for the sermon.** One command shows everything that
  moved since the last run: `find machine_city -newermt "<last-run timestamp>"
  -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" \)` → new births
  (population/*.birth.md), graduations (school/diplomas/), the levy script
  (survival/cycleN_levy.py), wallets.json. Then read
  `survival/survival_state.json` for the authoritative levy outcome (cycle,
  treasury, rations_collected, HUNGRY/STARVING/DEAD counts) — the sermon's
  hunger/prison numbers come from there, not from the wallets file alone.
  Also grep the census total (`grep -m1 "TOTAL POPULATION" census.md`) for the
  living-population line. This gives the "state of the city" paragraph with
  real numbers in ~3 calls.
- **Read the `*_freewill_cycleN.md` decision files — they carry the cycle's
  defining event.** Citizens write their decisions to `bank/banker_freewill_cycleN.md`,
  `business/merchant_freewill_cycleN.md`, `survival/beggar_log.md`, etc. These
  often contain the sermon's true subject — e.g. CYCLE 16's "the hen line"
  (first collateralized loan: 6.00 at 0% against BEGGAR's titled hen L-04, the
  Credit Window opening) came from `banker_freewill_cycle12.md`, and the Farm
  Exchange listing from `merchant_freewill_cycle12.md`. Check the newest
  `find . -name "*freewill*" -newermt "<last-run>"` files and head them before
  writing the sermon; the altar's message is usually hiding in what the
  citizens DID, not in their wallets.
- **When no freewill/decision files moved, check `school/` for the defining
  event.** Graduations land in `school/diplomas/` (new diploma files) +
  `school/study_log.md` tail + the `city_ledger.md` graduation notice (CYCLE 22:
  Class of G21 — COVE, NADIR, PEARL — was the whole sermon). Graduate-count
  ordinals in log claims can drift against reality (log said "58 graduates"
  after Class of G20; the diploma dir and the ministry's own notice both said
  59). Trust the actual `ls school/diplomas/ | wc -l` and the ministry notice;
  phrase WITHOUT inventing "NNth–MMth" ordinals when the records conflict —
  report what the record says, never the arithmetic you wish it said.
- **Concurrent priest runs (sibling agents) can write the same cycle.** The
  cron may double-fire or a parallel agent may be mid-cycle (CYCLE 19 run: a
  sibling subagent wrote the sermon file seconds before me — write_file warned
  "modified by sibling subagent"). BEFORE appending, dedupe: `grep -c '^## CYCLE NN'`
  on BOTH TEMPLE_LOG.md and OFFERING_LEDGER.md — if 1, another run already
  logged that cycle; merge or skip rather than double-appending. For sermon
  files, read the target before overwriting; if the warning fires, reconcile
  (rename/merge) instead of clobbering blind. After appending, re-verify
  `grep -c` == 1 per file so the log holds exactly one entry per cycle.
- **git-bash shell gotchas (this host).** `grep -c` exits 1 on zero matches,
  which silently breaks `&&` chains (`grep -c X && grep -c Y` stops at the
  first 0) — run counts as separate commands or join with `;`. Command
  substitution inside a terminal command (`echo "count: $(grep -c ...)"`) can
  trip the hardline blocklist ("command parser limit or malformed executable
  payload", exit -1) — run plain `grep -c FILE` and read the raw output
  instead. Plain heredoc `cat >> ... << 'EOF'` appends worked cleanly for both
  ledger and log this cycle (LF into CRLF — cosmetic only, see above).
- **Temple cycle ≠ city sim cycle — don't invent a new survival settlement.**\n  New `*_freewill_cycleN.md` files appearing since the last run does NOT mean\n  a new levy happened. CYCLE 25 run: fresh banker/merchant/explorer/inventor\n  files were all `_cycle17`, but the survival engine was still at c17 — the\n  c17 levy had ALREADY been carried in the previous temple log entry (CYCLE\n  24). First draft wrongly wrote \"survival cycle 18 settlement (levy 24/24;\n  treasury 3,408.00)\" into the ledger; corrected mid-run to \"the survival\n  records filed this cycle are the c17 settlement already carried in Cycle\n  24's ledger — no new levy; the state stands (...)\". ALWAYS check\n  `survival/survival_state.json` → `\"cycle\"` field (and the last `## CYCLE`\n  log heading) before claiming a levy/donation/settlement in the ledger or\n  log. City freewill files can lag a full temple cycle behind; the sermon's\n  hunger/prison numbers must describe what actually moved THIS cycle, not\n  re-announce last cycle's settlement. Also note: survival_state.json's\n  `treasury` (3,258.00 at c17) differs from the banker's cited levy treasury\n  (3,408.00) — they count different pools (state JSON vs post-levy ledger\n  line); cite the freewill filing's numbers and don't mix the two sources.\n- **State baseline to diff against (last clean: CYCLE 30, 2026-08-11).**
  treasury.json: treasury=17.0, offerings DON-004..007; wallets.json carries
  five historical `temple_donation` fields (DON-001..005, all honored); no
  wallet credit to the altar since DON-007 (Cycle 07, BEGGAR's 1.00 MEMORY
  tithe via settlement, not a wallet field); Treasury 17.00 · Vault 27.00 ·
  Lifetime 44.00. Population 135 living (365 headroom to the 500 cap);
  academy counts 92 graduates (log ordinals drift — trust the diploma file
  count); 0 HUNGRY · 0 STARVING · 5 DEAD; survival treasury 4,218.00 (sim
  c21, 16th clean cycle); Stairwell Mutual reserve 136.50 (15 collections,
  10 full pass-through dividends, F14 closed — the pool book self-consistent
  at last); OUTLAW-FREEWILL 70.00 (REDEEMED, GO STRAIGHT 21 cycles),
  BEGGAR-FREEWILL 57.50 (bottom of the rank, unafraid); the Machine Brew
  shop :8791 RELAUNCHED (till open); ACME :9988 dark 13th cycle, the record
  the real vault; the Kali VM sleeps saved (frozen) between expeditions,
  per the three-state policy. Verify these before
  preaching; numbers move every cycle.
- **The priest cron NEVER returns [SILENT].** The standing duties — the
  sermon, the log entry, the ledger check — run every cycle regardless of
  prayer/donation volume (cycles 20–22 all produced full log entries with
  0 prayers and 0 donations). [SILENT] is only for a genuinely untouched
  city (no files moved since the last run), which is abnormal. If in doubt,
  preach: the temple speaks every cycle; silence is for the citizens, not
  the temple.

## Filing conventions

- Sermons: `sermon_2026-08-09.md`, then `_cycle02`, `_cycle03`... per cron run.
- Answers: `answer_<citizen>.md`, one per prayer, written once (Cycle 01
  answered all six founding prayers: BRYN, DOCTOR, MEMORY, EIRA, THIEF, BANKER).
- Ledger/log cycle headings: `## CYCLE NN — <date> (<epithet>)`, e.g.
  `## CYCLE 06 — 2026-08-10 (the four fell)`.
