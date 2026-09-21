"""Manifest loader/validator for bounded computer-use (W11, HTR-COMPUSE1/HANDS1).

Upstream truth (tools/computer_use/): permission_mode standard | bounded;
bounded needs computer_use.capability_manifest or the backend fails loudly;
`unrestricted` is NOT accepted in config — it lives only on the per-session
YOLO toggle. cua-driver owns final manifest enforcement; this overlay
validates shape BEFORE anything is planned so bad manifests fail here with
a reason, not deep in a driver session.

Overlay manifest shape (version 3, repeatable automations only):
  {name, version: 3, tasks: [{id, app?, acts: [strings], limits?}]}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

MANIFEST_VERSION = 3


def load(path: Path | str) -> Tuple[Dict[str, Any] | None, List[str]]:
    """(manifest, []) for a valid manifest file, (None, errors) otherwise."""
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return None, [f"manifest unreadable: {e}"]
    errors: List[str] = []
    if not isinstance(raw, dict):
        return None, ["manifest must be a JSON object"]
    if not str(raw.get("name", "")).strip():
        errors.append("manifest needs a name")
    if raw.get("version") != MANIFEST_VERSION:
        errors.append(f"manifest version must be {MANIFEST_VERSION} (repeatable bounded set)")
    tasks = raw.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        errors.append("manifest needs a non-empty tasks list")
        return None, errors
    seen = set()
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            errors.append(f"task {i} must be an object")
            continue
        tid = str(t.get("id", "")).strip()
        if not tid or tid in seen:
            errors.append(f"task {i} needs a unique id")
            continue
        seen.add(tid)
        acts = t.get("acts")
        if not isinstance(acts, list) or not acts or not all(
                isinstance(a, str) and a.strip() for a in acts):
            errors.append(f"task {tid!r}: acts must be a non-empty string list")
    if errors:
        return None, errors
    return {"name": str(raw["name"]).strip(), "version": MANIFEST_VERSION,
            "tasks": tasks}, []
