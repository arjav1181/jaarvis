"""W18 self-improvement loop tests — hermetic (temp HERMES_HOME, no network,
no models, no subprocess; the live executor is always a stub)."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from jarvis.curator import loop_trim as trim
from jarvis.kanban import loop_cards as cards
from jarvis.loop import miners
from jarvis.loop import run as looprun
from jarvis.loop import report as loopreport

SECRET_RE = re.compile(
    r"sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]+|xox[bap]-|AKIA[0-9A-Z]{10,}|"
    r"BEGIN [A-Z ]*PRIVATE KEY")

OWNED_NEW = [
    REPO / "jarvis" / "loop" / "__init__.py",
    REPO / "jarvis" / "loop" / "__main__.py",
    REPO / "jarvis" / "loop" / "_common.py",
    REPO / "jarvis" / "loop" / "miners.py",
    REPO / "jarvis" / "loop" / "report.py",
    REPO / "jarvis" / "loop" / "run.py",
    REPO / "jarvis" / "loop" / "README.md",
    REPO / "jarvis" / "loop" / "ensure-loop.sh",
    REPO / "jarvis" / "loop" / "weekly-review.example.json",
    REPO / "jarvis" / "kanban" / "loop_cards.py",
    REPO / "jarvis" / "curator" / "loop_trim.py",
]

PROTECTED = [  # W5-owned: byte-identical to origin/jarvis, always.
    REPO / "jarvis" / "kanban" / "ensure-kanban.sh",
    REPO / "jarvis" / "kanban" / "jarvis-ops.json",
    REPO / "jarvis" / "kanban" / "PR_CONTRACTS.md",
    REPO / "jarvis" / "curator" / "ensure-curator.sh",
    REPO / "jarvis" / "curator" / "pins.txt",
]

FORBIDDEN_IMPORTS = ("jarvis.hud", "jarvis.personas", "jarvis.soul",
                     "jarvis.permissions", "jarvis.proactivity",
                     "jarvis.habits", "jarvis.foresight", "jarvis.hands",
                     "jarvis.presence", "jarvis.apex")


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("JARVIS_LOOP_LIVE", raising=False)


# --- miners: red tests ---

def test_mine_red_tests_only():
    text = ("tests/jarvis/test_w9_presence.py::test_x - assert False\n"
            "FAILED tests/jarvis/test_w9_presence.py::test_stale - assert False\n"
            "ERROR tests/jarvis/test_w4_talk.py::test_cb - fixture 'm' not found\n"
            "1 failed, 1 error in 3.21s\n")
    found = miners.parse_pytest_summary(text)
    assert [(f["kind"], f["id"]) for f in found] == [
        ("red-test", "tests/jarvis/test_w9_presence.py::test_stale"),
        ("red-test", "tests/jarvis/test_w4_talk.py::test_cb")]
    assert all(f["citation"] for f in found)


def test_mine_red_tests_empty_week():
    assert miners.parse_pytest_summary("") == []
    assert miners.parse_pytest_summary("7 passed, 2 skipped in 1.0s\n") == []
    assert miners.parse_pytest_summary(None) == []


def test_mine_dedupes_repeated_lines():
    line = "FAILED a.py::test_t - boom\n"
    assert len(miners.parse_pytest_summary(line * 3)) == 1


# --- miners: cron runs + refusals ---

def test_mine_cron_failures_only():
    rows = [
        {"job": "ci-watchdog", "run_id": "r1", "conclusion": "failed",
         "ts": "2026-09-18T07:31:00Z", "detail": "gate red"},
        {"job": "morning-brief", "run_id": "r2", "conclusion": "completed",
         "ts": "2026-09-18T07:00:00Z", "detail": "ok"},
        {"job": "x", "run_id": "r3", "status": "cancelled", "detail": "op"},
        {"job": "y", "run_id": "r4", "status": "timed_out", "detail": "hung"},
    ]
    found = miners.parse_cron_runs(rows)
    assert [(f["kind"], f["id"]) for f in found] == [
        ("cron-failed", "ci-watchdog/r1"), ("cron-failed", "y/r4")]
    # JSONL text input works too.
    jsl = "\n".join(json.dumps(r) for r in rows)
    assert miners.parse_cron_runs(jsl) == found


def test_mine_refusals_denied_and_enforced_only():
    rows = [
        {"ts": "t1", "actor": "w", "action": "ship-pr:merge",
         "decision": "denied", "detail": "red"},
        {"ts": "t2", "actor": "w", "action": "hands:kill",
         "decision": "enforced", "detail": "L2"},
        {"ts": "t3", "actor": "w", "action": "memory:recall",
         "decision": "allowed", "detail": ""},
    ]
    found = miners.parse_refusals(rows)
    assert [f["kind"] for f in found] == ["refused-act"] * 2
    assert found[0]["citation"] == "audit ts=t1 actor=w action=ship-pr:merge"


def test_mine_all_counts():
    m = miners.mine_all("FAILED a.py::test_t - x\n",
                        [{"job": "j", "run_id": "r", "conclusion": "failed"}],
                        [{"ts": "t", "actor": "a", "action": "x",
                          "decision": "allowed"}])
    assert m["counts"] == {"red-test": 1, "cron-failed": 1, "refused-act": 0}
    assert m["total"] == 2


# --- kanban cards ---

def _finding(kind="red-test", fid="a.py::test_t"):
    return {"kind": kind, "id": fid, "title": f"{kind} {fid}",
            "citation": f"cite {fid}", "detail": "boom"}


def test_cards_one_per_finding_with_contracts():
    made = cards.build_fix_cards([_finding(),
                                  _finding("refused-act", "t/a/x")])
    assert len(made) == 2
    assert made[0]["assignee"] == "jarvis-worker"
    assert made[1]["assignee"] == "jarvis-orchestrator" and made[1]["triage"]
    keys = [c["idempotency_key"] for c in made]
    assert len(set(keys)) == 2 and all(k.startswith("jarvis-loop:") for k in keys)
    skills = set(trim.inventory_skills(REPO))
    for c in made:
        assert cards.validate_card(c, skills) == []
        assert "PR contract:" in c["body"] and "Citation:" in c["body"]
        assert re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
                            c["completion_contract"])


def test_cards_stable_keys_and_overflow_cap():
    many = [_finding(fid=f"a.py::test_{i}") for i in range(25)]
    first = cards.build_fix_cards(many)
    second = cards.build_fix_cards(many)
    assert [c["key"] for c in first] == [c["key"] for c in second]
    assert len(first) == cards.MAX_CARDS
    assert first[-1]["triage"] and "overflow" in first[-1]["key"]


def test_cards_validate_rejects_bad_shapes():
    bad = dict(_finding())
    c = cards.build_fix_cards([bad])[0]
    c["body"] = "no contract here"
    assert cards.validate_card(c) != []
    c2 = dict(cards.build_fix_cards([bad])[0])
    c2["completion_contract"] = "not-a-target"
    assert cards.validate_card(c2) != []


def test_cards_to_create_args_idempotent():
    c = cards.build_fix_cards([_finding()])[0]
    argv = cards.to_create_args(c)
    assert argv[:4] == ["hermes", "kanban", "--board", "jarvis-ops"]
    assert "--idempotency-key" in argv and "--triage" not in argv
    tri = cards.build_fix_cards([_finding("refused-act", "t/a/x")])[0]
    assert "--triage" in cards.to_create_args(tri)


# --- curator trims ---

def test_trim_pins_fenced_and_dead_cited():
    pins = ["explain-error", "ship-pr"]
    skills = ["explain-error", "ship-pr", "old-tool"]
    usage = {"old-tool": {"uses": 0, "last_used": ""}}
    r = trim.candidate_trims(skills, pins, usage, today="2026-09-22")
    assert [c["skill"] for c in r["candidates"]] == ["old-tool"]
    assert "pinned" in r and set(r["pinned"]) == {"explain-error", "ship-pr"}
    assert "curator usage old-tool" in r["candidates"][0]["citation"]


def test_trim_stale_and_unknown_usage():
    skills = ["fresh", "stale", "mystery"]
    usage = {"fresh": {"uses": 3, "last_used": "2026-09-20"},
             "stale": {"uses": 2, "last_used": "2026-01-01"}}
    r = trim.candidate_trims(skills, [], usage, today="2026-09-22")
    assert [c["skill"] for c in r["candidates"]] == ["stale"]
    assert r["unknown"] == ["mystery"]
    plan = trim.render_trim_plan(r)
    assert "hermes curator archive stale" in plan
    assert "pinned skills are fenced" in plan


def test_trim_pins_subset_of_inventory():
    pins = trim.load_pins()
    assert len(pins) >= 7
    assert set(pins) <= set(trim.inventory_skills(REPO))


# --- runner: dry-run default, two-key live gate ---

def test_run_dry_run_changes_nothing_but_files_report():
    calls = []
    receipt = looprun.run(pytest_text="FAILED a.py::test_t - x\n",
                          cron_records=[],
                          audit_rows=[],
                          usage={"a": {"uses": 1, "last_used": "2026-09-22"}},
                          executor=calls.append)
    assert receipt["ok"] and receipt["mode"] == "dry-run"
    assert calls == [], "dry-run must never touch the executor"
    assert receipt["total"] == 1 and len(receipt["cards"]) == 1
    assert receipt["card_errors"] == []
    md = Path(receipt["report"]["md"])
    assert md.is_file() and "weekly report (dry-run)" in md.read_text()


def test_run_live_refused_without_env_flag():
    calls = []
    receipt = looprun.run(pytest_text="FAILED a.py::test_t - x\n",
                          live=True, executor=calls.append)
    assert receipt == {"ok": False, "reason": "live-needs-flag",
                       "hint": receipt["hint"]}
    assert calls == []


def test_run_live_dispatches_with_flag_and_cites_failures(monkeypatch):
    monkeypatch.setenv("JARVIS_LOOP_LIVE", "1")
    calls = []

    def rec(argv):
        calls.append(argv)
        return "task T-1"
    receipt = looprun.run(pytest_text="FAILED a.py::test_t - x\n",
                          live=True, executor=rec)
    assert receipt["mode"] == "live"
    assert len(calls) == 1 and "--idempotency-key" in calls[0]
    assert receipt["executed"] == [{"key": receipt["cards"][0]["key"],
                                    "ok": True, "result": "task T-1"}]


def test_run_live_executor_error_cited_not_raised(monkeypatch):
    monkeypatch.setenv("JARVIS_LOOP_LIVE", "1")

    def boom(argv):
        raise RuntimeError("kanban down")
    receipt = looprun.run(pytest_text="FAILED a.py::test_t - x\n",
                          live=True, executor=boom)
    assert receipt["executed"][0]["ok"] is False
    assert "kanban down" in receipt["executed"][0]["result"]


def test_run_never_archives_even_live(monkeypatch):
    monkeypatch.setenv("JARVIS_LOOP_LIVE", "1")
    calls = []
    receipt = looprun.run(pytest_text="", usage={},
                          live=True, executor=calls.append)
    assert calls == [], "no cards means no dispatches even live"
    assert "nothing archived" in receipt["trim_plan"]
    # With a dead skill present, the plan still only previews hand-run cmds.
    review = trim.candidate_trims(["old-tool"], [], {"old-tool": {"uses": 0}},
                                  today="2026-09-22")
    plan = trim.render_trim_plan(review)
    assert "hermes curator archive old-tool" in plan
    assert "confirm by hand" in plan


def test_run_empty_week_report_is_honest():
    receipt = looprun.run()
    assert receipt["total"] == 0 and receipt["cards"] == []
    text = Path(receipt["report"]["md"]).read_text()
    assert "No failing signals this week" in text
    assert "No cards drafted" in text


def test_demo_inputs_labelled_and_mineable():
    d = looprun.demo_inputs()
    assert d["pytest_text"] and d["cron_records"] and d["audit_rows"]
    m = miners.mine_all(d["pytest_text"], d["cron_records"], d["audit_rows"])
    assert m["total"] == 2 + 1 + 1  # 2 red, 1 failed cron, 1 refusal


# --- lane discipline: turf, secrets, home ---

def test_owned_files_exist_and_are_secret_free():
    for p in OWNED_NEW:
        assert p.is_file(), f"missing owned file {p}"
        assert not SECRET_RE.search(p.read_text(encoding="utf-8",
                                                errors="replace")), p


def test_protected_w5_files_untouched():
    for p in PROTECTED:
        r = subprocess.run(["git", "diff", "--quiet", "origin/jarvis", "--",
                            str(p.relative_to(REPO))],
                           cwd=REPO, capture_output=True)
        assert r.returncode == 0, f"W5 file touched: {p}"


def test_no_forbidden_imports_in_lane_sources():
    lane = [REPO / "jarvis" / "loop" / f for f in
            ("__init__.py", "__main__.py", "_common.py", "miners.py",
             "report.py", "run.py")]
    lane += [REPO / "jarvis" / "kanban" / "loop_cards.py",
             REPO / "jarvis" / "curator" / "loop_trim.py"]
    for p in lane:
        src = p.read_text(encoding="utf-8")
        for mod in FORBIDDEN_IMPORTS:
            assert f"from {mod}" not in src and f"import {mod}" not in src, \
                f"{p.name} reaches into {mod}"
        assert not SECRET_RE.search(src), p


def test_home_must_be_explicit(monkeypatch):
    from jarvis.loop import _common as common
    monkeypatch.delenv("HERMES_HOME", raising=False)
    with pytest.raises(SystemExit):
        common.home()


def test_ensure_loop_syntax():
    r = subprocess.run(["bash", "-n", str(REPO / "jarvis" / "loop" / "ensure-loop.sh")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    spec = json.loads((REPO / "jarvis" / "loop" / "weekly-review.example.json").read_text())
    assert spec["schedule"] == "0 18 * * FRI"
    assert spec["workdir"] == str(REPO)
    assert "Never send, post, or merge" in spec["prompt"]
