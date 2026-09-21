"""Telegram universal remote (W11 hands): status + approved-act execution.

Upstream owns the wire (gateway adapter, inline buttons); W8 owns the queue
(jarvis.permissions.telegram: request/decide/pending/status). This overlay
owns the remote policy:

- status(): configured vs honest-absent (bot token lives upstream-side;
  none expected until the operator provides one).
- act(summary): remote acts are L2 by policy — files a W8 approval request
  (owner taps inline approve/deny), returns the sendable payload. When the
  token is absent the request is still queued (auditable intent) but flagged
  sendable False: nothing can be delivered until the operator configures
  the channel. Sending itself stays upstream-side, always.
- pending(): open remote requests oldest-first (W8 queue).
"""

from __future__ import annotations

from typing import Any, Dict, List

from jarvis.permissions import freeze as _freeze
from jarvis.permissions import telegram as _tg

from ._common import state_home


def status() -> Dict[str, Any]:
    st = _tg.status(home=state_home())
    return {"hand": "telegram-remote", **st,
            "capabilities": ["status reads (L0)", "approved-act execution (L2)",
                             "inline approve/deny (W8 queue)"]}


def act(summary: str, request_id: str) -> Dict[str, Any]:
    """File a remote-act approval request (L2, owner taps inline)."""
    summary = (summary or "").strip()
    request_id = (request_id or "").strip()
    if not summary or not request_id:
        return {"ok": False, "reason": "summary and request_id must be non-empty"}
    gate = _freeze.gate("L2", home=state_home())
    if not gate["allowed"]:
        return {"ok": False, "reason": "frozen", "detail": gate["reason"]}
    try:
        payload = _tg.request(summary, "L2", request_id, home=state_home())
    except ValueError as e:
        return {"ok": False, "reason": "bad_request", "detail": str(e)}
    st = _tg.status(home=state_home())
    sendable = st.get("state") == "configured"
    return {"ok": True, "hand": "telegram-remote", "level": "L2",
            "confirm": "inline approve/deny (owner tap)",
            "payload": payload,
            "sendable": sendable,
            "delivery": ("upstream gateway sends on approve" if sendable
                         else "honest-absent: queued but undeliverable until a bot token is configured"),
            "auto_approve": False}


def pending() -> List[Dict[str, Any]]:
    return _tg.pending(home=state_home())
