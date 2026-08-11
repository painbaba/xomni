# TTS / Voice / Music-Licensing Knowledge Bank (Aug 2026)

Live-verified Aug 9, 2026 for the "automated documentary narration voice+music stack <$50/mo" research task. Per-hour figures are estimates (method at bottom); all prices quoted from the URLs in the source list.

## TTS providers — pricing snapshot

| Provider / model | Plans / rates (live-fetched) | Cost per narration-hour (est.) |
|---|---|---|
| **edge-tts** (unofficial Edge endpoint) | Free. Voices incl. en-US-ChristopherNeural, en-US-GuyNeural, en-US-ChristopherMultilingualNeural (Azure neural catalog). Prosody-only control (rate/volume/pitch); no SLA; chunk for long runs | $0 |
| **Google Cloud TTS** | Neural2 $16/1M chars · Chirp 3 HD $30/1M · WaveNet/Standard $4/1M · Studio $160/1M · Instant custom voice $60/1M · free allowances 1M chars/mo (Chirp3/Neural2/Studio), 4M (WaveNet) | Neural2 ~$0.91/h · Chirp3 ~$1.71/h |
| **Google Gemini TTS** | Gemini 2.5 Flash TTS: $0.50/1M text tokens + $10/1M audio tokens · Gemini 3.1 Flash TTS (Preview): $1.00 + $20/1M · note on pricing page: 25 audio tokens = 1 second | ~$0.90/h · ~$1.80/h |
| **OpenAI** | gpt-4o-mini-tts: $0.60/1M text tokens + $12.00/1M audio tokens · legacy tts-1 $15/1M chars, tts-1-hd $30/1M chars · 13 voices (marin/cedar recommended), `instructions` param controls accent/emotion/intonation/tone/speed/whisper · custom voices: consent recording + ≤30s sample, max 20/org, eligible customers only · usage policy requires disclosing AI voices to end users | ~$1.08/h |
| **MiniMax** | T2A speech-2.8-turbo $60/M chars · speech-2.8-hd $100/M chars · Rapid Voice Cloning $1.5/voice · Voice Design $3/voice · Audio Subscription: Starter $5/100k pts · Standard $30/300k · Pro $99/1.1M · Scale $249/3.3M · Business $999/20M (voice slots 10→800, RPM 10→800) · speech-2.8 = sound tags (um/uh fillers), 7 emotions, 40 languages, 10-sec cloning | turbo ~$3.42/h · hd ~$5.70/h · sub ~$2.9/h |
| **Cartesia Sonic-3.5** | Free 20k cr (~27 min) · Pro $5/100k (~2.2h) · Startup $49/1.25M (~27.8h) · Scale $299/8M (~178h) · TTS ~12.5–15 cr/sec (page says 15; included-minutes math implies ~12.5) · instant cloning Pro+, professional cloning Startup+, commercial license from $5 · localizing a voice = 225 cr one-time | ~$1.76/h (Startup $49) |
| **ElevenLabs** | Free 10k cr · Starter $6/30k (instant cloning) · Creator $22/121k (professional cloning) · Pro $99/600k (44.1kHz PCM via API) · Scale $299/1.8M/3 seats · Business $990/6M/10 seats · V2 Multilingual 1 credit/char, V2 Flash/Turbo 0.5–1 credit/char · annual = 10 months · credits roll over ≤3× quota · extra minutes $0.17–0.36 | ~$10.5/h (V2) · ~$5.2/h (Flash) |

**Cost method:** English narration ≈ 950 chars/min ≈ 57,000 chars/h; token-based audio at 25 audio tokens/sec ≈ 90,000 audio tokens/h. State these as assumptions when quoting per-hour estimates.

## Music / SFX for monetized YouTube

- **YouTube Audio Library** (support.google.com/youtube/answer/3376882): royalty-free production music + SFX, "copyright-safe", **monetizable**; CC-licensed tracks still need attribution in the video description; standard-license tracks don't.
- **archive.org**: 75,512 audio items with CC0 license URL (API-verified, query below). CC0 = no attribution/permission needed.
- **Free Music Archive** (freemusicarchive.org/License_Guide — capital L + underscore; `/license-guide` 404s): **CC-based, NOT CC0** — artists pick the license. CC BY = commercial OK + attribution; **BY-NC / BY-NC-SA / BY-NC-ND = NOT for monetized videos** (NC bans commercial use; ND also bans syncing to video); retired FMA-Limited "Download Only" license = no video use. FMA is operated by Tribe of Noise; curated "royalty-free / all rights included" music is their paid Tribe of Noise PRO product. Homepage claim: "Royalty free music. Safe to use in all kinds of media like YouTube, Facebook and podcast episodes."
- **Suno** (suno.com/pricing): Free $0 — 50 cr/day, **no commercial use** · Pro $10/mo ($8/mo annual, $96/yr) — 2,500 cr/mo (~500 songs) + **commercial use rights for songs made while subscribed** · Premier $30/mo ($24/mo annual, $288/yr) — 10,000 cr/mo (~2,000 songs). ToS (suno.com/terms, rev. Mar 26 2026) assigns Pro/Premier all rights in Output made while subscribed but **"Suno makes no representation or warranty to you that any copyright will vest in any Output"**; free tier = non-commercial + attribution; **Remixes are always non-commercial, even on paid tiers**; output not unique across users. Pricing-FAQ (page payload): "Free plans don't include commercial rights. If you're on Pro or Premier, you can use your songs commercially, just make sure to follow the rules of any platform you share them on."
- **Udio** (www.udio.com/pricing): Free 10 cr/day + 100 cr/mo cap (3 full-length 2:10 gens/day) · Standard $10/mo ($8/mo annual) 2,400 cr/mo · Pro $30/mo ($24/mo annual) 6,000 cr/mo · top-ups 100 cr/$3, 1,000 cr/$25. **ToS (www.udio.com/terms-of-service — NOT `/terms`, which login-walls — rev. Nov 12 2025) grants NO commercial rights on ANY tier (VERIFIED Aug 10 2026):** §1.2 bans downloading/distributing Output on streaming/UGC platforms (YouTube/Spotify/TikTok explicitly listed); §5.2 bans commercial exploitation; §6.1 Udio owns all Output; §6.3 personal non-commercial only; §6.4 attribution "generated using the Services" required unless paid. **Udio is unusable for monetized video, period.** UMG settlement (Oct 29 2025) → transition to licensed walled-garden platform with downloads paused; current product is legacy.
- **YouTube licensing** (support.google.com/youtube/answer/2797468): uploads default to Standard YouTube license; CC BY option; you can monetize CC content only if the license grants commercial rights; a Content ID claim blocks CC-BY marking.

### Suno vs Udio — AI-music licensing for monetized video (verified Aug 10, 2026)
- **APIs:** neither has a public API. Suno: official **API Partner Program** announced Jul 2026 (curated early-access partners only, no public timeline; $400M round at $5.4B valuation); third-party wrappers (docs.sunoapi.org, sunor.cc, GitHub suno-work/Suno-API) are reverse-engineered and ToS-violating. Udio: official help page "we don't currently offer a public API" (Mar 2025).
- **2026 policy/legal events:** Suno to introduce a **downloads policy limiting mass distribution on streaming platforms** + audio **watermarking/fingerprinting** (CEO blog Aug 6, 2026 — video-sync use stays in the "professional, creative" bucket); Suno **lost the GEMA case in Germany** (Jul 31, 2026); Suno source-code hack revealed training on YouTube Music/Genius/Deezer (Jul 15, 2026); UMG–Udio settlement (Oct 2025) → licensed walled-garden platform where artists set voice/style permissions.
- **Streaming-royalty context:** US Copyright Office (2025) — only "human authorship" copyrightable, pure AI output not registrable; Spotify/Deezer tag AI tracks, Apple Music has AI Transparency Tags.
- **Verdict for documentary beds:** Suno Pro annual $8/mo = cheap + contractually safe for monetized-YouTube video beds (residual risk: no copyright warranty, non-unique output, rare Content-ID resemblance to existing songs, remix feature off-limits); **Udio = no on any tier**; CC0 archive.org = zero-risk free baseline. Recommended hierarchy: CC0 → Suno Pro custom beds → Udio (excluded).

## Recommended stack (<$50/mo, agent-automatable) — from this task's conclusion

- **Voice:** OpenAI gpt-4o-mini-tts primary (~$1.08/h, scriptable `instructions` param, REST API) · edge-tts ChristopherNeural as $0 draft/fallback · Cartesia Startup $49 (~27.8h) for quality-max · MiniMax for cheapest cloning ($1.5/voice).
- **Music:** YouTube Audio Library + archive.org CC0 (free, monetization-safe); Suno Pro $8/mo (annual) for custom beds with commercial rights. **Udio: excluded** — ToS bans YouTube/commercial use on all tiers (verified Aug 10, 2026).
- **Total:** ~$3–11/mo for 4× 35-min docs; $49 flat for the quality-max variant.

## Source URLs (all fetched 2026-08-09)

- https://elevenlabs.io/pricing
- https://cartesia.ai/pricing
- https://platform.minimax.io/docs/pricing/pay-as-you-go · https://platform.minimax.io/docs/pricing/audio-subscription · https://platform.minimax.io/docs/guides/models-intro
- https://cloud.google.com/text-to-speech/pricing
- https://developers.openai.com/api/docs/pricing.md · https://developers.openai.com/api/docs/guides/text-to-speech.md
- https://raw.githubusercontent.com/rany2/edge-tts/master/README.md
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts
- https://suno.com/pricing · https://www.udio.com/pricing (via r.jina.ai renders)
- https://suno.com/terms (rev. Mar 26 2026) · https://suno.com/safety (updated Aug 6 2026) · https://suno.com/blog/building-the-future-of-music-responsibly (Aug 6 2026: downloads policy + watermarking)
- https://www.udio.com/terms-of-service (rev. Nov 12 2025; `/terms` login-walls) · https://help.udio.com/en/articles/10756277-udio-public-api ("we don't currently offer a public API")
- https://www.digitalmusicnews.com/2026/07/03/suno-is-opening-an-api-partner-program/ · https://www.frontiernews.ai/news/article/suno-is-building-an-official-developer-api-despite-019c8a90 (API partner program, $5.4B valuation)
- https://www.medianama.com/2025/10/223-umg-udio-copyright-ai-music-creation-platform/ (UMG settlement details, artists set permissions) · https://www.cnet.com/tech/services-and-software/suno-plans-new-tools-to-make-ai-generated-music-more-transparent-is-it-enough/ (watermarking + Spotify/Apple AI-tagging) · https://www.thewindowsclub.com/create-royalty-free-background-music-youtube-videos-suno (community how-to: Suno Pro = safe for monetized YouTube)
- News (Bing/Google News RSS, Aug 2026): Suno lost GEMA case in Germany (MBW, Jul 31 2026); Suno source-code hack revealed YouTube Music/Genius/Deezer training data (TechCrunch/Variety/404 Media/The Verge, Jul 15 2026); UMG–Udio settlement (Oct 30–31 2025); UMG dismissal motion re musicians' union (Aug 5 2026)
- https://support.google.com/youtube/answer/2797468 · https://support.google.com/youtube/answer/3376882
- https://freemusicarchive.org/ · https://freemusicarchive.org/License_Guide
- https://www.minimax.io/news/minimax-speech-28
