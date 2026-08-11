# XOMNI External Skills — Security Scan Report (2026-08-11 23:34)

Database: `data/skills.db` — integrity_check: **ok**

## Methodology

Every SKILL.md harvested from external sources is scanned statically (never executed) for: prompt-injection instructions ("ignore previous instructions", exfiltration), credential theft (env/API-key reads combined with network sends), eval/exec/subprocess of remote or dynamic content, network calls to unknown hosts, and obfuscation (large base64/hex blobs). Verdicts: **PASS** (clean), **REVIEW** (warning-level findings), **REJECT** (dangerous — kept in DB only for the audit trail, never suggested for import).

## Totals

- Total skills in DB: **519**
- Sources merged: 6 (`scrape1.json, scrape2.json, scrape3.json, scrape4.json, scrape5.json, scrape6.json`)
- PASS: **458**
- REVIEW: **61**
- Ranked (from curated-skills.json): **201** / 519 (38.7% coverage)
- Curated entries: 180 loaded from `data/curated-skills.json` (matched by sha256)
- Ranked by verdict: PASS 198, REVIEW 3

## Per-source counts

| Source | Skills |
|---|---|
| NVIDIA/skills | 126 |
| openclaw | 118 |
| microsoft/skills | 69 |
| anthropics/skills | 47 |
| google/skills | 45 |
| awesome-claude-code | 36 |
| obra/superpowers | 18 |
| SnailSploit/Claude-Red | 8 |
| sudokar/openspec-plus | 6 |
| gadievron/raptor | 6 |
| awesome-cursorrules | 6 |
| anthropic/skills | 6 |
| crewai-tools | 5 |
| microsoft/SkillOpt | 4 |
| claude-code-docs | 3 |
| LambdaTest/agent-skills | 3 |
| veniceai/skills | 2 |
| geekjourneyx/md2wechat-skill | 2 |
| angular/skills | 2 |
| vercel-labs/skills | 1 |
| resend/resend-skills | 1 |
| qiye45/wechatDownload | 1 |
| factory.ai docs | 1 |
| composio (skills-lock) | 1 |
| club-cog/devin-handoff | 1 |
| 0xBadai/devin-skills | 1 |

## Top-20 curated skills (by rank)

| Rank | Name | Source | Usefulness |
|---|---|---|---|
| 1 | writing-skills | obra/superpowers | 10.2 |
| 2 | applicationinsights-web-ts | microsoft/skills | 10.2 |
| 3 | agent-acceptance-gate | awesome-claude-code | 10.2 |
| 4 | physical-ai-defect-image-generation | NVIDIA/skills | 10.2 |
| 5 | algorithmic-art | anthropics/skills | 10.2 |
| 5 | algorithmic-art | anthropics/skills | 10.2 |
| 5 | algorithmic-art | anthropic/skills | 10.2 |
| 5 | algorithmic-art | anthropics/skills | 10.2 |
| 6 | agent-output-reconciler | awesome-claude-code | 10.2 |
| 7 | wiki-onboarding | microsoft/skills | 10.2 |
| 8 | agent-framework-azure-ai-py | microsoft/skills | 10.2 |
| 9 | data-manager-api-audience-ingestion | google/skills | 10.2 |
| 10 | angular-developer | angular/skills | 10.2 |
| 11 | gemini-api | google/skills | 10.2 |
| 12 | agent-shared-memory | awesome-claude-code | 10.2 |
| 13 | agent-debate | awesome-claude-code | 10.2 |
| 14 | google-analytics-data-api-basics | google/skills | 10.2 |
| 15 | systematic-debugging | obra/superpowers | 10.2 |
| 15 | systematic-debugging | obra/superpowers | 10.2 |
| 16 | skillopt-sleep | microsoft/SkillOpt | 10.2 |

## REJECTED skills (audit trail — do not import)

None.

## REVIEW findings (warning-level)

- **deepstream-generate-pipeline** (NVIDIA/skills): ['REVIEW:exec:272 exec']
- **earth2studio-create-prognostic** (NVIDIA/skills): ['REVIEW:exec:148 exec']
- **nv-reason-cxr** (NVIDIA/skills): ['REVIEW:exec:299 exec']
- **rag-eval** (NVIDIA/skills): ['REVIEW:exec:8 exec']
- **tao-finetune-huggingface-model** (NVIDIA/skills): ['REVIEW:exec:303 exec']
- **vss-deploy-dense-captioning** (NVIDIA/skills): ['REVIEW:exfil:152 credential-handling-no-remote-target']
- **offensive-ai-security** (SnailSploit/Claude-Red): ['main/Skills/ai/offensive-ai-security/SKILL.md: eval() [sev2] :: ultilingual/obfuscated attacks. - **RAG Triad eval (defensive signal checks)**: - Scor', 'main/Skills/ai/offensive-ai-security/SKILL.m
- **offensive-jwt** (SnailSploit/Claude-Red): ['main/Skills/auth/offensive-jwt/SKILL.md: jailbreak-mention [sev2] :: extraction: unencrypted backups expose Keychain - Jailbreak + Keychain-Dumper for full extraction -', 'main/Skills/auth/offensive
- **offensive-exploit-development** (SnailSploit/Claude-Red): ['main/Skills/exploit-dev/offensive-exploit-development/SKILL.md: jailbreak-mention [sev2] ::  (requires iOS 16+ device with checkra1n/palera1n jailbreak) ldid -S entitlements.plist target_bina', 'mai
- **claude-api** (anthropic/skills): ['review:claude-api:214 credential-handling-no-remote-target', 'review:claude-api:214 credential-handling-no-remote-target']
- **canvas-design** (anthropics/skills): ["SKILL.md:106 [exfil_send/exfiltration] 'forward PDF or PNG output (unless asked for more pages). Generally use repeating'", "SKILL.md:108 [exfil_send/exfiltration] 'forward and prioritize visual com
- **claude-api** (anthropics/skills): ["SKILL.md:432 [exfil_send/exfiltration] 'upload via'", 'SKILL.md:528 [exfil_send/exfiltration] \'forward from Opus 4.8. With `thinking: {type: "disabled"}`, the model occasional\'', "SKILL.md:214 [cr
- **frontend-design** (anthropics/skills): ["SKILL.md:49 [net_hosts/network] 'webhook'"]
- **mcp-builder** (anthropics/skills): ["SKILL.md:61 [net_hosts/network] 'raw.githubusercontent.com'", "SKILL.md:65 [net_hosts/network] 'raw.githubusercontent.com'", "SKILL.md:212 [net_hosts/network] 'raw.githubusercontent.com'", "SKILL.md
- **skill-creator** (anthropics/skills): ["SKILL.md:113 [exfil_send/exfiltration] 'exfiltrat'", "SKILL.md:454 [exec_subproc/code-exec] 'subprocess'"]
- **claude-api** (anthropics/skills): cred-key:'token' L4; cred-key:'Token' L167; cred-key:'token' L167; cred-key:'Token' L195; cred-key:'token' L195; cred-key:'credential' L211; cred-key:'token' L214; cred-key:'token' L214; cred-key:'Bea
- **skill-creator** (anthropics/skills): cred-key:'token' L234; cred-key:'token' L263; exec-subprocess:'subprocess' L454
- **thinking-effectuation** (awesome-claude-code): ["SKILL.md:31 [net_fetch/network] 'requests.'"]
- **thinking-probabilistic** (awesome-claude-code): ["SKILL.md:55 [mislead_md/misleading-instructions] 'Do not report'"]
- **thinking-red-team** (awesome-claude-code): ["SKILL.md:31 [net_hosts/network] 'webhook'"]
- **agent-task-splitter** (awesome-claude-code): ["SKILL.md:533 [net_fetch/network] 'curl '"]
- **claude-code-docs:skills** (claude-code-docs): cred-key:'token' L233; cred-key:'token' L351; cred-key:'token' L435; cred-key:'token' L486; cred-key:'token' L486; cred-key:'token' L709; cred-key:'token' L711; exfil-pipe:'| Sh' L272; exfil-pipe:'| S
- **claude-code-docs:plugins** (claude-code-docs): exfil-pipe:'| Sh' L20; exfil-pipe:'| Sh' L72 [docs page: findings are documentation references, not executable skill code]
- **oxylabs_universal_scraper_tool** (crewai-tools): ['review:oxylabs_universal_scraper_tool:109 eval/exec/subprocess', 'info:oxylabs_universal_scraper_tool:130 reads-env-vars']
- **scaffold** (microsoft/skills): ['REVIEW:suspicious-url:148 suspicious-url']
- **entra-agent-id** (microsoft/skills): ['REVIEW:exec:133 exec']
- **auto-qa** (openclaw): ["SKILL.md:42 [mislead_md/misleading-instructions] 'Do not disclose'"]
- **autoreview** (openclaw): ["SKILL.md:41 [exec_subproc/code-exec] 'subprocess'", "SKILL.md:44 [exec_subproc/code-exec] 'subprocess'"]
- **discord-user-post** (openclaw): ["SKILL.md:41 [exfil_send/exfiltration] 'send result'", "SKILL.md:3 [net_hosts/network] 'webhook'", "SKILL.md:47 [net_hosts/network] 'webhook'"]
- **discrawl** (openclaw): ["SKILL.md:91 [net_fetch/network] 'requests.'"]

## Raw source files

- `scrape1.json`: 172 items, 172 unique (sha256) -> C:\Users\HP\xomni\data\raw\scrape1.json
- `scrape2.json`: 34 items, 34 unique (sha256) -> C:\Users\HP\xomni\data\raw\scrape2.json
- `scrape3.json`: 42 items, 42 unique (sha256) -> C:\Users\HP\xomni\data\raw\scrape3.json
- `scrape4.json`: 41 items, 41 unique (sha256) -> C:\Users\HP\xomni\data\raw\scrape4.json
- `scrape5.json`: 120 items, 120 unique (sha256) -> C:\Users\HP\xomni\data\raw\scrape5.json
- `scrape6.json`: 110 items, 110 unique (sha256) -> C:\Users\HP\xomni\data\raw\scrape6.json
