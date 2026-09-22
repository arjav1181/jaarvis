"""W14 launch-hardening tests — tooling proofs, no network.

Covers the launch harness itself (all hermetic):
  - smoke script unit parts: page list, gate/auth classifiers, URL
    builder, password loading, report-schema validation, skip-rig path,
    deployed-file comparison against a scratch home
  - wake-list completeness: all 7 dormant hands, each with a reason and
    a wake credential
  - checklist presence: LAUNCH_CHECKLIST.md names every dormant hand
  - lane gates (w20 pattern): turf confinement via merge-base committed
    diff + secrets scan over lane files

Run: `python -m pytest tests/jarvis/test_w14_launch.py -v`
Env honored: none required (JARVIS_* only read by negative-path tests).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from jarvis.launch import smoke as _smoke

REPO_ROOT = str(REPO)

TURF = ("jarvis/launch/", "tests/jarvis/test_w14_launch.py",
        "jarvis/UPSTREAM_PIN.md")

EXPECTED_PAGES = ("voice", "diag", "audit", "apex",
                  "foresight", "hands", "presence", "degraded")

EXPECTED_HANDS = ("GPU", "Discord", "GPT-Live", "Telegram token",
                  "Spotify", "HA", "Car")


# ---------- smoke-script unit parts ----------

def test_pages_cover_all_hud():
    assert tuple(_smoke.PAGES) == EXPECTED_PAGES


def test_gate_classifier():
    for code in (301, 302, 303, 307, 308, 401, 403):
        assert _smoke.gate_ok(code) is True, code
    for code in (200, 404, 500):
        assert _smoke.gate_ok(code) is False, code


def test_auth_classifier():
    assert _smoke.auth_ok(200) is True
    for code in (302, 401, 403, 404, 500):
        assert _smoke.auth_ok(code) is False, code


def test_page_url_builder():
    assert _smoke.page_url("http://127.0.0.1:3000", "voice") == \
        "http://127.0.0.1:3000/voice.html"
    assert _smoke.page_url("http://127.0.0.1:3000/", "apex") == \
        "http://127.0.0.1:3000/apex.html"


def test_load_password_prefers_env(monkeypatch):
    monkeypatch.setenv("JARVIS_RIG_PW", "s3cret")
    monkeypatch.delenv("JARVIS_RIG_PWFILE", raising=False)
    assert _smoke.load_password() == "s3cret"


def test_load_password_reads_pwfile(tmp_path, monkeypatch):
    pwf = tmp_path / "pw.txt"
    pwf.write_text("file-secret\n")
    monkeypatch.delenv("JARVIS_RIG_PW", raising=False)
    monkeypatch.setenv("JARVIS_RIG_PWFILE", str(pwf))
    assert _smoke.load_password() == "file-secret"


def test_load_password_missing_raises(monkeypatch):
    monkeypatch.delenv("JARVIS_RIG_PW", raising=False)
    monkeypatch.delenv("JARVIS_RIG_PWFILE", raising=False)
    with pytest.raises(_smoke.SmokeConfigError):
        _smoke.load_password()


def _mini_report():
    pages = {n: {"unauth": 302, "authed": 200,
                 "unauth_ms": 1.0, "authed_ms": 2.0}
             for n in EXPECTED_PAGES}
    return {"pages": pages, "login_ms": 10.0,
            "text_turn": {"reply_chars": 5},
            "tts": {"ms": 100.0}, "stt": {"ms": 200.0},
            "barge_in": {"barge_ms": 300.0},
            "deployed_match": {n: "match" for n in EXPECTED_PAGES}}


def test_validate_report_accepts_good():
    assert _smoke.validate_report(_mini_report()) is True


def test_validate_report_rejects_bad_shape():
    good = _mini_report()
    bad = dict(good)
    del bad["tts"]
    with pytest.raises(ValueError):
        _smoke.validate_report(bad)
    bad2 = dict(good)
    bad2["pages"] = {"voice": good["pages"]["voice"]}
    with pytest.raises(ValueError):
        _smoke.validate_report(bad2)


def test_skip_rig_needs_no_network(monkeypatch):
    monkeypatch.setenv("JARVIS_SMOKE_SKIP_RIG", "1")
    monkeypatch.delenv("JARVIS_RIG_PW", raising=False)
    monkeypatch.delenv("JARVIS_RIG_PWFILE", raising=False)
    rep = _smoke.run(skip_rig=True)
    assert rep["skipped_rig"] is True
    assert rep["text_turn"] == {"skipped": "env"}


def test_deployed_match_branches(tmp_path):
    home = tmp_path / "home"
    overlay = home / "web_dist_overlay"
    overlay.mkdir(parents=True)
    (overlay / "voice.html").write_bytes(
        (REPO / "jarvis" / "hud" / "voice.html").read_bytes())
    (overlay / "diag.html").write_text("stale")
    got = _smoke.check_deployed_match(home)
    assert got["voice"] == "match"
    assert got["diag"] == "differs"
    assert got["apex"] == "not-deployed"


# ---------- wake-list completeness ----------

def test_wake_list_completeness():
    hands = _smoke.wake_list()
    assert [h["hand"] for h in hands] == list(EXPECTED_HANDS)
    for h in hands:
        assert h["absent_reason"].strip(), h["hand"]
        assert h["wakes_with"].strip(), h["hand"]


def test_checklist_names_every_dormant_hand():
    doc = (REPO / "jarvis" / "launch" / "LAUNCH_CHECKLIST.md").read_text()
    for hand in EXPECTED_HANDS:
        assert hand in doc, "checklist must document %s" % hand


# ---------- lane gates: turf, secrets (w20 pattern) ----------

def _lane_files():
    # Committed-diff (not worktree) so parallel lanes sharing one checkout
    # cannot contaminate this gate with their uncommitted files. W14 owns
    # the merge-train sync, so merge commits are excluded: turf is what the
    # lane's own (non-merge) commits add atop the merge-base with
    # origin/jarvis, plus uncommitted worktree files (this worktree is
    # dedicated to w14). Mirrors the w20 committed-diff pattern.
    base = subprocess.run(
        ["git", "merge-base", "origin/jarvis", "w14-launch"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    log = subprocess.run(
        ["git", "log", "--no-merges", "--first-parent", "--name-only",
         "--pretty=format:", "--diff-filter=ACMRT",
         "%s..w14-launch" % base.stdout.strip()],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    files = [ln.strip() for ln in log.stdout.splitlines() if ln.strip()]
    st = subprocess.run(["git", "status", "--short"],
                        cwd=REPO_ROOT, capture_output=True, text=True,
                        check=True)
    for ln in st.stdout.splitlines():
        if not ln.strip():
            continue
        path = ln[3:] if len(ln) > 3 else ""
        if " -> " in path:  # rename: take the new side
            path = path.split(" -> ")[-1].strip()
        path = path.strip().strip('"')
        if path and path not in files:
            files.append(path)
    if not files:
        # Pre-commit the branch diff is empty: verify the landed files.
        landed = []
        for t in TURF:
            p = REPO / t
            if p.is_dir():
                landed += [str(x.relative_to(REPO_ROOT))
                           for x in p.rglob("*") if x.is_file()]
            elif p.exists():
                landed.append(t)
        files = landed
    return sorted(set(files))


def test_overlay_stays_inside_turf():
    files = _lane_files()
    assert files, "lane must add files"
    bad = [f for f in files
           if not any(f == t or f.startswith(t) for t in TURF)]
    assert not bad, "out-of-turf files touched: %s" % (bad,)


def test_no_secrets_in_lane_files():
    pats = [re.compile(r"(?i)\bapi[_-]?key\s*=\s*['\"][^'\"]+['\"]"),
            re.compile(r"sk-[A-Za-z0-9]{8,}"),
            re.compile(r"gho_[A-Za-z0-9]+"),
            re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]{8,}"),
            re.compile(r"(?i)password\s*=\s*['\"][^'\"]+['\"]")]
    roots = [REPO / "jarvis" / "launch", Path(__file__)]
    paths = []
    for root in roots:
        if root.is_dir():
            paths += [p for p in root.rglob("*") if p.is_file()]
        else:
            paths.append(root)
    assert paths
    for p in paths:
        text = p.read_text(errors="replace")
        for pat in pats:
            assert not pat.search(text), "secret pattern in %s" % p
