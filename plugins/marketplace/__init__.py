"""XOMNI self-hosted marketplace plugin (Monetization V2, M2).

Skill/MCP/plugin catalog with the 15% rails take-rate + UPI payout math,
publish/install/search operations, and verifiable sha256 receipts.

Zero hooks (new-plugin rule) and pure stdlib — nothing runs on the agent hot
path; everything is called explicitly by a host command or tool.
"""
from .core import (
    CATALOG_PATH,
    STATE_DIR,
    load_catalog,
    save_catalog,
    search,
    publish,
    install,
    sales_ledger,
    rails_report,
    verify_receipt,
)

__version__ = "0.1.0"

__all__ = [
    "CATALOG_PATH",
    "STATE_DIR",
    "load_catalog",
    "save_catalog",
    "search",
    "publish",
    "install",
    "sales_ledger",
    "rails_report",
    "verify_receipt",
]
