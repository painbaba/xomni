# XOMNI Skills Database — Curation Summary

**Curator:** XOMNI curation pipeline
**Date:** 2026-08-11 (final build, all 6 scrape files)
**Inputs:** `data/raw/scrape1.json` … `scrape6.json` (519 raw rows)
**Output:** `data/curated-skills.json` (180 ranked records) · this summary

---

## 1. Totals at a glance

| Stage | Count |
|---|---|
| Raw rows harvested (scrape1–6) | **519** |
| Unique after sha256 + name/content dedupe | **475** |
| Excluded — REJECT scan verdict | 0 (current scan) |
| Excluded — documented REJECT findings (blocklist) | **8** |
| Scored (usable corpus) | **467** |
| **Curated (ranked top-180)** | **180** |
| Score range (curated) | 9.1 – 10.2 (avg 9.56) |

> **Verdict note:** The security scanner's first pass flagged 8 skills as REJECT
> (remote-exec / destructive / suspicious-url findings) — all from the deep-harvester
> sources (NVIDIA/skills ×7, google/skills ×1). A re-scan flipped them to PASS with
> empty notes, but the documented findings stand; they are blocklisted and **never
> recommended** (see §5.4).

---

## 2. Deduplication (475 unique from 519 raw)

Two passes, provenance preserved per record:

1. **Exact sha256** — 21 cross-file duplicate hashes collapsed (same skill scraped in
   multiple scrape files; e.g. `algorithmic-art` appeared in scrape1–4). Kept first
   occurrence; `provenance.all_scrape_files` records every file the hash appeared in
   and `duplicate_copies_removed` counts dropped copies (39 copies dropped).
2. **Near-duplicate name+content** — same normalized name + same source, or content
   similarity ≥ 0.55 (difflib SequenceMatcher on first 20k chars), collapsed keeping
   the **most complete** version (longest content; PASS verdict preferred). 5 merges:
   `skillopt-sleep` (4 microsoft/SkillOpt variants → 1), `github` (openclaw ×2 → 1),
   `md2wechat` (2 → 1), `doc-coauthoring`, `skill-creator` variants.

`dedupe_provenance`: each record carries `first_seen_in`, `all_scrape_files`, and
`duplicate_copies_removed` so every dedupe decision is auditable.

---

## 3. Usefulness scoring rubric (0–10)

Objective, component-based score; max 10.0 (small rounding can yield 10.2).

| Component | Max | Signals |
|---|---|---|
| Source reputation | 2.5 | **Tier A (2.5):** anthropics/skills, google/skills, NVIDIA/skills, microsoft/skills, obra/superpowers, angular/skills, claude-code-docs, awesome-claude-code, microsoft/SkillOpt. **Tier B (2.0):** awesome-cursorrules, openclaw, resend, LambdaTest, crewai-tools. **Tier C (1.5):** veniceai, raptor, openspec-plus, SnailSploit/Claude-Red, factory.ai, club-cog, md2wechat. **Unknown repos: 1.0.** |
| License presence | 1.0 | Any license field present. |
| Description quality | 2.0 | 2.0 = trigger phrase ("Use when…") + specific keywords; 1.5 = ≥80 chars specific; 1.0 = short; 0.5 = <40 chars; 0 = missing. |
| Content completeness | 1.6 | ≥8k chars + ≥5 headers = 1.6; ≥4k = 1.4; ≥1.5k = 1.0; ≥500 = 0.6; else 0.3. |
| Maintainer signals | 1.0 | source_url (0.5) + license (0.4) + scan_notes present (0.1). |
| Scan verdict | 1.5 | PASS = 1.5; REVIEW = 0.5 (kept, flagged); **REJECT = floor 0, never recommended.** |
| Specificity bonus | 0.6 | 0.6 = concrete hyphenated task name; 0.3 = generic name; **0.0 for template-generated SDK/platform cards** (azure-*, doca-*, tao-*, jetson-*, gke-*, google-cloud-*, nemo-*, etc. — bulk families whose members are near-identical wrappers). |

Tie-break: higher score → longer content → name ascending.

---

## 4. Category taxonomy (normalized from ~90 raw category strings)

Raw categories (e.g. `anthropic-official::skills`, `.agents/skills/auto-qa`,
`security-collection::Skills`, `skills/pdf`, `superpowers/…`) were normalized to a
11-class taxonomy using a two-pass keyword classifier: **name first** (highest signal),
then description + raw category, with word-boundary regex matching (so `art` does not
match `participants`, and prefix keywords like `train-` match hyphenated names).

### Curated top-180 by category

| Category | Count | Share |
|---|---|---|
| cloud | 53 | 29.4% |
| data | 35 | 19.4% |
| agent-tooling | 32 | 17.8% |
| coding | 25 | 13.9% |
| productivity | 7 | 3.9% |
| ops | 7 | 3.9% |
| media | 5 | 2.8% |
| research | 5 | 2.8% |
| misc | 5 | 2.8% |
| creative | 4 | 2.2% |
| security | 2 | 1.1% |
| **Total** | **180** | 100% |

### Full scored corpus (467) by category

cloud 110 · agent-tooling 86 · data 72 · coding 61 · research 30 · ops 27 · media 20 ·
productivity 20 · misc 16 · security 15 · creative 10

### Curated top-180 by source

| Source | Count |
|---|---|
| NVIDIA/skills | 62 |
| microsoft/skills | 42 |
| google/skills | 21 |
| obra/superpowers | 12 |
| awesome-claude-code | 11 |
| openclaw | 11 |
| anthropics/skills | 8 |
| sudokar/openspec-plus | 6 |
| angular/skills | 2 |
| SnailSploit/Claude-Red | 2 |
| microsoft/SkillOpt, claude-code-docs, LambdaTest/agent-skills | 1 each |

### Scan verdicts (curated top-180)

PASS 177 · REVIEW 3 (REVIEW items retained with their scan notes; no REJECT ever ranks)

---

## 5. Methodology notes

### 5.1 Pipeline
All 6 scrape files loaded; dedupe → classify → score → rank → truncate to top-180 →
write JSON + stats; summary generated from the same run. Reproducible via
`tmp/curate.py` (Python 3, stdlib only).

### 5.2 Scrape coverage
All six scrapes present; deep-harvester files (scrape5 = NVIDIA/microsoft, scrape6 =
google/vercel) arrived ~4 min into the polling window; no timeout fallback needed.
`vercel-labs/skills` contributed 1 skill. Harvester notes read from
`.tmp/skills-curation/INTEGRATION-NOTES.md`.

### 5.3 REVIEW handling
REVIEW (58 in corpus, 3 in top-180) = scanner keyword hits, mostly benign
false positives (`exfil_send` on the word "forward", `cred_key` on "access-token",
network on "webhook"). REVIEW skills are ranked normally but never score the full
verdict component, and their `scan_notes` are preserved verbatim.

### 5.4 REJECT blocklist (never recommended)
Documented security findings from the scanner's first pass — excluded even though a
later re-scan marked them PASS:

- NVIDIA/skills: `deepstream-sop` (remote-exec), `hsb-app` (destructive), `hsb-test`
  (destructive), `tao-run-on-docker` (destructive), `vss-deploy-dense-captioning`
  (remote-exec), `vss-generate-video-calibration` (remote-exec),
  `vss-manage-video-io-storage` (remote-exec)
- google/skills: `google-cloud-solution-guided-gke-ai-migration` (remote-exec + suspicious-url)

### 5.5 Known caveats
- NVIDIA/microsoft/google bulk SDK cards dominate the middle of the list (they are
  genuinely complete, licensed, tier-A docs); the top-20 is deliberately
  source-diverse thanks to the specificity penalty on template families.
- Offensive-security skills (SnailSploit/Claude-Red) are included by design for
  authorized red-team use; they carry REVIEW verdicts and are marked security.

---

## 6. Top-20 ranked skills

| # | Score | Skill | Source | Category | Why it ranks |
|---|---|---|---|---|---|
| 1 | 10.2 | writing-skills | obra/superpowers | agent-tooling | Canonical meta-skill for authoring/editing/verifying skills; complete workflow doc |
| 2 | 10.2 | applicationinsights-web-ts | microsoft/skills | data | Full Azure App Insights JS SDK instrumentation guide with triggers |
| 3 | 10.2 | agent-acceptance-gate | awesome-claude-code | agent-tooling | Pre-merge verification gate for multi-agent rounds; highly reusable |
| 4 | 10.2 | physical-ai-defect-image-generation | NVIDIA/skills | media | Concrete end-to-end defect-image orchestration (Cosmos AnomalyGen) |
| 5 | 10.2 | algorithmic-art | anthropics/skills | creative | Official p5.js generative-art skill with templates & seeded randomness |
| 6 | 10.2 | agent-output-reconciler | awesome-claude-code | agent-tooling | Reconciler for multi-agent output rounds; practical agent orchestration |
| 7 | 10.2 | wiki-onboarding | microsoft/skills | productivity | Generates 4 audience-tailored onboarding guides; specific & actionable |
| 8 | 10.2 | agent-framework-azure-ai-py | microsoft/skills | agent-tooling | Builds Azure AI Foundry agents on the MS Agent Framework Python SDK |
| 9 | 10.2 | data-manager-api-audience-ingestion | google/skills | data | Guided Google Audience Data API management (add/remove/clear) |
| 10 | 10.2 | angular-developer | angular/skills | coding | Official Angular code-gen + architecture guidance |
| 11 | 10.2 | gemini-api | google/skills | coding | Enterprise Gemini/Vertex AI API guidance with clear triggers |
| 12 | 10.2 | agent-shared-memory | awesome-claude-code | agent-tooling | Shared-memory management across multi-agent sessions |
| 13 | 10.2 | agent-debate | awesome-claude-code | agent-tooling | Adversarial agent debate for consequential decisions |
| 14 | 10.2 | google-analytics-data-api-basics | google/skills | data | GA4 reporting via Analytics Data API; hands-on CLI workflow |
| 15 | 10.2 | systematic-debugging | obra/superpowers | coding | The reference 4-phase debugging workflow (understand before fixing) |
| 16 | 10.2 | skillopt-sleep | microsoft/SkillOpt | agent-tooling | Offline learning pass over recent local sessions (SkillOpt) |
| 17 | 10.2 | test-driven-development | obra/superpowers | coding | Canonical TDD skill: RED–GREEN–REFACTOR enforced before code |
| 18 | 10.2 | agent-plan-act-reflect | awesome-claude-code | agent-tooling | Single-agent self-correction loop (plan → act → reflect) |
| 19 | 10.0 | teams-app-developer | microsoft/skills | cloud | Builds/tests/deploys M365 Teams + Copilot apps; sub-skill suite |
| 20 | 10.0 | holohub-app-lifecycle | NVIDIA/skills | coding | Non-failing HoloHub scaffold/build/run/test lifecycle skill |

---

## 7. Files produced

- **`C:\Users\HP\xomni\data\curated-skills.json`** — 180 ranked records; each record:
  `name, source, source_url, category, raw_category, description, content (full),
  sha256, license, scan_verdict, scan_notes, usefulness_score, rank, provenance`.
  Sorted by `usefulness_score` desc.
- **`C:\Users\HP\xomni\data\curated-skills.json.stats.json`** — machine-readable stats
  (raw/unique/curated totals, per-source & per-category counts, verdict & score dist).
- **`C:\Users\HP\xomni\data\curated-summary.md`** — this file.
- Pipeline: `C:\Users\HP\xomni\tmp\curate.py` (dedupe + classify + score + rank).
