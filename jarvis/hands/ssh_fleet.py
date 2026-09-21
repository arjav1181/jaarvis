"""SSH-fleet workers (W11 hands): allowlisted, key-based, L2-everything.

Upstream owns the transport (terminal ssh backend: TERMINAL_SSH_HOST/USER/
PORT/KEY, key_path into SSHEnvironment). This overlay owns the Jarvis
policy:

- Per-host allowlist at <home>/jarvis/hands/ssh_allowlist.json —
  [{name, host, user, port?, key}]. Unknown host -> refused. No passwords
  anywhere: key path required and must exist at plan time (fail closed).
- Every remote act is L2 by policy under W8 rails: classified with
  risk.assess, then raised to L2 regardless (remote blast radius), with
  voice-pin confirm. Freeze denies via W8 freeze.gate.
- Plan-only: emits the terminal env mapping + command for the agent loop;
  the CLI opens no connections (probe with --probe would dial; default
  plans never dial).

Allowlist entries carry key PATHS, never key material.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from jarvis.permissions import freeze as _freeze
from jarvis.permissions import risk as _risk

from ._common import read_json, state_home, store_dir, utcnow, write_json

ALLOWLIST_NAME = "ssh_allowlist.json"


def _load() -> Dict[str, Any]:
    data = read_json(store_dir() / ALLOWLIST_NAME, None)
    return data if isinstance(data, dict) else {"hosts": []}


def set_allowlist(hosts: List[Dict[str, Any]]) -> Dict[str, Any]:
    clean = []
    for h in hosts:
        clean.append({"name": str(h.get("name", "")).strip(),
                      "host": str(h.get("host", "")).strip(),
                      "user": str(h.get("user", "")).strip(),
                      "port": int(h.get("port", 22)),
                      "key": str(h.get("key", "")).strip()})
    write_json(store_dir() / ALLOWLIST_NAME, {"hosts": clean, "updated_at": utcnow()})
    return {"ok": True, "hosts": [h["name"] for h in clean if h["name"]]}


def status() -> Dict[str, Any]:
    hosts = _load().get("hosts", [])
    return {"hand": "ssh-fleet", "configured": bool(hosts),
            "hosts": [h.get("name") for h in hosts],
            "auth": "key-based only (no passwords, ever)",
            "upstream": "terminal ssh backend (TERMINAL_SSH_*)"}


def plan(host_name: str, command: str, kind: str = "shell") -> Dict[str, Any]:
    """Emit the remote-execution plan for an allowlisted host (no dialing)."""
    command = (command or "").strip()
    if not command:
        return {"ok": False, "reason": "empty command"}
    gate = _freeze.gate("L2", home=state_home())
    if not gate["allowed"]:
        return {"ok": False, "reason": "frozen", "detail": gate["reason"]}
    hosts = {h.get("name"): h for h in _load().get("hosts", [])}
    h = hosts.get((host_name or "").strip())
    if h is None:
        return {"ok": False, "reason": "host_not_allowlisted",
                "detail": f"{host_name!r} is not on the fleet allowlist"}
    if not h.get("key") or not Path(h["key"]).exists():
        return {"ok": False, "reason": "key_absent",
                "detail": "key-based auth required; key path missing"}
    assessed = _risk.assess({"kind": kind, "target": f"{h['host']}:{command}",
                             "irreversible": True})
    return {
        "ok": True, "hand": "ssh-fleet", "host": h["name"],
        "level": "L2", "confirm": "voice-pin",
        "assessed": assessed["level"],
        "policy": "remote acts are L2 by policy under W8 rails",
        "terminal_env": {"TERMINAL_ENV": "ssh", "TERMINAL_SSH_HOST": h["host"],
                         "TERMINAL_SSH_USER": h["user"],
                         "TERMINAL_SSH_PORT": str(h.get("port", 22)),
                         "TERMINAL_SSH_KEY": h["key"]},
        "command": command[:2000],
        "auto_approve": False,
        "executes_in": "agent loop (upstream terminal ssh backend), not this CLI",
        "planned_at": utcnow(),
    }
