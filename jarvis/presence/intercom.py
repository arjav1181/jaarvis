"""W9 intercom intent parsing — 'tell the kitchen …' → room route. Stdlib only."""
import re

from .store import slug_room

_PATTERNS = (
    re.compile(r"^\s*(tell|message|ping|say to|announce to|broadcast to)\s+(?:the\s+)?(.+?)\s*[:,\-–—]\s*(.+)$", re.I | re.S),
    re.compile(r"^\s*(say|announce|broadcast)\s+in\s+(?:the\s+)?(.+?)\s*[:,\-–—]\s*(.+)$", re.I | re.S),
)
_ALL_RE = re.compile(r"^\s*(announce|broadcast|say)\s+to\s+all\s*[:,\-–—]\s*(.+)$", re.I | re.S)


def parse(text):
    """→ {kind: room|all|none, room, body} — never raises."""
    t = str(text or "")
    m = _ALL_RE.match(t)
    if m:
        return {"kind": "all", "room": "", "body": m.group(2).strip()}
    for pat in _PATTERNS:
        m = pat.match(t)
        if m:
            room = slug_room(m.group(2))
            body = m.group(3).strip()
            if room and body:
                return {"kind": "room", "room": room, "body": body}
    return {"kind": "none", "room": "", "body": t.strip()}
