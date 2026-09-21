"""W5 (skills + habits + fleet) suite — hermetic, no model calls.

Covers: repeatable skill port (deterministic, committed == generated,
manifest shas), Hermes frontmatter validity, /learn KB skill (verbatim
references, no secrets), cron job specs (schedules parse via the real
cron.jobs parser, pins + continuity + delivery set, monitor stability
 contract), kanban board spec (profiles, PR contracts), curator pins,
 overlay-only discipline, W4 test-contracts untouched (voice.html evolves
 under W13 — see test_w13_face.py).
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "jarvis" / "skills"
HABITS = REPO_ROOT / "jarvis" / "habits"
KANBAN = REPO_ROOT / "jarvis" / "kanban"
CURATOR = REPO_ROOT / "jarvis" / "curator"
FROZEN = Path("/home/runner/workspace/jarvis")
PORT_SCRIPT = REPO_ROOT / "jarvis" / "skills-port" / "port_skills.py"

REQUIRED_FM = {"name", "description", "version", "author", "license",
               "platforms", "x-jarvis-tier", "x-jarvis-trigger"}
SECRET_RE = re.compile(
    r"sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]+|xox[bap]-|AKIA[0-9A-Z]{10,}|"
    r"BEGIN [A-Z ]*PRIVATE KEY")


def read_skill(name):
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def frontmatter(text):
    assert text.startswith("---\n"), "missing frontmatter fence"
    end = text.index("\n---", 4)
    fm = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm


def skill_names():
    return sorted(p.name for p in SKILLS.iterdir()
                  if p.is_dir() and (p / "SKILL.md").is_file())


def test_port_deterministic_and_committed():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "gen"
        for _ in range(2):
            r = subprocess.run(["python3", str(PORT_SCRIPT), "--src", str(FROZEN),
                                "--out", str(out)], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
        first = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    second_run = subprocess.run(
        ["python3", str(PORT_SCRIPT), "--src", str(FROZEN), "--out", str(out)],
        capture_output=True, text=True)
    assert second_run.returncode == 0
    again = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    assert first == again, "port script not deterministic"
    manifest = json.loads((SKILLS / "manifest.json").read_text())
    generated = {e["name"] for e in manifest["skills"]}
    for name in generated:
        gen = (out / name / "SKILL.md").read_bytes()
        committed = (SKILLS / name / "SKILL.md").read_bytes()
        assert gen == committed, f"committed {name} != generated output"
    assert json.loads((out / "manifest.json").read_text()) == manifest


def test_manifest_shas():
    manifest = json.loads((SKILLS / "manifest.json").read_text())
    assert len(manifest["skills"]) >= 4
    for e in manifest["skills"]:
        raw = (SKILLS / e["name"] / "SKILL.md").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == e["sha256"], e["name"]
        assert (FROZEN / e["source"]).is_file(), e["source"]


def test_skill_frontmatter_all():
    names = skill_names()
    assert len(names) >= 7, names
    for name in names:
        fm = frontmatter(read_skill(name))
        missing = REQUIRED_FM - set(fm)
        assert not missing, f"{name}: missing {missing}"
        assert fm["name"] == name
        assert fm["x-jarvis-tier"] in {"L0", "L1", "L2"}, name
        assert fm["x-jarvis-trigger"].strip('"').strip(), name
        assert fm["x-jarvis-trigger"].strip('"') in fm["description"], name
        assert "metadata:" in read_skill(name) and "hermes:" in read_skill(name)


def test_ported_bodies_verbatim():
    manifest = json.loads((SKILLS / "manifest.json").read_text())
    for e in manifest["skills"]:
        frozen = (FROZEN / e["source"]).read_text(encoding="utf-8")
        body_frozen = frozen.split("---", 2)[-1] if frozen.startswith("---") else frozen
        ported = read_skill(e["name"])
        body_ported = ported.split("---", 2)[-1]
        assert body_ported.strip() == body_frozen.strip(), e["name"]


def test_no_home_paths_in_skills():
    for name in skill_names():
        assert "/home/" not in read_skill(name), name
        assert "/root/" not in read_skill(name), name


def test_kb_references_verbatim_and_secret_free():
    refs = SKILLS / "jarvis-kb" / "references"
    for doc in ("PRD.md", "TRD.md", "ARCHITECTURE.md", "SKILLS.md", "CONNECTORS.md"):
        assert (refs / doc).read_bytes() == (FROZEN / doc).read_bytes(), doc
    assert not list(SKILLS.rglob("password.txt")), "password.txt leaked in"
    assert not list(SKILLS.rglob("token.txt")), "token.txt leaked in"
    hay = "".join(p.read_text(encoding="utf-8", errors="replace")
                  for p in (SKILLS / "jarvis-kb").rglob("*") if p.is_file())
    assert not SECRET_RE.search(hay), "secret pattern in jarvis-kb"


def test_job_specs():
    from cron.jobs import parse_schedule
    skills = set(skill_names())
    for spec_f in sorted((HABITS / "jobs").glob("*.json")):
        spec = json.loads(spec_f.read_text())
        for k in ("name", "schedule", "prompt", "skills", "model", "provider",
                  "continuity", "deliver", "failure_deliver", "workdir",
                  "monitor_script"):
            assert k in spec, f"{spec_f.name}: missing {k}"
        assert spec_f.stem == spec["name"], "filename must match job name"
        parsed = parse_schedule(spec["schedule"])
        assert parsed["kind"] in {"cron", "interval", "once"}, spec["schedule"]
        assert spec["skills"] and set(spec["skills"]) <= skills, spec["skills"]
        assert spec["model"] and spec["provider"], "model/provider pins required"
        assert spec["continuity"] is True, "continuable threads required"
        assert spec["deliver"], "delivery target required"
        assert spec["workdir"] == str(REPO_ROOT), "workdir must be the fork"
        assert len(spec["prompt"]) > 50, "prompt must be self-contained"
        ms = spec["monitor_script"]
        if ms is not None:
            assert (HABITS / "scripts" / ms).is_file(), ms


def test_monitor_script_contract():
    s = HABITS / "scripts" / "ci-fingerprint.sh"
    r = subprocess.run(["bash", "-n", str(s)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    text = s.read_text()
    for banned in ("`date`", "$(date", "%Y", "%m", "%d", "%H", "%M", "%S",
                   "datetime", "timestamp("):
        assert banned not in text, f"clock call in monitor: {banned}"
    assert "gh run list" in text and "gh-unavailable" in text


def test_kanban_spec():
    spec = json.loads((KANBAN / "jarvis-ops.json").read_text())
    assert spec["board"] == "jarvis-ops" and spec["description"]
    roles = {p["name"]: p for p in spec["profiles"]}
    assert {p["role"] for p in spec["profiles"]} == {"orchestrator", "worker"}
    for p in spec["profiles"]:
        assert len(p["description"]) > 50, p["name"]
    keys = set()
    for t in spec["tasks"]:
        for k in ("key", "title", "body", "assignee", "priority",
                  "completion_contract"):
            assert t.get(k), f"task missing {k}"
        assert t["assignee"] in roles, t["key"]
        assert re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
                            t["completion_contract"]), t["key"]
        assert "PR contract:" in t["body"], t["key"]
        assert t["key"] not in keys, "idempotency keys unique"
        keys.add(t["key"])
    assert (KANBAN / "PR_CONTRACTS.md").is_file()


def test_curator_pins():
    pins = [ln.strip() for ln in (CURATOR / "pins.txt").read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]
    assert len(pins) >= 7
    assert set(pins) <= set(skill_names()), "every pin must be a Jarvis skill"


def test_no_core_files_touched():
    r = subprocess.run(["git", "diff", "upstream/main", "--name-only"],
                       cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    files = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert files, "overlay diff must not be empty"
    bad = [f for f in files
           if not (f == "jarvis" or f.startswith("jarvis/") or f.startswith("tests/jarvis/"))]
    assert not bad, f"core files touched: {bad}"


def test_w4_files_untouched():
    # W13 supersedes the voice.html pin: the HUD face wave intentionally
    # evolves jarvis/hud/voice.html (see tests/jarvis/test_w13_face.py).
    # The W4 *test contracts* stay pinned — W3/W4 suites still run green
    # against the evolved page, which is the real guard.
    for path in ("tests/jarvis/test_w4_talk.py",
                 "tests/jarvis/test_w3_bvoice.py"):
        r = subprocess.run(["git", "diff", "--quiet", "origin/jarvis", "--", path],
                           cwd=REPO_ROOT, capture_output=True, text=True)
        assert r.returncode == 0, f"W4 file touched: {path}"
