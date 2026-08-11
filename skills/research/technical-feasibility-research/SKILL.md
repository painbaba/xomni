---
name: technical-feasibility-research
description: Can-we-build-X feasibility verdicts with proof, not surveys.
---

# Technical Feasibility Research

## Why this skill exists
Users (esp. the India-market AI builder this serves) propose ambitious
technical theses — "decentralized AI supercomputer", "scrape all of X",
"community-owned inference network". The deliverable they need is a VERDICT
with proof, not a descriptive survey. The spec pattern they use demands:
"if something is impossible, prove why; if possible, explain exactly how".
This skill is the working method for that class of task.

## Core method (ordered — do NOT skip the order)

### 1. Find the binding constraint FIRST, from first principles
Before reading a single source, compute the physical/economic limit that
scales against reality (bandwidth, latency, energy, cost-per-unit). State
assumptions explicitly. This is the "kill shot" — if the math caps the idea
10x below what's usable, everything after is confirmation, not discovery.

- Distributed inference template: `references/bandwidth-latency-walls.md`
  (bytes/token × tok/s vs upload; tok/s ≤ 1/(L×RTT) latency floor).
- General rule: find the resource that is (a) fixed by physics/market and
  (b) consumed per unit of output. Compute the ceiling. If the ceiling is
  below usability, the thesis as written is dead — then hunt mutations.

### 2. Verify with PRIMARY sources, not summaries
- Papers: arXiv full text (e.g. DeepSeek-V3's own comm section proved the
  cross-node bottleneck), not abstracts.
- JS-rendered doc sites defeat curl: try `https://<host>/llms.txt` then
  `llms-full.txt` FIRST — the LLM-friendly doc-index convention (worked
  for docs.puter.com; sites with AI features usually ship one). No
  web_search tool? Bing RSS `https://www.bing.com/search?q=...&format=rss`
  returns parseable XML and rarely blocks; DuckDuckGo html endpoint
  (html.duckduckgo.com/html/?q=...) as fallback. Both beat spinning up
  the browser stack for a one-off lookup.
- Live projects: GitHub API (stars/license/pushed_at — 60 req/hr unauth),
  READMEs, official docs. A project's architecture CHOICES are evidence:
  exo requiring Thunderbolt-5 RDMA and Mesh-LLM gating splits on LAN both
  confirm the WAN bandwidth wall empirically.
- Prices: OpenRouter `/api/v1/models` + `/endpoints` (no auth) gives every
  provider's per-1M-token price — better than vendor pages.
- Mark unverifiable numbers "unverified". Timestamp everything.

### 3. Adversarial failure analysis
Actively try to kill the project. For each failure mode: probability,
impact, mitigation, remaining risk. Separate:
- PROVEN impossibilities (physics/math, P=1.0) — these are not "risks",
  they're the verdict.
- Real risks (P<1.0) — these compound the impossibilities (every mitigation
  spends the already-exhausted resource).

### 4. Economic reality check
Compute what one unit of contribution is WORTH vs what it COSTS the
contributor, with real current prices. Volunteer economies die when
value/contributor < electricity/contributor (usually by 100-1000x).
Check precedent: what do successful volunteer networks (Folding@home,
BOINC) actually prove — altruism works, income doesn't.

### 5. First-principles redesign
Ignore existing solutions; design what WOULD survive the constraint.
Then state honestly what premise of the original thesis the surviving
design abandons. The gap between thesis and mutation IS the finding.

### 6. Score and deliver
- Feasibility score 0-100 for the literal thesis AND for the best mutation.
- Report structure (per the user's spec): exec summary with score, state of
  the art, competitive tables, performance models with assumptions +
  sensitivity, failure matrix, security, economics, roadmap, build-vs-buy,
  first principles, novel ideas, 90-day plan, final recommendation.
- Every major conclusion gets a confidence (High/Medium/Low).

## Division of labor (proven pattern)
- I (main agent) do the constraint math, primary-source verification, and
  the verdict docs — the reasoning must not be delegated away.
- Parallel scouts (delegate_task) gather raw CITED source packs per track
  (SOTA / market / hardware) — independent workstreams, 3 max concurrent.
- Free API-key pools (NVIDIA NIM etc.) benchmarked first, then used as the
  synthesis workforce for the full report — see
  data-collection-strategy references/nvidia-nim-workforce.md.
- Workspace shape: sources/ (cited packs), notes/ (my analysis), report/
  (final), bench/ (model capability), README.md (spec skeleton).

## Pitfalls
- Don't stop at "it's hard" — prove the wall with numbers, then find the
  mutation that survives it.
- Don't spend the whole report re-proving the kill; full sections go to the
  survivable mutation.
- Don't trust catalogs as availability (NVIDIA /v1/models lists models a
  given account can't call — 404 per-account).
- Don't fabricate stars/prices/benchmarks — "unverified" is always safer.
- Free-tier claims ('unlimited', 'N free tokens') are marketing until
  verified on the provider's OWN subscribe/pricing page — JS-rendered SPA,
  use the browser stack, not curl. Tell of a dead claim: valid key +
  "insufficient balance" (z.ai 1113) = zero credits despite auth working;
  the "300M free GLM tokens" report was a paid tier's weekly quota misread
  as a giveaway.
- Vague user ask ("greatest deep research of the decade") → force scope
  FIRST: what decision does this research feed? Refuse to start until
  answered (budget/time-constrained user).
- Hype framing ("$1B+ impact") is marketing — treat the spec as the task,
  not the valuation.

## References
- references/bandwidth-latency-walls.md — the two-wall math templates for
  any distributed-compute feasibility question.
