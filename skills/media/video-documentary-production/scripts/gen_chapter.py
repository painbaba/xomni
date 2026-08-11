#!/usr/bin/env python3
"""gen_chapter.py — build a documentary chapter composition from a chapter spec.

Usage: python gen_chapter.py ch01.json [--out compositions/ch01.html] [--audio-dir narration]

ch01.json:
{
  "id": "ch01", "title": "ACT ONE", "dur": 300.0, "music": "bed-tense",
  "scenes": [
    {"id":"a1s1","kind":"divider","dur":45,"eyebrow":"Act One","headline":"THE RAID",
     "sub":"...","narration":"a1s1","riser":true},
    {"id":"a1s2","kind":"stat","stat":"1131","statLabel":"inspections",
     "sub":"...","narration":"a1s2","boom":true,"count":true},
    {"id":"a1s3","kind":"headline","masthead":"As reported","headline":"...",
     "deck":"...","attr":"...","narration":"a1s3"},
    {"id":"a1s4","kind":"quote","quote":"...","attr":"...","narration":"a1s4"},
    {"id":"a1s5","kind":"timeline","headline":"...","nodes":[{"t":"Jun 2026","label":"..."}],"narration":"a1s5"},
    {"id":"a1s6","kind":"list","headline":"...","items":["...","..."],"narration":"a1s6"},
    {"id":"a1s7","kind":"endcard","headline":"...","sub":"...","credits":"...","narration":"a1s7"}
  ]
}
Kinds: divider, title, stat, quote, timeline, list, headline, endcard.

Key behaviors (pitfalls baked in):
- Scene durations DERIVED from narration durations.json (narration + 10s, min 40s) — never trust hardcoded.
- Media srcs are PROJECT-ROOT-relative ("narration/x.mp3", "assets/beds/y.wav") — compositions/ files
  resolve from project root, NOT the composition's own directory.
- One audio track index per SFX type (narration 10, music 11, whoosh 12, riser 13, boom 14) —
  same-track overlap is a lint error.
- Headlines auto-fit by plain-text length (118/96/80/68px) to avoid 1920x1080 overflow.
- Count-ups use Math.round().toLocaleString("en-IN") for Indian digit grouping.
- Deterministic GSAP: paused timeline, fromTo tweens (no CSS transform conflicts), no repeat:-1.
"""
import json, sys, os, re

SFX_DUR = {"whoosh": 1.8, "riser": 1.6, "boom": 2.5, "tick": 0.08}

CSS = """
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #0a0d12; }
      body { font-family: Georgia, "Times New Roman", serif; color: #f2f0e8; -webkit-font-smoothing: antialiased; }
      #root { position: relative; width: 1920px; height: 1080px; overflow: hidden; background: #0a0d12; }
      .clip { position: absolute; inset: 0; overflow: hidden; }
      .scene { position: absolute; inset: 0; padding: 120px 170px; display: flex; flex-direction: column; justify-content: center; gap: 36px; }
      .eyebrow { font-family: "Segoe UI", system-ui, sans-serif; font-size: 32px; font-weight: 700; letter-spacing: 0.42em; color: #d9a441; text-transform: uppercase; }
      .hl { font-size: 118px; font-weight: 700; letter-spacing: -0.015em; line-height: 1.04; color: #f2f0e8; }
      .hl .red { color: #e5484d; }
      .hl .gold { color: #d9a441; }
      .sub { font-family: "Segoe UI", system-ui, sans-serif; font-size: 40px; font-weight: 400; line-height: 1.4; color: #9aa3b2; max-width: 1500px; }
      .stat-num { font-size: 330px; font-weight: 700; letter-spacing: -0.04em; line-height: 0.9; color: #d9a441; }
      .stat-label { font-size: 74px; font-weight: 700; letter-spacing: 0.01em; color: #f2f0e8; }
      .rule { width: 700px; height: 6px; background: linear-gradient(90deg, #e5484d, #d9a441); transform-origin: left center; }
      .quote-mark { font-size: 200px; line-height: 0.6; color: #e5484d; font-family: Georgia, serif; }
      .quote-text { font-size: 86px; font-weight: 400; line-height: 1.25; max-width: 1500px; color: #f2f0e8; }
      .quote-attr { font-family: "Segoe UI", system-ui, sans-serif; font-size: 34px; font-weight: 600; color: #9aa3b2; letter-spacing: 0.04em; }
      .tl-line { width: 1480px; height: 5px; background: #1c2434; }
      .tl-line .fill { width: 100%; height: 100%; background: linear-gradient(90deg, #e5484d, #d9a441); transform-origin: left center; }
      .tl-nodes { display: flex; justify-content: space-between; width: 1480px; }
      .tl-node { display: flex; flex-direction: column; gap: 18px; width: 300px; }
      .tl-node .dot { width: 26px; height: 26px; border-radius: 50%; background: #e5484d; box-shadow: 0 0 24px rgba(229,72,77,0.55); }
      .tl-node .t { font-family: "Segoe UI", system-ui, sans-serif; font-size: 32px; font-weight: 700; color: #d9a441; letter-spacing: 0.05em; }
      .tl-node .l { font-family: "Segoe UI", system-ui, sans-serif; font-size: 36px; font-weight: 500; color: #f2f0e8; line-height: 1.25; }
      .list-panel { display: flex; flex-direction: column; gap: 26px; width: 1480px; }
      .list-row { display: flex; align-items: center; gap: 30px; padding: 26px 40px; border-radius: 16px; background: #11161f; border-left: 6px solid #e5484d; }
      .list-row .mark { width: 18px; height: 18px; border-radius: 50%; background: #e5484d; flex-shrink: 0; }
      .list-row .txt { font-family: "Segoe UI", system-ui, sans-serif; font-size: 38px; font-weight: 500; color: #eef1f7; }
      .masthead { font-family: "Segoe UI", system-ui, sans-serif; font-size: 34px; font-weight: 700; letter-spacing: 0.5em; color: #6b7484; text-transform: uppercase; }
      .deck { font-family: "Segoe UI", system-ui, sans-serif; font-size: 44px; font-weight: 400; line-height: 1.35; color: #b9c1d0; max-width: 1500px; }
      .credits { font-family: "Segoe UI", system-ui, sans-serif; font-size: 34px; font-weight: 500; color: #6b7484; letter-spacing: 0.08em; }
      .bg-layer { position: absolute; inset: 0; }
"""

def hl_style(text):
    plain = re.sub(r"<[^>]+>", "", text)
    n = len(plain)
    if n <= 22: return ""
    if n <= 30: return ' style="font-size:96px"'
    if n <= 40: return ' style="font-size:80px"'
    return ' style="font-size:68px"'

def scene_html(s, idx):
    sid = s["id"]
    kind = s["kind"]
    parts = [f'      <section id="{sid}" class="clip" data-start="{s["start"]:.2f}" data-duration="{s["dur"]:.2f}" data-track-index="1">', f'        <div class="scene">']
    def el(cls, content, extra=""):
        return f'          <div id="{sid}-{cls}" class="{cls}"{extra}>{content}</div>'
    if kind == "divider":
        parts.append(el("eyebrow", s.get("eyebrow", "")))
        parts.append(el("rule", "", ' style="margin:12px 0"'))
        parts.append(el("hl", s.get("headline", ""), hl_style(s.get("headline", ""))))
        if s.get("sub"): parts.append(el("sub", s["sub"]))
    elif kind == "title":
        parts.append(el("eyebrow", s.get("eyebrow", "")))
        parts.append(el("hl", s.get("headline", ""), hl_style(s.get("headline", ""))))
        if s.get("sub"): parts.append(el("sub", s["sub"]))
    elif kind == "stat":
        parts.append(el("eyebrow", s.get("eyebrow", "")))
        parts.append(el("stat-num", s.get("stat", "0")))
        parts.append(el("stat-label", s.get("statLabel", "")))
        if s.get("sub"): parts.append(el("sub", s["sub"]))
    elif kind == "quote":
        parts.append(el("quote-mark", "“"))
        parts.append(el("quote-text", s.get("quote", "")))
        parts.append(el("quote-attr", s.get("attr", "")))
    elif kind == "timeline":
        parts.append(el("eyebrow", s.get("eyebrow", "")))
        parts.append(el("hl", s.get("headline", ""), hl_style(s.get("headline", ""))))
        parts.append('<div id="%s-tlwrap" style="display:flex;flex-direction:column;gap:44px;width:1480px">' % sid)
        parts.append(f'          <div id="{sid}-tl-line" class="tl-line"><div id="{sid}-tl-fill" class="fill"></div></div>')
        parts.append(f'          <div id="{sid}-tl-nodes" class="tl-nodes">')
        for i, n in enumerate(s.get("nodes", [])):
            parts.append(f'            <div id="{sid}-node{i}" class="tl-node"><span class="dot"></span><span class="t">{n["t"]}</span><span class="l">{n["label"]}</span></div>')
        parts.append('          </div>')
        parts.append('        </div>')
    elif kind == "list":
        parts.append(el("eyebrow", s.get("eyebrow", "")))
        parts.append(el("hl", s.get("headline", ""), hl_style(s.get("headline", ""))))
        parts.append(f'          <div id="{sid}-panel" class="list-panel">')
        for i, item in enumerate(s.get("items", [])):
            parts.append(f'            <div id="{sid}-row{i}" class="list-row"><span class="mark"></span><span class="txt">{item}</span></div>')
        parts.append('          </div>')
    elif kind == "headline":
        parts.append(el("masthead", s.get("masthead", "News Report")))
        parts.append(el("hl", s.get("headline", ""), hl_style(s.get("headline", ""))))
        if s.get("deck"): parts.append(el("deck", s["deck"]))
        if s.get("attr"): parts.append(el("quote-attr", s["attr"]))
    elif kind == "endcard":
        parts.append(el("eyebrow", s.get("eyebrow", "")))
        parts.append(el("hl", s.get("headline", ""), hl_style(s.get("headline", ""))))
        if s.get("sub"): parts.append(el("sub", s["sub"]))
        parts.append(el("credits", s.get("credits", "")))
    parts.append('        </div>')
    parts.append('      </section>')
    return "\n".join(parts)

def scene_tweens(s, out, scene_idx, chapter_len):
    sid = s["id"]; st = s["start"]; k = s["kind"]
    def ent(cls, t, dur=0.6, y=40, ease='"power4.out"', extra=""):
        out.append(f'      tl.fromTo("#{sid}-{cls}", {{ autoAlpha: 0, y: {y} }}, {{ autoAlpha: 1, y: 0, duration: {dur}, ease: {ease} }}, {st+t:.2f});')
    if k == "divider":
        ent("eyebrow", 0.5, y=16)
        out.append(f'      tl.fromTo("#{sid}-rule", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.7, ease: "power3.inOut" }}, {st+0.9:.2f});')
        ent("hl", 1.1, dur=0.7, y=46)
        if s.get("sub"): ent("sub", 1.7, y=18)
    elif k == "title":
        ent("eyebrow", 0.4, y=16)
        ent("hl", 0.7, dur=0.7, y=48)
        if s.get("sub"): ent("sub", 1.3, y=18)
    elif k == "stat":
        ent("eyebrow", 0.4, y=16)
        ent("stat-num", 0.7, dur=0.7, y=60)
        ent("stat-label", 1.25, y=20)
        if s.get("sub"): ent("sub", 1.6, y=18)
        if s.get("count") and s["stat"].replace(".", "", 1).isdigit():
            target = float(s["stat"])
            out.append(f'      const c_{sid.replace("-","_")} = {{ v: 0 }};')
            out.append(f'      tl.to(c_{sid.replace("-","_")}, {{ v: {target}, duration: 1.8, ease: "power2.out", onUpdate: function() {{ document.getElementById("{sid}-stat-num").textContent = Math.round(c_{sid.replace("-","_")}.v).toLocaleString("en-IN"); }} }}, {st+0.85:.2f});')
    elif k == "quote":
        out.append(f'      tl.fromTo("#{sid}-quote-mark", {{ autoAlpha: 0, scale: 0.7 }}, {{ autoAlpha: 1, scale: 1, duration: 0.5, ease: "back.out(1.8)" }}, {st+0.4:.2f});')
        ent("quote-text", 0.8, dur=0.8, y=34)
        ent("quote-attr", 1.6, y=16)
    elif k == "timeline":
        ent("eyebrow", 0.4, y=16)
        ent("hl", 0.7, dur=0.6, y=34)
        out.append(f'      tl.fromTo("#{sid}-tl-fill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 1.0, ease: "power3.inOut" }}, {st+1.3:.2f});')
        for i in range(len(s.get("nodes", []))):
            out.append(f'      tl.fromTo("#{sid}-node{i}", {{ autoAlpha: 0, scale: 0.8 }}, {{ autoAlpha: 1, scale: 1, duration: 0.45, ease: "back.out(2)" }}, {st+1.6+i*0.5:.2f});')
            out.append(f'      tl.fromTo("#{sid}-node{i} .t", {{ autoAlpha: 0, y: 12 }}, {{ autoAlpha: 1, y: 0, duration: 0.4 }}, {st+1.9+i*0.5:.2f});')
            out.append(f'      tl.fromTo("#{sid}-node{i} .l", {{ autoAlpha: 0, y: 12 }}, {{ autoAlpha: 1, y: 0, duration: 0.4 }}, {st+2.1+i*0.5:.2f});')
    elif k == "list":
        ent("eyebrow", 0.4, y=16)
        ent("hl", 0.7, dur=0.6, y=34)
        for i in range(len(s.get("items", []))):
            out.append(f'      tl.fromTo("#{sid}-row{i}", {{ autoAlpha: 0, x: -34 }}, {{ autoAlpha: 1, x: 0, duration: 0.45, ease: "power3.out" }}, {st+1.3+i*0.35:.2f});')
    elif k == "headline":
        ent("masthead", 0.4, y=14)
        ent("hl", 0.8, dur=0.7, y=44)
        if s.get("deck"): ent("deck", 1.5, y=20)
        if s.get("attr"): ent("quote-attr", 1.9, y=14)
    elif k == "endcard":
        out.append(f'      tl.fromTo("#{sid}-hl", {{ autoAlpha: 0, scale: 0.94 }}, {{ autoAlpha: 1, scale: 1, duration: 0.8, ease: "power3.out" }}, {st+0.5:.2f});')
        if s.get("sub"): ent("sub", 1.2, y=20)
        ent("credits", 1.6, y=16)
    ex = st + s["dur"] - 0.7
    out.append(f'      tl.fromTo("#{sid} .scene", {{ autoAlpha: 1 }}, {{ autoAlpha: 0, y: -22, duration: 0.6, ease: "power2.in" }}, {ex:.2f});')

def build(spec_path, out_path, audio_dir):
    spec = json.load(open(spec_path, encoding="utf-8"))
    audio_dir = os.path.abspath(audio_dir)
    durs = json.load(open(os.path.join(audio_dir, "durations.json"), encoding="utf-8")) if os.path.exists(os.path.join(audio_dir, "durations.json")) else {}
    # scene durations DERIVED from narration (never trust hardcoded dur)
    t = 0.0
    for s in spec["scenes"]:
        s["start"] = t
        if s.get("narration") and s["narration"] in durs:
            s["dur"] = max(40.0, durs[s["narration"]] + 10.0)
        else:
            s["dur"] = max(40.0, s.get("dur", 45.0))
        t += s["dur"]
    chapter_len = t

    scenes_html = "\n".join(scene_html(s, i) for i, s in enumerate(spec["scenes"]))
    tweens = []
    for i, s in enumerate(spec["scenes"]):
        scene_tweens(s, tweens, i, chapter_len)

    # audio: narration per scene (srcs PROJECT-ROOT-relative)
    audio_html = []
    for s in spec["scenes"]:
        nid = s.get("narration")
        if not nid or nid not in durs: continue
        a = s["start"] + 0.4
        audio_html.append(f'      <audio id="nar-{nid}" src="narration/{nid}.mp3" data-start="{a:.2f}" data-duration="{durs[nid]+0.5:.2f}" data-track-index="10" data-volume="1"></audio>')
    audio_html.append(f'      <audio id="music" src="assets/beds/{spec["music"]}.wav" data-start="0" data-duration="{chapter_len:.2f}" data-track-index="11" data-volume="0.22"></audio>')
    for s in spec["scenes"]:
        if s.get("boom"):
            audio_html.append(f'      <audio id="sfx-boom-{s["id"]}" src="assets/boom.wav" data-start="{s["start"]+0.7:.2f}" data-duration="2.5" data-track-index="14" data-volume="0.85"></audio>')
    for i, s in enumerate(spec["scenes"]):
        if i == 0 and s.get("riser"):
            audio_html.append(f'      <audio id="sfx-riser-{s["id"]}" src="assets/riser.wav" data-start="{s["start"]:.2f}" data-duration="1.6" data-track-index="13" data-volume="0.7"></audio>')
        if i > 0:
            audio_html.append(f'      <audio id="sfx-whoosh-{s["id"]}" src="assets/whoosh.wav" data-start="{s["start"]-0.15:.2f}" data-duration="1.8" data-track-index="12" data-volume="0.55"></audio>')

    music_fade = chapter_len - 3.0
    script = "\n".join(tweens)
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>{spec["title"]}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
{CSS}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="{spec["id"]}" data-start="0" data-duration="{chapter_len:.2f}" data-width="1920" data-height="1080">
      <div id="bg" class="clip" data-start="0" data-duration="{chapter_len:.2f}" data-track-index="0">
        <div class="bg-layer" style="background:radial-gradient(1100px 700px at 72% 18%, rgba(229,72,77,0.13), transparent 60%), radial-gradient(900px 600px at 18% 85%, rgba(217,164,65,0.06), transparent 55%), #0a0d12;"></div>
        <div class="bg-layer" style="background-image:linear-gradient(rgba(140,155,190,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(140,155,190,0.045) 1px, transparent 1px); background-size:110px 110px;"></div>
        <div class="bg-layer" style="background:radial-gradient(1500px 950px at 50% 50%, transparent 58%, rgba(0,0,0,0.5) 100%);"></div>
      </div>
{scenes_html}
{chr(10).join(audio_html)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
{script}
      tl.fromTo("#music", {{ volume: 0.0 }}, {{ volume: 0.22, duration: 2.0 }}, 0.2);
      tl.fromTo("#music", {{ volume: 0.22 }}, {{ volume: 0.0, duration: 2.8 }}, {music_fade:.2f});
      window.__timelines["{spec["id"]}"] = tl;
    </script>
  </body>
</html>
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[ok] {out_path} — {len(spec['scenes'])} scenes, {chapter_len:.0f}s ({chapter_len/60:.1f} min)")

if __name__ == "__main__":
    spec = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join("compositions", os.path.basename(spec).replace(".json", ".html"))
    audio = sys.argv[3] if len(sys.argv) > 3 else "narration"
    build(spec, out, audio)
