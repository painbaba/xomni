# XOMNI Sponsorship — Sponsor Guide

**Audience:** prospective sponsors · **Status:** early network, honest numbers
**What you sponsor:** a single, clearly-labeled sponsor line shown while developers work in the XOMNI agent.

---

## 1. What the network is

XOMNI is a free, open-source (MIT/Apache) terminal coding agent that merges 7 agents
(Hermes, OpenCode, Codex, Aider, Goose, OpenClaw) with 25 verified free models and a
one-command Windows install. Developers install it because it's free and useful — and
they opt in to a **sponsor line**: one line of text in the agent's status area while it works.

- **Impression-counted:** every render is counted per work event (LLM/tool call), not guessed. Idle gaps are skipped. You pay for what was actually shown.
- **50/50 split:** developers keep 50% of your campaign budget, split across impressions their installs generated. XOMNI's 50% is the network fee for running the rails (counting, receipts, escrow, auction).
- **Honest scale note:** the network is young and the installed base is still small. We are transparent about reach — you get verified impression counts, never inflated ones. Early sponsors get first pick of slots at fixed low rates.

## 2. What you buy

| Tier | What counts | Indicative price |
|---|---|---|
| **CPM** | 1,000 impressions (renders of your line) | $10–$40 / 1k |
| **CPC** | 1 click/engagement (dev opens your link) | $1–$8 |
| **CPA** | 1 action (dev completes your signup/install) | $20–$200 |

- **Targeting:** by agent (e.g. Codex sessions only), by country/region, and by local stack relevance (matched on local tool tags — locally; nothing leaves the machine; prompts and code are never read or transmitted).
- **Campaign shape:** you set budget `P`, choose a tier, pick targeting. The engine caps total spend at `P` — you cannot be overbilled.

## 3. Pricing math

**The formula.** For a campaign with fixed budget `P` and a developer whose installs served `share` of the campaign's impressions:

```
dev earnings  = min(0.5 × P × share, 0.5 × P)
sponsor spend = 0.5 × P × share   (per dev, escrow-capped so total ≤ P)
XOMNI fee     = the other 0.5 × P
```

The `min(..., 0.5 × P)` cap is the **payout invariant**: no single dev can ever take more than half your budget, and total dev payouts can never exceed the half you agreed to share. Your spend is bounded by escrow at every step (§4).

**Example 1 — fixed budget, CPM.** You run a **$500 CPM campaign**. Devs collectively split **$250**; XOMNI keeps **$250**. If one dev's installs served 10% of impressions, that dev earns `0.5 × 500 × 0.10 = $25`.

**Example 2 — a big dev.** You run **$1,000**. A dev's installs generate 80% of impressions: `min(0.5 × 1000 × 0.8, 0.5 × 1000) = $400`. The cap binds only if share exceeds 100% (it can't) — a safety rail, not a discount.

**Example 3 — CPC.** You set **$2 per click, $300 budget**. 60 devs click → `60 × $2 = $120` billed (escrow-capped under $300); devs split $60, XOMNI keeps $60. Unused budget is never charged.

## 4. Trust rails

- **Receipts.** Every render, click, and action carries an **HMAC-SHA256 signed receipt** (nonce, sponsor, event, timestamp). You verify each delivery yourself with the public verify tool — no shared ledger, no "trust us."
- **Escrow.** Your budget is escrowed per campaign. Spend is deducted only against verified events and is invariant-capped: total charged never exceeds budget (asserted continuously). No overbilling, no surprise invoices.
- **Second-price auction.** When multiple sponsors bid for a slot, the **second-price sealed-bid auction** runs: the highest bidder wins but pays the *second-highest* bid. You never pay more than you bid, and only what the market valued the slot at.
- **No telemetry.** Only counts, receipts, and a session hash sync; prompts, code, paths, and tags never leave the machine. Source is fully open for audit.

## 5. Onboarding

1. **Waitlist** — join the sponsor waitlist (company, product, budget range, tier). We publish it publicly as proof to devs that sponsors are real.
2. **Intro call** — 15 minutes: your goals, targeting options, honest reach numbers today (no inflated claims), and a rate card for your tier.
3. **Campaign setup** — you set budget `P`, tier, targeting, and copy. You approve escrow terms and the receipt-verification flow before anything runs.
4. **Launch** — the campaign serves in live dev sessions; you can pause/resume anytime.
5. **Reporting** — dashboard + raw receipt stream: impressions, clicks, actions, spend against escrow, and per-dev payout math. Verify every number independently.

## 6. FAQ

**Q: How do I know impressions are real?** Every render is receipt-signed and independently verifiable; the counting code is open source. Sync sends counts and receipts only — audit the math end-to-end.

**Q: What if my campaign underperforms?** You pay per verified event, escrow-capped at budget. Unused budget returns. Pause or stop anytime.

**Q: What targeting data is available?** Agent type, country/region, and stack-relevance tags. No prompts, code, or personal data — ever.

**Q: What does it cost to start?** Campaigns start in the **$250–$2,000 range**; the waitlist tells us your range so we can fit the slot. Early sponsors get fixed low CPM rates.

**Q: Why will devs tolerate ads in their agent?** The line is opt-in, clearly labeled, one line, capped in frequency — and it pays the developer 50% of your budget. The ad is the feature they installed.

---

**Next step:** join the waitlist → we reply within 2 business days. Honest numbers, verified delivery, escrow-protected spend.
