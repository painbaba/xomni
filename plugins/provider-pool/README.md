# provider-pool

The free-model layer of XOMNI: **25 models verified live** on the opencode
Zen gateway — the same base_url + key works in every stack agent.

**What it does:** catalogs 25 verified gateway models with tags + role
presets (default `deepseek-v4-flash`, vision `minimax-m3`); live health
check via `GET /models` (browser UA — Cloudflare 1010 otherwise); per-agent
config snippets; other free channels (NIM/Google/OpenRouter) cataloged as
wired|needs-keys — never assumes a key not in `.env`.

**Commands:** `/models [tag]` — live status + filterable model list;
`/provider [agent]` — per-agent config snippets.

**Speed posture:** **no hooks** — read-only, never alters behavior; the
only network activity is the explicit `/models` health check (a command,
not a hook) — zero cost per turn.

**Config:** `OPENCODE_GO_API_KEY` in `~/AppData/Local/hermes/.env`;
others: `NVIDIA_NIM_API_KEY_1..6`, `GOOGLE_AI_STUDIO_API_KEY_1..6`,
`OPENROUTER_API_KEY`.

```bash
cd plugins/provider-pool && python -m unittest tests.test_core -v
```
