# INDIA — Market Brief for the Bharat Pack (XOMNI)

**Source:** `.tmp/research-next/INDIA-FEATURES.md` (primary sources
live-fetched 2026-08-12). Every number here was read from an official page
or official rate-card CSV; anything not verifiable is flagged
`[UNVERIFIED]`.

---

## 1. WhatsApp — B2B-ONLY for XOMNI (hard constraint)

Meta's **AI Provider policy** (ToS update Jan 15, 2026; "New pricing
policy for AI Providers", updated May 21, 2026) lets third-party "AI
Providers" (LLMs / general-purpose AI assistants) operate on WhatsApp only
where Meta is legally required to permit it — **EU DMA markets and Brazil.
India is NOT on that list.**

> **XOMNI rule: never ship a consumer "chat with XOMNI on WhatsApp"
> assistant in India.** Non-compliance = WABA ban.

The compliant play is **B2B**: deploy XOMNI as a *business's own* WhatsApp
service agent on the business's WABA (kirana order confirmations, exam
reminders, creator notifications). Economics support it:

- **Free within the 24h customer-service window** — all non-template
  messages and utility templates inside an open CSW are free (since Nov
  2024 / Jul 2025). A service agent that only replies inside the window
  costs ≈₹0 per message.
- **India per-message rates** (official Meta INR CSV, effective Jul 1,
  2026): Marketing **₹0.8631**, Utility **₹0.1150**, Authentication
  **₹0.1150**, Auth-international ₹2.4971. India is Meta's cheapest tier.
- **INR billing localization** (Jan 1, 2026): all WABAs must migrate to
  INR by **Dec 31, 2026**; non-INR WABAs stop delivering Jan 1, 2027.
- Meta is productizing agent traffic (`pricing_category: "AI_BOT"` exists
  in the Pricing Analytics API; Business Agent pricing updates Aug 1 and
  Oct 1, 2026) — revisit consumer mode when that lands.

## 2. The vernacular AI stack (what this plugin wraps)

| Vendor | What | Cost | Status |
|---|---|---|---|
| **Sarvam AI** | Chat (Sarvam-105B/30B), TTS bulbul:v3 | 100 free credits; 105B ₹4 in / ₹2.5 cached / ₹16 out per 1M tokens; 30B ₹2.5 / ₹1.5 / ₹10; TTS ₹30/₹15 per char | verified (sarvam.ai/api-pricing) |
| **Bhashini (MeitY)** | ASR / TTS / MT, 22+ languages, billion+ inferences | free-to-register, approval-gated | pricing `[unverified — government-funded]` |
| **Krutrim Cloud (Ola)** | Chat, India-resident | free start, no card; bills INR | per-token pricing `[UNVERIFIED — pricing page 404s]` |
| edge-tts `hi-IN` etc. | voice fallback | free | shipped as locale hints in `core.LANGUAGES` |

Model-pool registry entries in `core.INDIAN_MODELS` carry `source="spec"`
and match provider-pool's snippet format, so the Indian stack plugs into
the same config.yaml slot as the 25-model free pool. Cloud residency:
Azure Central/South/West India; AWS ap-south-1/ap-south-2.

## 3. UPI rails — INR-native monetization (future feature #3)

- **Standard UPI = zero transaction fee** for merchants (GPay/PhonePe/
  Paytm flows); cards/wallets/netbanking 2% + GST, zero setup/AMC.
- Recurring: **UPI Autopay (mandates)** under RBI rules — target **UPI
  Intent / Autopay, NOT UPI Collect** (RBI-driven deprecation of Collect).
- RBI payment-data localization applies to payout rails (paying Indian
  creators) — store payments data in India.
- Pricing class for India buyers: ₹149–499/mo vs USD SaaS.

## 4. Regulatory note — DPDP + AI

- **DPDP Act 2023** (assent Aug 2023): consent/notice obligations for any
  user-data features. MeitY published draft DPDP Rules for consultation
  (Jan 2025); final rules **not confirmed notified** as of research —
  `[VERIFY current status at meity.gov.in / gazette]`.
- **No binding AI-specific law yet** (MeitY advisories + draft Digital
  India Act only). IndiaAI Mission (₹10,372 crore `[UNVERIFIED]`) is a
  cheap-enabler watch item.

## 5. Ranked features (impact × feasibility)

| # | Feature | Impact | Feasibility | Notes |
|---|---|---|---|---|
| 1 | Hindi/regional UI + voice (Bharat Pack) | 9 | 9 | ✅ **this plugin** |
| 2 | WhatsApp B2B agent mode (business WABA) | 10 | 6 | AI-Provider ToS → business-owned WABA only |
| 3 | UPI rails + INR pricing | 8 | 7 | Razorpay; UPI 0% MDR; Autopay; payout KYC |
| 4 | India model pool | 6 | 9 | ✅ **this plugin** (Sarvam/Bhashini/Krutrim) |
| 4b | Sarvam TTS dry-run preview (`/bharat tts`) | 5 | 9 | ✅ **this plugin** — payload shape + curl only, no live call, key by env name |
| 5 | Exam-prep skill packs (CBSE/ICSE 10/12) | 7 | 6 | syllabus drift + licensing risk |
| 6 | Offline / low-bandwidth mode | 5 | 4 | deprioritized |
| 7 | Retail-investor packs (IPO + crypto) | 6 | 5 | data licensing + SEBI-adjacent |

## 6. Risks

1. **WhatsApp policy (highest):** consumer AI assistant in India = WABA
   ban; template approval friction; INR migration deadline Dec 31, 2026.
2. **UPI/RBI:** recurring mandates need AFA; UPI Collect deprecated.
3. **DPDP/MeitY:** consent flows; final rules status unconfirmed.
4. **Model/pricing drift:** Sarvam/Krutrim/Bhashini are young vendors —
   free tiers and ₹ prices change; wrap behind provider-pool health checks.
