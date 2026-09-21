"""W8 proactivity pack — silencable spoken brief + watchdog alerts.

Silence is a flag, not an absence: settings live at
<home>/jarvis/proactivity.json {silenced: bool}. The speaker script honors
it (silenced -> payload recorded, nothing spoken). House Party sets it;
the owner clears it. brief.py builds the morning text (greeting + memory
glance); alerts.py diffs the CI fingerprint for speak-worthy changes.
"""

from __future__ import annotations

from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "permissions"))
from _common import jarvis_dir, read_json, write_json

STORE = "proactivity.json"


def is_silenced(home: Path | str | None = None) -> bool:
    """True when the house is silent (default: speak)."""
    data = read_json(Path(jarvis_dir(home)) / STORE, None)
    return bool(isinstance(data, dict) and data.get("silenced"))


def set_silenced(silenced: bool, home: Path | str | None = None) -> dict:
    """Owner gesture: silence or restore proactive speech."""
    home = jarvis_dir(home)
    write_json(Path(home) / STORE, {"silenced": bool(silenced)})
    return {"silenced": bool(silenced)}
