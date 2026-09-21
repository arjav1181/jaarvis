"""Suite runner: batch-run a what-if suite (W10, HTR-FORE1).

One command runs the whole file: compute scenarios execute locally (timed
per-scenario ms, measured not claimed), predict scenarios file to the
ledger (idempotent — reruns return the existing entry, never a duplicate),
delegate scenarios fold into ONE delegate_task-compatible batch payload
(plan-only; judgment executes in the agent loop, the runner spends zero).

The run receipt is persisted under <home>/jarvis/foresight/runs/ so the
nightly brief can cite recent numbers.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from . import ledger as _ledger
from ._common import store_dir, utcnow, write_json
from .suites import compute_expr, validate_delegate_tasks


def run_suite(suite: Dict[str, Any], author: str = "operator") -> Dict[str, Any]:
    name = suite["name"]
    computed: List[Dict[str, Any]] = []
    recorded: List[Dict[str, Any]] = []
    deleg: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    for s in suite["scenarios"]:
        kind = s["kind"]
        if kind == "compute":
            t1 = time.perf_counter()
            try:
                val = compute_expr(str(s["expr"]), dict(s["inputs"]))
                computed.append({"id": s["id"], "ok": True, "value": val,
                                 "ms": round((time.perf_counter() - t1) * 1000, 1)})
            except (ValueError, ZeroDivisionError, OverflowError) as e:
                computed.append({"id": s["id"], "ok": False, "error": str(e)[:200],
                                 "ms": round((time.perf_counter() - t1) * 1000, 1)})
        elif kind == "predict":
            source = f"suite:{name}/{s['id']}"
            dup = next((e for e in _ledger.list_entries(status="open")
                        if e.get("source") == source), None)
            if dup is not None:
                recorded.append({"id": s["id"], "duplicate": True,
                                 "entry_id": dup["id"]})
                continue
            r = _ledger.record(s["question"], s["predicted"], s["confidence"],
                               s["horizon"], author=author, source=source)
            recorded.append({"id": s["id"], "duplicate": False,
                             "entry_id": (r.get("entry") or {}).get("id"),
                             "ok": r["ok"],
                             "reason": r.get("reason")})
        else:  # delegate
            task: Dict[str, Any] = {"goal": str(s["goal"]).strip(),
                                    "role": str(s.get("role", "foresight-scout"))}
            if str(s.get("context", "")).strip():
                task["context"] = str(s["context"]).strip()[:2000]
            deleg.append(task)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    delegate_payload: Dict[str, Any] | None = None
    if deleg:
        err = validate_delegate_tasks(deleg)
        if err:
            delegate_payload = {"ok": False, "error": err}
        else:
            delegate_payload = {
                "ok": True, "tool": "delegate_task", "tasks": deleg,
                "executes_in": ("agent loop (upstream delegate_task "
                                "tasks-batch), not this CLI"),
            }
    receipt = {"suite": name, "at": utcnow(), "author": author,
               "computed": computed, "recorded": recorded,
               "delegate": delegate_payload, "elapsed_ms": elapsed_ms}
    runs = store_dir() / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
    write_json(runs / f"{name}-{stamp}.json", receipt)
    return receipt


def recent_runs(limit: int = 5) -> List[Dict[str, Any]]:
    runs = store_dir() / "runs"
    try:
        files = sorted(runs.glob("*.json"), reverse=True)[:limit]
    except OSError:
        return []
    out = []
    for f in files:
        try:
            import json
            r = json.loads(f.read_text())
            out.append({"suite": r.get("suite"), "at": r.get("at"),
                        "computed": len(r.get("computed", [])),
                        "computed_ok": sum(1 for c in r.get("computed", [])
                                           if c.get("ok")),
                        "recorded": len(r.get("recorded", [])),
                        "delegated": len((r.get("delegate") or {}).get("tasks", []))})
        except (OSError, ValueError):
            continue
    return out
