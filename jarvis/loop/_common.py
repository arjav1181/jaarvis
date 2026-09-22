"""W18 loop shared helpers: explicit home, tiny JSON store, UTC clock.

Standalone copy of the apex/foresight contract (explicit HERMES_HOME, never
guessed) so the loop never imports outside its §4 turf.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def home() -> Path:
    h = os.environ.get("HERMES_HOME")
    if not h:
        raise SystemExit("HERMES_HOME is not set — refusing to guess a home.")
    return Path(h)


def store_dir() -> Path:
    d = home() / "jarvis" / "loop"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_json(path: Path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, obj) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(path)
    return path
