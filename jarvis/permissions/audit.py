"""W8 audit ledger — append-only JSONL of permission decisions.

Event: {ts, actor, action, decision, detail}. Decisions: allowed | denied |
enforced. Append-only by convention (no delete API — the file is the record).
Readers: tail() newest-first, summary() counts by decision. The HUD audit
page renders snapshots of this file (see hud/audit.html + snapshot job).
"""

from __future__ import annotations

import json
from pathlib import Path

from ._common import jarvis_dir, utc_now

STORE = "audit.jsonl"

REQUIRED = ("actor", "action", "decision")


def log(event: dict, home: Path | str | None = None) -> dict:
    """Append one event. Missing keys raise — the ledger never takes half rows."""
    for key in REQUIRED:
        if not (event or {}).get(key):
            raise ValueError(f"audit event needs {key!r}")
    home = jarvis_dir(home)
    row = {"ts": utc_now(), "actor": event["actor"], "action": event["action"],
           "decision": event["decision"], "detail": str(event.get("detail", ""))}
    path = Path(home) / STORE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def tail(limit: int = 50,     decision: str | None = None,
         home: Path | str | None = None) -> list[dict]:
    """Newest-first rows, optional decision filter. Unreadable file -> []."""
    path = Path(jarvis_dir(home)) / STORE
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and (decision is None or row.get("decision") == decision):
            rows.append(row)
    rows.reverse()
    return rows[: max(0, int(limit))]


def summary(home: Path | str | None = None) -> dict:
    """Counts by decision + total. Unknown decisions bucket under other."""
    counts = {"allowed": 0, "denied": 0, "enforced": 0, "other": 0, "total": 0}
    for row in tail(limit=10**6, home=home):
        decision = row.get("decision")
        key = decision if decision in ("allowed", "denied", "enforced") else "other"
        counts[key] += 1
        counts["total"] += 1
    return counts
