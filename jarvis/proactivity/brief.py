"""W8 proactivity — morning brief text (spoken unprompted unless silenced).

Pure builder: greeting for the soul + memory glance (open threads count,
never contents beyond one cited line). The speaker (speak.py) decides
whether it gets a voice.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "soul"))
import depth


def build(soul: str = "jarvis", when: _dt.datetime | None = None,
          entries: list[str] | None = None) -> str:
    """Two lines max: greeting + one memory glance (or quiet-house note)."""
    when = when or _dt.datetime.now()
    hello = depth.greet(soul, when)
    if entries is None:
        entries = depth.read_memory_entries()
    live = [e.strip() for e in entries if e.strip()]
    if not live:
        return f"{hello} The house is quiet — nothing on the board."
    first = live[0]
    snippet = first if len(first) <= 120 else first[:117].rsplit(" ", 1)[0] + "…"
    return (f"{hello} {len(live)} memor{'y' if len(live) == 1 else 'ies'} on the board. "
            f"Top of the pile: \"{snippet}\"")
