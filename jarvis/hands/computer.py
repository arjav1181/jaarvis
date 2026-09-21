"""Bounded computer-use gate (W11 hands, default OFF).

Upstream owns the desktop (cua-driver MCP via the `computer_use` tool);
this overlay owns the Jarvis policy around it:

- Default OFF: no opt-in record -> every run refused with the setup
  contract. Enabling needs an explicit flag AND a valid manifest.
- Manifests only: free-form desktop goals are refused (no manifest =
  no run). The manifest path travels with the plan so the backend's own
  bounded enforcement applies.
- YOLO refused, not approved: mode yolo always returns a refusal, in
  attended sessions, headless, and cron alike. `unrestricted` can never
  come from this overlay.
- Freeze kills the hand: W8 freeze.gate("L2") denies while frozen.
- Driver honesty: cua-driver presence is probed (binary + --version,
  best-effort); absent -> plan marked runnable False with the setup
  contract. Execution itself stays in the agent loop — the CLI spends
  nothing and clicks nothing.

Context reporting: `attended` is observed (tty or JARVIS_HANDS_ATTENDED=1),
never claimed; plans always carry per-step approvals with auto_approve False.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from jarvis.permissions import freeze as _freeze
from jarvis.permissions import risk as _risk

from . import manifests as _manifests
from ._common import read_json, state_home, store_dir, utcnow, write_json

OPTIN_NAME = "computer.optin.json"

SETUP_CONTRACT = {
    "driver": "cua-driver binary on PATH (upstream `hermes computer-use doctor` verifies)",
    "mode": "bounded via computer_use.capability_manifest (upstream config key)",
    "manifest": "a version-3 overlay manifest under jarvis/hands/manifests/",
    "optin": "explicit `jarvis-hands computer enable --manifest <file> --i-accept-desktop-risk`",
}

YOLO_REFUSAL = ("yolo refused — unrestricted desktop control is never granted "
                "by this overlay, attended or not, headless or cron")


def _driver_probe() -> Dict[str, Any]:
    binary = shutil.which("cua-driver")
    if not binary:
        return {"present": False, "binary": None, "version": None}
    try:
        out = subprocess.run([binary, "--version"], capture_output=True,
                             text=True, timeout=5)
        ver = (out.stdout or "").strip().splitlines()
        return {"present": True, "binary": binary,
                "version": (ver[0] if ver else None)}
    except (OSError, subprocess.SubprocessError):
        return {"present": True, "binary": binary, "version": None}


def _context() -> Dict[str, Any]:
    attended = bool(os.environ.get("JARVIS_HANDS_ATTENDED")) or sys.stdin.isatty()
    return {"attended": attended,
            "cron_hint": os.environ.get("HERMES_CRON_JOB", "") != ""}


def status(env: Dict[str, str] | None = None) -> Dict[str, Any]:
    optin = read_json(store_dir() / OPTIN_NAME, None)
    return {"hand": "computer", "default": "off",
            "enabled": bool(optin and optin.get("enabled")),
            "manifest": (optin or {}).get("manifest"),
            "driver": _driver_probe(),
            "context": _context(),
            "upstream": "computer_use tool (standard|bounded; unrestricted is YOLO-toggle-only)",
            "setup_contract": SETUP_CONTRACT}


def enable(manifest: str, accept_risk: bool = False) -> Dict[str, Any]:
    if not accept_risk:
        return {"ok": False, "reason": "risk_not_accepted",
                "note": "re-run with --i-accept-desktop-risk (typed, on purpose)"}
    m, errors = _manifests.load(manifest)
    if errors:
        return {"ok": False, "reason": "bad_manifest", "errors": errors}
    rec = {"enabled": True, "manifest": str(Path(manifest).resolve()),
           "manifest_name": m["name"], "at": utcnow()}
    write_json(store_dir() / OPTIN_NAME, rec)
    return {"ok": True, **rec}


def disable() -> Dict[str, Any]:
    p = store_dir() / OPTIN_NAME
    was = p.exists()
    p.unlink(missing_ok=True)
    return {"ok": True, "was_enabled": was, "disabled_at": utcnow()}


def yolo() -> Dict[str, Any]:
    """YOLO mode request. Always refused — this is the whole point."""
    return {"ok": False, "reason": "yolo_refused", "detail": YOLO_REFUSAL}


def run_plan(manifest: str, goal: str) -> Dict[str, Any]:
    """Validate goal+manifest+freeze+driver, emit the execution plan (no clicks)."""
    goal = (goal or "").strip()
    if not goal:
        return {"ok": False, "reason": "empty goal — manifests run named tasks, not vibes"}
    gate = _freeze.gate("L2", home=state_home())
    if not gate["allowed"]:
        return {"ok": False, "reason": "frozen", "detail": gate["reason"]}
    optin = read_json(store_dir() / OPTIN_NAME, None)
    if not (optin and optin.get("enabled")):
        return {"ok": False, "reason": "default_off",
                "setup_contract": SETUP_CONTRACT}
    m, errors = _manifests.load(manifest)
    if errors:
        return {"ok": False, "reason": "bad_manifest", "errors": errors}
    if Path(manifest).resolve() != Path(str(optin.get("manifest"))).resolve():
        return {"ok": False, "reason": "manifest_not_opted_in",
                "detail": "only the enabled manifest runs; enable it first"}
    driver = _driver_probe()
    steps = []
    for t in m["tasks"]:
        lvl = _risk.assess({"kind": "system",
                            "target": f"desktop:{t.get('app', 'frontmost')}:{t['id']}",
                            "irreversible": True})
        steps.append({"task": t["id"], "acts": t["acts"],
                      "level": "L2", "confirm": "voice-pin",
                      "assessed": lvl["level"],
                      "approval": "operator confirm per task (auto_approve never set)"})
    return {
        "ok": True, "hand": "computer", "mode": "bounded (manifest)",
        "manifest": m["name"], "goal": goal[:500],
        "runnable": driver["present"],
        "driver": driver,
        "setup_contract": SETUP_CONTRACT if not driver["present"] else None,
        "context": _context(),
        "steps": steps,
        "auto_approve": False,
        "executes_in": "agent loop (upstream computer_use tool), not this CLI",
        "planned_at": utcnow(),
    }
