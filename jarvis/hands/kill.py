"""Kill path for every hand (W11): freeze covers all.

kill_all(reason) drops W8 freeze; each hand's gate consults freeze first,
so one command denies computer/ssh/telegram/car-home together. L0 texture
(status reads) continues — the kill stops ACTS, not visibility.
"""

from __future__ import annotations

from typing import Any, Dict

from jarvis.permissions import freeze as _freeze

from . import car_home as _car
from . import computer as _computer
from . import ssh_fleet as _ssh
from . import telegram_remote as _tg
from ._common import state_home


def kill_all(reason: str, by: str = "owner") -> Dict[str, Any]:
    frozen = _freeze.freeze(reason, by=by, home=state_home())
    hands = {}
    for name, mod in (("computer", _computer), ("ssh-fleet", _ssh),
                      ("telegram-remote", _tg), ("car-home", _car)):
        gate = _freeze.gate("L2", home=state_home())
        hands[name] = {"acts": "denied" if not gate["allowed"] else "allowed",
                       "reads": "allowed"}
    return {"ok": True, "frozen": frozen["frozen"], "reason": frozen["reason"],
            "hands": hands,
            "thaw": "owner types THAW (unfreeze) or BREAK GLASS (+ voice PIN when set)"}


def gates() -> Dict[str, Any]:
    st = _freeze.status(home=state_home())
    gate = _freeze.gate("L2", home=state_home())
    return {"frozen": st["frozen"], "reason": st["reason"],
            "acts": "denied" if st["frozen"] else "allowed",
            "detail": gate["reason"]}
