# FREE voice + music + SFX stack for documentaries — live-verified 2026-08-09

All facts fetched live (curl + headless browser) from the cited URLs. Prices/limits move —
re-verify before committing. Complementary to `tts-providers-2026.md` (paid TTS).

## Free cloud TTS tiers

| Provider | Free allowance | After free tier | Commercial use |
|---|---|---|---|
| ElevenLabs (elevenlabs.io/pricing) | **10,000 credits/mo ≈ ~10 min** (128kbps, 44.1kHz) | Starter $6=30k cr · Creator $22=121k · Pro $99=600k + 192kbps/44.1kHz PCM | **Free = no commercial license**; starts on paid plans |
| OpenAI (developers.openai.com/api/docs/pricing) | **NO free tier** | gpt-4o-mini-tts **$12/1M audio tokens + $0.60/1M text tokens** (~$0.86–1.30 per 60 min); tts-1 $15/1M chars; tts-1-hd $30/1M chars | yes |
| Google Cloud TTS (cloud.google.com/text-to-speech/pricing) | **Per-model monthly free chars, billing card REQUIRED** ("You must enable billing… automatically charged if your usage exceeds the number of free characters"): WaveNet & Standard **0–4M chars** free; Neural2 / Chirp 3 HD / Studio / Polyglot **0–1M** free | WaveNet $4/1M · Neural2 $16/1M · Chirp3 HD $30/1M · Studio $160/1M | yes |
| Azure Speech (azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/) | **Free F0 = 0.5M chars/mo** neural TTS | usage-based | yes |
| AWS Polly (aws.amazon.com/polly/pricing/) | **First 12 months: Standard 5M chars/mo, Neural 1M/mo, Long-Form 500K/mo, Generative 100K/mo**; +$200 new-customer credits (since Jul 15, 2025) | usage-based | yes |

- Google math: 1M chars ≈ 1,000 min ≈ **~16.6 h narration free/mo** (Neural2/WaveNet) — the
  biggest cloud free quota, but needs credit card + billing enabled. Gemini TTS models have NO
  free tier (audio $10/1M tokens, 25 tokens/sec of audio).
- AWS quote: "the free tier includes 5 million characters per month… For Neural voices, the
  free tier includes 1 million characters per month… for the first 12 months."

## Local open-source TTS (free forever, Windows)

| Engine | License | Langs / Voices | Windows install | Notes |
|---|---|---|---|---|
| **Kokoro** (huggingface.co/hexgrad/Kokoro-82M, github.com/hexgrad/kokoro) | **Apache-2.0** | v1.0 (Jan 2025): **54 voices / 9 langs** — US EN 11F+9M, UK EN 4F+4M, JA, ZH, ES, FR, HI, IT, PT-BR (VOICES.md) | `pip install kokoro soundfile` + **espeak-ng .msi** (README has explicit Windows steps) | 82M params, StyleTTS2 arch, real-time CPU, 24 kHz; ~11.5M HF downloads/mo. Deep male: **am_michael, am_fenrir, am_puck** (US), **bm_george** (UK). Quality grades B/C (training-data based) |
| **Chatterbox** (github.com/resemble-ai/chatterbox) | **MIT** | Turbo 350M (EN) · Nano 110M (EN, **CPU 3× realtime on 8 cores**) · **Multilingual V3 0.5B, 23+ langs** · 6 single-lang finetunes | `pip install chatterbox-tts` (py3.11 recommended; torch; GPU recommended, CPU works) | "SoTA open-source TTS" (25.9k stars). **Zero-shot clone from ~10 s reference clip** — supply a deep male ref for authoritative VO |
| **Piper** (github.com/rhasspy/piper — archived Oct 6 2025, MIT → successor github.com/OHF-Voice/piper1-gpl, **GPL**) | MIT→GPL | **~45 languages** in docs/VOICES.md (ar, ca, cs, cy, da, de, el, en_GB, en_US, es, fa, fi, fr, hu, is, id, it, ka, kk, lb, lv, ml, hi, ne, nl, no, pl, pt, ro, ru, sk, sl, sr, sv, sw, te, tr, uk, vi, zh…) | `pip install piper-tts`; **v1.6.0 ships Windows wheel** `piper_tts-1.6.0-cp39-abi3-win_amd64.whl` (verify via api.github.com/repos/OHF-Voice/piper1-gpl/releases) | VITS→ONNX; instant on any CPU, flatter/more synthetic; en_US-ryan-high, en_GB-northern_english_male for male VO. GPL only matters for embedding the code, not your output audio |
| **Coqui XTTS-v2** (huggingface.co/coqui/XTTS-v2) | **Coqui Public Model License = NON-COMMERCIAL** ⚠️ | 17 langs; 6 s voice cloning | `pip install TTS` (py 3.9–<3.12); ~1.8 GB model; GPU strongly recommended (CPU painfully slow) | **Avoid for monetized YouTube** — license forbids commercial use; repo unmaintained (Coqui shut down 2024) |
| **MeloTTS** (github.com/myshell-ai/MeloTTS) | **MIT** ("free for both commercial and non-commercial use") | EN (US/UK/IN/AU), ES, FR, ZH, JA, KO; **1 voice/language** | `pip install melotts`; CPU real-time | Fine backup; single voice per lang limits choices |

### Deep authoritative male documentary voice — verdict
1. Zero effort: edge-tts `en-US-ChristopherNeural` (free, no install, best authority of the free cloud set).
2. **Free forever + license-clean local: Kokoro `am_michael` / `am_fenrir` / `bm_george`** (Apache-2.0, no attribution, CPU real-time).
3. Best local quality: **Chatterbox Multilingual cloned from a ~10 s deep-male reference** (MIT; GPU recommended).
4. Don't use: XTTS-v2 (non-commercial license), Piper for finals (flat), ElevenLabs free past ~10 min/mo, OpenAI (no free tier).
5. Cloud free-quota supplements (card required): Google WaveNet/Neural2 (~16 h/mo), Polly neural (1M/mo, 12 mo), Azure F0 (0.5M/mo), ElevenLabs (~10 min/mo).

## Music — monetization-verified sources

1. **YouTube Audio Library** (support.google.com/youtube/answer/3376882) — the #1 source:
   - "royalty-free production music and sound effects… **copyright-safe**. The Audio Library is found exclusively in YouTube Studio."
   - "If you're in the YouTube Partner Program, **you can monetize videos with music and sound effects from the Audio Library**."
   - "won't be claimed by a rights holder through the **Content ID** system." / "Only music and sound effects from the Audio Library are known to YouTube to be copyright-safe."
   - Two filterable license types: **Creative Commons = attribution required** in description; **standard YT Audio Library license = no attribution**. Auto "Music in this Video" section on watch page.
   - Has a **Sound effects tab** (category + duration filters) — SFX covered by same monetization terms.
2. **Free Music Archive** (freemusicarchive.org, /about/) — "**Royalty free music. Safe to use in all kinds of media like YouTube, Facebook and podcast episodes.**" / "free access to **open licensed** [Creative Commons] original music… featured in countless videos, podcasts, films… documentaries." **Per-track CC license decides monetization** (BY = fine w/ credit; BY-NC = no). ⚠️ FMA license-guide/FAQ subpages 404'd Aug 2026 — site partially broken.
3. **Incompetech / Kevin MacLeod** — FAQ (incompetech.com/music/royalty-free/faq.html): "Can I use your music for YouTube videos? **Yes, AND you can monetize the videos. Be sure to credit me.**" All music **CC BY 4.0**; credit format: `"<Title>" Kevin MacLeod (incompetech.com) — Licensed under Creative Commons: By Attribution 4.0 — https://creativecommons.org/licenses/by/4.0/` (in video description for YT). Remixing allowed ("chop, splice, compress… MUST make clear in credits which parts are yours"). Paid **Standard License** only where attribution impossible (radio/TV ads, corporate) — see /music/royalty-free/licenses/.
4. **archive.org CC0** — live count (Aug 2026): **75,512 audio items** with CC0 dedication:
   `https://archive.org/advancedsearch.php?q=mediatype:audio+AND+licenseurl:"http://creativecommons.org/publicdomain/zero/1.0/"&fl[]=identifier&rows=0&output=json` (+ `AND+title:(ambient OR drone …)` for beds). Direct download: `https://archive.org/download/<id>/<file>`. **CC0 = zero attribution, fully monetization-safe.** Ideal for 10-min drone beds at different offsets.
5. **Free AI music — free tiers are NOT monetization-safe:**
   - **Suno** (suno.com/pricing): Free $0 = **50 credits/day** (daily renewal), v4.5-all model only, 8-min uploads, shared queue, no stems — **"No commercial use"** explicitly on the pricing page. Pro $8/mo = 2,500 credits/mo + commercial rights for new songs.
   - **Udio** (udio.com/pricing): Free = **10 credits/day, 100 credits/mo (no rollover)**, 2 concurrent gens (4 songs), 32-s songs, **3 full-length (2:10) songs/day**; Standard $10/mo = 2,400 credits; extra credits 100=$3 / 1,000=$25. ToS (udio.com/terms-of-service): free outputs "solely for your personal and **non-commercial** purposes" (trial users can't even download).
   - Verdict: for monetized channels, AI-music free tiers are useless; pay ($8 Suno / $10 Udio) or use CC0/CC BY sources (legally safer anyway).

## SFX
1. **freesound.org** (freesound.org/help/faq/) — every sound carries one of **three CC licenses**: **CC0** (anything incl. commercial; just don't claim authorship), **CC BY** (commercial OK + credit: `"sound" by user (freesound.org/s/soundID/) licensed under CC BY 4.0`), **CC BY-NC** (no commercial — skip). Filter by CC0/CC BY for docs. Sampling+ license retired.
2. **YT Audio Library SFX tab** — copyright-safe + monetizable (see above).
3. **ffmpeg-synthesized risers/booms/whooshes/tick** — deterministic, zero licensing (commands in `pipeline-recipe.md`).

## Definitive free stack (monetized YouTube, 10–40 min docs)

| Layer | Primary | Backup | Never use |
|---|---|---|---|
| Voice | edge-tts `en-US-ChristopherNeural` → **Kokoro `am_michael`/`bm_george`** (Apache-2.0) | Chatterbox w/ deep-male ref (MIT); Google WaveNet/Neural2 free chars; Polly neural; Azure F0 | Coqui XTTS (non-commercial); ElevenLabs free >10 min/mo; OpenAI (no free tier) |
| Music beds | **YT Audio Library** ("Attribution not required" filter) | archive.org CC0 (75k+ items); Incompetech CC BY (credit in description); FMA CC BY tracks | Suno free, Udio free (no commercial rights); FMA BY-NC tracks; jamendo BY-NC-ND on archive.org |
| SFX | **YT Audio Library SFX** | freesound CC0 filter; ffmpeg-synthesized | freesound BY-NC |
| AI music | only if paid: Suno Pro $8/mo | Udio Standard $10/mo | free tiers of both |

Attribution checklist: CC BY anywhere (Incompetech, FMA CC BY, freesound CC BY) → paste credit
into the description; CC0 & YT Audio Library standard license → nothing required.

## URL pitfalls (learned live, Aug 2026)
- **Incompetech old paths 404**: `incompetech.com/music/royalty-free-music.html` and
  `.../royalty-free-music/licenses/` are dead. Working paths: `/music/royalty-free/faq.html`,
  `/music/royalty-free/licenses/`, `/music/royalty-free/music.html`.
- **FMA subpages 404**: `/licensing/`, `/about/license-guide/`, `/about/faq/` all returned 404
  (JS-rendered site partially broken). Use homepage claim + per-track CC license instead.
- **Suno help center article URLs 404** (help.suno.com articles are unstable) — get plan facts
  from `suno.com/pricing` directly.
- **ElevenLabs ToS / FAQ pages are JS-walled** (curl returns 200 + 0 bytes) — use
  `elevenlabs.io/docs/llms.txt` (page index) + `.md`-suffix docs trick (see tts-providers-2026.md).
- **Udio pricing is JS-rendered** — curl gets a 53-byte shell; use headless browser. FAQ
  answers ("10 credits per day and 100 credits per month (no rollovers)") render in the page.
- **GitHub releases API** (`api.github.com/repos/<owner>/<repo>/releases`) is the fastest way
  to verify a project ships a Windows wheel (used to confirm piper1-gpl v1.6.0 win_amd64.whl).
