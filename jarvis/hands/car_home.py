"""Car/home API probe (W11 hands): presence-only, honest-absent.

Spec: car/home APIs only where keys already exist (none expected). This
module checks ENV VAR presence and nothing else — no connections, no
reads of Home Assistant / Spotify state (homelab is W6-deferred, hands
off), no network. Absent -> setup contract, never a dial attempt.
"""

from __future__ import annotations

import os
from typing import Any, Dict

PROBED = ("TESLA_API_KEY", "TESLA_CLIENT_ID", "CAR_API_KEY",
          "HOME_ASSISTANT_TOKEN", "HASS_URL", "SMART_HOME_API_KEY")


def status(env: Dict[str, str] | None = None) -> Dict[str, Any]:
    env = dict(os.environ) if env is None else env
    found = sorted(k for k in PROBED if str(env.get(k, "")).strip())
    if found:
        return {"hand": "car-home", "state": "keyed",
                "keys_present": found,
                "note": "keys exist; every act through this hand is L2 + freeze-gated"}
    return {"hand": "car-home", "state": "absent",
            "reason": "no car/home API keys in env (none expected)",
            "setup_contract": {
                "car": "CAR_API_KEY or TESLA_* env vars on the gateway process",
                "home": "HOME_ASSISTANT_TOKEN (+ HASS_URL) — W6-deferred, do not configure here",
            },
            "note": "presence probe only — never connects, never reads device state"}
