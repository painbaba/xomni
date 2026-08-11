# XOMNI — Go-To-Market Plan

**Status:** Draft v1 · **Audience:** internal (solo founder) · **Last updated:** launch planning
**North-star metric:** daily active installs (see §7)

This plan is written to be honest, not optimistic. Every number that is not a fact is
marked as an assumption. No invented traction. The product facts below are real and are
the only claims we make in marketing:

- **7 merged agents** out of the box (Hermes, OpenCode, jcode, Codex, Aider, Goose, OpenClaw)
- **17 plugins**, **25 verified free models** (verified = tested to actually work, not scraped from a list)
- **Sponsorship engine**: sponsor line, 50/50 impression share, capped payouts, CPM/CPC/CPA tiers, receipts, escrow, auction
- Works on **Windows**, **one-command install**, sources MIT/Apache, **677 passing tests**

---

## 1. WHO BUYS

Nobody "buys" XOMNI in the traditional sense — the agent is free. The buyers are
**sponsors who pay for attention inside the agent**, and the sellers are **developers
who install it and earn a share**. Both sides are customers, and both ICPs below matter.

### Primary ICPs (developers who install and earn)

| ICP | Who they are | Why XOMNI fits | Pain we solve |
|---|---|---|---|
| **Solo devs** | Freelancers, indie hackers, one-person SaaS builders | Terminal-native, one-command install, works on Windows | Paying $20/mo+ per AI tool on top of already-thin margins |
| **Small agencies** (2–15 devs) | Web/automation shops billing clients hourly | Multi-agent coverage (Codex, Aider, Goose...) covers their whole stack; 50/50 sponsor share is a side revenue line | Tool sprawl: 4 agents × 4 subscriptions; they want one client that does all of it |
| **AI-tool tinkerers** | People who try every new CLI agent, watch AI YouTubers, live on /r/LocalLLaMA and Hacker News | 25 **verified** free models is a concrete, checkable claim; sponsorship line is novel and fun to try | Subscription fatigue + FOMO; they want the thing that's *free and interesting* |
| **YouTube / Content-Rewards creators** | Dev YouTubers, tutorial writers, people earning from content-reward programs | They already use free models for cost reasons; sponsor line monetizes their installs passively | Their content-reward income is small and unstable; every marginal rupee/dollar counts |

**The wedge for all four:** "One command, 6 agents, 25 free models that actually work."
The sponsorship earnings are the retention hook — but only after sponsors exist (see §4).

### Secondary ICPs (India-specific)

| ICP | Who they are | Why XOMNI fits | Distribution reality |
|---|---|---|---|
| **Indian dev shops** | Small service companies (2–50 devs), often WhatsApp-native, price-sensitive, deal in rupees | Free forever core = zero procurement friction; no USD subscription to justify | They don't read Hacker News; they live in WhatsApp groups and Telegram channels. Reach = broadcast + vernacular explainer |
| **College devs** | CS students, hackathon crowds, first-job seekers | Free is the only price they can afford; 25 free models is a career cheat-code for them | Massive volume, near-zero budget; good for seeding installs (the metric that matters) and word-of-mouth; weak as direct revenue |

**Positioning note:** price is *not* the barrier for any ICP because the core is free.
The barrier is **trust** (a third-party CLI agent, see §6) and **discovery** (nobody knows
XOMNI exists yet). The plan below is mostly a discovery-and-trust plan.

---

## 2. THE PRODUCT OFFER

### Open core: the agent is the free bait (and it's genuinely good)

- Agent itself: **free forever, MIT/Apache sources** — no license key, no "pro" wall on core features.
- 7 merged agents, 17 plugins, 25 verified free models, Windows support, one-command install, 677 tests.
- "Free forever" is a strategic choice, not charity: we need **installed base**, because the installed base *is* the product we sell to sponsors.

### The moat: the sponsorship NETWORK

Revenue is not the software. Revenue is the **two-sided network**:

```
Sponsor (pays) ──► XOMNI sponsor marketplace ◄── Dev (installs + earns 50%)
                        │
                        └── XOMNI keeps 50% (network fee)
```

- XOMNI **runs the sponsor marketplace**: ad serving, impression counting, receipts, escrow, auction, payout caps.
- Devs earn **50/50** on impressions their installs generate.
- XOMNI takes the **other half as the network fee**.

Why this is a moat and not a feature:

1. **Network effects both ways.** More installs → sponsors pay more for reach → more sponsor money → more devs install to earn → more installs. Competitors can copy the sponsor line in a week; they cannot copy 10,000 installs overnight.
2. **XOMNI owns the rails.** Counting, receipts, escrow, auction — the trust layer between sponsor and dev. Whoever runs the rails keeps the fee.
3. **Switching cost for devs.** Once a dev has sponsor earnings flowing, switching agents means forfeiting that stream.
4. **Moat is earned, not claimed.** This only holds if we actually reach meaningful install counts and real sponsors. Until then it's a feature (see §4 for the honest version).

### Future paid tiers (only after the network exists)

- **Managed gateway** — hosted model routing/fallback for teams that don't want to run their own config (priced per seat or per token).
- **Team seats** — org management, shared model configs, centralized billing.
- **Priority support** — SLA'd help for agencies whose billable hours depend on the agent.

Order matters: do **not** launch paid tiers before the network. Paid tiers before sponsors
= confusing the offer and diluting the "free forever" story that drives installs.

---

## 3. CHANNELS (in priority order)

Priority = expected installs per hour of effort, given we are one person with no budget.
Every channel has concrete actions, not vibes.

### 1. GitHub — stars via README + Show HN

- **README is the landing page.** One-command install at the very top, then a 10-second demo GIF, then the facts table (7 agents / 17 plugins / 25 verified free models / 677 tests). Screenshot of the sponsor line in action.
- **Show HN post** ("Show HN: XOMNI — one CLI, 6 agents, 25 free models, devs earn 50% on sponsored impressions"). HN is the single highest-leverage audience for solo devs and AI tinkerers. Post on a Tuesday/Wednesday morning US time.
- `hackernews` launch support: answer every comment, fix every legitimate gripe within 48h, log all feedback.
- Star-for-star / giveaway tactics: no. Organic only — a gamed star count dies in one HN comment thread.

### 2. X/Twitter — launch thread, build in public

- **Launch thread** (10–15 posts): hook = "I built a free open-source CLI that merges 6 AI agents, verified 25 free models actually work, and pays you 50% of sponsor revenue for installing it. Thread: how it works ↓". Demo GIF, the sponsor line, the numbers.
- **Build-in-public cadence** after launch: 3×/week — shipping updates, model-verification wins, sponsor-engine progress, test-count screenshots (677 and climbing).
- Reply to every AI-agent tweet from accounts >10k followers with something genuinely useful, not a pitch.

### 3. Product Hunt

- Launch **2–3 weeks after Show HN** (ride the momentum, don't split the launch).
- First-party comment thread: "what I learned building a sponsor marketplace inside a terminal agent" — the story *is* the product.
- Ask the small group of real users we'll have by then to upvote organically. No paid votes.

### 4. YouTube — 90-second demo video

- **One video, 90 seconds max:** install → `/models` showing 25 verified free models → sponsor line rendering in a real session → "devs earn 50%".
- Script it like a terminal screencast with captions; no intro, no outro, no music.
- Post on YouTube + embed in README + post to HN thread + tweet. 90 seconds because attention is the constraint, not production value.
- Second video (optional, later): "I put a sponsor marketplace inside a coding agent — here's what sponsors pay."

### 5. Dev Discords / Telegram groups

- Target: AI-tooling Discords (LangChain/LlamaIndex-adjacent, local-LLM servers), CLI-tool communities, and the big dev Telegram channels.
- **Rule: never spam.** Show up as a member for a week, then share the tool where it solves a stated problem ("what free models actually work in 2026?" — we have the verified list).
- Concrete: 10 communities × 1 genuine contribution per week. Track replies, not joins.

### 6. India-specific — WhatsApp broadcast + vernacular explainer

- **WhatsApp broadcast to dev groups** (the ICP's native channel): short Hindi/English-Hinglish message with the one-command install and the free-models hook. Keep it under 3 lines; the link is the pitch.
- **Vernacular explainer:** a 2–3 minute Hindi (or Hinglish) screen-recording walkthrough — "6 AI agents free, 25 free models, Windows pe chalega" — posted to YouTube/WhatsApp status/Telegram. Price-sensitivity means "free + works on Windows" is the entire value prop; say exactly that.
- College devs: post in campus/hackathon WhatsApp groups and Telegram channels; the free-models angle is the hook, the 50% sponsor share is the bonus.
- Expect lower conversion, higher trust-building: India reach is cheap, so volume is the play — 100 group shares beats 1 polished post.

---

## 4. PRICING

### The offer pricing (what devs pay)

**₹0 / $0 forever.** The core agent, all 7 merged agents, 17 plugins, 25 verified free
models, Windows support — free. No trial, no freemium wall, no "community edition"
that's secretly crippled. This is the whole trust story, and it must never be broken.

### The business pricing (what sponsors pay)

The sponsorship network is the business. Honest sketch — **every number below is an
assumption to validate with real sponsor conversations, not a commitment**:

| Item | Assumption (to test) |
|---|---|
| Sponsor pays per campaign | **$X per campaign** (X to be set in sponsor talks; start in the $250–$2,000 range per campaign) |
| Dev share | 50% of campaign budget, split across impressions their installs generated |
| XOMNI network fee | 50% (the other half) |
| Payout cap | capped per dev per period (already in the engine — prevents a single dev farming the network) |
| Rate model | CPM / CPC / CPA tiers (already in the engine) |
| Trust rails | receipts, escrow, auction (already in the engine — these are the sales pitch to sponsors) |

**Worked example (illustrative):** a sponsor runs a $500 campaign. Devs whose installs
served the impressions split $250; XOMNI keeps $250. If a dev's installs generate 10% of
a campaign's impressions, they earn $25. Tiny numbers per dev — which is exactly why the
**capped payout + receipts** design matters, and why we must be honest with devs about
what "earn 50%" realistically means at our launch scale.

### The honest problem (read this twice)

> **The network is worthless until sponsors exist.** A dev installing XOMNI to earn
> sponsor money, with zero sponsors on the other side, earns $0. We cannot ship this
> plan on the promise of "future sponsors."

**Phase 1 (now → first real sponsor):**
1. **Demo sponsors:** ship 1–2 friendly sponsors (a dev tool or model provider we know,
   or a low-cost campaign from our own network) so the sponsor line actually renders and
   the earnings flow is real, end-to-end, from day one.
2. **Sponsor waitlist:** a public "Sponsor a campaign" page + waitlist form. The waitlist
   is the honest proof to devs that sponsors are coming, and the proof to sponsors that
   devs are coming.
3. **No sponsor revenue is budgeted** in the first 90 days. If phase 1 fails to land a
   paying sponsor by day 90, the business case is in question — see §6.

**Phase 2 (post-first-sponsor):** auction-based campaigns, tiered CPM/CPC/CPA, volume
discounts for repeat sponsors, self-serve sponsor dashboard.

**Phase 3 (post-scale):** managed gateway, team seats, priority support (§2). Only now.

---

## 5. 30-DAY LAUNCH CHECKLIST

Day-by-day buckets. The shape: **Days 1–5 polish, 6–8 demo, 9–14 first launch (HN), 15–21
community seeding, 22–30 PH + sponsor outreach.** Everything is single-person-sized.

### Days 1–5 — Repo polish
- [ ] README rewrite: install command first, GIF second, facts table third
- [ ] Screenshots: sponsor line + `/models` (25 verified free models visible)
- [ ] Verify one-command install on a **clean Windows machine** (fresh VM if needed)
- [ ] License headers / LICENSE files present (MIT/Apache story is a selling point)
- [ ] CONTRIBUTING.md + issue templates (signals a real project)
- [ ] All 677 tests green on a clean clone; note the count in README

### Days 6–8 — Demo video
- [ ] Shoot 90-second video (install → `/models` → sponsor line)
- [ ] Captions + upload to YouTube; embed in README
- [ ] 10-second GIF clipped from the video for HN/Twitter

### Days 9–14 — First launch (Show HN + X thread)
- [ ] Day 9: X/Twitter build-in-public thread starts (3 posts/day through day 14)
- [ ] Day 11: Show HN post (Tuesday/Wednesday US morning)
- [ ] Days 11–14: answer **every** HN comment <48h; log feedback; fix the top 3 complaints
- [ ] Ping the 10–20 real people who'll have used it by now to comment honestly (never astroturf)

### Days 15–21 — Community seeding + first 100 users
- [ ] Join 10 dev Discords/Telegram groups; 1 genuine contribution each per week
- [ ] India: WhatsApp broadcast to 20+ dev groups; vernacular explainer video posted
- [ ] College angle: 5 campus/hackathon groups seeded
- [ ] Track toward **first 100 users** (daily active installs — see §7); if <50 by day 21, double down on the channel that converted best and cut the rest

### Days 22–30 — Product Hunt + sponsor outreach
- [ ] Day 24: Product Hunt launch (2–3 weeks after HN, momentum intact)
- [ ] Sponsor outreach: 20 warm-candidate sponsors contacted (dev tools, model providers, AI courses); pitch = "X reachable dev installs, verified impressions, escrow + receipts built in"
- [ ] Sponsor waitlist page live and linked everywhere
- [ ] Day 28: honest retrospective — what converted, what didn't, kill what didn't
- [ ] Day 30: post-launch report (public build-in-public post): installs, retention, sponsor pipeline, lessons

---

## 6. RISKS

| Risk | Severity | Reality | Mitigation |
|---|---|---|---|
| **No sponsors yet = zero revenue** | Critical | Revenue model depends entirely on a two-sided network; until a sponsor pays, dev earnings are $0 and the "earn 50%" hook is hollow | Demo sponsors before marketing the earnings hook; sponsor waitlist from day 1; honest messaging ("sponsors are coming") instead of fake earnings screenshots; 90-day go/no-go on the business case |
| **Competition (Claude Code, Codex CLI, etc. — free-ish)** | High | Big players give away powerful agents; our 7 merged agents are a convenience, not a moat; their brand trust dwarfs ours | Compete on what they won't do: free-model verification (25 verified), Windows-first support, and a dev-earning sponsor model they can't copy without changing their own business; free forever core means we never lose on price |
| **Trust (third-party client)** | High | Devs will be asked to install a CLI that runs their coding sessions and shows them ads; "why should I trust this?" is the #1 objection | Open source (MIT/Apache — everything inspectable); signed releases/updates; **no telemetry** (state it in the README); 677 tests as visible proof of care; sponsor engine with receipts/escrow so money handling is auditable; never sell "the ads will go away" — they won't |
| Sponsor fraud / impression gaming | Medium | Capped payouts + a dev farming impressions | Already mitigated in engine design: caps, verification, receipts — keep hardening before scaling spend |
| Single-founder burnout / distribution ceiling | Medium | One person cannot be on HN, X, YouTube, WhatsApp, Discords, and sponsors simultaneously | The checklist is deliberately small; cut channels that don't convert by day 21; India channels are cheap volume, not time sinks |
| Brand damage from ads inside a dev tool | Medium | Devs hate ads; the sponsor line could be the thing that makes people *not* install | Sponsor line is opt-in-visible, clearly labeled, and pays the dev — the ad *is* the feature; keep the line tasteful and capped in frequency |

**Trust is the launch-critical risk, not revenue.** Revenue risk is covered by the 90-day
go/no-go. Trust risk is existential: one "this exfiltrates your code" thread on HN kills
the project regardless of code quality. Hence: open source, signed updates, no telemetry,
and every claim in the README being verifiably true.

---

## 7. THE ONE METRIC

> **Daily active installs** (DAI): unique machines that ran XOMNI in the last 24h.

Why this one:

- It is the **leading indicator for everything else**. Sponsor revenue = f(installed base).
  Dev earnings = f(installed base). Network moat = f(installed base). Stars, upvotes, and
  retweets are vanity; installs that *keep running* are the network.
- **Active** (not cumulative downloads) because a downloaded-but-abandoned install earns
  nothing and sells nothing. It measures the thing sponsors pay for: *reachable devs*.
- It's measurable honestly: a `xomni --version`/startup ping (with no telemetry — the
  count is derived from anonymous heartbeat, documented in the README).

**Targets (assumptions):** 100 DAI by day 30, 500 by day 90, 1,000 by day 180. At 1,000
DAI we have a real pitch to sponsors ("1,000 reachable dev installs, verified impressions,
escrow + receipts"). Below 100 DAI at day 30, fix retention before adding channels.

Everything in this plan serves that number. If a tactic doesn't move daily active
installs, it gets cut.
