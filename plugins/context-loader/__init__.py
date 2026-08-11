"""Context Loader — aider-style context injection (web pages + images).

Model tools:
  fetch_page(url)       — fetch a web page and return clean readable text
                          (toolset "web")
  describe_image(path)  — describe a local jpg/png via the opencode vision
                          gateway, model minimax-m3 (toolset "file")
Slash commands:
  /fetch <url>          — interactive fetch of a web page
  /describe <path>      — interactive image description
"""
from __future__ import annotations

import os

from . import core

_CTX = None

HELP_FETCH = "usage: /fetch <url> — fetch a web page (http/https) and return its text"
HELP_DESCRIBE = "usage: /describe <image path> — describe a local image (.jpg/.jpeg/.png)"
_KEY_HINT = (
    "OPENCODE_GO_API_KEY not found in ~/AppData/Local/hermes/.env — "
    "set it to enable the vision gateway"
)


def _fetch_page_tool(params: dict) -> str:
    url = (params.get("url") or "").strip()
    if not url:
        return "fetch_page: missing required argument 'url'"
    return core.fetch_page(url)


def _describe_image_tool(params: dict) -> str:
    path = os.path.expanduser((params.get("path") or "").strip())
    if not path:
        return "describe_image: missing required argument 'path'"
    try:
        data_url = core.image_to_data_url(path)
    except ValueError as exc:
        return f"describe_image: {exc}"
    key = core.load_key()
    if not key:
        return f"describe_image: {_KEY_HINT}"
    return core.vision_describe(data_url, key)


def _handle_fetch(raw: str) -> str:
    url = (raw or "").strip()
    if not url:
        return HELP_FETCH
    return core.fetch_page(url)


def _handle_describe(raw: str) -> str:
    path = os.path.expanduser((raw or "").strip())
    if not path:
        return HELP_DESCRIBE
    try:
        data_url = core.image_to_data_url(path)
    except ValueError as exc:
        return f"/describe: {exc}"
    key = core.load_key()
    if not key:
        return f"/describe: {_KEY_HINT}"
    return core.vision_describe(data_url, key)


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_tool(
        "fetch_page",
        toolset="web",
        schema={
            "description": (
                "Fetch a web page (http/https) and return its content as clean, "
                "readable text — title, headings (h1-h3) and links preserved, "
                "scripts/styles stripped, 512KB cap, 20s timeout. Returns an "
                "error string for non-200 responses or unsupported schemes. "
                "Use this to pull documentation, articles or specs into context."
            ),
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "absolute http(s) URL of the page to fetch"},
            },
            "required": ["url"],
        },
        handler=_fetch_page_tool,
        description="Fetch a web page as clean readable text (aider-style context)",
        emoji="🌐",
    )
    ctx.register_tool(
        "describe_image",
        toolset="file",
        schema={
            "description": (
                "Read a local image (.jpg/.jpeg/.png, up to ~4MB) and return a "
                "detailed description produced by the vision model (minimax-m3 "
                "via the opencode Zen gateway). Requires OPENCODE_GO_API_KEY in "
                "~/AppData/Local/hermes/.env. Returns an error string if the "
                "gateway is unreachable."
            ),
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "absolute or relative path to the image file"},
            },
            "required": ["path"],
        },
        handler=_describe_image_tool,
        description="Describe a local image with the vision model (aider-style context)",
        emoji="🖼️",
    )
    ctx.register_command(
        "fetch", handler=_handle_fetch,
        description="Fetch a web page (http/https) and show it as clean readable text",
        args_hint="<url>",
    )
    ctx.register_command(
        "describe", handler=_handle_describe,
        description="Describe a local image (.jpg/.jpeg/.png) with the vision model",
        args_hint="<image path>",
    )
