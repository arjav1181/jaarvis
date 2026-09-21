"""Nightly foresight brief renderer (W10, HTR-FORE1).

Reads the ledger + recent run receipts and renders one honest page: the
calibration line ("right 8/10" or unscored), open predictions, overdue
resolutions, and the last batch runs. Text goes to the operator; the JSON
feeds foresight.html via the snapshot.
"""

from __future__ import annotations

from typing import Any, Dict, List

from . import calibrate as _cal
from . import ledger as _ledger
from . import runner as _runner
from ._common import utcnow


def build(today: str | None = None) -> Dict[str, Any]:
    entries = _ledger.list_entries()
    cal = _cal.score(entries)
    open_e = [e for e in entries if e.get("status") == "open"]
    due = _ledger.overdue(today)
    runs = _runner.recent_runs()
    lines = [f"Foresight brief — {cal_headline(cal)}."]
    lines.append(f"{len(open_e)} open predictions, {len(due)} overdue, sir.")
    for e in due[:5]:
        lines.append(f"OVERDUE {e['id']}: {e['question'][:80]} (due {e['horizon']})")
    for r in runs[:3]:
        lines.append(
            f"Run {r['suite']} at {r['at']}: {r['computed_ok']}/{r['computed']} "
            f"computed ok, {r['recorded']} filed, {r['delegated']} delegated (plan only).")
    if not runs:
        lines.append("No suite runs yet, sir — run the numbers with jarvis-foresee run-suite.")
    return {"text": "\n".join(lines), "headline": cal_headline(cal),
            "calibration": cal, "open": len(open_e),
            "overdue": [{"id": e["id"], "question": e["question"],
                         "horizon": e["horizon"]} for e in due],
            "recent_runs": runs, "built_at": utcnow()}


def cal_headline(cal: Dict[str, Any]) -> str:
    return _cal.headline(cal)
