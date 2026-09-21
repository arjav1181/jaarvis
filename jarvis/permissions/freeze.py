"""W8 freeze + break-glass + House Party Protocol.

freeze(reason) drops the house into a safe state: L1/L2 actions are denied
at the gate, L0 read-only texture continues. unfreeze() is the normal path
(owner typed gesture); break_glass() is the emergency path (owner + voice
PIN when a PIN exists) and logs loudly to the audit ledger. house_party()
is the one-word emergency: freeze + silence proactivity + alert summary.

State: <home>/jarvis/FROZEN.json {reason, at, by}. Absent file = unfrozen.
"""

from __future__ import annotations

from pathlib import Path

from . import audit as _audit
from . import voice_pin as _pin
from ._common import jarvis_dir, read_json, utc_now, write_json

STORE = "FROZEN.json"
BREAK_GLASS_PHRASE = "BREAK GLASS"


def status(home: Path | str | None = None) -> dict:
    """{frozen, reason, at, by} — frozen False when no flag file."""
    home = jarvis_dir(home)
    data = read_json(Path(home) / STORE, None)
    if not isinstance(data, dict) or not data.get("reason"):
        return {"frozen": False, "reason": None, "at": None, "by": None}
    return {"frozen": True, "reason": data.get("reason"),
            "at": data.get("at"), "by": data.get("by")}


def freeze(reason: str, by: str = "owner",
           home: Path | str | None = None) -> dict:
    """Freeze the house. Idempotent — re-freezing refreshes the record."""
    home = jarvis_dir(home)
    reason = (reason or "").strip() or "unspecified"
    record = {"reason": reason, "at": utc_now(), "by": by}
    write_json(Path(home) / STORE, record)
    _audit.log({"actor": by, "action": "freeze", "decision": "enforced",
                "detail": reason}, home=home)
    return {"frozen": True, **record}


def gate(level: str, home: Path | str | None = None) -> dict:
    """Gate one level while frozen: L1/L2 denied, L0 allowed. Unfrozen: allowed."""
    state = status(home)
    if not state["frozen"]:
        return {"allowed": True, "reason": "not frozen"}
    if level in ("L1", "L2"):
        return {"allowed": False,
                "reason": f"frozen ({state['reason']}) — {level} denied until thaw"}
    return {"allowed": True, "reason": "frozen — L0 texture continues"}


def unfreeze(gesture: str, home: Path | str | None = None) -> dict:
    """Normal thaw: the owner types THAW. Wrong gesture changes nothing."""
    home = jarvis_dir(home)
    if (gesture or "").strip() != "THAW":
        return {"frozen": True, "reason": "gesture must be exactly THAW"}
    (Path(home) / STORE).unlink(missing_ok=True)
    _audit.log({"actor": "owner", "action": "unfreeze", "decision": "allowed",
                "detail": "typed THAW"}, home=home)
    return {"frozen": False}


def break_glass(phrase: str, pin: str | None = None,
                home: Path | str | None = None) -> dict:
    """Emergency thaw: exact phrase + voice PIN when one exists. Always LOUD
    in the audit ledger, pass or fail."""
    home = jarvis_dir(home)
    ok = (phrase or "").strip() == BREAK_GLASS_PHRASE
    if ok and _pin.is_set(home):
        ok = bool(_pin.verify(pin or "", home).get("ok"))
    _audit.log({"actor": "owner", "action": "break-glass", "decision": "allowed" if ok else "denied",
                "detail": "emergency thaw" if ok else "failed break-glass attempt"}, home=home)
    if not ok:
        return {"frozen": status(home)["frozen"],
                "reason": "phrase must be exactly BREAK GLASS (+ voice PIN when set)"}
    (Path(home) / STORE).unlink(missing_ok=True)
    return {"frozen": False}


def house_party(by: str = "owner", home: Path | str | None = None) -> dict:
    """One word -> full-silent, alerted safe-state. Silences proactivity
    (settings flag, honored by the speaker scripts) and freezes L1/L2."""
    from jarvis.proactivity import settings as _settings
    home = jarvis_dir(home)
    frozen = freeze("house-party-protocol", by=by, home=home)
    _settings.set_silenced(True, home=home)
    _audit.log({"actor": by, "action": "house-party", "decision": "enforced",
                "detail": "full-silent safe-state; proactivity silenced"}, home=home)
    return {"frozen": frozen["frozen"], "silenced": True,
            "alert": "HOUSE PARTY — house frozen, chatter silenced, owner alerted"}
