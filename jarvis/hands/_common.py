"""W10-style shared helpers for W11 hands: explicit home, tiny JSON store, UTC clock.

State lives at <home>/jarvis/hands (opt-ins, allowlists, manifests live in
repo; secrets never do — allowlists carry key PATHS, never key material).
"""

from __future__ import annotations

from pathlib import Path

from jarvis.apex._common import home, read_json, utcnow, write_json  # noqa: F401

__all__ = ["home", "read_json", "utcnow", "write_json", "store_dir", "state_home"]


def store_dir() -> Path:
    d = home() / "jarvis" / "hands"
    d.mkdir(parents=True, exist_ok=True)
    return d


def state_home():
    """W8-permissions home (its functions take the jarvis dir explicitly)."""
    return home() / "jarvis"
