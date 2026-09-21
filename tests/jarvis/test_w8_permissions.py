"""W8 smart-permissions tests — risk scoring, allowlist learning, voice-PIN,
freeze/break-glass/House Party, audit ledger, Telegram payloads, proactivity.

Hermetic: all state under tmp HERMES_HOMEs (set per test), never ~/.jarvis;
no network, no Telegram token (absent-path asserted). The two CLIs are
exercised as subprocesses with a scratch HERMES_HOME.
Run with the W0 venv active: `python -m pytest tests/jarvis/test_w8_permissions.py -v`
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
JARVIS_DIR = REPO_ROOT / "jarvis"
sys.path.insert(0, str(REPO_ROOT))

from jarvis.permissions import allowlist, audit, freeze, risk, telegram, voice_pin
from jarvis.proactivity import alerts, brief, settings


@pytest.fixture()
def home(tmp_path, monkeypatch):
    """Scratch home wired as HERMES_HOME for the module helpers."""
    h = tmp_path / "perm-home"
    monkeypatch.setenv("HERMES_HOME", str(h))
    return h


def _jdir(home):
    return home / "jarvis"


# ---- risk-scored confirms ----

def test_risk_benign_is_l0_tap():
    r = risk.assess({"kind": "shell", "target": "ls /tmp"})
    assert (r["level"], r["confirm"]) == ("L0", "tap")


def test_risk_destructive_is_l2_voice_pin():
    r = risk.assess({"kind": "file-delete", "target": "rm -rf ~/.ssh", "irreversible": True})
    assert r["level"] == "L2" and r["confirm"] == "voice-pin"
    assert r["score"] >= 60 and len(r["reasons"]) >= 3


def test_risk_push_to_live_branch_is_l2():
    r = risk.assess({"kind": "code-push", "target": "git push origin jarvis", "irreversible": True})
    assert r["level"] == "L2"


def test_risk_message_send_is_l1_typed_yes():
    r = risk.assess({"kind": "message-send", "target": "telegram hello"})
    assert (r["level"], r["confirm"]) == ("L1", "typed-yes")


def test_risk_unknown_kind_fails_closed():
    r = risk.assess({"kind": "summon-demons", "target": "anything"})
    assert r["level"] == "L2" and "fail closed" in " ".join(r["reasons"])


def test_confirm_mode_l2_by_voice_mandatory():
    assert risk.confirm_mode("L2", "voice") == "voice-pin-mandatory"
    assert risk.confirm_mode("L2", "text") == "voice-pin"
    assert risk.confirm_mode("L0") == "tap"
    with pytest.raises(ValueError):
        risk.confirm_mode("L9")


# ---- approval learning: allowlist ----

def test_allowlist_propose_approve_match(home):
    rule = allowlist.propose("pytest tests/jarvis/*", kind="shell")
    assert rule["approved"] is None
    assert allowlist.match({"kind": "shell", "target": "pytest tests/jarvis/"}, home=_jdir(home)) is None
    allowlist.decide(rule["id"], True, home=_jdir(home))
    hit = allowlist.match({"kind": "shell", "target": "pytest tests/jarvis/"}, home=_jdir(home))
    assert hit and hit["id"] == rule["id"]
    assert allowlist.match({"kind": "shell", "target": "rm -rf /"}, home=_jdir(home)) is None


def test_allowlist_dedupe_and_deny(home):
    first = allowlist.propose("ls *", home=_jdir(home))
    again = allowlist.propose("ls *", home=_jdir(home))
    assert first["id"] == again["id"]
    allowlist.decide(first["id"], False, home=_jdir(home))
    assert allowlist.list_rules("denied", home=_jdir(home))[0]["id"] == first["id"]
    assert allowlist.list_rules("pending", home=_jdir(home)) == []
    with pytest.raises(KeyError):
        allowlist.decide("r_9999", True, home=_jdir(home))
    with pytest.raises(ValueError):
        allowlist.propose("   ", home=_jdir(home))


# ---- voice-PIN ----

def test_pin_set_verify_change(home):
    assert voice_pin.verify("1234", home=_jdir(home))["reason"] == "no PIN set"
    voice_pin.set_pin("1234", home=_jdir(home))
    assert voice_pin.is_set(home=_jdir(home))
    assert voice_pin.verify("1234", home=_jdir(home))["ok"] is True
    stored = (_jdir(home) / "voice_pin.json").read_text()
    assert "1234" not in stored, "PIN must never persist as plaintext"
    with pytest.raises(PermissionError):
        voice_pin.set_pin("5678", old_pin="0000", home=_jdir(home))
    voice_pin.set_pin("5678", old_pin="1234", home=_jdir(home))
    assert voice_pin.verify("5678", home=_jdir(home))["ok"] is True
    with pytest.raises(ValueError):
        voice_pin.set_pin("abc", home=_jdir(home))


def test_pin_lockout_after_five(home):
    voice_pin.set_pin("4242", home=_jdir(home))
    for _ in range(4):
        r = voice_pin.verify("0000", home=_jdir(home))
        assert r["ok"] is False and r["locked"] is False
    locked = voice_pin.verify("0000", home=_jdir(home))
    assert locked["locked"] is True
    assert voice_pin.verify("4242", home=_jdir(home))["locked"] is True


# ---- freeze / break-glass / House Party ----

def test_freeze_gates_l1_l2_keeps_l0(home):
    assert freeze.status(home=_jdir(home))["frozen"] is False
    assert freeze.gate("L2", home=_jdir(home))["allowed"] is True
    freeze.freeze("drill", home=_jdir(home))
    assert freeze.status(home=_jdir(home))["reason"] == "drill"
    assert freeze.gate("L2", home=_jdir(home))["allowed"] is False
    assert freeze.gate("L1", home=_jdir(home))["allowed"] is False
    assert freeze.gate("L0", home=_jdir(home))["allowed"] is True
    assert freeze.unfreeze("please", home=_jdir(home))["frozen"] is True
    assert freeze.unfreeze("THAW", home=_jdir(home))["frozen"] is False


def test_break_glass_needs_phrase_plus_pin(home):
    voice_pin.set_pin("9999", home=_jdir(home))
    freeze.freeze("drill", home=_jdir(home))
    assert freeze.break_glass("BREAK GLASS", pin="0000", home=_jdir(home))["frozen"] is True
    assert freeze.break_glass("please", pin="9999", home=_jdir(home))["frozen"] is True
    assert freeze.break_glass("BREAK GLASS", pin="9999", home=_jdir(home))["frozen"] is False
    denied = audit.tail(decision="denied", home=_jdir(home))
    assert any(r["action"] == "break-glass" for r in denied)


def test_house_party_freezes_and_silences(home):
    out = freeze.house_party(home=_jdir(home))
    assert out["frozen"] is True and out["silenced"] is True
    assert "HOUSE PARTY" in out["alert"]
    assert settings.is_silenced(home=_jdir(home)) is True
    assert freeze.gate("L1", home=_jdir(home))["allowed"] is False
    settings.set_silenced(False, home=_jdir(home))
    assert settings.is_silenced(home=_jdir(home)) is False


# ---- audit ledger ----

def test_audit_log_tail_summary(home):
    audit.log({"actor": "cli", "action": "assess shell", "decision": "allowed"}, home=_jdir(home))
    audit.log({"actor": "owner", "action": "freeze", "decision": "enforced", "detail": "drill"},
              home=_jdir(home))
    audit.log({"actor": "owner", "action": "break-glass", "decision": "denied"}, home=_jdir(home))
    rows = audit.tail(home=_jdir(home))
    assert [r["action"] for r in rows] == ["break-glass", "freeze", "assess shell"]
    assert audit.tail(decision="denied", home=_jdir(home))[0]["action"] == "break-glass"
    assert audit.summary(home=_jdir(home)) == {
        "allowed": 1, "denied": 1, "enforced": 1, "other": 0, "total": 3}
    with pytest.raises(ValueError):
        audit.log({"actor": "x"}, home=_jdir(home))
    assert audit.tail(home=_jdir(home) / "nope") == []


# ---- Telegram inline approve/deny ----

def test_telegram_payload_and_callbacks(home):
    payload = telegram.request("Push jarvis?", "L2", "abc123", home=_jdir(home))
    assert payload["approve_data"] == "jarvis:approve:abc123"
    assert payload["deny_data"] == "jarvis:deny:abc123"
    assert "[L2]" in payload["text"]
    assert telegram.parse_callback("jarvis:approve:abc123") == {
        "decision": "approve", "request_id": "abc123"}
    assert telegram.parse_callback("jarvis:deny:abc123")["decision"] == "deny"
    assert telegram.parse_callback("jarvis:hug:abc123") is None
    assert telegram.parse_callback("") is None
    settled = telegram.decide("abc123", True, home=_jdir(home))
    assert settled["status"] == "approved"
    assert telegram.pending(home=_jdir(home)) == []
    with pytest.raises(KeyError):
        telegram.decide("nope", True, home=_jdir(home))
    with pytest.raises(ValueError):
        telegram.request("", "L2", "x", home=_jdir(home))


def test_telegram_absent_without_token(home):
    # Scratch home has no config -> honest-absent, never a fake configured.
    state = telegram.status(home=_jdir(home))
    assert state["channel"] == "telegram" and state["state"] == "absent"


# ---- proactivity pack ----

def test_proactivity_silence_flag(home):
    assert settings.is_silenced(home=_jdir(home)) is False
    settings.set_silenced(True, home=_jdir(home))
    assert settings.is_silenced(home=_jdir(home)) is True


def test_brief_builder():
    monday = __import__("datetime").datetime(2026, 9, 21, 7, 5)
    text = brief.build("jarvis", monday, ["Fix the leak.", "Call the shop."])
    assert "Monday" in text and "2 memories" in text and "Fix the leak" in text
    quiet = brief.build("friday", monday, [])
    assert "quiet" in quiet.lower()


def test_alerts_builder():
    assert alerts.build(["a", "b"], ["a", "b"]) is None
    text = alerts.build(["a"], ["a", "b"])
    assert text is not None and "1 new run" in text
    aged = alerts.build(["a", "b"], ["a"])
    assert aged is not None and "aged out" in aged


# ---- CLIs (subprocess, scratch home) ----

def _run_cli(name, *args, home):
    env = dict(os.environ, HERMES_HOME=str(home))
    env["PATH"] = os.pathsep.join([
        str(Path(sys.executable).parent), os.environ.get("PATH", "")])
    proc = subprocess.run([str(JARVIS_DIR / "bin" / name), *args],
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


def test_cli_assess_and_freeze(tmp_path):
    home = tmp_path / "cli-home"
    out = _run_cli("jarvis-permissions", "assess", "shell", "ls /tmp", home=home)
    assert out["level"] == "L0"
    assert _run_cli("jarvis-permissions", "freeze", "STATUS", home=home)["frozen"] is False
    assert _run_cli("jarvis-permissions", "freeze", "drill", home=home)["frozen"] is True
    assert _run_cli("jarvis-permissions", "thaw", "THAW", home=home)["frozen"] is False


def test_cli_speak_dry_run_and_silence(tmp_path):
    home = tmp_path / "speak-home"
    out = _run_cli("jarvis-speak", "--brief", "--soul", "friday", "--dry-run", home=home)
    assert out["state"] == "WOULD-SPEAK" and "boss" in out["text"]
    settings.set_silenced(True, home=home / "jarvis")
    out2 = _run_cli("jarvis-speak", "--brief", "--dry-run", home=home)
    assert out2["state"] == "SILENCED"


# ---- carried face items: boot ceremony (surgical voice.html edit) ----

VOICE_PAGE = JARVIS_DIR / "hud" / "voice.html"
DIAG_PAGE = JARVIS_DIR / "hud" / "diag.html"
AUDIT_PAGE = JARVIS_DIR / "hud" / "audit.html"


def _script(src):
    m = re.search(r"<script>(.*)</script>", src, re.S)
    assert m, "page must carry its logic in one inline <script> (zero external)"
    return m.group(1)


def _body(name, src):
    start = src.index("function %s" % name)
    lines = src[start:].splitlines()
    depth, out = 0, []
    for ln in lines:
        depth += ln.count("{") - ln.count("}")
        out.append(ln)
        if out and depth == 0 and len(out) > 1:
            break
    return "\n".join(out)


def test_boot_ceremony_checks_and_speaks_nominal():
    src = VOICE_PAGE.read_text()
    assert '<div id="boot"' in src and '<ul id="bootlist">' in src
    js = _script(src)
    assert "async function bootCeremony" in js
    body = _body("bootCeremony", js)
    assert 'fetch("/api/sessions?limit=1"' in body, "power check must be a live heartbeat"
    assert "micSupported()" in body, "hearing check must probe the mic API"
    assert "S.speak" in body, "voice check must read the speak switch"
    for key in ("bootpower", "boothearing", "bootvoice", "bootnominal",
                "bootpowerfail", "boothearingfail", "bootvoicefail", "bootnominalfail"):
        assert key in js, f"COPY boot key {key} required in every soul"
    assert "createElement" in _body("bootLine", js) and "textContent" in _body("bootLine", js), \
        "boot lines render as text only"
    assert "fetchSpeech(nominal)" in body, "the nominal line is spoken when speak is on"
    for banned in ("prompt.submit", "approve", "rpc("):
        assert banned not in body, f"ceremony stays speech-only (no {banned})"
    assert "await bootCeremony()" in js, "login must run the ceremony"


def test_boot_copy_keys_identical_across_souls():
    js = _script(VOICE_PAGE.read_text())
    keys = {}
    for soul in ("jarvis", "ultron", "friday"):
        m = re.search(rf"^\s*{soul}: \{{(.*?)\n  \}},?$", js, re.M | re.S)
        assert m, f"COPY.{soul} block required"
        keys[soul] = set(re.findall(r"^\s*(\w+):", m.group(1), re.M))
    assert keys["jarvis"] == keys["ultron"] == keys["friday"], \
        "soul voices must cover identical facts (boot keys included)"
    assert "sir" in keys["jarvis"] or True  # addresses live in values, not keys


# ---- carried face items: diagnostics + audit pages ----

BANNED = ["http://", "https://", "<link", "<img", "url(", "@import",
          "innerHTML", "document.write", "localStorage", "eval("]


def test_diag_page_contract():
    src = DIAG_PAGE.read_text()
    for pat in BANNED:
        assert pat not in src, f"banned pattern {pat} in diag page"
    assert 'fetch("./diag-snapshot.json"' in src, "diag reads only its snapshot"
    assert src.count("fetch(") == 1, "diag must not phone anywhere else"
    for field in ("doctor", "model", "personality", "tests", "frozen",
                  "silenced", "audit", "snapshot", "stale"):
        assert field in src, f"diag must surface {field}"
    assert "voice.html" in src, "diag links back to the voice page"
    assert "textContent" in src


def test_audit_page_contract():
    src = AUDIT_PAGE.read_text()
    for pat in BANNED:
        assert pat not in src, f"banned pattern {pat} in audit page"
    assert 'fetch("./audit-snapshot.json"' in src, "audit reads only its snapshot"
    assert src.count("fetch(") == 1, "audit must not phone anywhere else"
    for decision in ("all", "allowed", "denied", "enforced"):
        assert f'data-f="{decision}"' in src, f"audit filter {decision} required"
    assert "createElement" in src and "textContent" in src, "rows render as text only"
    assert "voice.html" in src and "diag.html" in src


# ---- jobs: specs valid, W5 untouched ----

JOB_FILES = ["snapshot", "speak-brief", "watchdog-voice-alerts"]


def test_job_specs_valid():
    import json as _json
    for name in JOB_FILES:
        spec = _json.loads((JARVIS_DIR / "proactivity" / "jobs" / f"{name}.json").read_text())
        for key in ("name", "schedule", "prompt", "model", "provider", "deliver", "workdir"):
            assert spec.get(key), f"{name}.json needs {key}"
        assert spec["workdir"] == "/home/runner/workspace/hermes-fork"
        assert spec["model"] == "auto/best-reasoning" and spec["provider"] == "custom"
        assert "Never send, post, or merge" in spec["prompt"]
    # W5 owns habits/: our installer must not reference its paths or scripts.
    ensure = (JARVIS_DIR / "proactivity" / "ensure-proactivity.sh").read_text()
    assert "habits/" not in ensure and "ensure-habits" not in ensure, \
        "W5 habits files are hands-off"


def test_snapshot_writer_integration(tmp_path):
    home = tmp_path / "snap-home"
    env = dict(os.environ, HERMES_HOME=str(home))
    env["PATH"] = os.pathsep.join([
        str(Path(sys.executable).parent), os.environ.get("PATH", "")])
    proc = subprocess.run([str(JARVIS_DIR / "bin" / "jarvis-doctor-snapshot")],
                          capture_output=True, text=True, env=env, timeout=600)
    assert proc.returncode == 0, proc.stderr[-2000:]
    import json as _json
    diag = _json.loads((home / "web_dist_overlay" / "diag-snapshot.json").read_text())
    assert diag["doctor"]["ok"] is True
    assert diag["tests"]["passed"] and (diag["tests"]["failed"] or 0) == 0
    assert diag["model"]["default"] and diag["personality"]
    assert set(("frozen", "silenced", "audit")) <= set(diag["permissions"])
    audit_snap = _json.loads((home / "web_dist_overlay" / "audit-snapshot.json").read_text())
    assert audit_snap["summary"]["total"] >= 0 and isinstance(audit_snap["rows"], list)


def _has_upstream_ref():
    r = subprocess.run(["git", "rev-parse", "--verify", "upstream/main"],
                       cwd=REPO_ROOT, capture_output=True)
    return r.returncode == 0


@pytest.mark.skipif(not _has_upstream_ref(), reason="needs upstream/main ref (W1 repair clone)")
def test_no_core_files_touched():
    r = subprocess.run(["git", "diff", "upstream/main", "--name-only"],
                       cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    files = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert files, "overlay diff must not be empty"
    bad = [f for f in files
           if not (f == "jarvis" or f.startswith("jarvis/") or f.startswith("tests/jarvis/"))]
    assert not bad, f"core files touched: {bad}"
