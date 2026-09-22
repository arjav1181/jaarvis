"""W18 failure miners — pure parsers over caller-supplied evidence.

Three sources, three parsers, zero side effects (no subprocess, no network,
no model calls — hermetic by construction):

1. red tests ......... pytest ``-rf`` short-summary text (FAILED/ERROR lines).
2. failed cron runs ... records shaped like ``hermes cron history`` rows:
   {job, run_id, status|conclusion, ts, detail}.
3. refused acts ....... permission-audit rows (jarvis/permissions/audit.py
   shape): {ts, actor, action, decision, detail}; refused means the decision
   is ``denied`` or ``enforced``.

Every finding carries a citation (node id, job+run, audit ts+action) so the
weekly report can cite instead of vibe. Findings dedupe on (kind, id).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

KINDS = ("red-test", "cron-failed", "refused-act")

_FAIL_LINE = re.compile(r"^(FAILED|ERROR)\s+(\S+?)(?:\s+-\s+(.*))?$")
_SHORT_COUNT = re.compile(r"(\d+)\s+(failed|error)", re.IGNORECASE)

CRON_FAIL = {"failed", "failure", "error", "timed_out", "timeout"}
REFUSED = {"denied", "enforced"}


def _finding(kind: str, fid: str, title: str, citation: str,
             detail: str = "") -> Dict[str, Any]:
    return {"kind": kind, "id": fid, "title": title[:160],
            "citation": citation[:240], "detail": (detail or "")[:500]}


def parse_pytest_summary(text: str) -> List[Dict[str, Any]]:
    """Mine red tests from pytest short-summary output.

    Only FAILED/ERROR lines become findings; passes, skips, warnings, and
    the count line never do. Unparseable text -> [] (an empty week, not an
    exception — the report says so honestly).
    """
    out: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        m = _FAIL_LINE.match(line.strip())
        if not m:
            continue
        status, node, reason = m.group(1), m.group(2), (m.group(3) or "").strip()
        out.append(_finding(
            "red-test", node,
            f"red test: {node}",
            f"pytest {status} {node}",
            reason or f"reported {status.lower()} by pytest",
        ))
    return _dedupe(out)


def _coerce_records(records) -> List[Dict[str, Any]]:
    if records is None:
        return []
    if isinstance(records, str):
        rows: List[Dict[str, Any]] = []
        for line in records.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
        return rows
    if isinstance(records, list):
        return [r for r in records if isinstance(r, dict)]
    return []


def parse_cron_runs(records) -> List[Dict[str, Any]]:
    """Mine failed cron runs. ``cancelled`` is operator intent, not failure."""
    out: List[Dict[str, Any]] = []
    for r in _coerce_records(records):
        verdict = str(r.get("conclusion", r.get("status", ""))).strip().lower()
        if verdict not in CRON_FAIL:
            continue
        job = str(r.get("job", r.get("job_id", "unknown-job")))
        run_id = str(r.get("run_id", r.get("id", "unknown-run")))
        out.append(_finding(
            "cron-failed", f"{job}/{run_id}",
            f"cron run failed: {job} ({run_id})",
            f"cron history job={job} run={run_id} ts={r.get('ts', '?')}",
            str(r.get("detail", r.get("error", ""))),
        ))
    return _dedupe(out)


def parse_refusals(rows) -> List[Dict[str, Any]]:
    """Mine refused acts from permission-audit rows (denied/enforced only)."""
    out: List[Dict[str, Any]] = []
    for r in _coerce_records(rows):
        if str(r.get("decision", "")).strip().lower() not in REFUSED:
            continue
        actor = str(r.get("actor", "?"))
        action = str(r.get("action", "?"))
        ts = str(r.get("ts", "?"))
        out.append(_finding(
            "refused-act", f"{ts}/{actor}/{action}",
            f"refused act: {actor} tried {action} ({r.get('decision')})",
            f"audit ts={ts} actor={actor} action={action}",
            str(r.get("detail", "")),
        ))
    return _dedupe(out)


def _dedupe(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for f in findings:
        key = (f["kind"], f["id"])
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def mine_all(pytest_text: str = "", cron_records=None,
             audit_rows=None) -> Dict[str, Any]:
    """Run all three miners; always returns {findings, counts}."""
    findings = (parse_pytest_summary(pytest_text)
                + parse_cron_runs(cron_records)
                + parse_refusals(audit_rows))
    findings = _dedupe(findings)
    counts = {k: 0 for k in KINDS}
    for f in findings:
        counts[f["kind"]] += 1
    return {"findings": findings, "counts": counts, "total": len(findings)}
