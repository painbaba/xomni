# Anthropic / claude.ai dossier (2026-08-08, verified live)

## Program facts (H1, /anthropic)
- OPEN SCOPE: "rewards reports for all owned assets based on impact, even
  if not listed in scope" — claude.ai, console.anthropic.com, API,
  Claude Code CLI all in.
- Bounties: Low avg $190 (13.9% of submissions), Medium $1,104 (43.2%),
  High $3,563 (41.8%), Critical $8,000 (1.1%); non-core $100-250.
- Speed: 8h first response, 14h triage, ~6d to bounty. 390 resolved,
  Gold Standard Safe Harbor, retesting + collaboration.
- Scope exclusions: "Core Ineligible Findings" list; Claude Code
  auto-accept-edits behavior explicitly NOT a vuln; GitHub Action vulns
  in-scope repos = non-core.

## Session harness (claude_harness.py pattern)
- Auth = session cookies: sessionKey (sk-ant-sid02-...), routingHint
  (sk-ant-rh- JWT: sub = user UUID, name, phone_verified, age_verified),
  cf_clearance + _cf_bm + _cfuvid (Cloudflare), lastActiveOrg (org UUID).
- curl works with the cookie string + normal UA. Errors come back as
  structured JSON: {"type":"error","error":{"type":"not_found_error"|...
  "permission_error"|"invalid_request_error","message":...},"request_id":...}
- 200 OK on /api/organizations + /api/bootstrap = session valid.

## API surface (23 endpoints fired on a fresh /new load, all 200)
- /api/account_profile, /api/bootstrap, /api/account (memberships)
- /api/organizations/discoverable -> {"organizations":[],"can_create_personal":true}
- /api/team-trial/exposure-eligible
- /api/billing/{org}/gift/purchase_eligibility
- /api/organizations/{org}/*:
  experiences/claude_web?locale=, trial_status, projects
  (?include_harmony_projects=true&limit=30), projects_v2, chat_conversations_v2
  (?limit=30&starred=true/false), chat_conversations/{conv} (metadata:
  uuid, name, model, created_at), paused_subscription_details,
  cowork_settings, pending_domain_claim, marketplaces/list-account-*,
  mcp/remote_servers, mcp/remote_servers_with_connection, mcp/v2/bootstrap,
  memory/settings, prosumer_activation/tasks, shares
- NOT REST: message history (chat_conversations/{conv}/messages|history|
  events all 404 — streams via the chat endpoint), share creation (405
  on API — UI-only).

## Authz boundary test results (the methodology, all clean)
- Foreign RANDOM v4 org UUID on 7 sensitive endpoints (conversations,
  billing gift, subscription, memory, mcp, projects, trial) -> 404
  not_found with details.error_visibility="user_fa..." (no existence
  leak). Own UUID -> 200 real data. Boundary holds everywhere.
- Numeric org IDs (304959684, ±1, 1, 100) -> 400 "path.organization_uuid:
  Input should be a valid UUID" — sequential enumeration closed at
  validation.
- Conversation fetch requires org in path: /api/chat_conversations/{uuid}
  -> 404; /api/organizations/{org}/chat_conversations/{uuid} -> 200.
- Shares: GET /api/organizations/{org}/shares -> 200 [].
VERDICT: well-gated. IDOR would need another user's v4 UUIDs. On a
fresh single account the web surface is thin — grow content (projects,
MCP servers, shares) or get a second account before re-testing.

## Claude Code = paid wall (verified)
- npm i -g @anthropic-ai/claude-code (v2.1.224) installs fine; auth
  state in ~/.claude/.credentials.json (absent until login).
- `claude auth login` prints an OAuth URL
  (claude.com/cai/oauth/authorize?...code=true&state=...) with a
  "Paste code here" prompt. The code flow redirects to
  platform.claude.com/oauth/code/callback.
- Driving it headless: claude.com authorize bounces to
  claude.ai/login?selectAccount=true&returnTo=%2Foauth%2Fauthorize — the
  session cookies are .claude.ai so inject those and reload; the
  authorize page renders. BUT the page shows "Upgrade to Max or Pro" /
  "Claude Max or Pro is required to connect to Claude Code. Sign up for
  a Max or Pro subscription to connect your account, or use your API
  key." Free accounts CANNOT authorize Claude Code. Both unlock paths
  (Pro/Max subscription, API key) cost money.

## Pitfalls
- cf_clearance is fingerprint-bound: pasting the user's clearance into
  camoufox triggers a jsd/oneshot re-challenge; wait it out (title
  becomes "New chat - Claude" after ~15-25s), the app then loads and
  fires the /api/* calls normally.
- claude.com and claude.ai are separate cookie domains — session cookies
  are .claude.ai; the OAuth entry on claude.com needs the bounce through
  claude.ai login to pick them up.
- Camoufox server restart: `cd C:\Users\HP\camofox && npx camofox-browser`
  (port 9377; health shows browserConnected:false until first tab).
