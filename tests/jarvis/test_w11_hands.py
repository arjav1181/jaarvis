"""W11 hands tests — hermetic (temp HERMES_HOME, no network, no dialing)."""
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from jarvis.hands import car_home as _car
from jarvis.hands import computer as _comp
from jarvis.hands import kill as _kill
from jarvis.hands import manifests as _man
from jarvis.hands import snapshot as _snap
from jarvis.hands import ssh_fleet as _ssh
from jarvis.hands import telegram_remote as _tg
from jarvis.permissions import freeze as _frz

EXAMPLE = REPO / "jarvis" / "hands" / "manifests" / "disk-triage.example.json"


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))


def _jhome():
    return Path(os.environ["HERMES_HOME"]) / "jarvis"


# --- manifests ---

def test_example_manifest_loads():
    m, errors = _man.load(EXAMPLE)
    assert errors == [] and m["version"] == 3 and len(m["tasks"]) == 2


def test_manifest_rejects_bad_shapes(tmp_path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"name": "x", "version": 2, "tasks": []}))
    assert _man.load(bad)[1] != []
    bad.write_text(json.dumps({"name": "x", "version": 3,
                               "tasks": [{"id": "a", "acts": []}]}))
    assert any("acts" in e for e in _man.load(bad)[1])
    bad.write_text(json.dumps({"name": "x", "version": 3,
                               "tasks": [{"id": "a", "acts": ["capture"]},
                                         {"id": "a", "acts": ["capture"]}]}))
    assert any("unique" in e for e in _man.load(bad)[1])
    assert _man.load(tmp_path / "missing.json")[1] != []


# --- computer-use gate ---

def test_computer_default_off():
    st = _comp.status()
    assert st["default"] == "off" and st["enabled"] is False
    assert set(st["driver"]) == {"present", "binary", "version"}
    assert "manifest" in st["setup_contract"]


def test_computer_enable_needs_flag_and_manifest(tmp_path):
    assert _comp.enable(str(EXAMPLE))["reason"] == "risk_not_accepted"
    bad = tmp_path / "m.json"
    bad.write_text("{}")
    r = _comp.enable(str(bad), accept_risk=True)
    assert r["reason"] == "bad_manifest"
    ok = _comp.enable(str(EXAMPLE), accept_risk=True)
    assert ok["ok"] and _comp.status()["enabled"] is True
    assert _comp.disable()["was_enabled"] is True
    assert _comp.status()["enabled"] is False


def test_yolo_always_refused():
    r = _comp.yolo()
    assert r == {"ok": False, "reason": "yolo_refused", "detail": _comp.YOLO_REFUSAL}


def test_run_plan_gates_and_reports_driver(tmp_path):
    assert _comp.run_plan(str(EXAMPLE), "triage disk")["reason"] == "default_off"
    _comp.enable(str(EXAMPLE), accept_risk=True)
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"name": "other", "version": 3,
                                 "tasks": [{"id": "t", "acts": ["capture"]}]}))
    assert _comp.run_plan(str(other), "x")["reason"] == "manifest_not_opted_in"
    p = _comp.run_plan(str(EXAMPLE), "triage the disk")
    assert p["ok"] and p["mode"].startswith("bounded")
    assert p["runnable"] is False and "setup_contract" in p  # no cua-driver here
    assert all(s["level"] == "L2" for s in p["steps"])
    assert p["auto_approve"] is False
    _frz.freeze("drill", home=_jhome())
    assert _comp.run_plan(str(EXAMPLE), "x")["reason"] == "frozen"


# --- ssh fleet ---

def test_ssh_unconfigured_then_gated(tmp_path):
    assert _ssh.status()["configured"] is False
    assert _ssh.plan("prod", "uptime")["reason"] == "host_not_allowlisted"
    key = tmp_path / "id_ed25519"
    key.write_text("fake-key")
    _ssh.set_allowlist([{"name": "lab", "host": "lab.lan",
                         "user": "sir", "key": str(tmp_path / "missing")}])
    assert _ssh.plan("lab", "uptime")["reason"] == "key_absent"
    _ssh.set_allowlist([{"name": "lab", "host": "lab.lan",
                         "user": "sir", "port": 2222, "key": str(key)}])
    p = _ssh.plan("lab", "uptime")
    assert p["ok"] and p["level"] == "L2" and p["confirm"] == "voice-pin"
    assert p["terminal_env"]["TERMINAL_SSH_PORT"] == "2222"
    assert p["auto_approve"] is False
    _frz.freeze("drill", home=_jhome())
    assert _ssh.plan("lab", "uptime")["reason"] == "frozen"


# --- telegram remote ---

def test_telegram_absent_but_queues():
    st = _tg.status()
    assert st["hand"] == "telegram-remote" and st["state"] == "absent"
    r = _tg.act("restart the relay", "w11-drill-1")
    assert r["ok"] and r["level"] == "L2" and r["sendable"] is False
    assert r["payload"]["approve_data"] == "jarvis:approve:w11-drill-1"
    assert [p["id"] for p in _tg.pending()] == ["w11-drill-1"]
    assert _tg.act("", "")["reason"] == "summary and request_id must be non-empty"
    _frz.freeze("drill", home=_jhome())
    assert _tg.act("x", "y")["reason"] == "frozen"


# --- car/home ---

def test_car_home_absent_and_keyed():
    a = _car.status(env={})
    assert a["state"] == "absent" and "never" in a["note"]
    k = _car.status(env={"TESLA_API_KEY": "x"})
    assert k["state"] == "keyed" and k["keys_present"] == ["TESLA_API_KEY"]


# --- kill path ---

def test_kill_all_freezes_every_hand():
    r = _kill.kill_all("w11 drill")
    assert r["ok"] and r["frozen"] is True
    assert all(v["acts"] == "denied" for v in r["hands"].values())
    assert all(v["reads"] == "allowed" for v in r["hands"].values())
    assert _kill.gates()["acts"] == "denied"
    assert _frz.unfreeze("THAW", home=_jhome())["frozen"] is False
    assert _kill.gates()["acts"] == "allowed"


# --- snapshot + page ---

def test_snapshot_builds_without_secrets(tmp_path):
    key = tmp_path / "k"
    key.write_text("fake")
    _ssh.set_allowlist([{"name": "lab", "host": "h", "user": "u",
                         "key": str(key)}])
    s = _snap.build()
    assert s["ssh_fleet"]["hosts"] == [{"name": "lab", "key_present": True}]
    dump = json.dumps(s)
    assert str(key) not in dump and "fake" not in dump
    p = Path(os.environ["HERMES_HOME"]) / "jarvis" / "hands" / "hands-snapshot.json"
    assert p.exists() and json.loads(p.read_text())["built_at"] == s["built_at"]


def test_hud_page_contract():
    src = (REPO / "jarvis" / "hud" / "hands.html").read_text()
    assert 'fetch("./hands-snapshot.json"' in src
    for pat in ["http://", "https://", "<img", "url(", "@import",
                "innerHTML", "document.write", "localStorage", "eval("]:
        assert pat not in src, f"banned pattern {pat}"
    assert "textContent" in src
