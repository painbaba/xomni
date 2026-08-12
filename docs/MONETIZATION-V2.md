# XOMNI — Monetization V2 (Implementation Plan)

**Status:** build plan (P1 shipped 2026-08-12) · **Source of truth:** `.tmp/research-next/MONETIZATION-V2.md` (research memo, verified numbers)
**Guiding rules:** never monetize before trust; devs pay ₹0/$0 forever; privacy invariants (no prompt/code telemetry) are non-negotiable; UPI over crypto for India (30% VDA tax + 1% TDS makes crypto irrational there); 15% marketplace take-rate is the app-store norm (Apple Small Business Program, Google Play — verified).

---

## Phase 1 — Foundation: trust + distribution (4–6 weeks, ~0 entity work) ✅ P1 shipped

| Item | Status |
|---|---|
| **Cost tracking + budget caps** (`plugins/cost-tracker`) | ✅ **SHIPPED (this P1)** — sqlite cost ledger (`~/.xomni-cost/costs.db`), per-day/week caps, warn-only default + opt-in hard-stop, `/cost` commands, `cost_track` tool. **Zero hooks.** Free forever (moat). |
| **Sponsorship 2.0 deltas 1–2** (`plugins/perkline`) | ✅ **SHIPPED (this P1)** — contextual session slots (sponsor `tags` matched against a caller-supplied context string), auction floor (default CPM $10 min), house campaigns auto-fill unsold slots at floor price. v1 behavior preserved (`floor=0.0` default, empty tags = context-agnostic). |
| CPA verification spec (delta 3) | ⏳ Spec only — sponsor-side webhook/JS pixel handshake; 1–2 weeks. |
| omni-skills marketplace installer | ⏳ P0 from docs/COMPETITIVE.md — consume SKILL.md / marketplace.json / .claude-plugin / .codex-plugin formats. |
| 3–5 pilot sponsors, manual payouts | ⏳ Direct outreach; invoice + UPI QR / bank transfer (no payment stack yet). |

## Phase 2 — Rails: entity + payments (6–8 weeks)

- Incorporate (India Pvt Ltd vs US LLC decision doc — drives Razorpay KYC, GST, tax structure).
- **Razorpay integration:** sponsor checkout (2% + GST, ~2.36% effective) + dev payouts via Razorpay Payouts (UPI/IMPS/NEFT for India; Wise for global), payout threshold (₹500/$10) to amortize fees. Wire existing escrow/receipt invariants to real money. XOMNI must NOT become a Payment Aggregator (RBI PA rules).
- **Marketplace revenue-share v1:** hosted marketplace with "verified" badge (sandbox-gate review + 544-skill DB curation), **15% take-rate** (app-store parity), payouts to creators via the same rail. Price *services, not bytes* — git-cloneable content cannot be paywalled (structural piracy).

## Phase 3 — Scale: crypto pilot + yield (8–12 weeks, conditional)

- **Lightning pilot** for global dev payouts above a threshold (Lightspark/LNURL); India flows stay UPI. Tax-disclosure UI + CA review before go-live.
- Sponsorship 2.0 delta 3 (CPA webhooks), per-agent/country targeting, automated auction floor.
- Team seats / managed gateway enterprise tier — only after the network has cash flow.

**Sequencing:** Phase 1 = zero-cost trust + distribution (moat work); Phase 2 = monetize rails once sponsors exist (demand-pull); Phase 3 = optionality (crypto) + yield.

---

## P1 shipped — what exists now

### `plugins/cost-tracker` (zero hooks)

- `core.py` — pure stdlib (sqlite3): `log_call(model, provider, tokens_in, tokens_out)` → append-only ledger row with estimated USD cost from `COST_TABLE` (25 verified-free gateway models at $0; ~13 paid models at public list prices; unknown models → fallback rates, **flagged**). Budget caps per day/week (0 = no cap), **warn-only by default**, opt-in **hard-stop** blocks new calls over cap (blocked calls are NOT logged). `budget_status`, `top_models`, `totals`, `spent`, `set_budget`, `cmd_report` (/cost), `cmd_budget` (/cost budget), `cost_track` (the tool provider-pool calls explicitly).
- **Zero hooks** — new-plugin rule: nothing on the agent hot path.
- Tests: `cd plugins/cost-tracker && python -m unittest tests.test_core -q` → **14 tests**.

### `plugins/perkline` — sponsorship 2.0 deltas (v0.3.0)

- **Delta 1 — auction floor + house campaigns:** `run_auction(led, bids, floor=0.0)` discards bids below the floor; winner pays `max(second_price, floor)`; unsold slots auto-fill with the house campaign (`house_campaigns` config) at the floor price — impressions stay counted, house fills accrue $0 dev earnings, ledger honest. `/perkline auction` runs with the configured `auction.floor` (default CPM $10).
- **Delta 2 — contextual session slots:** sponsors carry `tags` (e.g. `["codex"]`, `["media", "omni"]`) matched against a caller-supplied context string: `eligible_sponsors(led, repo_tags, context)`, `record_render(..., context=...)`. Empty tags = context-agnostic (v1). Local-only, receipted; prompts/code never read (SPONSORS.md §4 privacy invariant).
- **Backward compatible:** `floor` defaults to 0.0; all v1 signatures still work; existing 18 tests unchanged and green.
- Tests: `cd plugins/perkline && python -m unittest tests.test_core -q` → **27 tests** (18 existing + 9 new delta tests).

---

## What stays free (the moat — never broken)

- **Core agent + all 17 plugins + 25 verified free models + Windows support** — free forever (SELLING.md §4).
- **Cost tracking / budget caps** — free; it is the honest-math proof that sells sponsorship, not a product to sell.
- **Marketplace installs + verified badges** — free to install; fees only on *money flows* (creator payout take-rate, sponsor campaigns).
- **Dev earnings: 50/50 sponsor share forever** — the retention hook and network-effect moat.
- **Privacy invariants** — no prompt/code telemetry, ever; receipts-only sync. Non-negotiable.

---

## Verified anchors (from research memo, 2026-08-12)

- Razorpay: 2% + GST per transaction, all modes; UPI Autopay eMandate; Payouts via NEFT/RTGS/IMPS/UPI.
- India crypto (Finance Act 2022, ss.115BBH + 194S): 30% flat on VDA gains + 1% TDS on transfers → **UPI over crypto for India**.
- App-store take-rate norm: Apple Small Business Program 15%, Google Play 15% → **15% marketplace take-rate**.
- OpenRouter live: 406 models, only 16 `:free` → cost volatility structural → budget caps are retention.
- codeburn (9,245★ MIT) validates standalone cost tracking; XOMNI's is stronger (the agent IS the spender).

## Flagged items (re-verify before Phase 2/3 build)

UPI Autopay mandate caps (₹15,000/₹1,00,000 — NPCI page bot-gated) · India crypto FAQ text (incometaxindia.gov.in 403) · RBI PA net-worth threshold (₹15Cr) · Google AI Overviews ads / Perplexity sponsored questions (reported only) · Lightning routing-fee % (industry range ~0.01–0.1%, unverified) · OpenRouter :free rate limits.
