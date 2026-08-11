# India crypto regulation & Binance status — verified Aug 2026

Condensed live-verified facts for "can an Indian retail user do X in crypto" research. All facts carry their source URL; re-verify before quoting in a new session (this space moves fast — RBI is actively lobbying Parliament).

## Binance in India
- **FIU-IND registration**: registered Aug 15, 2024 as a "reporting entity" after a 7-month block (Jan 2024 URL/app-store delisting); ~US$2.25M penalty; "19th global regulatory milestone"; CEO Richard Teng quote on tailoring services for India. [Cointelegraph 2024-08-15: https://cointelegraph.com/news/binance-india-relaunch-fiu-registration]
- **Futures/derivatives AVAILABLE to Indian users in 2026** (first-party proof): Binance announcement API with `region: IN` headers lists "India Exclusive: Trade Futures & Share 20,000 USDT Rewards" (2026-05-13, article id 273892) plus ongoing India promos through 2026-08-03. Binance would not run an India-exclusive futures campaign if Indians couldn't trade futures.
- **The "restriction" memory is Bybit, not Binance**: Binance's own feed carried "Breaking: ByBit Restrict Trading For Indian Users" (2025-01-10). Binance never restricted India derivatives.
- **Jun 22, 2026 "tightening" = Travel-Rule KYC, not a trading ban**: Indian users must now declare originator/beneficiary details (name, PAN/national ID, country, full address) on every crypto deposit/withdrawal; ET explicitly: Binance "has not imposed any limits on deposits and withdrawals"; Indians ≈ 7–9% of Binance's 300M registered users (~21–27M). [ET 2026-06-23: https://economictimes.indiatimes.com/markets/cryptocurrency/binance-tightens-rules-for-india-users-falls-in-line/articleshow/131922565.cms]
- **Not on any sanction list**: FIU-IND Oct 2025 notices hit 25 UNREGISTERED offshore platforms (Paxful, BingX, BitMEX, LBank, Phemex, CoinEx, Poloniex, Changelly, ...); Binance absent; ~50 VDA SPs FIU-registered; registration circular tightened (3rd revision, ~Sep 2025: ownership/tax/CERT-In audit/in-person meetings). [MediaNama 2025-10-03: https://www.medianama.com/2025/10/223-fiu-ind-notices-25-offshore-crypto-platforms-pmla-violation/]
- FIU-IND official VDA list subpage is WAF-blocked to this host — use press for the registered list.

## Tax regime (unchanged as of Aug 2026)
- **30% tax on VDA gains + 1% TDS on all transactions** — stated as current law by Moneycontrol reporting the May 20, 2026 Parliament Standing Committee meeting with Binance/WazirX/ZebPay (exchanges asked for TDS cut to 0.1%; denied). [Moneycontrol 2026-05-20: https://www.moneycontrol.com/news/business/startup/parliament-finance-panel-meets-binance-wazirx-zebpay-on-crypto-regulations-taxation-13925545.html]
- **Budget 2026 (Feb 1, 2026) RETAINED the 30%/1% regime** — "No Relief For Crypto Investors As India Retains Current Crypto Tax In Budget 2026" [Decrypt 2026-02-02, via Google News RSS]; Budget added new penalties for non-disclosure/misreporting of VDA assets [Moneycontrol 2026-02-01, same index].
- No loss offset against other income; derivatives P&L taxed the same. Enforcement ramping: tax authority targeted 400+ wealthy Binance traders (~US$42M evasion, Oct 2025, per The Block via GNews index); <25% of 645K FY2023 filers reported crypto trades [Cointelegraph 2026-07-08: https://cointelegraph.com/news/india-crypto-tax-underreporting-rbi-ban-push].

## On/off-ramps
- **Binance India: P2P in INR is the working on-ramp** — active INR P2P market ("Binance P2P Will Update Maker Fees for INR Market" 2024-10-15; "Trade with Shield Merchants, 75,000 INR rewards" 2026-04-01, from Binance announcement API region-IN). P2P settles via UPI/IMPS between individuals; banks don't block person-to-person UPI.
- **No direct bank-to-Binance rails** — Binance relies on crypto-only + P2P rupee access; by contrast Coinbase launched direct INR deposits/withdrawals via IMPS in India Jun 1, 2026 after its own FIU registration (Mar 2025), and offers spot + perpetual futures to Indian users. [Cointelegraph 2026-06-01: https://cointelegraph.com/news/coinbase-rolls-out-rupee-bank-rails-in-india-after-watchdog-approval]
- UPI-to-exchange remains unsupported by payment networks since the 2022 Coinbase-UPI episode (NPCI distanced itself).

## RBI / bank blocks
- **No new RBI circular or bank-level block in force (as of 2026-08-10).** 2018 banking circular struck down by Supreme Court Mar 2020; RBI May 2021 clarified banks can't cite it.
- **RBI is lobbying, not banning**: told the Parliamentary Standing Committee on Finance (Jul 2–3, 2026) it backs a "containment" strategy — keep banks insulated from crypto, prevent crypto in payments/settlements, "prohibition remains a recognized policy option" — but this is a position paper to a panel, NOT enacted law. [Cointelegraph 2026-07-03: https://cointelegraph.com/news/rbi-crypto-containment-india-policy-report; Reuters + India Today headlines 2026-07-08 "RBI backs crypto ban" via Google News RSS]
- Bank rails demonstrably still work for FIU-registered exchanges (Coinbase IMPS launch Jun 2026 post-dates the RBI statement).
- Watch item: policy debate is live; a future ban is possible, not present.

## Method notes for this sub-topic
- First-party product availability proof: Binance announcement API with region headers (see `live-news-and-blocked-sites.md` "Binance announcement CMS API" section).
- Search fallback when engines are captcha'd: Google News RSS with `hl=en-IN&gl=IN&ceid=IN:en`.
- Indian press access: MoneyControl/MediaNama via curl `<p>` extraction; Economic Times via browser snapshot only.
- Platform age policy: exchanges require 18+ for KYC (standard; couldn't verify on-page here — Binance pages blocked — flag as unverified if it matters).
