# XOMNI — Plugin Marketplace Rails (Spec)

**Status:** SPEC (no code) · **Owner:** monetization track · **Backlog:** P2-23 · **Date:** 2026-08-12
**Sources of truth:**
- `docs/MONETIZATION-V2.md` — Phase 2 marketplace revenue-share v1: 15% take-rate (app-store parity, verified), payout threshold ₹500/$10, "price services, not bytes", verified-badge gate (sandbox review + 544-skill DB curation)
- `docs/UPI.md` — India money rails: Razorpay UPI Intent (0% MDR), Razorpay Payouts (UPI free), ₹500 payout threshold, TDS flagged for CA review, 30%+1% VDA crypto note, DPDP consent posture, receipts-to-money audit
- `docs/SKILLS-MARKET.md` — shared skills registry: git-repo content model, `/skills publish` stamp→delegate→index→install, receipts on publish
- `plugins/receipts/README.md` — receipts ledger: append-only JSONL, verifiable handles `sha256:<hex>` / `url:<url>` / `exit:<code>:<tail>`
- `docs/SKILLS-SECURITY.md` — static scan verdicts PASS/REVIEW/REJECT (544 skills in DB, 2026-08-12)
- `docs/MCP-CATALOG.md` + `docs/NONINTERACTIVE.md` — badge model and `--yes` non-interactive install conventions
- `data/curated-skills.json` — listing metadata shape (sha256, scan_verdict, license, source, description)

**Scope:** the marketplace layer that sits on top of the free skills registry — listing, discovery, install, versioning, delisting, the **15% take-rate rail** (worked example + rounding/TDS assumptions), receipts for every money-adjacent side-effect, refunds/disputes, abuse/security, and how it composes with `docs/SKILLS-MARKET.md` and `docs/UPI.md`. Spec only; no code. Anything not yet grounded is explicitly marked **[PROPOSAL]**.

---

## 1. What the marketplace is (and is not)

- **Installs and verified badges are free, forever** — fees apply only to *money flows* (creator payout take-rate, sponsor campaigns) (`docs/MONETIZATION-V2.md` §"What stays free"). The marketplace never charges for installing or browsing.
- **Price services, not bytes.** Git-cloneable content cannot be paywalled (structural piracy — `docs/MONETIZATION-V2.md` Phase 2). A paid listing therefore sells the *service wrap* around the plugin: maintained updates, verified compatibility, support channel, priority review — the plugin bytes themselves stay installable for free via the registry path.
- **The marketplace is the paid layer over the free registry.** `docs/SKILLS-MARKET.md` defines the free content model (public git repos with `SKILL.md`, indexed by skills.sh, `/skills publish`, `/skills-marketplace <git-url>`). The marketplace reuses that model — a listed plugin is a git repo whose manifest is `plugin.yaml` — and adds paid SKUs, the take-rate, and payouts on top (§11).
- **Guiding invariants (unchanged):** devs pay ₹0/$0 forever; no prompt/code telemetry — receipts-only sync; XOMNI must NOT become a Payment Aggregator (RBI PA rules, `docs/UPI.md` §5); UPI over crypto for India (`docs/UPI.md` §7).

---

## 2. Listing

### 2.1 What makes a plugin listable (gates)

A plugin is listable only if **all** gates pass. Gates are fail-closed: any missing input → loud error, nothing listed (`docs/NONINTERACTIVE.md` rule 2, mirroring `/skills publish` fail-closed behavior in `docs/SKILLS-MARKET.md`):

| # | Gate | Check | Grounding |
|---|---|---|---|
| G1 | Manifest | `plugin.yaml` present with `name`, `version` (semver), `description` — same shape as `plugins/receipts/plugin.yaml` | repo convention |
| G2 | Tests green | the plugin's unit suite passes, e.g. `cd plugins/<name> && python -m unittest tests.test_core -q` (the pattern used by cost-tracker: 14 tests; perkline: 27) | `docs/MONETIZATION-V2.md` §P1; `plugins/receipts/README.md` |
| G3 | Static security scan | verdict **PASS** (or **REVIEW** with disclosed findings); **REJECT** is refused outright and never suggested for import | `docs/SKILLS-SECURITY.md` methodology (static scan, never executed; 544 skills in DB) |
| G4 | Provenance | `source` (owner/repo) and `license` recorded; `sha256` content fingerprint computed over the published copy (paths + bytes of every file) | `data/curated-skills.json` fields; `docs/SKILLS-MARKET.md` §publish receipt |
| G5 | Sandbox gate | v1 verified badge requires sandbox-gate review + curation entry (the 544-skill DB curation from Phase 2) | `docs/MONETIZATION-V2.md` Phase 2 |

**Paid SKU listing** (extra gates, **[PROPOSAL]**): a paid listing must additionally declare `price_inr` (one-time) or `price_inr_per_mo` (subscription), a refund window, and a support channel. Prices should sit in the realistic INR band for this buyer class (₹149–499/mo, `docs/UPI.md` §1) — suggested anchors: ₹149 / ₹299 / ₹499 one-time, ₹149–499/mo subscriptions.

### 2.2 Listing manifest

`plugin.yaml` (v1, mirrors `plugins/receipts/plugin.yaml`):

```yaml
name: my-plugin
version: "1.2.0"          # semver; must bump on any content change
description: "one-line summary shown in search results"
```

Marketplace-side metadata appended at listing time (from G3/G4, shape per `data/curated-skills.json`):

```json
{
  "name": "my-plugin",
  "source": "painbaba/xomni",
  "source_url": "https://github.com/painbaba/xomni/tree/main/plugins/my-plugin",
  "category": "agent-tooling",
  "description": "one-line summary shown in search results",
  "sha256": "<hex of published bundle fingerprint>",
  "license": "MIT",
  "scan_verdict": "PASS",
  "scan_notes": [],
  "price_inr": 299,
  "price_model": "PAID",
  "listed_at": "2026-08-12",
  "listing_receipt": "R…"
}
```

### 2.3 Listing flow + receipt

`/market list <dir> [--price-inr=299] [--dry-run]` — one path, host-first, modeled on `/skills publish` (`docs/SKILLS-MARKET.md`):

1. **Validate** (G1–G4; fail-closed, REJECT refused outright).
2. **Publish/stamp** — delegated to the host (`hermes skills publish --to github <dir>`) when available; repo-copy fallback otherwise; credit stamping per `docs/SKILLS-MARKET.md` (`author`, `source: xomni`, `published_at` set once, never rewritten; idempotent).
3. **Index** — the listing entry (2.2) enters the curated index; `--dry-run` validates and prints the exact delegated command without publishing.
4. **Receipt** — a `marketplace.listing` receipt is issued (§8.1). Print one-liner like the publish receipt: `RECEIPT: name=<name> version=<v> price_inr=<n> verdict=PASS sha256=<hex>` (`docs/SKILLS-MARKET.md` §publish).

**Paid-listing note:** flipping a FREE listing to PAID (or back) is itself a listing mutation — it re-issues the listing receipt with the new `price_model`. It never changes the free installability of the bytes (§1).

---

## 3. Discovery

### 3.1 Search

`/market search <query>` matches `name` / `description` / `category` over the curated index (same mechanics as `/skills-search <query>` over the skills DB, `docs/SKILLS-MARKET.md` command reference). `--paid-only` / `--free-only` filters; `--min-stars=N` filters on the stars badge.

### 3.2 Badges

Discovery rows carry badges in the **mcp-catalog model** — `docs/MCP-CATALOG.md` renders `name | purpose | price_model | verified` per server; the marketplace mirrors that with `name | category | price | stars | keyless | security`:

| Badge | Meaning | Derivation |
|---|---|---|
| `price` | `FREE` / `FREE-TIER+ADDON` / `PAID` | declared `price_model` (mcp-catalog vocabulary, `docs/MCP-CATALOG.md`) |
| `stars` | GitHub stars of `source` repo | from source metadata **[PROPOSAL: add `stars` to curated index — not present in `data/curated-skills.json` today]** |
| `keyless` | static scan found **no** credential reads (no `cred-key:'…'` findings) | derived from `scan_notes` absence of cred-key entries (`data/curated-skills.json` shows the finding format) |
| `security` | `PASS` / `REVIEW` / `REJECT` scan verdict | `scan_verdict` per `docs/SKILLS-SECURITY.md`; default search lists `PASS` only, `REVIEW` on explicit `--include-review`, `REJECT` never |

`verified` (the sandbox-gate badge from `docs/MONETIZATION-V2.md` Phase 2) is a fifth, marketplace-issued badge shown on the listing page, distinct from scan verdict.

---

## 4. Install

### 4.1 One command, non-interactive

```
/market install <name> --yes
# or CLI:  xomni plugins install <name> --yes
```

Follows `docs/NONINTERACTIVE.md` exactly:

- `--yes`/`-y` is **required to mutate**, mirroring `/mcp add <name>`: without it the command prints the plan + `confirm by re-running: /market install <name> --yes` and mutates nothing.
- The flag is stripped before name parsing; it can never be misread as a plugin name.
- **Idempotent:** re-run on an installed plugin prints `already registered — nothing to do` (the `/mcp add` no-op convention, `docs/NONINTERACTIVE.md` rule 3) and exits 0.
- **Fail-loud:** unknown name, REJECT verdict, missing git, config write error → `FAILED — <cause>` naming the cause; exit 1 (CLI) or FAILED line (plugin).

### 4.2 What install does

1. Resolve `<name>` in the curated index; refuse if `security=REJECT` or delisted.
2. Fetch the plugin bundle (shallow clone of the git repo / cached copy, cached under `~/.xomni-marketplaces`, fail-closed validation as in `/skills-marketplace`, `docs/SKILLS-MARKET.md`).
3. **Write host config** — append the plugin registration to the host `config.yaml` (same append path as `/mcp add <name>` → `config.yaml` `mcp_servers` and `xomni add <stack>` → `config.yaml` append; `docs/MCP-CATALOG.md`, `docs/NONINTERACTIVE.md`), recording the resolved `name` + `version` (pin).
4. **Issue receipts** (§8.2). Install is free — no payment step, no take-rate.

### 4.3 Paid SKU purchase (buyer side)

For `PAID` listings the config write is gated on payment via the UPI rail: buyer checks out with **Razorpay UPI Intent** (0% MDR; order amount in paise, currency INR, `receipt` = `sale_<plugin>_<buyer>`, webhook-driven `order.paid` state machine, HMAC-SHA256 verified, idempotent `event_id` handling — `docs/UPI.md` §2.1). On `order.paid` the sale is recorded, a `marketplace.sale` receipt is issued (§8.3), and the install proceeds. Expired/unpaid `collect_url` → `failed`, no refund needed (`docs/UPI.md` §2.1 edge cases).

---

## 5. Versioning & updates

- `version` is semver from `plugin.yaml`; any content change requires a bump (G2/G3 re-run on the new version — tests green + scan PASS before the new version is indexed).
- `/market update <name> --yes` — same non-interactive contract as install: idempotent, fail-loud, plan-then-confirm without `--yes`, writes the new version pin to `config.yaml`, issues an `exit:`-kind receipt for the update run (§8.2).
- Downgrade is allowed (`/market update <name>@<older-version> --yes`); the config pin is the record of what is actually installed.
- **[PROPOSAL]** Major (`X.0.0`) bumps require re-listing (fresh G5 sandbox gate) — minor/patch bumps only re-run G2+G3.
- Installed copies are **not** auto-updated; the pin is local and the user (or their `/market update`) controls when it moves.

---

## 6. Delisting

| Path | Trigger | Effect |
|---|---|---|
| Creator-initiated | `/market delist <name> --yes` | Removed from discovery index; new installs blocked; **already-installed copies keep working** — no remote kill switch (trust story, `docs/SELLING.md` §6) |
| Platform-initiated | scan verdict flips to REJECT on a re-scan, abuse finding (§10), or takedown | Same as above + listing entry marked `delisted_reason`; REJECT entries stay in the DB for the audit trail, never suggested for import (`docs/SKILLS-SECURITY.md`) |
| Paid SKU | delist mid-subscription | Refund/credit per §9; outstanding earnings unaffected |

Delisting issues a `marketplace.delist` receipt (sha256 over the final delisted entry) so the listing chain is complete and auditable.

---

## 7. The 15% take-rate rail

### 7.1 Principle

- **15% marketplace take-rate** on creator payout money flows — the app-store norm (Apple Small Business Program 15%, Google Play 15%, verified in `docs/MONETIZATION-V2.md` §"Verified anchors"; tabulated in `docs/UPI.md` §3). Not on installs, not on the free registry, not on sponsor flows (sponsor dev-share stays 50/50 per `docs/SPONSORS.md`).
- Take-rate applies to the **gross sale price** the buyer pays, at the moment the creator's earnings are credited.
- **UPI is the default checkout instrument** — it is the only 0% MDR rail, so at the standard checkout the full ₹100 of every ₹100 buyer rupee is available for the split (`docs/UPI.md` §3, §"Design consequence"). Cards/wallets/netbanking carry ~2.36% effective gateway cost (`docs/UPI.md` §3); **[PROPOSAL]** v1 absorbs that cost out of the rail take on gross (flagged for re-review at volume — `docs/UPI.md` §3).

### 7.2 Worked example — ₹500 sale

```
Gross sale price (buyer pays, UPI Intent, 0% MDR)   ₹500.00    (50,000 paise)
Marketplace take-rate 15%                           ₹ 75.00    (7,500 paise)
Creator nets                                        ₹425.00    (42,500 paise)
```

- The ₹75 rail take is **exactly** 15% of ₹500; ₹425 is the residual, so gross = take + creator net with no rounding artifact at this price point.
- The creator's ₹425 accrues in the earnings ledger. **Payout trigger: accrued earnings ≥ ₹500** (the threshold from `docs/MONETIZATION-V2.md` Phase 2 and `docs/UPI.md` §4) — a single ₹425 sale stays in the ledger until it crosses the threshold; then it pays out via **Razorpay Payouts (UPI — free)** (`docs/UPI.md` §4).
- A second example consistent with the buyer class: a ₹299 plugin (`docs/UPI.md` §1 band): take = ₹44.85 (4,485 paise), creator nets ₹254.15 (25,415 paise). Again exact — no rounding artifact.

### 7.3 Rounding & TDS assumptions (explicit)

1. **All money math is in paise** (Razorpay convention: order amounts in paise — `docs/UPI.md` §2.1).
2. **Rounding rule:** `take_paise = round(gross_paise × 0.15)` (half-up), `creator_paise = gross_paise − take_paise`. The take is rounded, the creator net is the **residual** — the split always sums exactly to gross, and creator net can never exceed gross or go negative. (At the anchored prices above the product is exact; the rule exists for arbitrary prices.)
3. **TDS: none assumed at sale time.** Per `docs/UPI.md` §4: the exact TDS section/rate for creator/dev earnings is **not pinned in research — `[FLAGGED: CA review before first payout]`; do not ship payouts with an assumed TDS rate.** The worked example above therefore shows gross and take only; if a CA-reviewed TDS rate applies later, it is deducted at **payout time** on the creator's net (e.g. ₹425), disclosed line-item in the payout receipt (§8.4), never silently absorbed into the take.
4. **Why this example never touches crypto:** India-domiciled payouts stay on UPI — crypto would carry 30% flat VDA tax (s.115BBH) + 1% TDS (s.194S) per transfer (`docs/UPI.md` §7; `docs/MONETIZATION-V2.md` §"Verified anchors" — "30%+1% TDS makes crypto irrational there"). The ₹425 nets the creator ₹425 on the UPI rail; on a crypto rail it would be a tax event before it is even a payout. Global (non-India) creator payouts: Wise, or the Phase 3 Lightning pilot above a threshold (backlog P2-24, `docs/UPI.md` §7).

### 7.4 Money-in / money-out summary

| Leg | Rail | Cost | Reference |
|---|---|---|---|
| Buyer → marketplace | Razorpay UPI Intent (default); cards ~2.36% effective fallback | 0% MDR on UPI | `docs/UPI.md` §2.1, §3 |
| Marketplace → creator | Razorpay Payouts, UPI preferred (free); IMPS/NEFT/RTGS per-transfer fee `[FLAGGED: pin fee card]` | ₹0 on UPI | `docs/UPI.md` §3–4 |
| Take-rate | 15% of gross, computed at earnings credit | — | `docs/MONETIZATION-V2.md`; `docs/UPI.md` §3 |
| Payout threshold | ₹500 accrued | — | `docs/MONETIZATION-V2.md` Phase 2; `docs/UPI.md` §4 |

### 7.5 Take-rate ledger & reconciliation

- Append-only earnings/take ledger (one row per sale: `sale_id`, `gross_paise`, `take_paise`, `creator_paise`, `sale_receipt_ref`), local + India-resident server copy (payment data stays in India — `docs/UPI.md` §5 localization).
- **Receipt-to-money audit:** every payout batch references the source `marketplace.sale` receipts (like perkline payouts reference the HMAC receipt set, `docs/UPI.md` §6.2); weekly reconciliation job matches Razorpay settlement statements ↔ earnings ledger ↔ receipts, idempotent and `event_id`-keyed (`docs/UPI.md` §6.4).
- **KYC + DPDP consent** for payout recipients before first payout (identity + VPA/bank ownership + consent notice for the personal data held — `docs/UPI.md` §4, §5).

---

## 8. Receipts integration

Every marketplace side-effect issues a verifiable receipt through the receipts plugin (`plugins/receipts/README.md`): append-only JSONL at `~/.xomni-receipts/receipts.jsonl`, handle kinds `sha256:<hex>` / `url:<url>` / `exit:<code>:<tail>`, verified with `/receipts verify <id>`. The receipts plugin is **optional at every site** — if unavailable, the path behaves exactly as before (`plugins/receipts/README.md` §"Integrated mutating paths").

### 8.1 Action → handle table

| Action | Side-effect | Handle kind | Verify re-checks |
|---|---|---|---|
| `marketplace.listing` | listing entry indexed | `sha256:<hex>` | published bundle fingerprint file exists + sha256 matches (content fingerprint = paths + bytes of every file, `docs/SKILLS-MARKET.md` §publish) |
| `marketplace.install` | config.yaml append | `exit:<code>:<tail>` | re-runs the recorded `meta['command']` (idempotent install, safe) → same exit code + tail |
| `marketplace.install.cache` | bundle cached at `~/.xomni-marketplaces` | `sha256:<hex>` | cached bundle dir fingerprint matches |
| `marketplace.sale` | order.paid recorded | `sha256:<hex>` | stored webhook/payment record file (India-resident) exists + sha256 matches |
| `marketplace.payout` | payout batch sent | `sha256:<hex>` | canonical payout-batch manifest file exists + sha256 matches |
| `marketplace.update` / `marketplace.delist` | config re-pin / index removal | `exit:<code>:<tail>` / `sha256:<hex>` | as above |

### 8.2 Install receipt (JSON shape)

```json
{"id": "R9f3a", "ts": "2026-08-12T14:02:11Z", "action": "marketplace.install",
 "target": "config.yaml", "result": "PASS my-plugin@1.2.0 appended",
 "handle": "exit:0:my-plugin@1.2.0 appended (2 lines)",
 "meta": {"plugin": "my-plugin", "version": "1.2.0", "pin": "1.2.0",
          "config_key": "plugins.my-plugin", "source_receipt": "R8b21",
          "command": "xomni plugins install my-plugin --yes"}}
```

### 8.3 Sale receipt (paid SKU)

```json
{"id": "R4c77", "ts": "2026-08-12T14:05:40Z", "action": "marketplace.sale",
 "target": "~/.xomni-marketplaces/sales/sale_my-plugin_R4c77.json",
 "result": "PASS order_paid gross=50000paise take=7500 creator=42500",
 "handle": "sha256:d34db5c8aed6a4e0440132bd0613aace70a693ec7819d5637ad77481d8e10d1b",
 "meta": {"plugin": "my-plugin", "version": "1.2.0", "order_id": "order_…",
          "payment_id": "pay_…", "amount_paise": 50000, "take_paise": 7500,
          "creator_paise": 42500, "instrument": "upi", "vpa": "u****@okhdfc",
          "bank": "hdfc"}}
```

`vpa`/`bank` are captured for the audit trail only — receipts-only rule, not PII telemetry (`docs/UPI.md` §2.1). Mask the VPA as shown.

### 8.4 Payout receipt

```json
{"id": "R2e11", "ts": "2026-08-12T18:00:00Z", "action": "marketplace.payout",
 "target": "~/.xomni-marketplaces/payouts/batch_2026-08-12.json",
 "result": "PASS batch_2026-08-12 payout 1 recipient net=50000paise tds=0",
 "handle": "sha256:<hex of canonical batch manifest>",
 "meta": {"batch_id": "batch_2026-08-12", "method": "razorpay_payouts_upi",
          "payout_ids": ["payout_…"], "net_paise": 50000, "tds_paise": 0,
          "tds_note": "rate not pinned — CA review before first payout (docs/UPI.md §4)",
          "sale_receipt_refs": ["R4c77", "R…"]}}
```

The Razorpay-side confirmation (payout status) lives server-side and is matched in reconciliation (`docs/UPI.md` §6.2); the local receipt proves the batch was sent with an exact, re-verifiable manifest.

---

## 9. Refunds & disputes (sketch)

- **UPI has no chargeback** — disputes are limited to bank-level fraud complaints; refunds go back to the original instrument via the Razorpay refund API with **no refund fee** (`docs/UPI.md` §2.1).
- **[PROPOSAL] v1 policy:** 7-day refund window for paid SKUs when the plugin fails to install or run on a supported host (Windows included); refunds are full-price (gross), issued to the original UPI instrument.
- **Take-rate on refunds reverses:** the refunded sale's `take_paise` is debited from the take ledger; if the creator was already paid out, the amount claws back from their future earnings ledger (never from a bank account — the ₹500 payout threshold makes this practical, `docs/UPI.md` §4). A `marketplace.refund` receipt (sha256 over the refund record) closes the loop.
- **Escalation:** anything outside the mechanical window (disputed quality, subscription cancellations) → manual review; the receipts chain (§8) is the evidence record. Terms (window, escalation path) must be written into the listing before checkout (`docs/UPI.md` §6.1 sets the same rule for sponsor escrow terms).

---

## 10. Abuse & security (sketch)

- **Listing gate reuses the `docs/SKILLS-SECURITY.md` machinery:** every listed plugin is statically scanned (never executed) for prompt-injection instructions, credential theft (env/API-key reads + network sends), eval/exec/subprocess of remote or dynamic content, unknown-host network calls, and obfuscation. Verdicts PASS / REVIEW / REJECT; REJECT is never suggested for import and stays only for the audit trail. Re-scan on every version bump (G2/G3).
- **Fail-closed everywhere:** missing manifest, REJECT verdict, invalid URL, empty/all-rejected marketplace → loud cause-naming errors, nothing written (`docs/NONINTERACTIVE.md`; `docs/SKILLS-MARKET.md` §publish).
- **Abuse cases to design against:** fake/inflated listings (mitigate: provenance + sha256 fingerprint + sandbox gate), off-platform payment evasion of the take-rate (mitigate: paid SKU terms require the marketplace checkout; evasion → delist), payout farming via sock accounts (mitigate: ₹500 threshold + KYC/DPDP onboarding before payout, `docs/UPI.md` §4), refund abuse (mitigate: instrument-restricted refunds, receipts chain).
- **Trust invariants:** no remote kill switch on installed copies (§6); no telemetry beyond receipts (`docs/SELLING.md` §6 — "no telemetry" is a stated trust claim); all money handling auditable via the receipts-to-money pairing (`docs/UPI.md` §6.2).

---

## 11. Composition with SKILLS-MARKET.md and UPI.md

```
                    ┌─────────────────────────────────────────────┐
                    │  MARKETPLACE (this spec, P2-23)             │
                    │  listing · discovery/badges · install ·     │
                    │  versioning · delisting · 15% take-rate ·   │
                    │  receipts · refunds · abuse                  │
                    └──────────┬──────────────────┬───────────────┘
                               │                  │
        docs/SKILLS-MARKET.md  │                  │  docs/UPI.md
        (free registry layer)  │                  │  (money layer)
  git-repo content model  ◄────┘                  └────►  UPI Intent checkout
  /skills publish (stamp→delegate→index)                  (0% MDR, paise orders)
  skills.sh directory / npx skills add                    Razorpay Payouts (UPI free)
  /skills-marketplace install                              ₹500 payout threshold
                                                           KYC + DPDP consent
                                                           TDS flagged (CA review)
                                                           receipts-to-money audit
```

- **Registry (SKILLS-MARKET.md) ↔ marketplace:** the marketplace does not fork the registry — it *extends* it. A listed plugin is a registry-conformant git repo plus a `plugin.yaml` manifest and curated-index metadata (§2.2). Free installs keep flowing through `/skills-marketplace` / `npx skills add` untouched; `/market install` adds the paid-SKU, badge, and take-rate layer on the same content model. `/skills publish` and `/market list` share the stamp→delegate→index→receipt flow (`docs/SKILLS-MARKET.md` §"Publish flow").
- **Money layer (UPI.md) ↔ marketplace:** the marketplace is the first real consumer of the UPI rails spec. Money-in = UPI Intent (§4.3); money-out = Razorpay Payouts with the ₹500 threshold and KYC/DPDP onboarding (§7.4–7.5); the 15% take-rate is already tabulated in `docs/UPI.md` §3. The marketplace adds the money-side event that UPI.md §6.4 sequencing assumes exists: `order.paid → sale recorded → earnings credited → threshold → payout batch → payout receipt`.
- **Non-overlap:** sponsor flows (perkline escrow, 50/50 dev share, `docs/SPONSORS.md`) are a separate money flow with a separate take (the other 50%); the marketplace take-rate applies to plugin sales only. Cost-tracker budgets are orthogonal (`docs/UPI.md` §6.3).

---

## 12. Acceptance criteria (P2-23)

1. `/market list <dir> --dry-run` validates G1–G4 and prints the exact delegated command without publishing.
2. Listing a PASS-verdict plugin issues a `marketplace.listing` receipt; `/receipts verify <id>` returns `{ok: true}`.
3. `/market install <name>` without `--yes` mutates nothing and prints the re-run command; with `--yes` it appends to `config.yaml` and issues `marketplace.install` + `marketplace.install.cache` receipts; re-run prints `already registered — nothing to do`.
4. A ₹500 sale computes `take_paise=7500`, `creator_paise=42500`; a ₹299 sale computes 4485 / 25415 (paise math, §7.3). Property test: for any gross in paise, `take + creator == gross` and `creator ≤ gross`.
5. Payout batch ≥ ₹500 via Razorpay Payouts (UPI) references every source sale receipt; payout receipt includes `payout_ids` and `tds_paise` with the CA-review flag note.
6. REJECT-verdict and delisted plugins are uninstallable-by-name and absent from `/market search` (REJECT also absent with `--include-review`).
7. Refund of a paid sale reverses take + creator earnings in the ledger and issues a `marketplace.refund` receipt.
8. No `input(` in the marketplace plugin surface (`PromptFreeGuaranteeTests` pattern, `docs/NONINTERACTIVE.md` §"Verification").

---

## 13. Open items / flagged (re-verify before build)

1. TDS section/rate on creator payouts — **CA review before first payout** (`docs/UPI.md` §4, §8 #5).
2. Razorpay Payouts fee card (UPI free; IMPS/NEFT/RTGS per-transfer fee) — pin exact rates (`docs/UPI.md` §8 #4).
3. Gateway-cost pass-through for non-UPI instruments (§7.1 **[PROPOSAL]**) — pricing decision.
4. `stars` badge source field — **[PROPOSAL]** to add to the curated index (not in `data/curated-skills.json` today).
5. Refund-window terms + escalation wording per listing (§9 **[PROPOSAL]**).
6. GST on the take-rate (with entity choice) — CA review (`docs/UPI.md` §5).
7. FX policy for any future USD-denominated SKUs — same `[FLAGGED]` as sponsor checkout (`docs/UPI.md` §6.1).

---

## 14. Sources

- `docs/MONETIZATION-V2.md` (2026-08-12, P1 shipped) — Phase 2 revenue-share v1: 15% take-rate (Apple SBP + Google Play verified), ₹500/$10 payout threshold, verified badge + 544-skill curation, "price services, not bytes", PA no-go.
- `docs/UPI.md` (2026-08-12) — UPI Intent (0% MDR, paise orders, webhook/idempotency), fee table incl. 15% take-rate row, ₹500 payout threshold, Razorpay Payouts UPI free, TDS flagged, 30%+1% VDA crypto note, DPDP/KYC posture, receipts-to-money audit.
- `docs/SKILLS-MARKET.md` — registry content model, publish flow (stamp → delegate → index → receipt), fail-closed validation.
- `plugins/receipts/README.md` + `plugins/receipts/plugin.yaml` — ledger shape, handle kinds, verify semantics, manifest fields.
- `docs/SKILLS-SECURITY.md` (2026-08-12) — static-scan verdicts PASS/REVIEW/REJECT; 544 skills in DB.
- `docs/MCP-CATALOG.md` — badge model (`price_model`, `verified`), `/mcp add <name> --yes` config append.
- `docs/NONINTERACTIVE.md` — `--yes` contract, fail-loud, zero silent cancels, plan-then-confirm.
- `docs/SELLING.md` — trust claims (no telemetry, signed updates), ₹0/$0 forever positioning.
- `data/curated-skills.json` — listing metadata shape (sha256, scan_verdict, scan_notes incl. cred-key format, license, source, rank).
