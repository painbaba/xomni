# XOMNI — UPI Payment Rails (Spec)

**Status:** SPEC (no code) · **Owner:** monetization track · **Backlog:** P1 item 13 · **Date:** 2026-08-12
**Sources of truth:**
- `.tmp/research-next/INDIA-FEATURES.md` — FINDING 3 (payment rails, verified 2026-08-12)
- `.tmp/research-next/MONETIZATION-V2.md` — §2 payment rails, §3 sponsorship 2.0 (verified 2026-08-12)
- `docs/MONETIZATION-V2.md` — Phase 2 rails plan (P1 shipped)
- **Live re-verification 2026-08-12 (this session):** razorpay.com/pricing FAQ (2% + GST all modes; zero MDR standard UPI; zero setup/AMC) and Razorpay docs nav (UPI Intent page; "Migrate from UPI Collect to UPI Intent/QR Code" pages; Subscriptions incl. UPI Autopay + e-Mandate; Payouts product) — all confirmed current.

**Scope:** payment architecture for XOMNI India monetization — Razorpay UPI Intent (one-time) + UPI Autopay (recurring), fee table, payout rails, compliance posture, sponsorship-engine integration, crypto-vs-UPI decision. Spec only; no code.

---

## 1. Why UPI, why Razorpay

- India buyers do not pay in USD, and UPI is the wallet of record (~500M+ WhatsApp-scale adoption; zero-fee rail). USD SaaS pricing is a non-starter for the ₹149–499/mo buyer class (`INDIA-FEATURES` FINDING 3, #3-ranked feature).
- **Standard bank-to-bank UPI = 0% MDR** for the merchant (Razorpay pricing FAQ: "No, there is Zero MDR on standard bank-to-bank UPI transactions" — live-verified 2026-08-12). Cards/wallets/netbanking = 2% + GST.
- Razorpay is a **licensed Payment Aggregator (PA)**. XOMNI rides its rails and must NOT become a PA itself (RBI PA rules: net-worth threshold ~₹15 Cr — `[FLAGGED: re-verify current RBI PA guidelines]`; XOMNI has no business holding or settling customer funds directly).
- One integration surface covers both money-in (sponsor campaign budgets, INR subscriptions) and money-out (dev/creator payouts via Razorpay Payouts).

**Guiding rules (from docs/MONETIZATION-V2.md):** never monetize before trust; devs pay ₹0/$0 forever; privacy invariants non-negotiable (no prompt/code telemetry — receipts-only sync); UPI over crypto for India; 15% marketplace take-rate is the app-store norm.

---

## 2. Payment flows (two rails, one Razorpay account)

### 2.1 One-time — Razorpay UPI Intent (sponsor checkout, INR top-ups, one-off purchases)

Flow (spec-level; Razorpay UPI Intent API):

1. **Create order** server-side with the campaign/budget reference (`order` with amount in paise, currency INR, `receipt` = XOMNI internal reference such as `campaign_<id>/dev_<id>`).
2. **Obtain the UPI Intent object** — the API returns a `collect_url` (redirect target) plus a UPI-linked VPA/QR. User is redirected to their UPI app (GPay/PhonePe/Paytm/BHIM) and approves the debit in-app.
3. **Confirmation** — the payment state machine is driven by **webhooks** (`payment.captured` → `order.paid`); server also polls `GET /orders/:id` / `GET /payments/:id` for reconciliation. Webhook signature must be verified (HMAC-SHA256 over the raw payload with the webhook secret, `X-Razorpay-Signature` header) and events processed **idempotently** (store `event_id`; replay-safe).
4. **Settlement** — captured funds settle to the XOMNI Razorpay account on the configured settlement cycle (T+1 typical for UPI); settlement value = order amount **minus the 2% + GST fee only for non-UPI instruments** (UPI = 0% MDR).

Notes/edge cases:
- The `collect_url` is short-lived (expires in minutes) — treat expired/unpaid as `failed`; escrow untouched, no refund needed.
- UPI has no chargeback; disputes are limited to bank-level fraud complaints. Refunds (when needed) go back to the original instrument via the Razorpay refund API — **no refund fee** (verified).
- Always capture `vpa` and `bank` from the payment object for the receipts ledger (audit trail, not PII telemetry — receipts-only rule).

### 2.2 Recurring — Razorpay UPI Autopay (subscriptions: ₹149–499/mo tier, sponsor retainers)

- Built on **UPI Autopay / eMandate** (NPCI recurring framework, RBI e-mandate rules). Razorpay Subscriptions product line covers cards, UPI Autopay, e-Mandate, Physical NACH (verified in product copy).
- **Mandate caps (NPCI rule):** ₹15,000 standard / ₹1,00,000 select categories per debit — `[FLAGGED: NPCI pages bot-gated in research; re-verify at npci.org.in before build]`. For the ₹149–499/mo tier this is a non-issue; caps matter only for large sponsor retainers.
- **RBI recurring-payment framework requirements:** AFA (Additional Factor of Authentication) at mandate creation; pre-debit notification/intimation per RBI e-mandate rules; explicit mandate lifecycle (create → activate → charge → pause → revoke) with customer-facing controls. Exact intimation cadence per RBI master direction — confirm at integration time with Razorpay docs (`[FLAGGED: cadence not pinned in research]`).
- **Build target: UPI Intent, NOT UPI Collect.** RBI-driven deprecation of UPI Collect for recurring — Razorpay docs carry migration pages "Migrate from UPI Collect to UPI Intent/QR Code" (Custom Checkout + S2S) (live-verified 2026-08-12). Any subscription/autopay feature must be built on Intent/Autopay from day one (`INDIA-FEATURES` FINDING 3).
- Failure handling: failed recurring debits → mandate retry policy + grace period; a failed subscription must not auto-pause a live sponsor campaign (escrow spend is event-based, not billing-based — §6).

---

## 3. Fee table (INR, verified 2026-08-12)

| Instrument | MDR / fee | Effective with 18% GST | Source |
|---|---|---|---|
| **Standard UPI (bank-to-bank, incl. UPI Intent)** | **0%** (zero MDR) | **0%** | Razorpay pricing FAQ (live-verified) |
| Cards / wallets / netbanking | **2% + GST** per transaction | **≈ 2.36%** | Razorpay pricing FAQ; MONETIZATION-V2 §2.1–2.2 |
| Setup / AMC / refund / settlement fees | ₹0 | — | Razorpay pricing FAQ (live-verified) |
| Custom enterprise pricing | above **₹5L/month** volume | — | MONETIZATION-V2 §2.1 |
| UPI Autopay mandates | per-instrument fee (UPI = 0% MDR; cards 2%+GST) | — | Razorpay Subscriptions docs |
| **Payouts** (Razorpay Payouts) | **free for UPI payout**; IMPS/NEFT/RTGS per-transfer fee; GST applies | — | `[FLAGGED: exact payout fee card not pinned in research — confirm Razorpay Payouts pricing page]` |
| Marketplace take-rate (Phase 2, docs/MONETIZATION-V2.md) | **15%** (app-store norm; Apple SBP + Google Play verified) | — | MONETIZATION-V2 §1.2 |
| Dev share of sponsor budgets | **50%** (perkline invariant) | — | SPONSORS.md §3 |

Design consequence: **make UPI the default checkout instrument** — it is the only 0% rail, and it is what Indian buyers use anyway. Non-UPI instruments are a convenience fallback, priced into the effective ~2.36% (small enough to absorb for v1; flag if volumes grow).

---

## 4. Payout rails (money out — devs, creators)

- **Razorpay Payouts** (API payouts via **UPI / IMPS / NEFT / RTGS**) is the India dev-payout rail (verified product; MONETIZATION-V2 §2.1). Beneficiary onboarding: **VPA (UPI ID) or bank account (IFSC + account number)** per recipient.
- **Payout threshold: ₹500** (USD ≈ $10 equivalent) to amortize per-transfer fees and reconciliation overhead (docs/MONETIZATION-V2.md Phase 2). Below threshold, earnings accrue in the dev ledger until the threshold is hit.
- **Global devs:** Wise (or PayPal) for non-India payouts; **crypto (Lightning) only above a threshold** as a Phase 3 pilot — see §7.
- **KYC + consent for recipients:** payout onboarding requires recipient identity (bank/VPA ownership verification) and **DPDP consent notice** for the personal data (name, VPA/account, PAN if applicable) held for payouts (`INDIA-FEATURES` #3: "DPDP-consent + KYC onboarding for payout recipients").
- **TDS on dev payouts:** Indian tax law applies TDS to payments for professional/technical services; the exact section/rate for creator/dev earnings is **not pinned in research — `[FLAGGED: CA review before first payout]`**. Do not ship payouts with an assumed TDS rate.
- Reconciliation: every payout must reference the source `receipt` (perkline HMAC receipt or marketplace sale id) so the money-side record and the local ledger are one-to-one auditable (§6).

---

## 5. Compliance notes (current posture, all flagged where unverified)

| Area | Status | Note |
|---|---|---|
| **RBI Payment Aggregator** | **XOMNI is NOT a PA** | Razorpay is the licensed PA; XOMNI never holds/settles customer funds. PA net-worth threshold ~₹15 Cr — `[FLAGGED: re-verify current RBI PA guidelines]` (MONETIZATION-V2 §2.2) |
| **RBI recurring payments** | Framework applies | AFA at mandate creation + pre-debit intimation per RBI e-mandate rules (§2.2). Build on UPI Intent/Autopay, never UPI Collect |
| **RBI payment data localization** | Applies to payout rails | Payments data stored in India (Razorpay does; XOMNI must not exfiltrate payment data out of India; keep payment data in Razorpay + India-resident storage) (`INDIA-FEATURES` FINDING 3) |
| **DPDP Act 2023** | Assent Aug 2023; **final rules NOT confirmed notified** | MeitY published draft DPDP Rules for consultation Jan 2025; final notification status unconfirmed as of research `[FLAGGED: verify meity.gov.in / gazette]`. Apply consent + notice obligations for payout KYC data and any user data now — do not wait for final rules (`INDIA-FEATURES` FINDING 3, RISKS 3) |
| **AI regulation** | **No binding AI law yet** | MeitY advisories + draft Digital India Act only, as of research date `[re-verify]` — no AI-specific license burden today, but keep labeling/consent obligations on the watchlist (`INDIA-FEATURES` FINDING 3) |
| **GST** | Applies | 18% GST on the 2% gateway fee (already priced into ~2.36%); XOMNI's own GST registration/scheme for invoicing sponsors + marketplace take-rate — `[FLAGGED: CA review with entity choice (India Pvt Ltd vs US LLC, docs/MONETIZATION-V2.md Phase 2)]` |
| **Crypto (India)** | **Not used for India flows** | Finance Act 2022: 30% flat on VDA gains (s.115BBH) + 1% TDS on transfers (s.194S, since 01-07-2022); no loss offset (`MONETIZATION-V2` §2.1; official pages 403-flagged, sections stable) |
| **KYC (recipients)** | Required | Payout recipients onboarded with identity + consent before first payout (§4) |

---

## 6. Sponsorship-engine integration (perkline escrow → real money)

### 6.1 Money-in: sponsor campaign budgets

- Today perkline escrow is **internal math**: campaign budget `P`, spend capped by `escrow_invariant` (total charged ≤ budget, asserted continuously; `escrow_spent[sponsor_id]`), 50/50 dev split, second-price auction, house fills at floor with $0 earnings (perkline v0.3.0, docs/MONETIZATION-V2.md §P1).
- **Rails mapping:** sponsor pays budget `P` via UPI Intent checkout (§2.1). The Razorpay `order.receipt` carries `campaign_<id>`. On `order.paid` webhook → **credit the campaign's escrow** in the perkline ledger (`budget` becomes real funded money; keep a parallel `funded` flag so unfunded campaigns never serve paid slots).
- **USD vs INR:** the rate card is USD ($10–40 CPM); checkout is INR. Spec decision: bill sponsors **in INR at a fixed conversion** (e.g., ₹/USD rate captured at checkout and frozen for the campaign) or introduce a USD-denominated settlement account. **`[FLAGGED: FX policy decision — do not silently float]`** — the escrow ledger must stay single-currency internally (USD math unchanged), with an INR settlement record per top-up.
- **Refund path:** unused escrow (campaign ends under budget) returns via Razorpay refund (no refund fee) or as credit toward the sponsor's next campaign — product decision, but must be written into the campaign terms before checkout.

### 6.2 Money-out: dev earnings

- Dev earnings accumulate from escrow math (`min(0.5 × P × share, 0.5 × P)` per dev; SPONSORS.md §3). **Payout trigger:** accrued earnings ≥ ₹500 threshold (§4) and verified receipts for the underlying events.
- Payout batch → Razorpay Payouts (UPI preferred — free) with `purpose` = dev earnings; each payout references the perkline receipt set. **Receipt-to-money audit:** the HMAC receipt (per-event, locally verifiable) pairs with the Razorpay `payment_id`/`payout_id`; `sync_payload` already ships counts + receipts only (privacy invariant intact — money records are receipts, not telemetry).
- **House campaigns** (budget 0, floor fills) never touch the payout rail — escrow math yields $0 spend/earnings naturally; no payout rows.

### 6.3 Cost-tracker budgets

- cost-tracker caps are **USD model-spend caps** (warn-only default, opt-in hard-stop, blocked calls not logged) — orthogonal to sponsor money. UPI rails do not change cost ledger semantics.
- One integration point: sponsor campaign spend is **revenue**, model spend is **cost**; the `/cost` digest and payout reports stay separate ledgers but share the same "honest math" story (docs/MONETIZATION-V2.md §4 — cost tracking is the proof that sells sponsorship).
- Optional phase-2 hook: when a hard-stop budget fires, the status line can route to house/unsponsored slots — no money impact (house fills are $0).

### 6.4 Sequence (v1 rails build, no code in this spec)

1. Sponsor onboarding: rate card → INR quote (fixed FX) → escrow terms → UPI Intent checkout.
2. `order.paid` webhook → escrow `funded` → campaign serves paid slots; receipts flow as today.
3. Weekly reconciliation job: Razorpay settlement statements ↔ escrow ledger ↔ receipts (idempotent, event_id-keyed).
4. Monthly payout batch: earnings ≥ ₹500 → Razorpay Payouts (UPI) → payout receipt stored → ledger marked paid.
5. Refunds/credits per campaign terms.

---

## 7. Crypto vs UPI — decision record

**Verdict: crypto is irrational for India-domiciled flows; UPI is the rail. (MONETIZATION-V2 §2.2, §5 Phase 3.)**

| Dimension | UPI (Razorpay) | Crypto (BTC/LN) |
|---|---|---|
| Merchant cost | **0% MDR** (UPI) / ~2.36% effective (other modes) | ~0.01–0.1% + base fee routing `[unverified industry range]` |
| Tax overhead (India) | None beyond normal income + GST | **30% flat on VDA gains (s.115BBH) + 1% TDS (s.194S)** per transfer; no loss offset — every transaction carries a tax event |
| Payer friction (sponsors) | UPI app, instant, familiar | Exchange onboarding, INR→crypto conversion, volatility |
| Compliance | RBI framework, licensed PA | VDA rules still forming; CA exposure |
| Payouts to Indian devs | Free UPI payout, ₹500 threshold | TDS obligations at 1% + dev-side 30% on gains → costlier than 2.36% |

- **Keep crypto only as:** (a) Phase 3 Lightning pilot for **global** dev payouts **above a threshold** (Lightspark/LNURL) where wire fees exceed routing fees; (b) a funding/novelty channel (accept BTC/LTC for campaigns) with **explicit tax-disclosure UI**. Both gated on CA review before go-live.
- **Do not design around crypto now.** Revisit only if India clarifies VDA treatment.
- Backlog linkage: P2 item 24 (Lightning micro-payouts pilot) — "India stays UPI — 30%+1% TDS."

---

## 8. Open items / flagged (re-verify before Phase 2 build)

1. UPI Autopay mandate caps ₹15,000 / ₹1,00,000 — NPCI pages bot-gated in research; re-verify npci.org.in.
2. RBI PA net-worth threshold (₹15 Cr) — re-verify current RBI PA guidelines.
3. DPDP Rules final notification status — verify meity.gov.in / gazette.
4. Razorpay Payouts fee card (UPI free; IMPS/NEFT/RTGS per-transfer fee) — pin exact rates.
5. TDS section/rate on dev/creator payouts — CA review.
6. FX policy for USD rate card → INR checkout — product decision (§6.1).
7. RBI e-mandate pre-debit intimation cadence — confirm with Razorpay docs at integration.
8. GST registration scheme (with entity choice) — CA review.
9. No binding AI law as of research date — re-verify quarterly (advisories/draft Digital India Act).

---

## 9. Sources

- `.tmp/research-next/INDIA-FEATURES.md` (2026-08-12) — FINDING 3: zero MDR UPI, 2%+GST others, UPI Collect→Intent migration, DPDP/RBI status flags.
- `.tmp/research-next/MONETIZATION-V2.md` (2026-08-12) — §2 rails facts (2% + GST, Payouts NEFT/RTGS/IMPS/UPI, mandate caps flagged, crypto 30%+1% TDS, PA threshold flagged), §3 sponsorship 2.0, §5 3-phase plan.
- `docs/MONETIZATION-V2.md` — Phase 2 rails plan; payout threshold ₹500/$10; PA no-go rule.
- `docs/SPONSORS.md` — escrow math, 50/50 split, receipts, second-price auction.
- `plugins/perkline` (v0.3.0) + `plugins/cost-tracker` — escrow/receipt/auction internals; USD budget caps.
- **Live re-verified 2026-08-12 (this session):** razorpay.com/pricing FAQ (2%+GST, zero MDR UPI, zero setup/AMC); razorpay.com/docs nav (UPI Intent, Collect→Intent migration pages, Subscriptions/UPI Autopay/eMandate, Payouts).
