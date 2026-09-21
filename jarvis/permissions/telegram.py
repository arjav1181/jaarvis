"""W8 Telegram inline approve/deny — payload builders + pending queue.

Upstream already renders inline approval buttons (see
tests/gateway/test_telegram_approval_buttons.py); this overlay owns the
Jarvis side: request framing, callback payloads namespaced
``jarvis:approve:<id>`` / ``jarvis:deny:<id>``, and a pending queue at
<home>/jarvis/pending.json. Sending itself stays upstream-side (needs a bot
token); status() reports configured vs honest-absent.
"""

from __future__ import annotations

import re
from pathlib import Path

from ._common import jarvis_dir, read_json, utc_now, write_json

STORE = "pending.json"
APPROVE_RE = re.compile(r"^jarvis:approve:([A-Za-z0-9_-]{1,64})$")
DENY_RE = re.compile(r"^jarvis:deny:([A-Za-z0-9_-]{1,64})$")


def _load(home) -> dict:
    data = read_json(Path(home) / STORE, None)
    return data if isinstance(data, dict) else {"pending": {}}


def _save(home, data) -> None:
    write_json(Path(home) / STORE, data)


def request(summary: str, level: str, request_id: str,
            home: Path | str | None = None) -> dict:
    """Queue an approval request; returns the sendable payload
    {text, approve_data, deny_data} (upstream adapter renders the buttons)."""
    home = jarvis_dir(home)
    summary = (summary or "").strip()
    request_id = (request_id or "").strip()
    if not summary or not request_id:
        raise ValueError("summary and request_id must be non-empty")
    if level not in ("L0", "L1", "L2"):
        raise ValueError(f"unknown level {level!r}")
    data = _load(home)
    data["pending"][request_id] = {"summary": summary, "level": level,
                                   "status": "open", "created": utc_now()}
    _save(home, data)
    return {"text": f"[{level}] Approve?\n{summary}",
            "approve_data": f"jarvis:approve:{request_id}",
            "deny_data": f"jarvis:deny:{request_id}"}


def parse_callback(callback_data: str) -> dict | None:
    """Parse an inline-button callback. None when not a Jarvis payload."""
    data = (callback_data or "").strip()
    m = APPROVE_RE.match(data)
    if m:
        return {"decision": "approve", "request_id": m.group(1)}
    m = DENY_RE.match(data)
    if m:
        return {"decision": "deny", "request_id": m.group(1)}
    return None


def decide(request_id: str, approve: bool, by: str = "owner",
           home: Path | str | None = None) -> dict:
    """Settle a pending request (owner taps inline). Unknown id raises."""
    from . import audit as _audit
    home = jarvis_dir(home)
    data = _load(home)
    item = data["pending"].get(request_id)
    if item is None or item.get("status") != "open":
        raise KeyError(f"no open request {request_id!r}")
    item["status"] = "approved" if approve else "denied"
    item["decided_by"] = by
    item["decided"] = utc_now()
    _save(home, data)
    _audit.log({"actor": f"telegram:{by}", "action": f"approve-request {request_id}",
                "decision": "allowed" if approve else "denied",
                "detail": item["summary"][:200]}, home=home)
    return item


def pending(home: Path | str | None = None) -> list[dict]:
    """Open requests oldest-first."""
    data = _load(jarvis_dir(home))
    return [{"id": rid, **item} for rid, item in data["pending"].items()
            if item.get("status") == "open"]


def status(home: Path | str | None = None) -> dict:
    """configured (bot token present in config) vs honest-absent."""
    token = ""
    try:
        from hermes_cli.config import load_config
        config = load_config() or {}
        platforms = config.get("platforms") or config.get("messaging") or {}
        tg = platforms.get("telegram") or {}
        token = str(tg.get("token") or tg.get("bot_token") or "")
    except Exception:
        token = ""
    if token and len(token) > 8:
        return {"channel": "telegram", "state": "configured",
                "open": len(pending(home))}
    return {"channel": "telegram", "state": "absent",
            "reason": "no Telegram bot token configured", "open": len(pending(home))}
