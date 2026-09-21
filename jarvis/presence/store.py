"""W9 presence — multi-room satellite registry. Stdlib only (also shipped
inside the dashboard plugin dir, so no third-party imports here)."""
import json
import os
import re
import time
from pathlib import Path

STALE_AFTER_S = 45
PRUNE_AFTER_S = 3600
MAX_TEXT = 500

_SAT_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_ROOM_RE = re.compile(r"^[a-z0-9-]{1,32}$")


def home_dir(home=None):
    h = home or os.environ.get("HERMES_HOME", "")
    if not h:
        raise RuntimeError("HERMES_HOME not set (refusing implicit ~/.hermes)")
    return Path(h)


def store_path(home=None):
    return home_dir(home) / "jarvis" / "presence.json"


def _blank():
    return {"satellites": {}, "outbox": [], "seq": 0}


def _load(home=None):
    p = store_path(home)
    if not p.exists():
        return _blank()
    try:
        st = json.loads(p.read_text())
        assert isinstance(st.get("satellites"), dict)
        assert isinstance(st.get("outbox"), list)
        return st
    except Exception:
        return _blank()


def _save(home, st):
    p = store_path(home)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1, sort_keys=True))
    tmp.replace(p)
    return p


def slug_room(room):
    return re.sub(r"[^a-z0-9-]", "", str(room or "").strip().lower())[:32]


def register(home=None, satellite_id="", room="", device="", caps=None):
    sid = str(satellite_id or "").strip()
    if not _SAT_RE.match(sid):
        return {"ok": False, "reason": "bad_satellite_id"}
    r = slug_room(room)
    if not _ROOM_RE.match(r):
        return {"ok": False, "reason": "bad_room"}
    caps = caps or {}
    st = _load(home)
    now = time.time()
    st["satellites"][sid] = {
        "room": r,
        "device": str(device or "")[:64],
        "mic": bool(caps.get("mic", True)),
        "speaker": bool(caps.get("speaker", True)),
        "listening": False,
        "last_seen": now,
        "registered_at": st["satellites"].get(sid, {}).get("registered_at", now),
    }
    _prune(st, now)
    _save(home, st)
    return {"ok": True, "satellite": sid, "room": r}


def heartbeat(home=None, satellite_id="", listening=False):
    st = _load(home)
    sat = st["satellites"].get(str(satellite_id))
    if sat is None:
        return {"ok": False, "reason": "unknown_satellite"}
    sat["last_seen"] = time.time()
    sat["listening"] = bool(listening)
    _prune(st)
    _save(home, st)
    return {"ok": True, "satellite": str(satellite_id)}


def _prune(st, now=None):
    now = now if now is not None else time.time()
    dead = [sid for sid, s in st["satellites"].items()
            if now - s.get("last_seen", 0) > PRUNE_AFTER_S]
    for sid in dead:
        del st["satellites"][sid]
        st["outbox"] = [m for m in st["outbox"] if m["to"] != sid]
    return dead


def status(home=None, now=None):
    now = now if now is not None else time.time()
    st = _load(home)
    roster = []
    for sid in sorted(st["satellites"]):
        s = st["satellites"][sid]
        age = now - s.get("last_seen", 0)
        roster.append({
            "satellite": sid,
            "room": s["room"],
            "device": s["device"],
            "mic": s["mic"],
            "speaker": s["speaker"],
            "listening": s["listening"],
            "age_s": round(age, 1),
            "stale": age > STALE_AFTER_S,
            "pending": sum(1 for m in st["outbox"] if m["to"] == sid),
        })
    live = sum(1 for r in roster if not r["stale"])
    return {"ok": True, "satellites": roster,
            "live": live, "silent": len(roster) - live, "now": now}


def _live_in(st, room=None, sid=None, now=None):
    now = now if now is not None else time.time()
    out = []
    for rid, s in st["satellites"].items():
        if now - s.get("last_seen", 0) > STALE_AFTER_S:
            continue
        if sid is not None and rid != sid:
            continue
        if room is not None and s["room"] != room:
            continue
        out.append(rid)
    return sorted(out)


def intercom(home=None, text="", frm="operator",
             to_room=None, to_satellite=None, to_all=False):
    text = str(text or "").strip()
    if not text or len(text) > MAX_TEXT:
        return {"ok": False, "reason": "bad_text"}
    st = _load(home)
    if to_all:
        targets = _live_in(st)
    elif to_satellite is not None:
        if to_satellite not in st["satellites"]:
            return {"ok": False, "reason": "unknown_satellite"}
        targets = _live_in(st, sid=to_satellite)
    elif to_room is not None:
        r = slug_room(to_room)
        known = sorted({s["room"] for s in st["satellites"].values()})
        if r not in known:
            return {"ok": False, "reason": "unknown_room", "known_rooms": known}
        targets = _live_in(st, room=r)
    else:
        return {"ok": False, "reason": "no_target"}
    if not targets:
        return {"ok": False, "reason": "no_live_targets",
                "detail": "targets registered but all silent (stale) — nothing spoke"}
    now = time.time()
    queued = []
    for rid in targets:
        st["seq"] += 1
        st["outbox"].append({"id": st["seq"], "to": rid, "from": str(frm)[:64],
                             "text": text, "ts": now})
        queued.append(st["seq"])
    _prune(st, now)
    _save(home, st)
    return {"ok": True, "targets": targets, "queued": queued}


def outbox(home=None, satellite_id=""):
    st = _load(home)
    if str(satellite_id) not in st["satellites"]:
        return {"ok": False, "reason": "unknown_satellite"}
    msgs = [m for m in st["outbox"] if m["to"] == str(satellite_id)]
    return {"ok": True, "messages": msgs}


def ack(home=None, satellite_id="", ids=()):
    st = _load(home)
    want = {int(i) for i in ids}
    before = len(st["outbox"])
    st["outbox"] = [m for m in st["outbox"]
                    if not (m["to"] == str(satellite_id) and m["id"] in want)]
    _save(home, st)
    return {"ok": True, "acked": before - len(st["outbox"])}
