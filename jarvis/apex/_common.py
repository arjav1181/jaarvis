"""W7 apex shared helpers: explicit home, tiny JSON store, UTC clock."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def home() -> Path:
    h = os.environ.get("HERMES_HOME")
    if not h:
        raise SystemExit("HERMES_HOME is not set — refusing to guess a home.")
    return Path(h)


def store_dir() -> Path:
    d = home() / "jarvis" / "apex"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def write_json(path: Path, obj) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")
    return path
