# Agent-Reach setup (this host, Aug 2026)

Session detail for the Agent-Reach channel stack install. Complements the
Camofox setup in `camofox-hermes-setup.md`.

## Install path used

```bash
# Dedicated venv (never Hermes' venv). Native path required on this host.
python -m venv "C:/Users/HP/.agent-reach-venv"
"C:/Users/HP/.agent-reach-venv/Scripts/python.exe" -m pip install \
  https://github.com/Panniantong/agent-reach/archive/main.zip
# pipx lives in the venv too (needed for bili-cli / twitter-cli):
"C:/Users/HP/.agent-reach-venv/Scripts/python.exe" -m pip install pipx
export PATH="$HOME/.local/bin:$PATH"   # pipx exes land here on Windows
pipx install bilibili-cli   # bili.exe -> ~/.local/bin
pipx install twitter-cli    # twitter.exe -> ~/.local/bin
```

Agent-reach auto-installs its skill for both agents:
`~/.agents/skills/agent-reach` (Hermes) and `~/.openclaw/skills/agent-reach`
(OpenClaw). Do not hand-write those; the installer manages them.

## Channel status after `install --system --channels=all` (5/15 verified live)

Working without user action:
- YouTube (yt-dlp + `--js-runtimes node` config auto-applied)
- V2EX (public API)
- RSS/Atom
- Any webpage via Jina Reader (`curl https://r.jina.ai/URL`)
- Bilibili search/hot/rank/video detail via bili-cli (no login). NOTE:
  bili-cli search returns empty for English queries — use Chinese terms
  (e.g. `bili search "物理"` works, `bili search "physics class 10"` → empty).

Installed but needs USER credentials (never do these yourself — ask):
- Twitter/X: `agent-reach configure twitter-cookies`
- Xiaohongshu: `agent-reach configure xhs-cookies`
- Xueqiu (stocks): `agent-reach configure --from-browser chrome --platform xueqiu`
- OpenCLI backend (Reddit/Facebook/Instagram/Xiaohongshu): user installs the
  Chrome extension (chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk),
  keeps the browser logged in; daemon auto-starts on first use.
- Xiaoyuzhou podcast transcription: needs free Groq API key
  (console.groq.com) via `agent-reach configure groq-key`.

Half-verified: Exa semantic search (mcporter config written, but doctor won't
claim it without a live remote call); GitHub (gh CLI present + auth config
detected, not runtime-verified).

## Useful commands

```bash
agent-reach install --env=auto                       # read-only health check
agent-reach install --system --channels=all          # full install
agent-reach configure groq-key                       # hidden input
# Doctor status legend: green=verified live, [!]=needs login/key, [X]=missing
```

## Tested smoke tests

- `curl -s "https://r.jina.ai/https://example.com"` → clean markdown (Title,
  URL Source, body). Verified.
- `bili hot` → trending list. Verified. `bili search "物理"` → results.
- `bili search "physics class 10"` → empty (English query limitation).

## OpenCLI extension wiring (verified working, Aug 2026)

OpenCLI 1.8.6 ships 163 site adapters (reddit, facebook, instagram,
xiaohongshu, xueqiu, twitter, bilibili, youtube, ...). The Chrome extension
bridges the daemon to the user's real browser session (reuses their logins,
never reads passwords).

Opening the extension page from git-bash on Windows:
- `cmd //c start URL`, `start "" URL`, `explorer.exe URL` → all no-op/fail
- `python -c "import webbrowser; webbrowser.open(URL)"` → returns success but
  nothing appears
- RELIABLE: invoke Chrome directly:
  `"/c/Program Files/Google/Chrome/Application/chrome.exe" "URL"` (exit 0,
  tab opens)

After the user installs the extension and keeps Chrome open, verify:
```bash
opencli doctor   # → [OK] Daemon running on port 19825, [OK] Extension connected
                 #   (v1.0.22), profile listed, "Everything looks good!"
```
Then smoke-test through the real session:
- `opencli reddit popular --limit 3` → posts with score/comments (no API key, no 403)
- `opencli reddit search "icse class 10"` → real search results
- `opencli facebook whoami` → `AUTH_REQUIRED: c_user cookie missing` until the
  user logs into facebook.com in Chrome (same for Instagram/XHS)
- `opencli xiaohongshu search ...` → may `TIMEOUT` after 60s (site slow or
  needs login; retry with `--timeout <seconds>` or `OPENCLI_BROWSER_COMMAND_TIMEOUT`)

Decide per-platform whether logins are worth asking for: Reddit + YouTube +
Bilibili + Jina + Exa covers most research needs without any social logins;
FB/IG/XHS matter mainly if the user's own business uses them (distribution),
which is the user's domain, not the scraper's.
