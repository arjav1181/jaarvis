"""Hands snapshot builder (W11): one JSON resume of every hand's state.

Key material never appears: ssh entries report names + key presence, never
paths; telegram reports state, never tokens.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from . import car_home as _car
from . import computer as _computer
from . import kill as _kill
from . import ssh_fleet as _ssh
from . import telegram_remote as _tg
from ._common import read_json, store_dir, utcnow, write_json

SNAP_NAME = "hands-snapshot.json"


def build() -> Dict[str, Any]:
    comp = _computer.status()
    ssh = _ssh.status()
    tg = _tg.status()
    keys = []
    try:
        data = read_json(store_dir() / _ssh.ALLOWLIST_NAME, {})
        for h in (data or {}).get("hosts", []):
            keys.append({"name": h.get("name"),
                         "key_present": bool(h.get("key")) and Path(str(h["key"])).exists()})
    except OSError:
        keys = []
    snap = {
        "computer": {k: comp[k] for k in ("default", "enabled", "manifest") if k in comp}
        | {"driver_present": comp["driver"]["present"],
           "driver_version": comp["driver"]["version"]},
        "ssh_fleet": {"configured": ssh["configured"], "hosts": keys},
        "telegram": {"state": tg.get("state"), "open": tg.get("open")},
        "car_home": {"state": _car.status()["state"]},
        "kill": _kill.gates(),
        "built_at": utcnow(),
    }
    write_json(store_dir() / SNAP_NAME, snap)
    return snap
