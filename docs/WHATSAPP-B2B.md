# WhatsApp B2B Agent Mode — XOMNI as a business-owned WABA assistant

**Status:** P1 wave · Backlog item 12 · 2026-08-12
**Sources:** `.tmp/research-next/INDIA-FEATURES.md` (primary-source research,
live-fetched 2026-08-12) + the Hermes gateway source
(`gateway/platforms/whatsapp_cloud.py`) in the installed Hermes host. Every
price, date, and env var below traces to one of those two.

**TL;DR:** XOMNI runs on Hermes, and Hermes ships an official Meta WhatsApp
Business Cloud API adapter (`hermes whatsapp-cloud`). Point it at a
**business-owned WABA**, and XOMNI becomes that business's WhatsApp service
agent — order confirmations, reminders, notifications — for **≈₹0 per message**
inside the 24h window, ₹0.115 utility templates outside it. One hard rule:
**B2B only in India** (see §1).

---

## 1. The B2B-only rule (compliance first — non-negotiable)

Meta's **AI Provider policy** (ToS update **Jan 15, 2026**; "New pricing
policy for AI Providers" page updated May 21, 2026) lets third-party "AI
Providers" — LLMs / general-purpose AI assistants — operate on WhatsApp **only
where Meta is legally required to permit it**: the **EU DMA markets and
Brazil. India is NOT on that list.**

> **XOMNI rule: never ship a consumer "chat with XOMNI on WhatsApp" assistant
> in India.** A third-party consumer AI bot there is non-compliant; detection
> = WABA ban + loss of the business's number.

**The compliant play is B2B:** deploy XOMNI as a *business's own* service
agent on the *business's own* WABA (kirana order confirmations, exam
reminders, creator notifications, coach follow-ups). The business owns the
WABA, the number, the templates, and the billing — XOMNI/Hermes is the engine
behind it. That is exactly the economically attractive path anyway (§3).

Revisit consumer mode when Meta's Business Agent pricing updates land
(**Aug 1 and Oct 1, 2026**; `pricing_category: "AI_BOT"` already exists in the
Pricing Analytics API) — until then it's policy-blocked in India.

## 2. WABA setup — Meta Business Platform

The WABA (WhatsApp Business Account) belongs to the **business**, not to
XOMNI. Setup order (all in Meta Business Manager / App Dashboard):

1. **Business account** at business.facebook.com — verify the business
   (documentation + display name approval).
2. **WhatsApp Business Account (WABA)** — create under the business; then
   add a **phone number** (dedicated, not already on personal WhatsApp).
3. **App** — create a Meta app, add the **WhatsApp product** (Cloud API).
4. **System user** — create one in Business Settings, grant `whatsapp_business_messaging`
   + `whatsapp_business_management`, generate a **permanent access token**
   (starts with `EAA…`).
5. **Webhook** — a **public HTTPS URL** is required (the wizard's documented
   path is a `cloudflared` tunnel to the Hermes gateway). Meta calls your
   webhook on every inbound message.
6. **Phone number ID + WABA ID** — both are Meta's internal **15–17 digit
   IDs, NOT phone numbers** (the #1 setup trap — see §5).

`hermes whatsapp-cloud` walks all 6 credentials interactively, validates field
shapes, auto-generates the verify token, and prints the follow-up steps
(tunnel, gateway start, Meta webhook-dashboard config, recipient allowlist).

## 3. INR per-message pricing (India)

Per-message pricing has applied since **Jul 1, 2025** (conversation-based
model deprecated). You are charged **only when a template message is
delivered**; the rate depends on template category + recipient country code.
Official Meta INR rate card, effective **Jul 1, 2026**:

| Template category | India rate (INR, per message) | ≈ USD |
|---|---|---|
| **Marketing** | **₹0.8631** | ~$0.010 |
| **Utility** | **₹0.1150** | ~$0.0014 |
| **Authentication** | **₹0.1150** | ~$0.0014 |
| Authentication-international | ₹2.4971 | ~$0.030 |

**Free inside the 24h customer-service window (CSW):**

- All **non-template** messages (text, image, …) inside an open CSW are free
  (since Nov 2024). A CSW opens when the user messages the business (or after
  a template delivery) and lasts **24 hours**.
- **Utility templates inside an open CSW are also free** (since Jul 2025).
- Volume-tier discounts exist for utility/auth categories.

**⇒ A service agent that only replies inside the 24h window costs ≈₹0 per
message.** Proactive outreach outside the window is the only billed path:
utility ₹0.115 (order status, reminders), marketing ₹0.8631 (broadcasts),
auth ₹0.115 (OTPs).

**INR billing localization (mandatory):** launched **Jan 1, 2026** for India
Sold-To businesses. **All WABAs must migrate to INR by Dec 31, 2026** — from
**Jan 1, 2027** Meta stops delivering messages from non-INR WABAs. Meta
invoices Indian businesses in rupees (local entity).

## 4. Template approval flow

Templates are the **only** way to initiate a conversation outside the 24h
CSW — so they're the only billed message type, and they need approval first:

1. **Create** in Business Manager (or Graph API
   `POST /<WABA_ID>/message_templates`) with a category —
   `MARKETING` | `UTILITY` | `AUTHENTICATION` (category sets the price).
2. **Submit for review** — status `PENDING`; review is typically 24–48h but
   can run longer. India-specific content (kirana/coach/creator use-cases)
   should state the business name and purpose clearly to pass.
3. **Approved** → usable outside the window. `REJECTED` → the reason is
   returned; fix and resubmit. `PAUSED` → quality-rating issues (user
   feedback); fix content, don't fight the algorithm.
4. **Send** only APPROVED templates; include the `{{1}}`-style variable
   placeholders exactly as approved.

Inside an open CSW you don't need templates at all — free-form replies.

## 5. The Hermes gateway bridge (`hermes whatsapp-cloud`)

The Hermes host ships the **official** WhatsApp Cloud API adapter
(`gateway/platforms/whatsapp_cloud.py`). It is a *complement* to the Baileys
bridge, not a replacement:

| | `hermes whatsapp` (Baileys) | `hermes whatsapp-cloud` (Cloud API) |
|---|---|---|
| Meta-official | No (unofficial bridge) | **Yes — WhatsApp Business Platform** |
| Account type | Personal | **Business (WABA required)** |
| Public webhook URL | Not needed | **Required** (HTTPS) |
| Auth | QR pairing | **Token-based** (system-user token) |
| Risk | Account-ban risk | ToS-compliant (B2B use) |

**Env vars (exact names from the adapter source):**

| Env var | Required | What it is |
|---|---|---|
| `WHATSAPP_CLOUD_PHONE_NUMBER_ID` | ✅ | Meta's 15–17 digit **internal ID**, NOT the phone number (#1 trap) |
| `WHATSAPP_CLOUD_ACCESS_TOKEN` | ✅ | System-user **permanent token** (starts `EAA…`) |
| `WHATSAPP_CLOUD_APP_ID` | — | Meta app ID (HMAC signing) |
| `WHATSAPP_CLOUD_APP_SECRET` | — | HMAC key for `X-Hub-Signature-256` verification |
| `WHATSAPP_CLOUD_WABA_ID` | — | WABA ID (analytics) |
| `WHATSAPP_CLOUD_VERIFY_TOKEN` | — | `hub.verify_token` shared secret (auto-generated by the wizard) |
| `WHATSAPP_CLOUD_WEBHOOK_HOST` | — | bind host (default: all interfaces) |
| `WHATSAPP_CLOUD_WEBHOOK_PORT` | — | default **8090** |
| `WHATSAPP_CLOUD_WEBHOOK_PATH` | — | default **`/whatsapp/webhook`** |
| `WHATSAPP_CLOUD_API_VERSION` | — | Graph API version (default `v20.0`) |
| `WHATSAPP_CLOUD_ALLOWED_USERS` / `ALLOW_FROM` | — | recipient allowlist (the wizard writes this) |

The adapter covers: outbound text/media via Graph API, inbound webhook server
with verify-token handshake, `X-Hub-Signature-256` HMAC + wamid replay
protection, media upload/download (image/video/audio/document), and **Phase 5:
the 24-hour conversation window + template fallback** — i.e. it implements
exactly the economics in §3.

**The bridge makes it an XOMNI agent:** the same provider config powers every
gateway surface, so the WABA-connected agent runs the full XOMNI stack —
plugins, skills, MCP servers — on the free-model pool (see §6). Secrets live
in `~/AppData/Local/hermes/.env`; settings in `config.yaml`.

## 6. Provider config shape (WABA-connected agent)

No new code needed — the documented shape lives in the provider-pool plugin
(`plugins/provider-pool/core.py`, `WABA_AGENT_BLOCK`): the brain is the same
OpenAI-compatible gateway as the rest of the stack, and the channel is the
Cloud API adapter above. The WABA agent is therefore just a normal Hermes
provider block + the `WHATSAPP_CLOUD_*` env vars + `hermes whatsapp-cloud`
setup. See also [`PROVIDERS.md`](PROVIDERS.md) for the full provider catalog
and [`../plugins/bharat-pack/docs/INDIA.md`](../plugins/bharat-pack/docs/INDIA.md)
for the broader India market brief.

## 7. Cost worked example — kirana order agent (₹0.115 ceiling)

| Event | Billed? |
|---|---|
| Customer: "2 atta, 1 dal — evening" | free (opens CSW) |
| Agent reply: order confirm, ETA (free-form) | free (inside 24h CSW) |
| Agent proactive: "order out for delivery" (utility template) | **₹0.115** |
| Agent proactive: "50% off Sunday" (marketing template) | **₹0.8631** |
| OTP / one-time passcode (auth template) | **₹0.115** |

A service agent that only ever *responds* costs ₹0. A kirana doing daily
utility updates spends ~₹0.115 × deliveries/day. Compare: one marketing
broadcast to 10k users = ₹8,631.

## 8. Checklist before production

- [ ] Business verified; WABA owned by the business (never XOMNI's)
- [ ] System-user token scoped to `whatsapp_business_messaging` only
- [ ] `WHATSAPP_CLOUD_PHONE_NUMBER_ID` holds the **ID**, not the number
- [ ] Public HTTPS webhook (cloudflared) → gateway port 8090
- [ ] Recipient allowlist set (`WHATSAPP_CLOUD_ALLOWED_USERS`) during rollout
- [ ] Templates approved for each category you'll send (marketing/utility/auth)
- [ ] **INR billing migration done before Dec 31, 2026**
- [ ] No consumer "chat with an AI" surface (B2B-only rule, §1)

## 9. Sources

- Research: `.tmp/research-next/INDIA-FEATURES.md` (pricing CSV numbers,
  policy dates; primary sources live-fetched 2026-08-12)
- Meta — WhatsApp Business Platform pricing:
  https://developers.facebook.com/docs/whatsapp/pricing
- Meta — AI Providers pricing policy:
  https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/ai-providers/
- Hermes — Cloud API adapter source:
  `gateway/platforms/whatsapp_cloud.py` (env vars verified from code)
- Related: [`PROVIDERS.md`](PROVIDERS.md) · [`BACKLOG.md`](BACKLOG.md)
  · [`../plugins/bharat-pack/docs/INDIA.md`](../plugins/bharat-pack/docs/INDIA.md)
