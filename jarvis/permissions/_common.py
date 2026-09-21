"""W8 smart permissions — shared home helpers (HERMES_HOME-aware).

All state lives under <home>/jarvis/ (never the default profile unless the
operator points HERMES_HOME there explicitly). Import surfaces only; the CLI
entry is jarvis/bin/jarvis-permissions.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]


def home_dir() -> Path:
    """Active home: $HERMES_HOME, else ~/.jarvis (same default as jarvis-persona)."""
    return Path(os.environ.get("HERMES_HOME") or os.path.join(os.path.expanduser("~"), ".jarvis"))


def jarvis_dir(home: Path | str | None = None) -> Path:
    """Overlay state dir; created on write paths only."""
    return Path(home) if home is not None else home_dir() / "jarvis"


def read_json(path: Path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
