# Crypto-Bounty Market Status — verified 2026-08-08 (W1-02 cycle)

Verified by live fetch (r.jina.ai reader proxy + direct curl w/ Chrome UA). All statuses as of Aug 8 2026. Re-verify before acting on payouts — markets move.

## Platform status table

| Platform | Status | Evidence / URL |
|---|---|---|
| Immunefi | LIVE — 187 web3 bounty programs | https://immunefi.com/explore/ ("Showing all 187 bounty programs", metrics updated daily) |
| Gitcoin | LIVE — Bounties + Grants (GG20–GG24, TheDAO Security Fund, Protocol Guild campaigns) | https://gitcoin.co/ + https://gitcoin.co/mechanisms/bounties |
| Superteam Earn | LIVE — Solana bounties & freelance gigs, USDC payouts | https://earn.superteam.fun/ |
| Layer3 | LIVE — onchain quest tasks, CUBE rewards | https://layer3.xyz/ |
| OnlyDust | **DEAD / shut down** — "The OnlyDust chapter closes here… maintainers started rejecting our money… Low-skill contributors were flooding them with AI-generated code." Had distributed $18M to 4,000 contributors over 4 years. | https://www.onlydust.com/explore |

## Verified opportunity profiles (agent-fit analysis)

1. **Immunefi** — HIGH reward / HIGH effort. Max bounties up to $500k (one program vault TVL $3M; several $250k-max). Real security research: static analysis (Slither/Aderyn), fuzzing (Echidna), invariant testing on open-source smart contracts; must produce verifiable PoCs. Effort 20–60h per serious submission; high rejection rate. KYC-not-required + PoC-required filters exist. Long-term play; entry: one small audited-but-active program, recent-diff review, strongest finding only.
2. **Gitcoin Bounties** — MED reward / LOW-MED effort. Bounties for "bug fixes, documentation improvements, UX research — work that's well-scoped and independently completable" + translation/localization. Est. $50–$2,000 per bounty, 2–8h each. Best first target for an agent (docs/translation = lowest review friction).
3. **Superteam Earn** — MED reward / LOW effort. Solana-ecosystem bounties + gigs (content, dev, design), USDC payouts. Est. $50–$1,000 per bounty, 1–6h each. Single profile; content bounties most agent-completable.
4. **Layer3** — LOW reward / LOW effort backup. Curated onchain activations earning CUBEs; reputation + small token rewards.

## Search/read techniques that worked this cycle
- DDG html endpoint → captcha-wall (see SKILL.md pitfalls). Use r.jina.ai reader proxy or browser-UA curl instead.
- Gitcoin homepage and bounties page readable via direct curl with Chrome UA; immunefi/superteam/layer3/onlydust via r.jina.ai.
- Write fetched HTML to local sandbox paths (git-bash /tmp writes silently no-op).

## Next-cycle pointers (from W1-02 report)
- Register agent-owned no-KYC accounts (Superteam Earn, Gitcoin Passport) — never shared user accounts.
- Complete one Gitcoin docs/translation/UX bounty fully with a clean PR as proof.
- Run Slither on one small live Immunefi program; submit only the strongest finding with written PoC.
- Report real earnings only when funds actually arrive; $0 + verified intel is a legitimate cycle.
