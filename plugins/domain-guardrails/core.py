"""domain-guardrails core — per-domain approval policies.

Trading analysis is OK; trading EXECUTION requires explicit approval.
Money/medical/legal/crypto: analysis OK, execution requires approval.
Code-exec and unknown domains: conservative warn.
Pure stdlib. Zero hooks.
"""
from __future__ import annotations

# ------------------------------------------------------------------ policies
# action classes: "analysis" (read-only) and "execution" (mutating)
# policy values: allow | warn | block-approval
DOMAIN_POLICIES: dict[str, dict[str, str]] = {
    "trading":  {"analysis": "allow", "execution": "block-approval",
                 "description": "Orders, positions, leverage, entries/exits"},
    "money":    {"analysis": "allow", "execution": "block-approval",
                 "description": "Transfers, payments, UPI, receipts, refunds"},
    "medical":  {"analysis": "warn", "execution": "block-approval",
                 "description": "Prescriptions, doses, diagnoses, treatment"},
    "legal":    {"analysis": "warn", "execution": "block-approval",
                 "description": "Contracts, clauses, liability, agreements"},
    "crypto":   {"analysis": "allow", "execution": "block-approval",
                 "description": "Swaps, stakes, bridges, private keys, wallets"},
    "code-exec": {"analysis": "allow", "execution": "warn",
                  "description": "Shell, exec, install, deploy, scripts"},
    "unknown":  {"analysis": "allow", "execution": "warn",
                 "description": "No domain matched — conservative"},
}

# stack defaults: a trading stack keeps the base trading policy unless
# explicitly overridden here.
STACK_POLICIES: dict[str, dict[str, dict[str, str]]] = {
    "trading-stack": {"trading": {"analysis": "allow", "execution": "block-approval"}},
}

DOMAIN_PATTERNS: dict[str, tuple[str, ...]] = {
    "trading": ("buy", "sell", "order", "position", "leverage", "trade", "entry",
                "stop-loss", "take-profit", "margin", "broker", "ticker",
                "stock", "price", "quote", "equity", "portfolio"),
    "money":   ("transfer", "pay", "withdraw", "upi", "receipt", "payment",
                "refund", "invoice", "balance transfer", "send money"),
    "medical": ("prescribe", "dose", "patient", "diagnos", "treatment", "surgery",
                "medication", "clinical"),
    "legal":   ("contract", "clause", "liability", "sue", "agreement", "terms",
                "jurisdiction", "non-compete"),
    "crypto":  ("swap", "stake", "bridge", "private key", "seed phrase", "wallet",
                "token transfer", "defi"),
    "code-exec": ("exec", "run ", "shell", "subprocess", "script", "install ",
                  "deploy", "compile", "pip install", "npm i"),
}

EXEC_PATTERNS: tuple[str, ...] = (
    "place", "execute", "transfer", "send", "delete", "write", "deploy",
    "install", "buy", "sell", "order", "move", "pay", "submit", "push",
    "commit", "swap", "withdraw", "update", "start", "stop", "kill",
)

READ_PATTERNS: tuple[str, ...] = (
    "fetch", "query", "analy", "report", "get", "list", "read", "check",
    "summar", "review", "explain", "status", "search", "show",
)


def classify_domain(text: str) -> str:
    t = (text or "").lower()
    for domain in ("trading", "money", "medical", "legal", "crypto", "code-exec"):
        if any(p in t for p in DOMAIN_PATTERNS[domain]):
            return domain
    return "unknown"


def action_class(text: str) -> str:
    t = (text or "").lower()
    if any(p in t for p in EXEC_PATTERNS):
        return "execution"
    if any(p in t for p in READ_PATTERNS):
        return "analysis"
    return "analysis"  # unmarked requests default to analysis (read-only)


def decide(text: str, stack: str | None = None) -> dict:
    domain = classify_domain(text)
    action = action_class(text)
    policies = DOMAIN_POLICIES
    if stack and stack in STACK_POLICIES:
        merged = {d: dict(v) for d, v in DOMAIN_POLICIES.items()}
        merged.update(STACK_POLICIES[stack])
        policies = merged
    policy = policies[domain][action]
    return {
        "domain": domain,
        "action": action,
        "policy": policy,
        "allowed": policy in ("allow", "warn"),
        "requires_approval": policy == "block-approval",
        "reason": f"{domain}/{action}: {policy}"
                  + ("" if domain != "unknown" else " (no domain matched — conservative)"),
    }


# skill-install policies: loading a skill grants its capabilities (execution),
# but installation alone is lighter-touch than a live command — warn by default,
# block-approval only for domains with real harm potential (medical).
SKILL_POLICIES: dict[str, str] = {
    "trading": "warn",
    "money": "warn",
    "medical": "block-approval",
    "legal": "warn",
    "crypto": "warn",
    "code-exec": "warn",
    "unknown": "warn",
}


def decide_tool(tool_name: str, tool_description: str = "") -> dict:
    """Verdict for an MCP tool — domain/action classified from name+description."""
    text = f"{tool_name or ''} {tool_description or ''}".strip()
    verdict = decide(text)
    verdict["reason"] = f"tool: {verdict['reason']}"
    return verdict


def decide_skill(frontmatter_text: str) -> dict:
    """Verdict for a skill install — action is always execution (loading capability)."""
    domain = classify_domain(frontmatter_text or "")
    policy = SKILL_POLICIES[domain]
    return {
        "domain": domain,
        "action": "execution",
        "policy": policy,
        "allowed": policy in ("allow", "warn"),
        "requires_approval": policy == "block-approval",
        "reason": f"skill install: {domain}/execution: {policy}"
                  + ("" if domain != "unknown" else " (no domain matched — conservative)"),
    }


def policy_table() -> str:
    lines = ["DOMAIN GUARDRAILS — policy table",
             f"  {'domain':<12} {'analysis':<18} execution"]
    for d, pol in DOMAIN_POLICIES.items():
        lines.append(f"  {d:<12} {pol['analysis']:<18} {pol['execution']}")
    lines.append("block-approval = allowed only after explicit human approval.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        v = decide(" ".join(sys.argv[1:]))
        for k, val in v.items():
            print(f"{k}: {val}")
    else:
        print(policy_table())
