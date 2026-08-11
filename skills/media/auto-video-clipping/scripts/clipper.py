#!/usr/bin/env python3
"""
AutoClipper — automatic podcast/stream clipping pipeline.
Usage:
  python clipper.py <youtube_url> [--clips N] [--window 45] [--min-score 2.5] [--keywords "money,tax,secret"]

Pipeline:
  1. yt-dlp downloads best audio (streamed, no full video needed for scoring)
  2. faster-whisper transcribes with word timestamps (GPU if available, CPU fallback)
  3. Scoring: sliding windows ranked by speech density + keyword hits + energy words
  4. ffmpeg renders top-N clips as 9:16 vertical shorts with burned-in captions
Output: clips/ dir with .mp4 files ready to upload.

Windows notes (verified Aug 2026):
  - Run with Python 3.14 (the interpreter that has yt_dlp/faster-whisper):
    /c/Users/HP/AppData/Local/Programs/Python/Python314/python.exe clipper.py ...
  - Install first: python -m pip install faster-whisper
  - YouTube downloads need cookies (bot-check): log into YouTube in Chrome, CLOSE
    Chrome, then add --cookies-from-browser chrome. Local files work with no cookies.
"""
import argparse, json, math, os, re, subprocess, sys, tempfile, shutil, time

YDL = None
def ydl_opts():
    return {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(WORKDIR, 'src.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

def download(url):
    # Local file? Skip download entirely.
    if os.path.exists(url):
        print(f'[1/4] Using local file: {url}')
        return url
    import yt_dlp
    print('[1/4] Downloading audio...')
    with yt_dlp.YoutubeDL(ydl_opts()) as y:
        info = y.extract_info(url, download=True)
        f = os.path.join(WORKDIR, 'src.' + (info.get('ext') or 'm4a'))
        if not os.path.exists(f):
            cands = [x for x in os.listdir(WORKDIR) if x.startswith('src.')]
            f = os.path.join(WORKDIR, cands[0])
        print(f'      saved: {f} ({os.path.getsize(f)//1024//1024} MB)')
        return f

def transcribe(audio):
    print('[2/4] Transcribing with faster-whisper...')
    from faster_whisper import WhisperModel
    def build(device):
        ct = 'float16' if device == 'cuda' else 'int8'
        return WhisperModel('small', device=device, compute_type=ct)
    # Try CUDA; if the DLLs are missing it raises at encode time -> fall back to CPU
    devices = []
    try:
        import ctranslate2
        if getattr(ctranslate2, 'get_cuda_device_count', lambda: 0)() > 0:
            devices = ['cuda', 'cpu']
    except Exception:
        devices = ['cpu']
    if not devices:
        devices = ['cpu']
    model, words = None, []
    for dev in devices:
        try:
            model = build(dev)
            print(f'      device: {dev}')
            segments, info = model.transcribe(audio, word_timestamps=True, vad_filter=True)
            words = []
            for seg in segments:
                for w in (seg.words or []):
                    words.append({'w': w.word.strip().lower(), 's': w.start, 'e': w.end})
            print(f'      {len(words)} words, {info.language} ({info.language_probability:.0%})')
            return words
        except Exception as e:
            print(f'      {dev} failed ({str(e)[:60]}), trying next...')
            continue
    raise RuntimeError('transcription failed on all devices')

def score_windows(words, window, keywords, energy_words):
    """Sliding-window scoring: speech density + keyword + energy word hits."""
    if not words: return []
    # word density per second (excitement proxy) using 5s buckets
    dur = words[-1]['e']
    buckets = [0.0] * (int(dur) + 2)
    for w in words:
        for t in range(int(w['s']), min(int(w['e']) + 1, len(buckets))):
            buckets[t] += 1.0 / max(w['e'] - w['s'], 0.3)
    scores = []
    step = max(5, window // 6)
    for start in range(0, max(int(dur) - window, 1), step):
        end = start + window
        seg_words = [w for w in words if start <= w['s'] < end]
        if len(seg_words) < 15:  # too quiet
            continue
        density = sum(buckets[start:end]) / window
        kw_hits = sum(1 for w in seg_words if w['w'] in keywords)
        en_hits = sum(1 for w in seg_words if w['w'] in energy_words)
        # density normalized around typical speech (~2.5 wps)
        score = max(0, density - 1.8) * 1.0 + kw_hits * 2.0 + en_hits * 1.5
        # penalize overlap with already-chosen windows later
        scores.append({'start': start, 'end': end, 'score': round(score, 2),
                       'words': len(seg_words), 'kw': kw_hits, 'en': en_hits})
    return scores

def pick_clips(scores, n, min_score, min_gap):
    scores.sort(key=lambda s: -s['score'])
    chosen = []
    for s in scores:
        if s['score'] < min_score: continue
        if any(abs(s['start'] - c['start']) < min_gap for c in chosen): continue
        chosen.append(s)
        if len(chosen) >= n: break
    chosen.sort(key=lambda s: s['start'])
    return chosen

def make_captions(words, start, end, ass_path, width=1080, height=1920):
    """Burn captions via ASS: bottom-third, word-group highlighting."""
    seg = [w for w in words if w['s'] >= start - 0.5 and w['e'] <= end + 0.5]
    # group into lines of ~5 words with timing
    lines = []
    cur, cur_s, cur_e = [], None, None
    for w in seg:
        if cur_s is None: cur_s = w['s']
        cur_e = w['e']
        cur.append(w['w'])
        if len(cur) >= 5 or (cur_e - cur_s) > 4:
            lines.append((cur_s - start, cur_e - start, ' '.join(cur)))
            cur, cur_s, cur_e = [], None, None
    if cur: lines.append((cur_s - start, cur_e - start, ' '.join(cur)))
    if not lines: return
    def ts(t):
        t = max(0, t)
        h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
        return f'{h}:{m:02d}:{s:05.2f}'
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write('[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n')
        f.write('[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Outline, Shadow, Alignment, MarginV\n')
        f.write('Style: Cap,Segoe UI,64,&H00FFFFFF,&H00000000,&H96000000,-1,3,1,2,140\n\n')
        f.write('[Events]\nFormat: Layer, Start, End, Style, Text\n')
        for s, e, txt in lines:
            f.write(f'Dialogue: 0,{ts(s)},{ts(e)},Cap,,0,0,0,,{txt}\n')

def render(audio, words, clip, i, captions):
    """Render one 9:16 vertical clip with captions."""
    os.makedirs(os.path.join(WORKDIR, 'clips'), exist_ok=True)
    out = os.path.join(WORKDIR, 'clips', f'clip_{i:02d}_{int(clip["start"])}-{int(clip["end"])}.mp4')
    ass = os.path.join(WORKDIR, f'cap_{i:02d}.ass')
    make_captions(words, clip['start'], clip['end'], ass)
    d = clip['end'] - clip['start']
    # 9:16: crop center 56.25% width then scale to 1080x1920.
    # Use a relative ASS filename (chdir to WORKDIR) to dodge Windows drive-colon escaping.
    vf = ("crop=iw*9/16:ih,scale=1080:1920:force_original_aspect_ratio=increase,"
          f"crop=1080:1920,subtitles=cap_{i:02d}.ass")
    cmd = ['ffmpeg', '-y', '-ss', str(clip['start']), '-t', str(d),
           '-i', audio,
           '-vf', vf,
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26',
           '-c:a', 'aac', '-b:a', '128k', '-ar', '44100',
           '-movflags', '+faststart', out]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=WORKDIR)
    if r.returncode != 0:
        print(f'      render failed: {r.stderr[-300:]}')
        return None
    print(f'      {out}  ({d:.0f}s, score {clip["score"]})')
    return out

def main():
    global WORKDIR
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--clips', type=int, default=3)
    ap.add_argument('--window', type=int, default=45, help='candidate window seconds')
    ap.add_argument('--min-score', type=float, default=2.5)
    ap.add_argument('--min-gap', type=int, default=60)
    ap.add_argument('--keywords', default='money,secret,amazing,guaranteed,never,best,worst,actually,tax,crash,invest')
    ap.add_argument('--workdir', default=os.path.join(os.path.expanduser('~'), 'clipper'))
    args = ap.parse_args()
    WORKDIR = args.workdir
    os.makedirs(WORKDIR, exist_ok=True)
    t0 = time.time()
    audio = download(args.url)
    words = transcribe(audio)
    kw = set(args.keywords.lower().split(','))
    en = set(['wow','crazy','huge','massive','oh','wait','no','yes','really','seriously','insane','unbelievable'])
    print(f'[3/4] Scoring {args.window}s windows...')
    scores = score_windows(words, args.window, kw, en)
    clips = pick_clips(scores, args.clips, args.min_score, args.min_gap)
    if not clips:
        print('      No clip passed min-score. Lower --min-score or widen --window.')
        return
    print(f'      picked {len(clips)} clips: ' + ', '.join(f'{c["start"]:.0f}-{c["end"]:.0f}s(score {c["score"]})' for c in clips))
    print('[4/4] Rendering vertical clips...')
    for i, c in enumerate(clips, 1):
        render(audio, words, c, i, True)
    print(f'Done in {time.time()-t0:.0f}s. Clips in {os.path.join(WORKDIR, "clips")}')

if __name__ == '__main__':
    main()
