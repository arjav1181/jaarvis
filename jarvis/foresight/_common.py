"""W10 foresight shared helpers: explicit home, tiny JSON store, UTC clock.

Same contract as jarvis.apex._common (one clock, HERMES_HOME explicit, never
guessed); the foresight store lives at <home>/jarvis/foresight so ledgers
never mingle with apex state.
"""

from __future__ import annotations

from pathlib import Path

from jarvis.apex._common import home, read_json, utcnow, write_json  # noqa: F401

__all__ = ["home", "read_json", "utcnow", "write_json", "store_dir"]


def store_dir() -> Path:
    d = home() / "jarvis" / "foresight"
    d.mkdir(parents=True, exist_ok=True)
    return d
