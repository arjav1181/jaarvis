"""W20 queue — briefs/alerts queued while degraded, replayed on recovery.

Append-only ``degraded-queue.jsonl`` under ``$HERMES_HOME/jarvis/``; replay
drains it into ``degraded-replayed.jsonl`` and reports what was missed
(downtime window + item count + items). No model calls anywhere here.
"""
import json
import os
import time
from pathlib import Path

from . import probe as _probe

KINDS = ("brief", "alert")
MAX_TEXT = 2000


def home_dir(home=None):
    h = home or os.environ.get("HERMES_HOME", "")
    if not h:
        raise RuntimeError("HERMES_HOME not set (refusing implicit ~/.hermes)")
    return Path(h)


def queue_path(home=None):
    return home_dir(home) / "jarvis" / "degraded-queue.jsonl"


def replayed_path(home=None):
    return home_dir(home) / "jarvis" / "degraded-replayed.jsonl"


def enqueue(kind="", text="", home=None, now=None):
    """Queue a brief/alert for replay. Works online or off (honest backlog)."""
    kind = str(kind or "").strip().lower()
    if kind not in KINDS:
        return {"ok": False, "reason": "bad_kind", "kinds": list(KINDS)}
    text = str(text or "").strip()
    if not text or len(text) > MAX_TEXT:
        return {"ok": False, "reason": "bad_text"}
    now = now if now is not None else time.time()
    p = queue_path(home)
    p.parent.mkdir(parents=True, exist_ok=True)
    item = {"kind": kind, "text": text, "queued_at": now}
    with p.open("a") as fh:
        fh.write(json.dumps(item, sort_keys=True) + "\n")
    return {"ok": True, "queued": item, "pending": len(pending(home))}


def pending(home=None):
    p = queue_path(home)
    if not p.exists():
        return []
    out = []
    try:
        for ln in p.read_text().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                it = json.loads(ln)
            except Exception:
                continue
            if isinstance(it, dict) and it.get("kind") in KINDS:
                out.append(it)
    except OSError:
        return []
    return out


def replay(home=None, now=None):
    """Drain the queue; returns the backfill report (what was missed)."""
    items = pending(home)
    now = now if now is not None else time.time()
    st = _probe.read_state(home)
    window = {"since": st.get("since"), "until": now,
              "down_events": len(st.get("down_events") or [])}
    if items:
        rp = replayed_path(home)
        rp.parent.mkdir(parents=True, exist_ok=True)
        with rp.open("a") as fh:
            for it in items:
                rec = dict(it)
                rec["replayed_at"] = now
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
        qp = queue_path(home)
        try:
            qp.unlink()
        except OSError:
            qp.write_text("")
    return {"ok": True, "replayed": len(items), "items": items,
            "missed_window": window}


def recover(base_url="", timeout=_probe.PROBE_TIMEOUT_S, fetcher=None,
            home=None, now=None):
    """Recovery handshake: probe, and only on success replay + report.

    Relay still down -> ``{"ok": False, "reason": <probe reason>}`` and the
    queue is untouched. Never claims recovery without a passing probe.
    The missed window spans the pre-check downtime start (``since`` before
    this handshake flipped the state) to now — so the report names the
    outage it just survived, not the instant it recovered.
    """
    pre = _probe.read_state(home)
    res = _probe.check(base_url=base_url, timeout=timeout, fetcher=fetcher,
                       home=home, now=now)
    if res["status"] != _probe.STATUS_ONLINE:
        return {"ok": False, "reason": res["reason"],
                "status": res["status"], "banner": res["banner"],
                "pending": len(pending(home))}
    at = now if now is not None else time.time()
    rep = replay(home=home, now=at)
    if pre.get("status") == _probe.STATUS_DEGRADED and pre.get("since"):
        rep["missed_window"] = {"since": pre["since"], "until": at,
                                "down_events": len(pre.get("down_events")
                                                   or [])}
    return {"ok": True, "status": _probe.STATUS_ONLINE,
            "line": _probe.ONLINE_LINE, "backfill": rep}
