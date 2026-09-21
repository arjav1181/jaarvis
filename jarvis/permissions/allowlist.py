"""W8 approval learning — allowlist rules the human approves.

Flow: the agent proposes a rule after a repeated approval
(propose() dedupes pending ones); the human approves or denies it
(explicit gestures only — proposals never self-approve); match() gates
future actions. Store: <home>/jarvis/allowlist.json.
Rule: {id, pattern, kind, proposed_by, approved: null|true|false, created}.
match() honors approved rules only (approved == true).
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from ._common import jarvis_dir, read_json, utc_now, write_json

STORE = "allowlist.json"


def _load(home) -> dict:
    data = read_json(Path(home) / STORE, None)
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        return {"rules": []}
    return data


def _save(home, data) -> None:
    write_json(Path(home) / STORE, data)


def propose(pattern: str, kind: str = "shell", proposed_by: str = "agent",
            home: Path | str | None = None) -> dict:
    """Propose a rule; returns the existing pending rule when identical."""
    home = jarvis_dir(home)
    pattern = (pattern or "").strip()
    if not pattern:
        raise ValueError("pattern must be non-empty")
    data = _load(home)
    for rule in data["rules"]:
        if rule["pattern"] == pattern and rule["approved"] is None:
            return rule
    rule = {"id": f"r_{len(data['rules']) + 1:04d}", "pattern": pattern,
            "kind": kind, "proposed_by": proposed_by,
            "approved": None, "created": utc_now()}
    data["rules"].append(rule)
    _save(home, data)
    return rule


def decide(rule_id: str, approve: bool, home: Path | str | None = None) -> dict:
    """Human decision: approve=True allows, False denies. Returns the rule."""
    home = jarvis_dir(home)
    data = _load(home)
    for rule in data["rules"]:
        if rule["id"] == rule_id:
            rule["approved"] = bool(approve)
            rule["decided"] = utc_now()
            _save(home, data)
            return rule
    raise KeyError(f"unknown rule {rule_id!r}")


def list_rules(status: str = "all", home: Path | str | None = None) -> list[dict]:
    """status: all | pending | approved | denied."""
    data = _load(jarvis_dir(home))
    rules = data["rules"]
    if status == "pending":
        return [r for r in rules if r["approved"] is None]
    if status == "approved":
        return [r for r in rules if r["approved"] is True]
    if status == "denied":
        return [r for r in rules if r["approved"] is False]
    return list(rules)


def match(action: dict, home: Path | str | None = None) -> dict | None:
    """First approved rule whose pattern matches kind:target (or bare target)."""
    target = str((action or {}).get("target", "")).lower()
    kind = str((action or {}).get("kind", "")).lower()
    for rule in list_rules("approved", home):
        pattern = rule["pattern"].lower()
        if (fnmatch.fnmatchcase(target, pattern)
                or fnmatch.fnmatchcase(f"{kind}:{target}", pattern)):
            return rule
    return None
