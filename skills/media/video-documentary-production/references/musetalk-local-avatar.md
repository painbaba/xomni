# MuseTalk 1.5 — FREE Local Lip-Sync Avatar (RTX 3050 Laptop 4GB)

Verified install 2026-08-10. MuseTalk (Tencent, MIT = commercial OK) is the winner for
free talking-head avatars on a 4GB-VRAM laptop: officially tested on RTX 3050 Ti
Laptop 4GB fp16, ~6-7 min per 10s 720p clip. LatentSync needs 8GB+; LivePortrait is
video-retargeting (not audio-driven); Wav2Lip is research/non-commercial license.
Tavus Developer Free (5 min/mo API, no watermark) is the only usable free CLOUD
alternative (D-ID trial = 3 min one-time + watermark).

## Install (Windows, git-bash) — session-verified, with the mmpose correction
```
git clone --depth 1 https://github.com/TMElyralab/MuseTalk && cd MuseTalk
python -m venv venv        # MUST be Python 3.11 — requirements pin numpy==1.23.5 (no py3.13 wheels)
./venv/Scripts/python.exe -m pip install -q --upgrade pip setuptools wheel
./venv/Scripts/python.exe -m pip install -q "torch==2.1.0" "torchvision==0.16.0" --index-url https://download.pytorch.org/whl/cu121
./venv/Scripts/python.exe -m pip install -q -r requirements.txt
./venv/Scripts/python.exe -m pip install -q "numpy==1.23.5"        # RE-PIN: mmdet pulls numpy 2.x, which breaks torch 2.1 + tensorflow 2.12
./venv/Scripts/python.exe -m pip install -q "huggingface_hub==0.30.2"  # transformers 4.39.2 requires hub <1.0; upgrading breaks import
./venv/Scripts/python.exe -m pip uninstall -q -y tensorflow tensorboard tensorflow-intel  # UNUSED by MuseTalk code; only numpy-constraint baggage
./venv/Scripts/python.exe -m pip install -q "mediapipe==0.10.21"   # NOT mediapipe 1.x — 1.0 REMOVED mp.solutions
# ⛔ DO NOT install mmcv/mmdet/mmpose/chumpy on Windows — verified dead ends, see "mmpose bypass" below
```
**CRITICAL pin matrix (learned the hard way — do NOT "upgrade"):**
- **torch MUST be 2.1.0+cu121, NOT the latest cu128.** mmcv==2.0.1 (pinned by
  MuseTalk's README) has Windows wheels ONLY for the torch-2.0/2.1 era; with torch
  2.11 it falls back to a source build and fails (`pkg_resources` missing / MSVC).
  Same for mmdet 3.1.0 + mmpose 1.1.0 + chumpy — all 2023-era, torch-2.1-compatible.
- The naive path (torch cu128 → mim install mmcv) is a VERIFIED dead end: no wheel,
  source build fails. Downgrade torch FIRST, then mim installs resolve real wheels.
- torchvision must match the torch downgrade (0.16.0 for 2.1.0).
- Disk hazard: venv + 7.3GB models + pip cache of big torch wheels fills C: (hit
  4.7GB free mid-install). `pip cache purge` freed 5.7GB. Purge caches before/after.
## mmpose bypass (REQUIRED on Windows — verified working 2026-08-10)
mmcv==2.0.1 has **NO Windows wheels at all** (checked openmmlab indices for
cu121/torch2.1 AND cu118/torch2.1 — empty; source build fails on MSVC). So the
official mmpose stack is a dead end on Windows. MuseTalk uses mmpose ONLY for face
landmarks (indices 28/29/30 = nose bridge) in `musetalk/utils/preprocessing.py`.
Replace it with mediapipe FaceMesh:

1. Pin `mediapipe==0.10.21` (mediapipe **1.x removed `mp.solutions`** → AttributeError).
2. Patch `preprocessing.py`: delete the mmpose imports + dwpose init; add
   `mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1,
   refine_landmarks=True)`. Add helper returning a 68-point COCO-style array:
   - `flm[28]=pts[9]` (glabella), `flm[29]=pts[168]` (bridge mid), `flm[30]=pts[6]`
     (bridge low) — FaceMesh→COCO mapping; nose bridge must stay monotonic y.
   - full-face bounds for the bbox fallback: `flm[0]=pts[234]`, `flm[16]=pts[454]`,
     `flm[8]=pts[152]` (chin), `flm[27]=pts[10]` (forehead); rest zeros; `None` if
     no face (caller falls back to the FAN bbox / placeholder).
3. Replace both `inference_topdown(model, ...)` call sites (get_bbox_range +
   get_landmark_and_bbox) with the helper.
4. Verified: import chain PASS, face landmarks PASS (68×2, monotonic), no-face
   → None, full get_landmark_and_bbox 2/2 valid bboxes. Then inference runs.
Also: uninstall tensorflow/tensorboard (never imported — only numpy-constraint
baggage); if mmdet ever ran it pulls matplotlib 3.11.1 (needs numpy≥1.25) and numpy
2.x — pin numpy 1.23.5 + matplotlib ≤3.7.x after any such install.

Status (2026-08-10, complete): the corrected chain above IS confirmed — torch
2.1.0+cu121, mediapipe 0.10.21, numpy 1.23.5, hub 0.30.2, all 7.3GB models
downloaded via snapshot_download, preprocessing patched, verification 4/4 PASS,
inference runs with `--version v15 --use_float16 --batch_size 2`.

Pitfalls hit (verified):
- numpy build fails on py3.13 (`Failed to build 'numpy'`) → use `python` (3.11), not `python3`.
- Torch download is big — run installs as background jobs with notify; the 600s
  foreground timeout kills them mid-download (torch resume works on retry).
- requirements.txt does NOT pin torch — install it explicitly.
- Missing modules surfaced one-by-one at import time (torchvision, then mmpose) —
  the requirements.txt misses torchvision; install it with the SAME index as torch.

## Models (7.3GB total) — huggingface_hub 0.30.2 has NO `-m` entry
`python -m huggingface_hub` fails; the `hf` CLI (hf.exe) may be missing. Use the API:
```python
from huggingface_hub import snapshot_download
snapshot_download("TMElyralab/MuseTalk", local_dir="models/musetalk")
snapshot_download("stabilityai/sd-vae-ft-mse", local_dir="models/sd-vae",
                  allow_patterns=["config.json","diffusion_pytorch_model.bin"])
snapshot_download("openai/whisper-tiny", local_dir="models/whisper",
                  allow_patterns=["config.json","pytorch_model.bin","preprocessor_config.json"])
snapshot_download("yzd-v/DWPose", local_dir="models/dwpose", allow_patterns=["dw-ll_ucoco_384.pth"])
snapshot_download("ManyOtherFunctions/face-parse-bisent", local_dir="models/face-parse-bisent",
                  allow_patterns=["79999_iter.pth","resnet18-5c106cde.pth"])
```
Note: `hf download` (newer huggingface_hub) also works; upgrading to hf 1.x warns
"transformers 4.39.2 requires <1.0" — if inference breaks, pin back to 0.30.2.

## Source video: synthetic presenter (ethics — never real faces)
1. Generate face: `curl "https://image.pollinations.ai/prompt/professional%20news%20presenter%20studio?width=1024&height=576"` (verify with PIL; it returns JPEG even with Accept: application/json).
2. Base video from still (MuseTalk needs a VIDEO with a detectable face):
```
ffmpeg -y -loop 1 -i presenter.jpg -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,zoompan=z='min(zoom+0.0015,1.25)':d=138:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25" -t 5.5 -c:v libx264 -pix_fmt yuv420p -an base.mp4
```
3. Narration audio must be wav 16kHz mono: `ffmpeg -i u1.mp3 -ar 16000 -ac 1 u1.wav`

## Inference
`scripts/realtime_inference.py` is WEBCAM-only (no video/audio args). Use
`scripts/inference.py` with a task YAML:
```yaml
# configs/inference/upi.yaml
task_0:
 video_path: "C:/.../base.mp4"
 audio_path: "C:/.../u1.wav"
 bbox_shift: -5
```
```
./venv/Scripts/python.exe -m scripts.inference --inference_config configs/inference/upi.yaml \
  --result_dir results/upi --version v15 --use_float16 --batch_size 2 --output_vid_name upresenter.mp4 \
  --unet_config ./models/musetalkV15/musetalk.json --unet_model_path ./models/musetalkV15/unet.pth
```
- `--use_float16` + `--batch_size 2` are the 4GB-VRAM settings.
- ⚠️ `scripts/inference.py` has STALE defaults (`--unet_config ./models/musetalk/config.json` →
  FileNotFoundError) — ALWAYS pass `--unet_config`/`--unet_model_path` explicitly, per the
  repo's own `inference.sh` (v1.5 = `./models/musetalkV15/musetalk.json` + `unet.pth`).
- ⚠️ Model layout: the HF snapshot of TMElyralab/MuseTalk downloads NESTED
  (`models/musetalk/musetalkV15/unet.pth`, `models/musetalk/musetalk/...`) — the scripts
  expect FLAT paths. Flatten before inference:
  `cp models/musetalk/musetalkV15/* models/musetalkV15/ && cp models/musetalk/musetalk/*.json models/musetalk/musetalk/*.bin models/musetalk/`
- Result is an mp4 WITH the input audio embedded — mute it when splicing into a
  composition and play the original narration track separately for frame-perfect sync.

## Synthetic face — VALIDATE before building base.mp4 (verified gotcha)
The first Pollinations prompt ("professional news presenter studio") returned a valid
JPEG with NO detectable face — both mediapipe FaceMesh AND the FAN detector found
nothing, so the whole inference chain produced no bbox and crashed (division by zero
in the bbox-shift print). Rules:
1. Prompt MUST be face-focused: "close-up portrait photo of a professional indian male
   news anchor, face clearly visible, looking directly at camera, suit, neutral studio
   background, photorealistic" (1024x576 works).
2. Pollinations plain GET returns HTTP 200 with EMPTY body — send
   `Accept: application/json` header; it still returns a JPEG.
3. Auto-validate each candidate with `mp_face_landmarks(frame)` (mediapipe); keep the
   first candidate that returns a 68x2 array; loop 2-3 prompts until one passes.

### Portrait quality ladder (verified by the asset swarm, 2026-08-10)
For the host-card portrait (and any still the camera lingers on), resolution matters —
768px looks soft in a 148px+ circular crop at 1080p. Measured hierarchy:
1. **FLUX.1-schnell via the official BFL HF Space** (1536×1536 / 1344×1536): best quality.
   Call the Gradio API (POST event → poll `event_id` → grab `gradio_api/file=...` URL).
   ⚠️ ZeroGPU quota: anonymous gets ~65s of GPU/min — after a few images the Space
   returns `You have exceeded your ZeroGPU quota`; retry loops just burn time. An HF
   token raises the quota. (black-forest-labs-flux-1-schnell.hf.space)
2. **Pollinations caps EVERY model at 768×768** (flux, turbo, sdxl, kandinsky, sana —
   all tested). Fine for the 148px card, not for full-frame.
3. **thispersondoesnotexist.com is DEAD** (domain for sale, returns HTML) — the working
   synthetic-face source is this-person-does-not-exist.com (1024×1024, random face,
   no prompt control).
4. Mirror verified downloads to **files.catbox.moe** (upload, get a stable URL) so the
   composition's asset URL survives source churn — the swarm's ranked picks were all
   catbox-mirrored.
Rule: any generated face that must be visible on screen gets the face-validation check
(`mp_face_landmarks` non-None) AND the highest-res generator you can reach — the user's
quality bar is "best in quality, best in assets".

## User verdict (2026-08-10) — talking-head rejected on 4GB
MuseTalk on the RTX 3050 4GB produced a working lip-synced clip, but the user REJECTED
the output ("its fucked up ... without approach was best"). The approved avatar look
for this stack is the STATIC host-card: a synthetic portrait that POPS UP during
narration (rounded image + name chip, slide/scale/fade in at narration start, out at
scene end) — no lip-sync. Keep MuseTalk as the engine only if quality improves
(higher-res source face, better base video); default to the static pop. See the
Remotion avatar splice pattern in `references/remotion-migration.md`.
