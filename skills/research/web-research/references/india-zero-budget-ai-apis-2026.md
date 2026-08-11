# India Zero-Budget AI API Channels — verified knowledge bank (compiled Aug 7, 2026)

Every claim below was live-verified on Aug 7, 2026 against official docs/pricing/agreement pages, news RSS, or browser. "UNVERIFIED" = login-gated or no official source at compile time. Bottom line: **no international AI provider accepts UPI**; Indian Visa/MC debit cards with international e-commerce enabled are the only card path (RuPay will not work).

## 1. GitHub Student Developer Pack
- Official eligibility FAQ (education.github.com/students accordion, expand via browser_console): students **13+, enrolled in a degree/diploma-granting course**, school email and/or dated enrollment proof. **Class 12 school students are NOT officially eligible** (document-based approvals sometimes happen — anecdotal, UNVERIFIED). Apply at github.com/settings/education/benefits.
- Pack contents (education.github.com/pack, live): Azure for Students **$100 credit, no card, 18+ only**; Azure 13–17 = App Services/Functions/Notification Hubs/MySQL-in-app/App Insights/DevOps, no credit; GitHub Pro; **Copilot Student — new plan signups temporarily paused** (as of Aug 7, 2026); Codespaces Pro (3K Actions min, 180 hrs/mo, 20GB storage); Heroku $13/mo × 24; MongoDB $50 Atlas; JetBrains; Camber Student (200 LLM msgs/mo); Notion Education + AI; Stripe $1k fee waiver; Namecheap/.TECH/Name.com domains; FrontendMasters 6mo; Educative 6mo.
- ⚠️ **GitHub Models retired July 30, 2026** (playground, catalog, inference API, BYOK all gone) — do not recommend it; docs.github.com/en/github-models states retirement.

## 2. Chinese provider payment methods (no UPI anywhere)
- **DeepSeek** (platform.deepseek.com): Alipay/WeChat + international Visa/MC reported; top-up login-gated — UNVERIFIED live. No free tier. Note: DeepSeek V4 Flash API in public beta (2026).
- **Kimi/Moonshot**: top-up = **Alipay + WeChat only** — verified via official 充值协议 at platform.kimi.com/docs/agreement/payment.md; international platform.kimi.ai account/billing guide also lists only WeChat Pay + Alipay QR. No cards, no free tier.
- **MiniMax**: China platform top-up = **WeChat Pay + corporate bank transfer only** (verified docs/faq/about-account.md). International card path UNVERIFIED. Token Plan invite promo (10% voucher) runs Dec 26, 2025–Aug 31, 2026.
- **Zhipu/GLM**: China (open.bigmodel.cn) = Alipay/WeChat. **International z.ai = free tier that needs no payment**: pricing.md shows GLM-5.2 / 5.1 / 5 / 4.7 / 4.6 / 4.5 / 4.5-X / 4.5-Air all "Limited-time Free"; paid via Stripe (min $0.50 after discounts). Best cheap Chinese option from India.
- **Alibaba Model Studio (intl)**: free quota for new users (Singapore region); must complete profile → PAYG (needs card) to continue. Quota amount UNVERIFIED.

## 3. Referral / credit programs verified (2026)
- **OpenCode Go** (opencode.ai/docs/go): $5 first month, $10/mo after, ~18 curated open coding models, API key usable in any agent. **Refer-a-friend = $5 credit to both** (official @opencode X post May 20, 2026). Payment via card (Stripe) — UPI UNVERIFIED. Referral credit can effectively zero out month 1 IF a card is available.
- **z.ai Invite Friends, Get Credits** (docs.z.ai/devpack/credit-campaign-rules.md, rules updated Mar 15, 2026): inviter earns 10% of friend's first paid GLM Coding order as credits, paid out after 3 successful invites; invitee gets 10% off first order.
- **MiniMax Token Plan invite**: 10% of friend's payment as voucher (90-day validity), invitee 10% off.
- Puter referral: UNVERIFIED.

## 4. India-specific (all verified real)
- **Sarvam AI** (docs.sarvam.ai): **₹100 free credits for every new user, never expire**; INR pricing (Sarvam 105B chat ₹29.28/1M in, ₹10.98 cached, ₹73.2 out); top-up from dashboard.sarvam.ai/billing — UPI expected, UNVERIFIED. Vision API ₹0.5/page after 67% cut (Jun 2026).
- **IndiaAI Compute Portal** (compute.indiaai.gov.in): 10,000+ GPUs via empanelled CSPs (E2E Networks, Jio Platforms, Tata Comm, Sify, NTT/Neysa…); end-user categories incl. **Students**, Early-Stage Startups/Researchers, India AI Fellowship; subsidized ~₹67/hr (Mar 2025, IT Min. Vaishnaw); application-based. Free student credits UNVERIFIED.
- **Bhashini** (bhashini.gov.in): real govt Indian-language AI (ASR/TTS/MT); JS-only portal; register for API access — exact limits UNVERIFIED. Coverage expanding (OpenGov Jun 2026, UNDP Dec 2025).
- **E2E Networks** (e2enetworks.com): India GPU cloud (H100/H200/B200), MeitY-empanelled, "Get Started with Free Credits", B200 from $6.99/hr.
- **Jio AI Cloud** (aicloud.jio.com): free 100GB AI cloud storage for Jio users — consumer product, NOT a dev API. **Krutrim**: free-cloud promo ended Diwali 2025; now paid INR.

## 5. No-card checklist (all signup + use from India without any card)
| Channel | Free tier (verified) | URL |
|---|---|---|
| Google AI Studio | ~5,000 req/day free (Jun 2026 roundup; limits were cut mid-2026 but tier remains) | ai.google.dev/gemini-api/docs/pricing |
| NVIDIA NIM | Free API for developer-program members; token-credit expansion Jul 2, 2026 | build.nvidia.com |
| Groq | Free, no card; ~5 free models post-Jun 17, 2026 deprecations; gpt-oss-120b 1k req/day; Whisper v3 Turbo free | docs.groq.com |
| Cerebras | Free tier; gpt-oss-120b free | cloud.cerebras.ai |
| Cloudflare Workers AI | 10,000 neurons/day free (docs updated Aug 7, 2026) | developers.cloudflare.com/workers-ai/platform/pricing |
| HuggingFace | Free inference API (rate-limited) | huggingface.co/pricing |
| Puter | Free access to OpenAI/Claude/Gemini/Llama/DeepSeek via Puter.js — no API key, no card (official tutorial Jul 2026) | developer.puter.com/tutorials/free-unlimited-ai-api |
| OpenRouter | 30+ `:free` models, signup no card | openrouter.ai |
| Bonus | Mistral (phone verify, no card, 2 RPM free); SambaNova free tier; z.ai GLM limited-time free; Sarvam ₹100 | console.mistral.ai |

## Verification techniques that worked (no login needed)
- Payment methods without login: fetch `llms.txt` for docs index, then the **legal/agreement .md mirrors** — platform.kimi.com/docs/agreement/payment.md, platform.minimaxi.com/docs/faq/about-account.md, docs.z.ai/guides/overview/pricing.md, docs.sarvam.ai/api/getting-started/pricing.md.
- Secondary roundup: r.jina.ai on HackerNoon "The Zero-Cost AI Stack for Developers in 2026" (Jun 25, 2026) — provider-by-provider free-tier detail.
- News RSS: IndiaAI GPU ₹67/hr (Mar 2025), NVIDIA token credits (Jul 2026), Sarvam Epoch API credits (Jul 2026).
