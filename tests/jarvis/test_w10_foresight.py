"""W10 foresight tests — hermetic (temp HERMES_HOME, no network, no models)."""
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from jarvis.foresight import brief as br
from jarvis.foresight import calibrate as cal
from jarvis.foresight import ledger as lg
from jarvis.foresight import runner as rn
from jarvis.foresight import snapshot as snap
from jarvis.foresight.suites import compute_expr, load_suite, validate_delegate_tasks


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))


def _rec(**kw):
    d = {"question": "Will it rain?", "predicted": "yes",
         "confidence": 0.7, "horizon": "2026-12-31"}
    d.update(kw)
    r = lg.record(**d)
    assert r["ok"], r
    return r["entry"]


# --- ledger ---

def test_record_and_ids():
    e1 = _rec()
    e2 = _rec(question="Other?")
    assert e1["id"].startswith("F-") and e1["status"] == "open"
    assert e1["id"] != e2["id"]
    assert lg.summary()["open"] == 2


def test_record_rejects_bad_input():
    assert lg.record("", "yes", 0.7, "2026-12-31")["ok"] is False
    assert lg.record("q", "yes", 1.5, "2026-12-31")["ok"] is False
    assert lg.record("q", "yes", "high", "2026-12-31")["ok"] is False
    assert lg.record("q", "yes", 0.7, "tomorrow")["ok"] is False


def test_resolve_verdict_and_double_resolve():
    e = _rec(predicted="yes")
    r = lg.resolve(e["id"], "YES", note="rained")
    assert r["ok"] and r["entry"]["correct"] is True
    assert r["entry"]["status"] == "resolved"
    assert lg.resolve(e["id"], "yes") == {"ok": False, "reason": "already_resolved"}
    assert lg.resolve("F-20990101-999", "yes") == {"ok": False, "reason": "unknown_id"}


def test_resolve_wrong_outcome_is_incorrect():
    e = _rec(predicted="yes")
    r = lg.resolve(e["id"], "no")
    assert r["ok"] and r["entry"]["correct"] is False


def test_overdue_lists_only_past_open():
    a = _rec(question="past?", horizon="2020-01-01")
    _rec(question="future?", horizon="2099-01-01")
    ids = [e["id"] for e in lg.overdue(today="2026-01-01")]
    assert ids == [a["id"]]


# --- calibration ---

def test_calibration_unscored_when_empty():
    c = cal.score([])
    assert c["scored"] is False and "unscored" in c["note"]


def test_calibration_counts_and_brier():
    for i in range(8):
        e = _rec(question=f"q{i}?", confidence=0.8)
        lg.resolve(e["id"], "yes")
    for i in range(2):
        e = _rec(question=f"w{i}?", confidence=0.8)
        lg.resolve(e["id"], "no")
    c = cal.score(lg.list_entries())
    assert c["accuracy"] == "8/10" and c["resolved"] == 10
    assert c["rate"] == pytest.approx(0.8)
    # Brier: 8x(0.8-1)^2 + 2x(0.8-0)^2 over 10 = (0.32+1.28)/10
    assert c["brier"] == pytest.approx(0.16)
    hot = next(b for b in c["buckets"] if b["lo"] == 0.8)
    assert (hot["n"], hot["hits"]) == (10, 8)
    assert "right 8/10" in cal.headline(c)


# --- compute evaluator ---

def test_compute_arithmetic():
    assert compute_expr("a * 2 + b", {"a": 3, "b": 4}) == 10.0
    assert compute_expr("(x - y) / z", {"x": 9, "y": 3, "z": 2}) == 3.0


def test_compute_rejects_hostile_exprs():
    for bad in ("__import__('os').system('x')", "a.attr", "f(1)",
                "a + unknown", "[1,2]", "'str'", "a if b else c"):
        with pytest.raises(ValueError):
            compute_expr(bad, {"a": 1, "b": 2, "f": 3})
    with pytest.raises(ValueError):
        compute_expr("a + b", {"a": True, "b": 1})
    with pytest.raises(ZeroDivisionError):
        compute_expr("a / b", {"a": 1, "b": 0})


# --- suite loading ---

def test_example_suite_loads():
    p = REPO / "jarvis" / "foresight" / "suites" / "monthly-numbers.example.json"
    suite, errors = load_suite(p)
    assert errors == [] and suite["name"] == "monthly-numbers"
    assert {s["kind"] for s in suite["scenarios"]} == {"compute", "predict", "delegate"}


def test_suite_rejects_bad_shapes(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"name": "", "scenarios": [{"kind": "nope"}]}))
    suite, errors = load_suite(bad)
    assert suite is None and len(errors) >= 2
    bad.write_text(json.dumps({"name": "x", "scenarios": [
        {"id": "p", "kind": "predict", "question": "q",
         "predicted": "y", "confidence": 9, "horizon": "2026-01-01"}]}))
    assert load_suite(bad)[1] != []


def test_delegate_gate_mirrors_upstream():
    ok = [{"goal": "Gather the last 7 days of watchdog outcomes with counts."}]
    assert validate_delegate_tasks(ok) is None
    short = [{"goal": "Gather the failure counts please"}, {"goal": "fix it"}]
    assert "too short" in validate_delegate_tasks(short)
    marked = [{"goal": "Check <thing to check> now please hurry"}]
    assert "template" in validate_delegate_tasks(marked)


# --- runner ---

def test_run_suite_executes_records_plans(tmp_path):
    suite = {"name": "t", "scenarios": [
        {"id": "c1", "kind": "compute", "inputs": {"a": 2}, "expr": "a * 21"},
        {"id": "c2", "kind": "compute", "inputs": {"a": 1}, "expr": "a / 0"},
        {"id": "p1", "kind": "predict", "question": "Q?", "predicted": "yes",
         "confidence": 0.6, "horizon": "2099-01-01"},
        {"id": "d1", "kind": "delegate",
         "goal": "Summarize yesterday's cron outcomes from the local logs."},
    ]}
    r1 = rn.run_suite(suite, author="tester")
    assert r1["computed"][0]["id"] == "c1" and r1["computed"][0]["ok"] is True
    assert r1["computed"][0]["value"] == 42.0 and "ms" in r1["computed"][0]
    assert r1["computed"][1]["ok"] is False
    assert r1["recorded"][0]["ok"] is True
    assert r1["delegate"]["ok"] and r1["delegate"]["tool"] == "delegate_task"
    assert "agent loop" in r1["delegate"]["executes_in"]
    # Rerun: compute reruns, predict dedupes, receipt persisted again.
    r2 = rn.run_suite(suite, author="tester")
    assert r2["recorded"][0]["duplicate"] is True
    assert r2["recorded"][0]["entry_id"] == r1["recorded"][0]["entry_id"]
    assert lg.summary()["open"] == 1
    assert len(rn.recent_runs()) == 2


# --- brief + snapshot ---

def test_brief_headline_tracks_ledger():
    b = br.build()
    assert "unscored" in b["headline"] and "No suite runs yet" in b["text"]
    e = _rec()
    lg.resolve(e["id"], "yes")
    b2 = br.build()
    assert "right 1/1" in b2["headline"]


def test_snapshot_builds_and_writes():
    s = snap.build()
    assert s["example_suite"]["valid"] is True
    assert "calibration" in s and "overdue" in s
    p = Path(os.environ["HERMES_HOME"]) / "jarvis" / "foresight" / "foresight-snapshot.json"
    assert p.exists() and json.loads(p.read_text())["built_at"] == s["built_at"]


def test_hud_page_contract():
    src = (REPO / "jarvis" / "hud" / "foresight.html").read_text()
    assert 'fetch("./foresight-snapshot.json"' in src
    for pat in ["http://", "https://", "<img", "url(", "@import",
                "innerHTML", "document.write", "localStorage", "eval("]:
        assert pat not in src, f"banned pattern {pat}"
    assert "textContent" in src
