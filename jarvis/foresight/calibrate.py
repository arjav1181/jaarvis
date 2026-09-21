"""Calibration scoring over resolved predictions (W10, HTR-FORE1 "right 8/10").

Pure functions over ledger entries: accuracy count + rate, Brier score
(mean squared error of confidence vs outcome), and per-bucket hit rates.
Empty ledgers report unscored — never 0/0, never a fabricated score.
"""

from __future__ import annotations

from typing import Any, Dict, List

BUCKETS = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]


def score(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    resolved = [e for e in entries if e.get("status") == "resolved"]
    if not resolved:
        return {"scored": False, "resolved": 0,
                "note": "unscored — no resolved predictions yet"}
    correct = sum(1 for e in resolved if e.get("correct") is True)
    n = len(resolved)
    brier = sum((float(e.get("confidence", 0.5)) - (1.0 if e.get("correct") else 0.0)) ** 2
                for e in resolved) / n
    buckets = []
    for lo, hi in BUCKETS:
        members = [e for e in resolved if lo <= float(e.get("confidence", 0)) < hi]
        hits = sum(1 for e in members if e.get("correct") is True)
        buckets.append({"lo": lo, "hi": min(hi, 1.0), "n": len(members),
                        "hits": hits,
                        "rate": (hits / len(members)) if members else None})
    return {
        "scored": True,
        "resolved": n,
        "correct": correct,
        "accuracy": f"{correct}/{n}",
        "rate": correct / n,
        "brier": round(brier, 4),
        "buckets": buckets,
    }


def headline(cal: Dict[str, Any]) -> str:
    if not cal.get("scored"):
        return "calibration unscored, sir — no resolved predictions yet"
    return (f"right {cal['accuracy']} ({cal['rate']:.0%}), "
            f"Brier {cal['brier']} over {cal['resolved']} resolved")
