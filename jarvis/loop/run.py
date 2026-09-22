"""W18 loop runner — mine → cards → trim proposals → cited report.

Mode discipline (the whole point of the file):

- Dry-run is the default: zero ``hermes kanban create`` calls, zero curator
  archives. The weekly report is still filed (that IS the deliverable).
- Live needs TWO keys per run: ``run(live=True)`` in code AND the
  ``JARVIS_LOOP_LIVE=1`` environment flag. Either missing -> refused with
  ``{"ok": False, "reason": "live-needs-flag"}`` and nothing executed.
- Even live, curator trims stay operator-executed previews (the model-spend
  review is a by-hand ``hermes curator run --dry-run``); only kanban creates
  dispatch, each under its ``jarvis-loop:`` idempotency key.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List

from jarvis.curator.loop_trim import (candidate_trims, inventory_skills,
                                      load_pins, render_trim_plan)
from jarvis.kanban.loop_cards import (MAX_CARDS, build_fix_cards, to_create_args,
                                      validate_card)

from . import miners
from ._common import REPO_DIR, store_dir, utcnow
from .report import build_report, save_report

LIVE_ENV = "JARVIS_LOOP_LIVE"


def _default_executor(argv: List[str]) -> str:
    r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(argv[:4])} failed: "
                           f"{(r.stdout + r.stderr)[-500:]}")
    return r.stdout.strip()


def run(pytest_text: str = "", cron_records=None, audit_rows=None,
        usage: Dict[str, Any] | None = None,
        live: bool = False, repo_root: Path | str = REPO_DIR,
        executor: Callable[[List[str]], str] | None = None,
        today: str | None = None) -> Dict[str, Any]:
    """Execute one Friday-loop pass. Returns the filed receipt."""
    if live and os.environ.get(LIVE_ENV) != "1":
        return {"ok": False, "reason": "live-needs-flag",
                "hint": f"live needs run(live=True) plus {LIVE_ENV}=1 per run"}
    mode = "live" if live else "dry-run"

    mined = miners.mine_all(pytest_text, cron_records, audit_rows)
    skills = inventory_skills(repo_root)
    cards = build_fix_cards(mined["findings"], max_cards=MAX_CARDS)
    card_errors = [e for c in cards for e in validate_card(c, set(skills))]
    review = candidate_trims(skills, load_pins(), usage, today=today)
    trim_plan = render_trim_plan(review)

    executed: List[Dict[str, Any]] = []
    if live:
        run_exec = executor or _default_executor
        for card in cards:
            argv = to_create_args(card)
            try:
                out = run_exec(argv)
                executed.append({"key": card["key"], "ok": True,
                                 "result": str(out)[-200:]})
            except Exception as e:  # noqa: BLE001 — cited, never raised
                executed.append({"key": card["key"], "ok": False,
                                 "result": str(e)[-200:]})

    report_md = build_report(mined, cards, review, mode=mode)
    receipt = {"ok": True, "mode": mode, "at": utcnow(),
               "counts": mined["counts"], "total": mined["total"],
               "findings": mined["findings"], "cards": cards,
               "card_errors": card_errors,
               "trims": review["candidates"],
               "trim_plan": trim_plan,
               "executed": executed}
    paths = save_report(report_md, receipt)
    receipt["report"] = {k: str(v) for k, v in paths.items()}
    return receipt


def demo_inputs() -> Dict[str, Any]:
    """Synthetic week for `--demo` previews (never presented as real)."""
    return {
        "pytest_text": (
            "FAILED tests/jarvis/test_w9_presence.py::test_stale_is_honest - assert False\n"
            "ERROR tests/jarvis/test_w4_talk.py::test_callback - fixture missing\n"
            "1 failed, 1 error in 3.21s\n"
        ),
        "cron_records": [
            {"job": "ci-watchdog", "run_id": "r-1042", "conclusion": "failed",
             "ts": "2026-09-18T07:31:00Z", "detail": "npm audit gate red"},
            {"job": "morning-brief", "run_id": "r-1043", "conclusion": "completed",
             "ts": "2026-09-18T07:00:00Z", "detail": "delivered"},
        ],
        "audit_rows": [
            {"ts": "2026-09-18T09:00:00Z", "actor": "jarvis-worker",
             "action": "ship-pr:merge", "decision": "denied",
             "detail": "red CI is a report, never a merge"},
            {"ts": "2026-09-18T09:01:00Z", "actor": "jarvis-worker",
             "action": "memory:recall", "decision": "allowed", "detail": ""},
        ],
        "usage": {"explain-error": {"uses": 12, "last_used": "2026-09-17"},
                  "ship-pr": {"uses": 0, "last_used": ""}},
    }
