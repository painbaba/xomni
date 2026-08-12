# XOMNI — Lightning Micro-Payouts Pilot (Spec)

**Status:** SPEC (no code) · **Owner:** monetization track · **Backlog:** P2 item 24 · **Date:** 2026-08-12
**Scope:** global (non-India) micro-payouts to marketplace creators over Bitcoin Lightning. **India stays UPI** (30% VDA tax + 1% TDS makes crypto irrational for India-domiciled flows). Spec only; no code.
**Sources of truth:** `docs/UPI.md` §4/§7 (crypto-vs-UPI decision record, P2-24 backlog linkage), `docs/MONETIZATION-V2.md` Phase 3 (Lightning pilot), `docs/SKILLS-MARKET.md` (creator/publisher identity + credit stamping), `plugins/receipts/README.md` (verifiable handles). Marketplace revenue-share v1 is specced in `docs/MARKETPLACE.md` (created in the same wave — reference it there when it lands).

---

## 1. Why Lightning for micro-payouts

**Problem:** marketplace creators (skill publishers, `docs/SKILLS-MARKET.md`) earn small amounts — a single skill sale or marketplace share can be far below what any traditional rail can move economically:

- **Cards / cross-border wires** carry per-transfer fees, FX spread, and often a **minimum-transaction floor** — a $0.50 payout can cost more than its value to send.
- **UPI is India-only** (0% MDR, `docs/UPI.md` §3) and has **no cross-border outflow path** for rupee payouts to global creators — cross-border rupee payout friction is a structural blocker, not a fee problem.
- **Wise/PayPal** (the Phase 2 global fallback, `docs/UPI.md` §4) amortize fine at the ₹500/$10 threshold but are uneconomic below it.

**Lightning properties (pilot rationale):**

| Property | Lightning | vs. alternative |
|---|---|---|
| Minimum-transaction floor | **None** — sats are sub-rupee divisible; anti-dust floor is a policy choice, not a rail constraint | cards/wires have hard floors |
| Settlement | **Near-instant** (seconds, payment-channel finality) | UPI T+1 settlement; wires take days |
| Routing fees | ~0.01–0.1% + base fee `[unverified industry range — flagged]` | cards 2% + GST + FX (`docs/UPI.md` §3); per-transfer wire fees |
| Cross-border | **Native** — money is global by construction | UPI: India-only; cards: FX + cross-border fees |

**Pilot verdict (mirrors `docs/UPI.md` §7):** Lightning is the only rail that makes **sub-threshold, sub-rupee, global** payouts viable. It is a *global-only* instrument: for India-domiciled flows, UPI remains the rail (see §4).

---

## 2. Pilot scope

### 2.1 Who participates

- **Global (non-India) marketplace creators** — skill publishers with credit-stamped `SKILL.md` (author derived + `source: xomni` stamp, `docs/SKILLS-MARKET.md` "Credit policy") and/or marketplace revenue-share creators (15% take-rate rail, `docs/MONETIZATION-V2.md` Phase 2; `docs/MARKETPLACE.md`).
- **India creators are excluded from the pilot** — their payouts stay on Razorpay UPI (free rail, ₹500 payout threshold, `docs/UPI.md` §4).
- Recipients onboard with **identity + consent** before first payout (KYC posture mirrors `docs/UPI.md` §4: name, payout identifier, DPDP-style consent notice for the data held).

### 2.2 Amount band, currencies, caps — ALL PROPOSALS

| Parameter | Value | Label |
|---|---|---|
| Per-payout band | **₹10–₹2,000 INR-equivalent, denominated in sats** at payout-time conversion | **PROPOSAL** |
| Denomination | sats (BTC on Lightning); ledger records INR-equivalent + sats + FX rate per payout | **PROPOSAL** |
| Anti-dust floor | ≥ ~1,000 sats (~₹10) to avoid spam payouts | **PROPOSAL** |
| Daily cap per creator | 5 payouts / ₹2,000-equivalent (whichever hits first) | **PROPOSAL** |
| Monthly cap per creator | ₹8,000-equivalent (≈ 4× daily band ceiling) | **PROPOSAL** |
| Pilot aggregate cap | ₹2,00,000-equivalent, then hold + review | **PROPOSAL** |
| FX policy | Rate captured at payout creation, frozen for that payout (same single-currency-ledger principle as `docs/UPI.md` §6.1) | **PROPOSAL** |

Threshold note: the ₹500 payout threshold in `docs/UPI.md` §4 exists to amortize per-transfer fees; Lightning's negligible fees make **below-threshold payouts viable** — that is the entire point of the pilot. The anti-dust floor replaces the ₹500 gate for global creators.

---

## 3. Node & keys handling

### 3.1 Custodial vs non-custodial — PROPOSAL

- **Pilot runs custodial (Lightspark)** — matches the Phase 3 plan in `docs/MONETIZATION-V2.md` and `docs/UPI.md` §7. Rationale: key management, channel liquidity, and invoice routing are custodial problems; the custodian is the regulated counterparty (see §4). Non-custodial (own node / LND) is a Phase-C-or-later option — **flagged: revisit at general rollout**.

### 3.2 HARD RULE — key material never enters the repo

> **Seed phrases, private keys, and node admin credentials NEVER live in the repo, in code, in tests, or in fixtures. Key material is env-injected (e.g. `LIGHTSPARK_API_TOKEN` from the runtime environment) or held entirely by external custody.**

- No `.env`, no key files, no mnemonic strings, no test vectors containing real secrets — ever. This extends the repo hygiene already enforced for the plugins surface (`plugins/receipts`, `plugins/omni-skills`).
- CI and local runs get credentials **only** via environment variables; anything else fails loudly (fail-closed, matching the publish/install posture in `docs/SKILLS-MARKET.md`).

### 3.3 Invoice flow (BOLT11) + receipts

1. **Create BOLT11 invoice** for the payout amount in msat (amount band §2.2) with a **fixed expiry window** — **PROPOSAL: 24h**; expired invoices are never paid, they are re-issued (BOLT11 `expiry` field).
2. **Pay via Lightning Address / LNURL-pay** when the creator provides one (`user@domain`): the address resolves to a BOLT11 invoice at pay time — the LNURL endpoint is a live URL, so the receipts-plugin **`url:<url>` handle** (live GET → HTTP 200, `plugins/receipts/README.md`) is the natural verifiable handle for the payment endpoint.
3. **Payment hash as the receipt handle:** every BOLT11 invoice carries a payment hash (SHA-256 of the preimage). The payment hash is a hex fingerprint of the payment — issue a receipts-ledger receipt with **`sha256:<payment_hash>`** as the handle (`plugins/receipts/README.md` handle table), plus `meta` = {invoice, amount_msat, fx, creator_id, settlement_status}.
4. **Verification:** `/receipts verify <id>` re-checks the handle; settlement confirmation additionally re-checks the payment against the custodian's API. Receipts-only sync keeps the privacy invariant (`docs/MONETIZATION-V2.md` — no prompt/code telemetry; money records are receipts).

---

## 4. Compliance notes

| Area | Posture | Source |
|---|---|---|
| **INDIA STAYS ON UPI** | **Lightning is global-only in the pilot. No India participants, no INR→crypto conversion for India flows.** Finance Act 2022: **30% flat tax on VDA gains (s.115BBH) + 1% TDS on transfers (s.194S)**, no loss offset — every crypto transaction is a tax event; plus cross-border rupee payout friction. | `docs/UPI.md` §7 table; `docs/MONETIZATION-V2.md` anchors |
| India payout rail (unchanged) | Razorpay Payouts via UPI — **0% MDR**, ₹500 threshold, DPDP consent for recipient data | `docs/UPI.md` §3–§4 |
| KYC/AML | Recipient identity + consent at onboarding (mirrors `docs/UPI.md` §4); **sanctions screening** (OFAC/EU lists) for global recipients before any payout — **PROPOSAL: screen at onboarding + per-batch** | `docs/UPI.md` §4 |
| Record-keeping | Receipts ledger (`~/.xomni-receipts/receipts.jsonl`) is the audit trail; every payout → one receipt (payment-hash handle) → one-to-one auditable with the money-side record | `plugins/receipts/README.md`; `docs/UPI.md` §4 reconciliation rule |
| Money-transmitter stance | XOMNI does not hold/settle customer funds; the **custodial counterparty (Lightspark) is the regulated entity** for the global rail — **PROPOSAL: verify Lightspark licensing/entity posture at build** | `docs/UPI.md` §5 (RBI PA no-go) |
| Tax-disclosure UI | Any participant in a crypto flow sees explicit tax disclosure; **CA review before go-live** (both gates from `docs/UPI.md` §7 and `docs/MONETIZATION-V2.md` Phase 3) | `docs/UPI.md` §7 |

---

## 5. Rollout

### Phase A — Closed pilot (PROPOSAL: 2–4 weeks)
- 5–10 invited global creators from the skills market (`docs/SKILLS-MARKET.md` publishers / marketplace verified creators).
- **Manual payout batches** via Lightspark; weekly reconciliation vs the receipts ledger; every payout issues a receipt (payment-hash handle, §3.3).
- **Gate: CA review sign-off before the first live payout** (inherited from `docs/UPI.md` §7 and `docs/MONETIZATION-V2.md` Phase 3).

### Phase B — Invite (PROPOSAL: +4 weeks)
- Open to verified marketplace creators (sandbox-gate reviewed — see `docs/SKILLS-MARKET.md` validation posture); self-serve Lightning-Address onboarding; automated payout trigger on accrued earnings; daily/monthly caps (§2.2) enforced in code.

### Phase C — General (conditional)
- Open to all global creators above the anti-dust floor; caps + kill-switch remain armed; revisit non-custodial option.

### Success metrics — ALL PROPOSALS
| Metric | Target |
|---|---|
| Payout success rate | ≥ 99% |
| Median invoice→settled latency | < 60s |
| All-in cost per payout (routing + custody fees) | < 1% of payout value |
| Global-creator opt-in | ≥ 60% of eligible creators |
| Support burden | < 1 ticket per 100 payouts |

### Kill-switch criteria — ALL PROPOSALS
- **Any key/seed exposure or suspected compromise → immediate halt** (non-negotiable).
- Settlement failure rate > 5% over any 24h window.
- All-in cost per payout ≥ 3% of payout value (routing-fee spike).
- Custodian incident / licensing change / sanctions-list impact.
- Regulatory change: India VDA clarification, FX controls, or new global crypto rules.
- Dispute/fraud losses exceeding the pilot aggregate cap budget.

---

## 6. Open items / flagged (re-verify before build)

1. Lightning routing-fee % (~0.01–0.1% industry range) — unverified, pin with real Lightspark quotes.
2. Lightspark pricing, licensing, and jurisdiction posture — confirm at integration.
3. Amount band, caps, expiry window, anti-dust floor — all proposals pending product review.
4. FX policy (rate capture/freeze per payout) — align with `docs/UPI.md` §6.1 flagged FX decision.
5. Non-custodial option for Phase C — key-management + travel-rule implications (CA review).
6. TDS section/rate on creator payouts for India recipients — already flagged in `docs/UPI.md` §8; unchanged (India rail untouched by this pilot).
7. `docs/MARKETPLACE.md` (same wave) — creator payout terms cross-reference when it lands.

---

## 7. Sources

- `docs/UPI.md` — §3 fee table (UPI 0% MDR verified), §4 payout rails (₹500 threshold, KYC/consent, global fallback), §7 crypto-vs-UPI decision record (30%+1% TDS, P2 item 24 backlog linkage), §8 flagged items.
- `docs/MONETIZATION-V2.md` — Phase 2 marketplace revenue-share (15% take-rate, creators via same rail), Phase 3 Lightning pilot (Lightspark/LNURL, India stays UPI, tax-disclosure UI, CA review gate).
- `docs/SKILLS-MARKET.md` — publisher identity, credit stamping, fail-closed validation.
- `plugins/receipts/README.md` — verifiable handles (`url:<url>`, `sha256:<hex>`), ledger, verify semantics.
- `docs/MARKETPLACE.md` — marketplace revenue-share v1 (created in the same wave; not present at authoring time — cross-reference on arrival).
