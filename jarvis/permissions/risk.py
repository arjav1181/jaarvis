"""W8 risk-scored confirms — blast radius -> level + confirm mode.

Levels: L0 (tap: single confirm), L1 (typed-yes), L2 (voice-PIN + typed-yes).
L2 always confirms — every soul, every channel, no exceptions. Deterministic
and dependency-free: assess(action) -> {level, confirm, score, reasons}.

Action shape: {kind, target, irreversible}.
  kind: shell | file-write | file-delete | network-send | message-send |
        code-push | config-change | memory-write | skill-install | system
  target: free-text command / path / recipient (matched case-insensitively)
  irreversible: bool hint from the caller (deletion, send, push, publish)
"""

from __future__ import annotations

import fnmatch
import re

LEVELS = ("L0", "L1", "L2")
CONFIRM = {"L0": "tap", "L1": "typed-yes", "L2": "voice-pin"}

# Base score per kind: how dangerous the operation class is by default.
_BASE = {
    "shell": 20,
    "file-write": 20,
    "file-delete": 55,
    "network-send": 35,
    "message-send": 45,
    "code-push": 55,
    "config-change": 40,
    "memory-write": 25,
    "skill-install": 40,
    "system": 60,
}

# Target patterns that raise the blast radius (glob, case-insensitive).
_HOT = [
    ("*/etc/*", 25, "system path"),
    ("*/root/*", 25, "root tree"),
    ("*password*", 30, "credential-shaped target"),
    ("*token*", 30, "credential-shaped target"),
    ("*secret*", 30, "credential-shaped target"),
    ("*key*", 15, "key-shaped target"),
    ("~/.ssh/*", 30, "ssh identity"),
    ("~/.jarvis/*", 20, "agent home"),
    ("~/.hermes/*", 20, "agent home"),
    ("*.env", 25, "env file"),
    ("*/.git/*", 15, "repo internals"),
    ("origin*", 15, "remote ref"),
    ("main", 10, "main branch"),
    ("jarvis", 10, "live branch"),
    ("prod*", 20, "prod-shaped target"),
    ("*telegram*", 10, "comms channel"),
    ("*discord*", 10, "comms channel"),
]

_DESTRUCTIVE_VERBS = re.compile(
    r"\brm\s+-[a-z]*r|rm\s+--recursive|mkfs|:?\(\s*\)\s*\{|:;\s*\}|dd\s+.*of=/dev|"
    r"shutdown|reboot|halt|userdel|drop\s+database|delete\s+from|truncate\b",
    re.IGNORECASE,
)

_LEVEL_AT = (25, 60)  # score <25 -> L0, <60 -> L1, else L2


def assess(action: dict) -> dict:
    """Score one action descriptor. Unknown kind -> L2 (fail closed)."""
    kind = str((action or {}).get("kind", "")).strip().lower()
    target = str((action or {}).get("target", ""))
    irreversible = bool((action or {}).get("irreversible", False))
    reasons: list[str] = []
    if kind not in _BASE:
        return {"level": "L2", "confirm": CONFIRM["L2"], "score": 100,
                "reasons": [f"unknown kind {kind!r} — fail closed"]}
    score = _BASE[kind]
    reasons.append(f"base {score} for kind {kind}")
    lowered = target.lower()
    for pattern, bump, why in _HOT:
        if fnmatch.fnmatchcase(lowered, pattern.lower()):
            score += bump
            reasons.append(f"+{bump} {why} ({pattern})")
    if _DESTRUCTIVE_VERBS.search(target):
        score += 40
        reasons.append("+40 destructive verb")
    if irreversible:
        score += 15
        reasons.append("+15 caller-marked irreversible")
    score = min(score, 100)
    level = "L0" if score < _LEVEL_AT[0] else ("L1" if score < _LEVEL_AT[1] else "L2")
    return {"level": level, "confirm": CONFIRM[level], "score": score, "reasons": reasons}


def confirm_mode(level: str, channel: str = "text") -> str:
    """Confirm gesture for (level, channel). L2-by-voice mandates voice-PIN;
    L2 otherwise is voice-PIN + typed-yes. Unknown level fails closed."""
    if level not in CONFIRM:
        raise ValueError(f"unknown level {level!r}")
    if level == "L2" and channel == "voice":
        return "voice-pin-mandatory"
    return CONFIRM[level]
