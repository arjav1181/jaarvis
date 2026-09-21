"""W9 presence plugin API — mounted at /api/plugins/presence/ by the dashboard.

Inherits the dashboard auth gate (same cookie gate as every /api/* route, plus
the plugin runtime allow-list): no new auth surface. State lives in
$HERMES_HOME/jarvis/presence.json via the bundled store.py (stdlib only).
"""
import sys
from pathlib import Path

try:
    from fastapi import APIRouter
    from pydantic import BaseModel, Field
except Exception:  # dashboard imports this file; hard-fail loudly, not silently
    raise

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store as _store  # noqa: E402  (deployed copy of jarvis/presence/store.py)

router = APIRouter()


class Register(BaseModel):
    satellite_id: str = Field(min_length=1, max_length=64)
    room: str = Field(min_length=1, max_length=64)
    device: str = Field(default="", max_length=64)
    mic: bool = True
    speaker: bool = True


class Heartbeat(BaseModel):
    satellite_id: str = Field(min_length=1, max_length=64)
    listening: bool = False


class Intercom(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    to_room: str = ""
    to_satellite: str = ""
    to_all: bool = False
    frm: str = Field(default="operator", max_length=64)


class Ack(BaseModel):
    satellite_id: str = Field(min_length=1, max_length=64)
    ids: list = Field(default_factory=list)


@router.post("/register")
def register(body: Register):
    return _store.register(satellite_id=body.satellite_id, room=body.room,
                           device=body.device,
                           caps={"mic": body.mic, "speaker": body.speaker})


@router.post("/heartbeat")
def heartbeat(body: Heartbeat):
    return _store.heartbeat(satellite_id=body.satellite_id,
                            listening=body.listening)


@router.get("/status")
def status():
    return _store.status()


@router.post("/intercom")
def intercom(body: Intercom):
    kw = {"text": body.text, "frm": body.frm}
    if body.to_all:
        kw["to_all"] = True
    elif body.to_satellite:
        kw["to_satellite"] = body.to_satellite
    elif body.to_room:
        kw["to_room"] = body.to_room
    else:
        return {"ok": False, "reason": "no_target"}
    return _store.intercom(**kw)


@router.get("/outbox")
def outbox(satellite_id: str = ""):
    return _store.outbox(satellite_id=satellite_id)


@router.post("/ack")
def ack(body: Ack):
    try:
        ids = [int(i) for i in body.ids]
    except Exception:
        return {"ok": False, "reason": "bad_ids"}
    return _store.ack(satellite_id=body.satellite_id, ids=ids)
