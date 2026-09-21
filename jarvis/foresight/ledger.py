"""Prediction ledger: append-only JSONL + derived state (W10, HTR-FORE1).

A prediction is an authored, dated claim: {question, predicted, confidence,
horizon, author}. Nothing here judges — recording an entry files the claim,
`resolve` later files the verdict (correct = outcome matches predicted,
case-insensitive). The ledger is the raw material; calibrate.py scores it.

Entries live in <home>/jarvis/foresight/predictions.jsonl (append-only);
ledger.json caches counts for the snapshot path. IDs are F-YYYYMMDD-NNN.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from ._common import read_json, store_dir, utcnow, write_json

LEDGER_NAME = "predictions.jsonl"
STATE_NAME = "ledger.json"


def _read() -> List[Dict[str, Any]]:
    p = store_dir() / LEDGER_NAME
    out = []
    try:
        for line in p.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def _valid_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def record(question: str, predicted: str, confidence: float,
           horizon: str, author: str = "operator",
           source: str = "cli") -> Dict[str, Any]:
    """File a prediction claim. Returns {"ok", "entry"} or {"ok": False, "reason"}."""
    q = (question or "").strip()
    pr = (predicted or "").strip()
    if not q or not pr:
        return {"ok": False, "reason": "question and predicted must both be non-empty"}
    if len(q) > 500 or len(pr) > 200:
        return {"ok": False, "reason": "question (<=500) / predicted (<=200) too long"}
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "confidence must be a number 0..1"}
    if not 0.0 <= c <= 1.0:
        return {"ok": False, "reason": "confidence must be a number 0..1"}
    if not _valid_date(horizon):
        return {"ok": False, "reason": "horizon must be YYYY-MM-DD"}
    existing = _read()
    day = utcnow()[:10].replace("-", "")
    entry = {
        "id": f"F-{day}-{len(existing) + 1:03d}",
        "question": q, "predicted": pr, "confidence": c,
        "horizon": horizon, "author": (author or "operator")[:80],
        "source": (source or "cli")[:160],
        "status": "open", "created_at": utcnow(),
    }
    p = store_dir() / LEDGER_NAME
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    _restate(existing + [entry])
    return {"ok": True, "entry": entry}


def resolve(pid: str, outcome: str, resolver: str = "operator",
            note: str = "") -> Dict[str, Any]:
    """File the verdict on an open prediction. Never rewrites history."""
    entries = _read()
    for e in entries:
        if e.get("id") == pid:
            if e.get("status") != "open":
                return {"ok": False, "reason": "already_resolved"}
            out = (outcome or "").strip()
            if not out:
                return {"ok": False, "reason": "outcome must be non-empty"}
            e["status"] = "resolved"
            e["outcome"] = out[:200]
            e["correct"] = out.lower() == str(e.get("predicted", "")).strip().lower()
            e["resolver"] = (resolver or "operator")[:80]
            e["note"] = (note or "")[:200]
            e["resolved_at"] = utcnow()
            p = store_dir() / LEDGER_NAME
            with p.open("w") as f:
                for row in entries:
                    f.write(json.dumps(row) + "\n")
            _restate(entries)
            return {"ok": True, "entry": e}
    return {"ok": False, "reason": "unknown_id"}


def _restate(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    open_ids = [e["id"] for e in entries if e.get("status") == "open"]
    res_ids = [e["id"] for e in entries if e.get("status") == "resolved"]
    state = {"open": len(open_ids), "resolved": len(res_ids),
             "total": len(entries), "open_ids": open_ids,
             "resolved_ids": res_ids, "updated_at": utcnow()}
    write_json(store_dir() / STATE_NAME, state)
    return state


def list_entries(status: str | None = None) -> List[Dict[str, Any]]:
    entries = _read()
    if status in ("open", "resolved"):
        entries = [e for e in entries if e.get("status") == status]
    return entries


def overdue(today: str | None = None) -> List[Dict[str, Any]]:
    """Open predictions whose horizon has passed (honest nudge list)."""
    day = today or utcnow()[:10]
    return [e for e in _read()
            if e.get("status") == "open" and str(e.get("horizon", "")) < day]


def summary() -> Dict[str, Any]:
    st = read_json(store_dir() / STATE_NAME, None)
    if not isinstance(st, dict):
        st = _restate(_read())
    st["overdue"] = len(overdue())
    return st
