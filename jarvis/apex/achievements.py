"""Achievements engine: session-history badges (W7 apex, HTR-OBS1 morale).

Upstream has no gamification — only internal failure streaks. This overlay
keeps its own append-only event log (jarvis/apex/events.jsonl) and awards
badges from pure functions over that log, so results are reproducible and
testable. `jarvis-achieve record <event>` appends; `jarvis-achieve list`
shows earned badges + progress toward locked ones.

Rules (all computed, none claimed):
- first-light      first event ever recorded
- early-riser      a brief event before 08:00 UTC
- night-owl        any event between 00:00–05:00 UTC
- streak-3         events on 3 distinct UTC dates
- streak-7         events on 7 distinct UTC dates
- watchdog-clean   a watchdog-quiet event
- reviewer         a moa-review event
- party-starter    a house-party event (W8 protocol in action)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ._common import read_json, store_dir, utcnow, write_json

EVENTS_NAME = "events.jsonl"
STATE_NAME = "achievements.json"

BADGES = {
    "first-light": {"name": "First Light", "desc": "the engine saw its first event"},
    "early-riser": {"name": "Early Riser", "desc": "morning brief before 08:00 UTC"},
    "night-owl": {"name": "Night Owl", "desc": "tinkering between 00:00–05:00 UTC"},
    "streak-3": {"name": "Three-Day Streak", "desc": "active on 3 distinct days"},
    "streak-7": {"name": "Seven-Day Streak", "desc": "active on 7 distinct days"},
    "watchdog-clean": {"name": "All Quiet", "desc": "a watchdog run with nothing changed"},
    "reviewer": {"name": "Second Opinion", "desc": "ran a jarvis-review plan"},
    "party-starter": {"name": "Party Starter", "desc": "House Party Protocol engaged"},
}


def _events() -> List[Dict[str, Any]]:
    p = store_dir() / EVENTS_NAME
    out = []
    try:
        for line in p.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(__import__("json").loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def record(kind: str, detail: str = "", at: str | None = None) -> Dict[str, Any]:
    p = store_dir() / EVENTS_NAME
    p.parent.mkdir(parents=True, exist_ok=True)
    ev = {"at": at or utcnow(), "kind": kind, "detail": detail[:200]}
    with p.open("a") as f:
        f.write(__import__("json").dumps(ev) + "\n")
    earned = evaluate()
    return {"recorded": ev, "earned_now": earned["earned"],
            "total_earned": len(earned["earned"])}


def _hour(ev: Dict[str, Any]) -> int:
    try:
        return datetime.strptime(ev["at"], "%Y-%m-%dT%H:%M:%SZ").hour
    except (KeyError, ValueError):
        return -1


def evaluate(events: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    evs = events if events is not None else _events()
    kinds = {e.get("kind") for e in evs}
    days = sorted({str(e.get("at", ""))[:10] for e in evs if e.get("at")})
    earned: Dict[str, str] = {}
    if evs:
        earned["first-light"] = evs[0].get("at", "")
    if any(k == "brief" and 0 <= _hour(e) < 8 for e in evs for k in [e.get("kind")]):
        earned["early-riser"] = utcnow()
    if any(0 <= _hour(e) < 5 for e in evs):
        earned["night-owl"] = utcnow()
    if len(days) >= 3:
        earned["streak-3"] = days[2]
    if len(days) >= 7:
        earned["streak-7"] = days[6]
    if "watchdog-quiet" in kinds:
        earned["watchdog-clean"] = utcnow()
    if "moa-review" in kinds:
        earned["reviewer"] = utcnow()
    if "house-party" in kinds:
        earned["party-starter"] = utcnow()
    locked = [b for b in BADGES if b not in earned]
    state = {"earned": earned, "locked": locked,
             "events": len(evs), "active_days": len(days),
             "evaluated_at": utcnow()}
    write_json(store_dir() / STATE_NAME, state)
    return state


def summary() -> Dict[str, Any]:
    st = read_json(store_dir() / STATE_NAME, None) or evaluate()
    return {"earned": {k: {"badge": BADGES[k]["name"], "at": v}
                       for k, v in st.get("earned", {}).items()},
            "locked": {k: BADGES[k] for k in st.get("locked", [])},
            "events": st.get("events", 0),
            "active_days": st.get("active_days", 0)}
