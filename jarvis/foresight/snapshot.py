"""Foresight snapshot builder (W10): one JSON resume of the engine's state."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from . import brief as _brief
from . import ledger as _ledger
from .suites import load_suite
from ._common import store_dir, utcnow, write_json

SNAP_NAME = "foresight-snapshot.json"
EXAMPLE_SUITE = Path(__file__).resolve().parent / "suites" / "monthly-numbers.example.json"


def build() -> Dict[str, Any]:
    b = _brief.build()
    example: Dict[str, Any] = {"present": EXAMPLE_SUITE.exists()}
    if example["present"]:
        suite, errors = load_suite(EXAMPLE_SUITE)
        example["valid"] = not errors
        example["errors"] = errors
        example["name"] = (suite or {}).get("name")
    snap = {
        "headline": b["headline"],
        "calibration": b["calibration"],
        "ledger": {"open": b["open"], "resolved": b["calibration"].get("resolved", 0)},
        "overdue": b["overdue"],
        "recent_runs": b["recent_runs"],
        "example_suite": example,
        "built_at": utcnow(),
    }
    write_json(store_dir() / SNAP_NAME, snap)
    return snap
