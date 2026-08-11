"""Context Loader — aider-style context injection: web pages + images as context.

Pure stdlib, no Hermes imports. Unit-testable in isolation.

- fetch_page(url)        -> clean readable text of a web page (title, h1-h3,
                            links kept; script/style stripped; 512KB cap; 20s
                            timeout; browser User-Agent)
- image_to_data_url(...) -> base64 data URL of a local jpg/png (<= 4MB)
- vision_describe(...)   -> description of an image via the opencode Zen gateway
                            (model minimax-m3), browser User-Agent required
                            (403 error code 1010 without it)
- load_key()             -> OPENCODE_GO_API_KEY from ~/AppData/Local/hermes/.env
"""
from __future__ import annotations

import base64
import html as html_mod
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"
DEFAULT_TIMEOUT = 20
MAX_PAGE_BYTES = 512 * 1024  # 512KB response cap
DEFAULT_MAX_IMAGE_BYTES = 4 * 1024 * 1024  # ~4MB
VISION_URL = "https://opencode.ai/zen/go/v1/chat/completions"
VISION_MODEL = "minimax-m3"
VISION_TIMEOUT = 90
VISION_MAX_TOKENS = 900
VISION_PROMPT = (
    "Describe this image in detail: its subject, any visible text, people, "
    "objects, setting, and anything else notable."
)
ENV_PATH = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes", ".env")

# ---------------------------------------------------------------------------
# HTML -> text (small regex-based converter)
# ---------------------------------------------------------------------------

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.I | re.S)
_SKIP_RE = re.compile(r"<(script|style|noscript|template)\b[^>]*>.*?</\1\s*>", re.I | re.S)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_LINK_RE = re.compile(r"<a\b[^>]*href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a\s*>", re.I | re.S)
_HEADING_RE = re.compile(r"<h([1-3])\b[^>]*>(.*?)</h\1\s*>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_PUNCT_RE = re.compile(r"\s+([,.;:!?%])")


def _clean_fragment(fragment: str) -> str:
    """Strip inner tags from a captured fragment and collapse whitespace."""
    text = _TAG_RE.sub(" ", fragment)
    text = html_mod.unescape(re.sub(r"\s+", " ", text)).strip()
    return _PUNCT_RE.sub(r"\1", text)


def html_to_text(html: str | None) -> str:
    """Convert an HTML document to clean, readable text.

    Keeps the <title> (as a leading "Title:" line), <h1>-<h3> headings (as
    # / ## / ### lines) and links (as [text](href)); strips script/style/
    noscript/template blocks, comments and tags; collapses whitespace and
    drops blank lines. Unsafe links (javascript:/data:/vbscript:) are reduced
    to their anchor text.
    """
    if not html:
        return ""
    title = ""
    m = _TITLE_RE.search(html)
    if m:
        title = _clean_fragment(m.group(1))
    body = _SKIP_RE.sub(" ", html)
    body = _COMMENT_RE.sub(" ", body)

    def _link(match) -> str:
        href = html_mod.unescape(match.group(1).strip())
        text = _clean_fragment(match.group(2))
        low = href.lower()
        if not href or low.startswith(("javascript:", "data:", "vbscript:")):
            return text  # drop unsafe/empty links, keep the anchor text
        return f"[{text}]({href})"

    body = _LINK_RE.sub(_link, body)

    def _heading(match) -> str:
        level = int(match.group(1))
        text = _clean_fragment(match.group(2))
        return f"\n{'#' * level} {text}\n"

    body = _HEADING_RE.sub(_heading, body)
    body = html_mod.unescape(_TAG_RE.sub(" ", body))

    lines = []
    for raw in body.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        line = _PUNCT_RE.sub(r"\1", line)
        if line:
            lines.append(line)
    out = "\n".join(lines)
    if title:
        out = f"Title: {title}\n\n{out}" if out else f"Title: {title}"
    return out


# ---------------------------------------------------------------------------
# Web page fetching
# ---------------------------------------------------------------------------

def fetch_page(url: str, timeout: int = DEFAULT_TIMEOUT, max_bytes: int = MAX_PAGE_BYTES) -> str:
    """Fetch a web page and return clean readable text (or an error string).

    Only http/https URLs are accepted. Responses are read with a browser
    User-Agent, capped at ``max_bytes`` (512KB default), decoded using the
    response charset (utf-8 fallback) and converted by :func:`html_to_text`.
    Failures return a string starting with "fetch_page:".
    """
    url = (url or "").strip()
    if not url:
        return "fetch_page: no URL given"
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        return f"fetch_page: unsupported URL scheme {scheme!r} for {url!r} (only http/https allowed)"
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if status != 200:
                return f"fetch_page: HTTP {status} for {url}"
            raw = resp.read(max_bytes + 1)
            truncated = len(raw) > max_bytes
            data = raw[:max_bytes]
            charset = None
            try:
                charset = resp.headers.get_content_charset()
            except AttributeError:
                pass
            if not charset:
                charset = "utf-8"
            html = data.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        return f"fetch_page: HTTP error {exc.code} for {url}"
    except urllib.error.URLError as exc:
        return f"fetch_page: network error for {url}: {exc.reason}"
    except OSError as exc:
        return f"fetch_page: request failed for {url}: {exc}"
    text = html_to_text(html)
    note = f" [truncated at {max_bytes} bytes]" if truncated else ""
    return f"URL: {url}{note}\n\n{text}"


# ---------------------------------------------------------------------------
# Local image -> base64 data URL
# ---------------------------------------------------------------------------

_MIME_BY_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def image_to_data_url(path: str, max_bytes: int = DEFAULT_MAX_IMAGE_BYTES) -> str:
    """Read a local image (jpg/jpeg/png, <= max_bytes) as a base64 data URL.

    Raises ValueError with a clear message for missing files, unsupported
    extensions, or files over the size cap.
    """
    path = (path or "").strip()
    if not path:
        raise ValueError("no image path given")
    if not os.path.isfile(path):
        raise ValueError(f"no such file: {path}")
    ext = os.path.splitext(path)[1].lower()
    mime = _MIME_BY_EXT.get(ext)
    if mime is None:
        raise ValueError(f"unsupported image type {ext!r} (use .jpg, .jpeg or .png): {path}")
    size = os.path.getsize(path)
    if size > max_bytes:
        raise ValueError(f"image too large: {size} bytes exceeds the {max_bytes}-byte limit: {path}")
    with open(path, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


# ---------------------------------------------------------------------------
# Vision gateway (opencode Zen, model minimax-m3)
# ---------------------------------------------------------------------------

def vision_describe(data_url: str, key: str, timeout: int = VISION_TIMEOUT) -> str:
    """Send an image data URL to the opencode Zen vision gateway.

    Returns the model's description, or an error string starting with
    "vision:". The browser User-Agent is mandatory (the gateway answers 403
    with error code 1010 when it is missing).
    """
    if not key:
        return "vision: no API key provided (OPENCODE_GO_API_KEY missing)"
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": VISION_MAX_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": BROWSER_UA,
    }
    req = urllib.request.Request(
        VISION_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
            detail = f" ({body[:200]})" if body else ""
        except Exception:
            pass
        return f"vision: gateway HTTP error {exc.code} for {VISION_URL}{detail}"
    except urllib.error.URLError as exc:
        return f"vision: gateway unreachable ({exc.reason}) — is opencode.ai reachable?"
    except OSError as exc:
        return f"vision: gateway unreachable ({exc}) — is opencode.ai reachable?"
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return f"vision: unexpected gateway response: {exc}"
    if not content or not str(content).strip():
        return "vision: the model returned an empty description."
    return str(content).strip()


# ---------------------------------------------------------------------------
# API key loading
# ---------------------------------------------------------------------------

def load_key(env_path: str = ENV_PATH) -> str | None:
    """Read OPENCODE_GO_API_KEY from a .env file (default: ~/AppData/Local/hermes/.env).

    Returns the key value, or None when the file or the key is missing. The
    key is never logged or printed by this plugin.
    """
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key_name, _, value = line.partition("=")
                if key_name.strip() == "OPENCODE_GO_API_KEY":
                    val = value.strip().strip("\"'").strip()
                    if val:
                        return val
    except (FileNotFoundError, OSError):
        pass
    return None
