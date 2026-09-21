"""W8 voice-PIN — mandatory step-up for L2-by-voice.

Salted SHA-256, never plaintext (asserted in tests). Store:
<home>/jarvis/voice_pin.json {salt, hash, attempts, locked_until}.
5 wrong attempts -> 15-minute lockout. Changing the PIN requires the old one
(or break-glass, which logs loudly — see freeze.py).
"""

from __future__ import annotations

import hashlib
import secrets
import time
from pathlib import Path

from ._common import jarvis_dir, read_json, utc_now, write_json

STORE = "voice_pin.json"
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _load(home) -> dict:
    data = read_json(Path(home) / STORE, None)
    return data if isinstance(data, dict) else {}


def _save(home, data) -> None:
    write_json(Path(home) / STORE, data)


def _hash(pin: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{pin}".encode("utf-8")).hexdigest()


def is_set(home: Path | str | None = None) -> bool:
    data = _load(jarvis_dir(home))
    return bool(data.get("salt") and data.get("hash"))


def set_pin(new_pin: str, old_pin: str | None = None,
            home: Path | str | None = None) -> dict:
    """Set (or change) the PIN. Change requires the current PIN."""
    home = jarvis_dir(home)
    new_pin = (new_pin or "").strip()
    if not (new_pin.isdigit() and 4 <= len(new_pin) <= 12):
        raise ValueError("PIN must be 4-12 spoken digits")
    data = _load(home)
    if data.get("hash"):
        if old_pin is None or _hash(old_pin, data["salt"]) != data["hash"]:
            raise PermissionError("current PIN required to change it")
    salt = secrets.token_hex(16)
    _save(home, {"salt": salt, "hash": _hash(new_pin, salt),
                 "attempts": 0, "locked_until": 0, "set_at": utc_now()})
    return {"ok": True}


def verify(pin: str, home: Path | str | None = None) -> dict:
    """Verify a PIN attempt. Returns {ok, locked, remaining}."""
    home = jarvis_dir(home)
    data = _load(home)
    if not data.get("hash"):
        return {"ok": False, "locked": False, "remaining": 0, "reason": "no PIN set"}
    now = time.time()
    if now < float(data.get("locked_until") or 0):
        return {"ok": False, "locked": True, "remaining": 0, "reason": "locked out"}
    if _hash((pin or "").strip(), data["salt"]) == data["hash"]:
        data["attempts"] = 0
        data["locked_until"] = 0
        _save(home, data)
        return {"ok": True, "locked": False, "remaining": MAX_ATTEMPTS}
    attempts = int(data.get("attempts") or 0) + 1
    data["attempts"] = attempts
    if attempts >= MAX_ATTEMPTS:
        data["locked_until"] = now + LOCKOUT_SECONDS
        data["attempts"] = 0
        _save(home, data)
        return {"ok": False, "locked": True, "remaining": 0, "reason": "locked out"}
    _save(home, data)
    return {"ok": False, "locked": False,
            "remaining": MAX_ATTEMPTS - attempts, "reason": "wrong PIN"}
