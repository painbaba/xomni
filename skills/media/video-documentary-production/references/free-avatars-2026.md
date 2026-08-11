# Free Avatar / Talking-Head Presenter Scenes (verified Aug 2026)

Goal: pro presenter segments (Dhruv Rathee / Fern formula) for documentary narration at $0.
User rejected paid HeyGen API ("heygen api is paid") — this is the free candidate research.

## The verdict: LOCAL = MuseTalk 1.5 (Tencent), CLOUD = Tavus Developer Free

| Rank | Model | Runs on 4GB? | Commercial? | 10s @720p | Verdict |
|---|---|---|---|---|---|
| 1 | **MuseTalk 1.5** (TMElyralab) | ✅ officially tested RTX 3050 Ti Laptop 4GB (fp16) | ✅ MIT | ~6–7 min | THE 4GB winner |
| 2 | Wav2Lip | ✅ (CPU too) | ❌ research/non-commercial | ~2–5 min CPU | license blocks monetized docs |
| 3 | SadTalker | ⚠️ 4–6GB @256px | ✅ Apache-2.0 | 3–8 min | stale (2024) |
| 4 | LivePortrait | ⚠️ 2–4GB @512 | ✅ MIT | real-time | NOT audio-driven (video retargeting) — wrong tool |
| 5 | LatentSync 1.5/1.6 | ❌ 8GB/18GB min | ✅ Apache-2.0 | — | best quality, 2–4× our VRAM |
| 6 | EchoMimic V2/V3 | ❌ 16GB-class | ✅ Apache-2.0 | — | datacenter VRAM |
| 7 | Hallo2/3 | ❌ >8GB | ✅ MIT | 2.5+ hrs/10s | no |
| 8 | EMO/EMO2 | ❌ A100-class | ❌ | — | EMO2 not open source |
| 9 | Sonic | ❌ 32GB | ❌ CC BY-NC-SA | — | non-commercial |

Cloud free tiers (live-verified): **Tavus Developer Free** = full API + **5 min/mo** AI video
generation, no watermark, 1080p, no credit card — the ONLY recurring free avatar API found.
D-ID trial = 14 days / 3 min total, full-screen watermark, personal-use only. HeyGen/Synthesia/
Akool/Captions/Elai/DeepBrain/Vidnoz/Colossyan/Hedra all gate API behind paid. A 60s trailer
(2 presenter clips ≈ 30–45s avatar video) fits Tavus's 5 min/mo.

## ETHICS RULE (non-negotiable)
Never lip-sync REAL identifiable people to our narration (deepfake territory, monetization
risk). Use a SYNTHETIC face. This also means: skip the tempting public-domain politician/
celebrity talking-head clips on Wikimedia as MuseTalk sources.

## The working recipe (executed Aug 2026)

1. **Synthetic presenter face** — Pollinations (free, no key):
   `curl -sL -H "Accept: application/json" "https://image.pollinations.ai/prompt/<prompt>?width=1024&height=576&nologo=true" -o presenter.jpg`
   Prompt e.g. `professional%20news%20anchor%20man%20in%20suit%20studio%20background%20looking%20at%20camera%20frontal%20face%20cinematic%20lighting`.
   NOTE: returns a JPEG even with the JSON header; sync endpoint can return HTTP 200 with an
   EMPTY body — retry. `thispersondoesnotexist.com` is bot-blocked (returns HTML) — skip.
2. **Base video from the still** (MuseTalk needs a VIDEO, a slow-zoom still works — lip motion
   is generated anyway):
   `ffmpeg -y -v error -loop 1 -i presenter.jpg -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,zoompan=z='min(zoom+0.0015,1.25)':d=138:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25" -t 5.5 -c:v libx264 -pix_fmt yuv420p -an base.mp4`
3. **MuseTalk install (Python ≤3.11 — the trap)**:
   - requirements.txt pins numpy==1.23.5 + tensorflow==2.12.0 → NO Python 3.13 wheels. Use
     `python` (3.11) not `python3` (3.13). Rebuild venv if you started with the wrong one.
   - Install setuptools/wheel FIRST (`Cannot import 'setuptools.build_meta'` backend error otherwise).
   - torch is NOT in requirements: `pip install torch --index-url https://download.pytorch.org/whl/cu128`
     (~2.5GB, driver 592.82/CUDA 13.1 accepts cu128).
   - Models: repo ships download_weights.sh/.bat → `hf download TMElyralab/MuseTalk`,
     `stabilityai/sd-vae-ft-mse`, `openai/whisper-tiny`, `yzd-v/DWPose`, face-parse-bisent (~3GB total).
4. **Inference**: `python -m scripts.realtime_inference --inference_mode talking_head
   --audio_path narration/u1.mp3 --video_path base.mp4` (~6-7 min per 5.5s clip on 3050 4GB fp16).
5. **Splice into the composition**: MUTE the avatar video and keep the separate narration track
   (MuseTalk was generated FROM that audio → lip-sync is frame-perfect by construction).

## Integration pattern (Remotion)
Scene type gets an `avatar?: string` field; Media renders `<Video src={staticFile('avatar/'+s.avatar)} />`
muted, object-fit cover, NO Ken Burns (presenters don't zoom), scrim only at bottom for text.
Design: avatar hook scene → cinematic middle → avatar endcard = the pro formula.
