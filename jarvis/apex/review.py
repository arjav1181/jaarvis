"""jarvis-review MoA preset resolver (W7 apex, HTR-MOA1).

The preset lives in jarvis/moa/jarvis-review.json: cheap references advise
once per turn, a frontier aggregator acts with full tools, privacy filter
full (prompts are scrubbed before fan-out). This module loads, validates,
and emits an execution plan.

The plan is the honest artifact: actual fan-out runs inside the agent loop
(upstream moa_loop / delegate_tool), never from a bare CLI. `jarvis-review
--plan` prints what WOULD run; `--check` validates the preset schema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ._common import utcnow

PRESET_PATH = Path(__file__).resolve().parent.parent / "moa" / "jarvis-review.json"

REQUIRED_TOP = {"name", "references", "aggregator", "privacy_filter", "fanout"}


def load_preset(path: Path | None = None) -> Dict[str, Any]:
    p = path or PRESET_PATH
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError) as e:
        raise SystemExit(f"preset unreadable at {p}: {e}")


def check_preset(preset: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    missing = REQUIRED_TOP - set(preset)
    if missing:
        errors.append(f"missing keys: {sorted(missing)}")
    refs = preset.get("references", [])
    if not isinstance(refs, list) or len(refs) < 1:
        errors.append("references must be a non-empty list")
    for r in refs if isinstance(refs, list) else []:
        if not isinstance(r, dict) or not r.get("model") or not r.get("task"):
            errors.append(f"bad reference entry: {r!r}")
    if preset.get("privacy_filter") != "full":
        errors.append("privacy_filter must be 'full' (prompts scrubbed pre-fanout)")
    if preset.get("fanout") not in ("user_turn", "per_iteration", "every_n"):
        errors.append(f"unknown fanout: {preset.get('fanout')!r}")
    return {"ok": not errors, "errors": errors,
            "name": preset.get("name"), "checked_at": utcnow()}


def plan(preset: Dict[str, Any], task: str) -> Dict[str, Any]:
    """Emit the fan-out execution plan for a task (no execution here)."""
    chk = check_preset(preset)
    if not chk["ok"]:
        return {"ok": False, "errors": chk["errors"]}
    if not task.strip():
        return {"ok": False, "errors": ["empty task"]}
    refs = preset["references"]
    return {
        "ok": True,
        "preset": preset.get("name"),
        "task": task.strip()[:500],
        "fanout": preset["fanout"],
        "steps": [
            {"phase": "fanout", "run": [
                {"reference": r.get("role", f"ref{i}"), "model": r["model"],
                 "task": r["task"]} for i, r in enumerate(refs)]},
            {"phase": "aggregate", "model": preset["aggregator"].get("model"),
             "note": preset["aggregator"].get("note", ""),
             "privacy_filter": preset["privacy_filter"]},
        ],
        "executes_in": "agent loop (upstream moa_loop/delegate_tool), not this CLI",
        "planned_at": utcnow(),
    }
