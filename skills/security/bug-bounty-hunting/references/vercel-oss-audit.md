# Vercel Open Source — autonomous code-audit campaign (Aug 2026)

Program: hackerone.com/vercel-open-source — 89% response efficiency,
launched Feb 2026, ALL scope entries are Source code (Critical max,
bounty-eligible). Tier structure: Tier 1 (flagship repos), Tier 2, Tier 3
(experimental). Repos live under github.com/vercel, vercel-labs, plus
sveltejs/svelte, nuxt/nuxt, nitrojs/nitro.

## Target selection
Fresh repos with 0 resolved reports = best dup odds. Verified fresh Aug
2026: vercel/chat ("Unified TypeScript SDK for chat bots", pushed same
day), vercel/eve ("Open Framework for Building Agents", 27.8MB), plus
vercel/ms, vercel/async-sema, vercel-labs/agent-skills. Heavily-hunted
ones to avoid first: vercel/ai (13 reports).

## Method (proven)
1. `git clone --depth 1 https://github.com/<org>/<repo>.git`
2. Map structure; grep high-risk patterns:
   `child_process|execSync|spawn\(|eval\(|new Function|shell:|fetch\(`
   and URL/path/token handling.
3. Feed the TOP 3-5 risk files to an LLM CLI for analysis — one file per
   call, code INLINE in the prompt.
4. VERIFY every LLM claim against the actual code before writing it up —
   LLMs hallucinate findings confidently. File:line evidence required.
5. Append candidates to a findings log (findings.md); never submit
   externally; human reviews drafts. Nightly cron for volume.

## GLM CLI quirk (bit us this session)
`glm` (C:\Users\HP\glm-tool) reads the prompt from ARGV, NOT stdin.
Piping code via stdin silently returns "No code was provided." Always
pass the code inline as the argument.

## Pass results 2026-08-07 (all verified, all clean)
- vercel/ms: parse() length-caps input <=100 chars (ReDoS mitigated), no
  object writes (no prototype pollution). 0-reports is earned.
- vercel-labs/agent-skills (vercel-cli-with-tokens SKILL.md): good hygiene
  — env-var token use, explicit anti `--token` flag guidance.
- vercel/chat: callback tokens = randomUUID 16-hex (64-bit, server-side
  store, 30d TTL) — unforgeable; all webhook adapters (Slack/WhatsApp/
  GitHub/Telegram) verify signatures with timingSafeEqual; state adapters
  (pg/redis) parameterized; docker CLI spawns with args ARRAYS (no shell).
  Informational only: modal-callback route is unauth POST relying on token
  secrecy (validation in external @vercel/workflow pkg); Telegram webhook
  auth conditional on secretToken config.
- vercel/eve: shellQuote() correct POSIX escaping; bash tool executes via
  SandboxSession backends (docker args-array, microsandbox, just-bash
  virtual-FS — no host-shell fallback); forwarded-principal requires
  trusted-forwarder gate, sender values overwritten, no token transport;
  ACP server line-bounded; repl spawn uses a fixed enum of agents.

## Second pass 2026-08-07 (reverse-audit + completion) — all clean
Reverse-audit strategy: shallow clones hide history —
`git fetch --depth 60 origin main` then `git show <sha>` recent
security commits; audit the FIX for incomplete coverage (this is the
highest-yield move in actively-hardened programs).
- 4cc3445c teams/slack HTML+URL hardening: `stripHtmlTags` do-while
  stable loop; `safeLinkHref` = `new URL(href)` canonicalize + allowlist
  {http:, https:, mailto:}. No bypass found.
- 4cc3445c slack: `BRACKETED_URL_PATTERN /<(https?:\/\/[^>]{1,2048})>/g`
  length-bounded; matched URLs only feed links metadata, NEVER fetched →
  no SSRF.
- 85e3d22b read-tool scoping (ai/scope.ts): `channelOf()` per-adapter
  strict thread-id decoders (discord slice(0,3), github/gchat/linear
  regex) — no crafted-id channel confusion. Fail-open default (no scope =
  workspace-wide + warn-once) is documented by design, not a bug.
- b6749238 X CRC signing-oracle fix: token constrained to
  `/^[A-Za-z0-9+/=_-]{16,128}$/` — JSON bodies can't match. Informational
  edge: >=16-digit numeric bodies ARE valid JSON and match → mini-oracle
  alive for those, but X events are objects → nothing forgable. Not
  reportable.
- chat approval workflow (workflow/index.ts): webhook URL token-swapped
  in thread.post (thread.ts:547) — never reaches clients; user identity
  from signature-verified platform events; approvers filter enforced.
- eve OAuth callback (runtime/connections/callback-route.ts): gated by
  unguessable hook token; request headers dropped from callbacks.
- eve connection-auth-tool-result.ts: JSON-serialization only, no secrets
  in logs. eve compiler: no eval/Function on untrusted input.
- async-sema full audit: deque FIFO, capacity-capped (16..2^30), no
  over-release, no unbounded queue.

## Reality check
Hardened production codebases produce clean passes as the NORM. A clean
pass is a finding of its own (documented, with evidence) — never
fabricate. The payout math is volume: nightly cron grinds the long tail
(eve compiler + channel adapters, swr, async-sema, state-ioredis) and
appends candidates to C:\Users\HP\vercel-audit\findings.md.
