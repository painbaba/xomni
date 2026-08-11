# Kimi Model Lineage & Moonshot AI — Verified Timeline (2023→2026)

Dense verified facts for the documentary script / follow-up research. Every claim checked against the source (URL inline) on 2026-08-07. K3 architecture/pricing/business detail lives in the sibling file `references/kimi-k3-2026.md` — this file covers the full lineage, founders, funding table, and product launches.

## Founding & founders
- Moonshot AI = Beijing Moonshot AI Technology Co., Ltd. (月之暗面, "Dark Side of the Moon"), named after Pink Floyd's album, Yang Zhilin's favorite; launched on its 50th anniversary. Founded **March 2023** (Wikipedia; GitHub org created 2023-03-28: https://api.github.com/orgs/moonshotai/repos).
- Founders: **Yang Zhilin (CEO), Zhou Xinyu, Wu Yuxin** — Tsinghua classmates and bandmates (rock band "Splay"). (https://en.wikipedia.org/wiki/Moonshot_AI)
- **Yang Zhilin bio**: b. 1992 Shantou, Guangdong; top Science score in Shantou Gaokao (667); Tsinghua (thermal engineering → CS; adviser Jie Tang, Z.ai co-founder) → CMU PhD 2015–2019 under Ruslan Salakhutdinov & William Cohen (thesis "Advances in Generative Feature Learning"); co-author of **XLNet** and **Transformer-XL**; interned Google Brain & Meta; co-founded Recurrent AI (2016); worked on Huawei PanGu (2020) and BAAI Wu Dao (2021); declined Apple recruitment + Stanford/MIT postdocs to return to China; mission "optimal conversion from energy to intelligence". (https://en.wikipedia.org/wiki/Yang_Zhilin)
- Dec 2024: Recurrent AI investor dispute (incl. GSR's Zhu Xiahou) went to HK arbitration; settled via HKIAC. (https://en.wikipedia.org/wiki/Yang_Zhilin)

## Funding rounds (verified)
| Date | Round | Valuation | Source |
|---|---|---|---|
| 2023 | Initial funding | $300M valuation; $60M raised; 40 employees | https://en.wikipedia.org/wiki/Moonshot_AI |
| Feb 2024 | Alibaba-led $1B (Alibaba ~$0.8B for 36%) | $2.5B | https://en.wikipedia.org/wiki/Moonshot_AI (TechCrunch/Bloomberg refs) |
| Aug 2024 | Tencent + Gaorong Capital $300M | $3.3B | https://en.wikipedia.org/wiki/Moonshot_AI (Bloomberg 2024-08-05) |
| Oct 2025 | ~$600M, IDG Capital-led (Tencent et al.) | ~$3.8B pre-money | https://pandaily.com/kimi-nears-600-million-funding-round-idg-reportedly-to-join/ |
| Jul 2026 | **$3.5B round** (surpassed goal) | **$35B** | Bloomberg 2026-07-29 via Google News RSS; Technode 2026-07-30 |
| Jul–Aug 2026 | Pre-IPO talks | seeking $50B; HK IPO first reported Mar 2026 | qz.com 2026-07-21; WSJ 2026-03-27 (via wiki refs) |

## Chatbot launch & context milestones
- **Oct 2023**: Kimi chatbot released (closed beta, deep cooperation with Volcengine). Claimed **200,000 Chinese characters / ~128k tokens** lossless context — first AI model to accept contexts of that size. Public launch **16 Nov 2023**. Name from Yang's English nickname. (https://en.wikipedia.org/wiki/Kimi_(AI))
- **Mar 2024**: 2M-character context version (internal/beta); Kimi outage 21 Mar + public apology. (https://en.wikipedia.org/wiki/Moonshot_AI)
- Jul 2024: context-caching public beta; **11 Oct 2024**: Kimi Explore Edition (autonomous search, reads 500+ pages) global; **MAU >36M** (~Oct 2024, per Yang Zhilin). (https://en.wikipedia.org/wiki/Kimi_(AI))
- Kimi ranked 3rd in Chinese consumer AI MAU (Aug 2024), fell to 7th (Jun 2025) — aicpb.com via Reuters refs. (https://en.wikipedia.org/wiki/Moonshot_AI)

## Model lineage (the core timeline)
| Model | Date | Params / arch | Key verified facts | Open? | Source |
|---|---|---|---|---|---|
| **K1** | 2024, app-only | — | **UNVERIFIED** — no open-source repo exists (HF/GitHub org listings lack it); exact release date could not be confirmed from any source | No | https://huggingface.co/api/models?author=moonshotai |
| **K1.5** | **20 Jan 2025** | multi-modal, RL-trained | Claims matched OpenAI o1: 77.5 AIME, 96.2 MATH-500, 94th-pct Codeforces, 74.9 MathVista; RL via long-context scaling + policy optimization, NO MCTS/value functions/PRMs | No (report only) | https://arxiv.org/abs/2501.12599 ; https://the-decoder.com/chinese-openai-o1-challenger-kimi-k1-5-now-available-as-free-web-version/ |
| **K2** | **11 Jul 2025** (weights; CNBC 14 Jul) | **1T total, MoE, 32B active**; 15.5T training tokens; 128K ctx | Beat Claude Opus 4 & GPT-4.1 on coding per Moonshot; API $0.15/M in, $2.50/M out; #1 most-downloaded on HF day after release ("another DeepSeek moment" — Nature) | **Yes** (modified MIT) | https://www.cnbc.com/2025/07/14/alibaba-backed-moonshot-releases-kimi-k2-ai-rivaling-chatgpt-claude.html ; https://www.nature.com/articles/d41586-025-02275-6 |
| **K2-Instruct-0905** | **9 Sep 2025** | same, ctx 128K→**256K** | better agentic coding | Yes | https://huggingface.co/moonshotai/Kimi-K2-Instruct-0905 |
| **K2 Thinking** | **6 Nov 2025** (HF repo 4 Nov) | 1T MoE / 32B active; 256K ctx | trained ~**$4.6M**; 200–300 sequential tool calls; native INT4; **HLE 44.9 / BrowseComp 60.2 / SWE-bench Verified 71.3** (above GPT-5 & Claude Sonnet 4.5); modified MIT (attribution ≥$20M/mo revenue or 100M MAU) | **Yes** | https://venturebeat.com/technology/moonshots-kimi-k2-thinking-emerges-as-leading-open-source-ai-outperforming ; https://en.wikipedia.org/wiki/Moonshot_AI |
| **K2.5** | **Jan 2026** (HF repo 1 Jan) | 1T MoE / 32B active; multimodal | native vision via **MoonViT 400M-param encoder**; images+video; "visual agentic intelligence" (replicates website user journeys from video) | Yes | https://en.wikipedia.org/wiki/Moonshot_AI ; https://www.kimi.com/blog/kimi-k2-5.html |
| **K2.6** | **Apr 2026** (HF repo 14 Apr) | 1T MoE / 32B active; 256K ctx | general-purpose multimodal (text/image/video); long-context codegen, reasoning, self-correction; agent swarms (~1,000 collaborating agents per ZDNET) | Yes | https://www.kimi.com/blog/kimi-k2-6 ; https://huggingface.co/moonshotai/Kimi-K2.6 |
| **K2.7-Code** | **Jun 2026** (HF repo 11 Jun) | coding specialist; 256K ctx | multi-step tool invocation; no non-thinking mode; +21.8% on Kimi Code Bench v2 vs K2.6 | Yes | https://huggingface.co/moonshotai/Kimi-K2.7-Code ; MarkTechPost 2026-06-12 |
| **K3** | **16 Jul 2026** (weights 27 Jul) | **2.8T, MoE 896 experts / 16 active**; KDA + AttnRes; 1M ctx | First open 3T-class model; trails only Claude Fable 5 & GPT-5.6 Sol overall; #1 WebDev Arena (1678 Elo); #3 Artificial Analysis; Elo 1547 (+732 vs K2.6) on private long-horizon eval; ~2.5× scaling efficiency vs K2 | **Yes** (custom license) | https://www.kimi.com/blog/kimi-k3 ; https://en.wikipedia.org/wiki/Kimi_(AI) ; VentureBeat 2026-07-27 |

- Other family releases (HF repo dates): Kimi-VL A3B (Apr 2025), Kimi-Audio-7B (Apr 2025), Kimi-Dev-72B (Jun 2025), Moonlight-16B-A3B = Muon-optimizer model (Feb 2025), Kimi-Linear-48B-A3B (Oct 2025, Kimi Delta Attention debut). (https://huggingface.co/api/models?author=moonshotai)

## Product moments
- **Kimi app**: leading China ChatGPT alternative through 2024; free tier + paid plans (May 2024; tiers named Moderato/Allegro/Allegretto/Vivace). "OK Computer" agent mode (Sep 2025): builds multi-page sites + editable slides, processes 1M rows. (https://en.wikipedia.org/wiki/Kimi_(AI))
- **Kimi Researcher** (Jun 2025): autonomous deep-research agent. Kimi Explore Edition (Oct 2024).
- **Kimi Code CLI**: kimi-cli repo created 2025-10-15 (revived/GA as kimi-code May–Jun 2026) — TypeScript terminal coding agent; "Kimi Code" positioned vs Claude Code. (https://api.github.com/orgs/moonshotai/repos ; MarkTechPost 2026-06-06)
- **Kimi Claw** (15 Feb 2026): hosted **OpenClaw** on kimi.com — 24/7 personal agents, 5,000 community skills, 40GB cloud storage. (MarkTechPost 2026-02-15 via Google News RSS)
- **Kimi Work** (10–12 Jun 2026): local desktop agent running **300-sub-agent swarms on K2.6**. (Decrypt 2026-06-12; Moneycontrol 2026-06-10)
- **Kimi WebBridge** (May 2026): browser extension letting agents drive the browser. (Decrypt 2026-05-14)
- **Mooncake** serving platform: ~100B tokens/day; Erik Riedel Best Paper Award, USENIX FAST. (https://en.wikipedia.org/wiki/Moonshot_AI)
- **K3 demand strain**: new K3 subscriptions paused ~19–20 Jul 2026 (GPU crunch). (BeInCrypto 2026-07-20 via RSS)

## Controversies (timeline flavor)
- Mar 2024: outage apology. Feb 2026: Anthropic accused Moonshot (with DeepSeek/MiniMax) of harvesting Claude data via thousands of fake accounts (NYT 2026-02-23). Jul 2026: OSTP director Kratsios alleged K3 = distillation of Claude Fable — experts pushed back. (https://en.wikipedia.org/wiki/Moonshot_AI ; https://www.businessinsider.com/white-house-kimi-k3-moonshot-ai-distillation-2026-7)
