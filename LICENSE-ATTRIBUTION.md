# License & attribution

The unified agent composes permissively-licensed open sources. All are
combinable; keep this file and the notices below with any redistribution.

| Component | Source | License |
|---|---|---|
| Host core (Hermes) | NousResearch/hermes-agent | MIT |
| Repo-map concept (shipped module) | Aider-AI/aider | Apache-2.0 |
| Statusline reference (vendored) | opencode-ai/opencode | MIT |
| Compaction port-plan reference | 1jehuang/jcode | MIT |
| Sandbox port-plan reference | openai/codex | Apache-2.0 |
| MCP catalog port-plan reference | aaif-goose/goose | Apache-2.0 |
| Sponsorship fundamental (concept) | WaitPerk (waitperk.com; sammpentz-commits/waitperk-client, PolyForm Shield for its client code) | concept reimplemented independently — no WaitPerk client code copied |

Notes:
- The `plugins/waitperk` module is an independent reimplementation of the
  public *concept* (one sponsor line, 50/50 impression-share split, capped
  payouts). It does not vendor or derive from WaitPerk's PolyForm-Shield client
  source.
- `vendor/opencode/` is a shallow reference clone for reading, kept for
  attribution and inspection; it is not part of the runtime.
- MIT/Apache-2.0 require retaining copyright notices on redistribution — see
  each vendored repo's LICENSE file.

| OpenClaw personal-assistant concepts (shipped modules) | OpenClaw (formerly Clawdbot) | MIT |
| OmniMemory / OmniMedia concept (shipped) | OpenClaw personal memory + media pipelines | concept reimplemented independently � no OpenClaw source copied |
