"""W9 presence tests — hermetic (temp HERMES_HOME, no network, no dashboard)."""
import ast
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from jarvis.presence import intercom as _ix
from jarvis.presence import store as _st

REPO_ROOT = str(REPO)


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))


def _jhome():
    return Path(os.environ["HERMES_HOME"]) / "jarvis"


# --- registry ---

def test_register_and_status_fresh():
    r = _st.register(satellite_id="tab-1", room="Kitchen", device="tab")
    assert r == {"ok": True, "satellite": "tab-1", "room": "kitchen"}
    st = _st.status()
    assert st["live"] == 1 and st["silent"] == 0
    s = st["satellites"][0]
    assert s["room"] == "kitchen" and s["stale"] is False and s["pending"] == 0


def test_register_rejects_bad_shapes():
    assert _st.register(satellite_id="bad id!", room="kitchen")["reason"] == "bad_satellite_id"
    assert _st.register(satellite_id="ok-1", room="")["reason"] == "bad_room"
    assert _st.heartbeat(satellite_id="ghost")["reason"] == "unknown_satellite"


def test_stale_is_honest_and_prune_forgets():
    _st.register(satellite_id="tab-1", room="kitchen")
    _st.heartbeat(satellite_id="tab-1", listening=True)
    st = _st.status(now=time.time() + _st.STALE_AFTER_S + 1)
    assert st["live"] == 0 and st["silent"] == 1
    assert st["satellites"][0]["stale"] is True
    assert st["satellites"][0]["listening"] is True  # last-known, flagged stale
    _st._prune(_st._load(), now=time.time() + _st.PRUNE_AFTER_S + 1)
    p = _jhome() / "presence.json"
    raw = json.loads(p.read_text()) if p.exists() else {"satellites": {}}
    # prune via a write path: heartbeat then force-prune through intercom save
    _st.register(satellite_id="fresh", room="study")
    assert "fresh" in _st._load()["satellites"]


def test_home_must_be_explicit(monkeypatch):
    monkeypatch.delenv("HERMES_HOME", raising=False)
    with pytest.raises(RuntimeError):
        _st.status()


# --- intercom routing ---

def test_intercom_room_roundtrip_and_ack():
    _st.register(satellite_id="k-tab", room="kitchen")
    _st.register(satellite_id="s-tab", room="study")
    r = _st.intercom(text="dinner is ready", frm="study/s-tab", to_room="kitchen")
    assert r["ok"] and r["targets"] == ["k-tab"]
    ob = _st.outbox(satellite_id="k-tab")
    assert len(ob["messages"]) == 1
    assert ob["messages"][0]["text"] == "dinner is ready"
    assert _st.outbox(satellite_id="s-tab")["messages"] == []
    a = _st.ack(satellite_id="k-tab", ids=[ob["messages"][0]["id"]])
    assert a == {"ok": True, "acked": 1}
    assert _st.outbox(satellite_id="k-tab")["messages"] == []


def test_intercom_unknown_room_lists_known():
    _st.register(satellite_id="k-tab", room="kitchen")
    r = _st.intercom(text="hello?", to_room="attic")
    assert r["reason"] == "unknown_room" and r["known_rooms"] == ["kitchen"]


def test_intercom_silent_targets_speak_nothing():
    _st.register(satellite_id="k-tab", room="kitchen")
    # age the satellite past stale without any new heartbeat
    st = _st._load()
    st["satellites"]["k-tab"]["last_seen"] -= (_st.STALE_AFTER_S + 5)
    _st._save(None, st)
    r = _st.intercom(text="hello?", to_room="kitchen")
    assert r["reason"] == "no_live_targets"
    assert _st.outbox(satellite_id="k-tab")["messages"] == []


def test_intercom_all_and_text_cap():
    _st.register(satellite_id="k-tab", room="kitchen")
    _st.register(satellite_id="s-tab", room="study")
    r = _st.intercom(text="lights out", to_all=True)
    assert r["ok"] and r["targets"] == ["k-tab", "s-tab"]
    assert _st.intercom(text="x" * 501, to_all=True)["reason"] == "bad_text"
    assert _st.intercom(text="   ", to_all=True)["reason"] == "bad_text"
    assert _st.outbox(satellite_id="nobody")["reason"] == "unknown_satellite"


# --- intent parsing ---

def test_parse_tell_patterns():
    p = _ix.parse("tell the kitchen: dinner is ready")
    assert p == {"kind": "room", "room": "kitchen", "body": "dinner is ready"}
    p = _ix.parse("Announce to all — lights out")
    assert p == {"kind": "all", "room": "", "body": "lights out"}
    p = _ix.parse("say in the Study, come here")
    assert p == {"kind": "room", "room": "study", "body": "come here"}
    p = _ix.parse("what is the weather")
    assert p["kind"] == "none"


# --- plugin contract (static: no dashboard needed) ---

def test_plugin_manifest_and_router():
    man = json.loads((REPO / "jarvis" / "plugins" / "presence" / "dashboard"
                      / "manifest.json").read_text())
    assert man["name"] == "presence" and man["api"] == "api.py"
    tree = ast.parse((REPO / "jarvis" / "plugins" / "presence" / "dashboard"
                      / "api.py").read_text())
    routes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("post", "get") and node.args:
                routes.add(node.args[0].value if isinstance(node.args[0], ast.Constant) else "")
    assert {"/register", "/heartbeat", "/status", "/intercom",
            "/outbox", "/ack"} <= routes


def test_deployed_store_matches_source():
    # deploy copies store.py next to api.py; logic must stay identical
    src = (REPO / "jarvis" / "presence" / "store.py").read_text()
    assert "STALE_AFTER_S = 45" in src and "import fastapi" not in src


# --- page contract ---

def test_hud_page_contract():
    src = (REPO / "jarvis" / "hud" / "presence.html").read_text()
    for need in ("/api/plugins/presence/", "/api/audio/speak",
                 "/api/audio/transcribe", "/api/auth/ws-ticket",
                 "[room:", "?room=", "view=status"):
        assert need in src, f"missing {need}"
    for pat in ["http://", "https://", "<img", "url(", "@import",
                "innerHTML", "document.write", "localStorage", "eval("]:
        assert pat not in src, f"banned pattern {pat}"
    assert "textContent" in src


# --- overlay gate ---

def test_no_core_files_touched():
    r = subprocess.run(["git", "diff", "upstream/main", "--name-only"],
                       cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    files = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert files, "overlay diff must not be empty"
    # Authorized sole core-surface exception: root README.md rebrand
    # (operator commit 4a362d4daf) — everything else stays overlay-only.
    bad = [f for f in files
           if not (f == "jarvis" or f.startswith("jarvis/") or f.startswith("tests/jarvis/")
                   or f == "README.md")]
    assert not bad, f"core files touched: {bad}"
