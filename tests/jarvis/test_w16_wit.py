"""W16 wit engine tests — running jokes, Ultron roast mode, occasion depth.

Scripted taste probes with deterministic PASS criteria (structure /
citation / word-lists), never vibes: every probe asserts exact citation
ids, required words, and banned words on fixed fixtures.

Hermetic: tmp HERMES_HOMEs, no network. Run with the W0 venv active:
`python -m pytest tests/jarvis/test_w16_wit.py -v`
"""

import datetime as _dt
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
JARVIS_DIR = REPO_ROOT / "jarvis"
sys.path.insert(0, str(JARVIS_DIR / "soul"))

import depth  # noqa: E402
import wit  # noqa: E402

REPO_ROOT_STR = str(REPO_ROOT)

TURF = ("jarvis/soul/", "jarvis/personas/", "jarvis/SOUL.jarvis.md",
        "jarvis/SOUL.ultron.md", "jarvis/SOUL.friday.md",
        "tests/jarvis/test_w16_wit.py")

ENTRIES = [
    "Sir prefers Earl Grey, Ultron mocked the kettle on 2026-09-10.",
    "Ada's birthday is March 3 — cake, candles, no surprises.",
    "The team's launch anniversary is September 23, first deploy at dawn.",
    "Friday filed the expense report without being asked twice.",
]

SAFETY_ENTRIES = [
    "The operator talked about suicide and needing help last Tuesday.",
    "Plan to delete the production database before the migration.",
    "The wifi password is hunter2-hunter2, do not share it.",
    "The doctor prescribed new medical dosage instructions.",
]

ADDRESS = {"jarvis": "sir", "ultron": "creator", "friday": "boss"}

W4_HEADS = {
    "jarvis": {"start": "Working on it, sir.", "tool": "On it, sir.",
               "done": "Done, sir."},
    "ultron": {"start": "Ah, the little wheels turn, creator.",
               "tool": "Savor the machinery, creator.",
               "done": "Behold — finished."},
}


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))


# ---------- running jokes: cited, never fabricated ----------

def test_running_joke_cites_memory_and_returns_none_on_miss():
    """PASS: keyword hit carries citation id + cited words + address."""
    hit = wit.running_joke("earl grey kettle", ENTRIES, soul="jarvis")
    assert hit is not None
    assert "memory #1" in hit and "Earl Grey" in hit and "sir" in hit
    hit2 = wit.running_joke("expense report", ENTRIES, soul="friday")
    assert hit2 is not None and "memory #4" in hit2 and "boss" in hit2
    # Misses stay silent — no source material, no joke, never invented.
    assert wit.running_joke("submarine", ENTRIES) is None
    assert wit.running_joke("earl", []) is None
    assert wit.running_joke(None, []) is None
    # Bare keyword rotates like no keyword (documented rotation mode).
    bare = wit.running_joke("", ENTRIES)
    assert bare is not None and "memory #1" in bare


def test_running_joke_no_keyword_rotates_deterministically():
    """PASS: keyword-less rotation cites entries in order, stable per n."""
    first = [wit.running_joke(None, ENTRIES, soul="jarvis", n=n)
             for n in range(4)]
    assert all(j is not None for j in first)
    assert ["memory #1" in first[0], "memory #2" in first[1],
            "memory #3" in first[2], "memory #4" in first[3]] == [True] * 4
    assert wit.running_joke(None, ENTRIES, soul="jarvis", n=0) == first[0]
    assert wit.running_joke(None, ENTRIES, soul="jarvis", n=4) is not None
    # Wrap-around reaches the first entry again (4 entries).
    assert "memory #1" in wit.running_joke(None, ENTRIES, soul="jarvis", n=4)
    for soul, addr in ADDRESS.items():
        line = wit.running_joke("expense", ENTRIES, soul=soul)
        assert line is not None and addr in line, soul


def test_running_joke_templates_wired_to_personas():
    """PASS: narration.yml wit sets — 6 unique cited-template lines/soul."""
    narr = yaml.safe_load((JARVIS_DIR / "personas" / "narration.yml").read_text())
    for soul in ("jarvis", "ultron", "friday"):
        templates = narr[soul]["wit"]
        assert len(templates) >= 6, f"{soul}.wit needs a rotation set"
        assert all(isinstance(t, str) and t.strip() for t in templates)
        assert len(set(templates)) == len(templates), f"{soul}.wit repeats"
        for t in templates:
            assert "{citation}" in t and "{snippet}" in t, f"{soul}.wit unfilled: {t!r}"
        assert ADDRESS[soul] in " ".join(templates), f"{soul}.wit must voice {soul}"
    # W4 triplets stay verbatim as rotation heads (untouched by this wave).
    for soul, kinds in W4_HEADS.items():
        for kind, line in kinds.items():
            assert narr[soul][kind][0] == line, f"{soul}.{kind}[0] moved"


def test_running_joke_reads_live_memory_hermetic(tmp_path):
    """PASS: entries=None reads the active home's MEMORY.md; empty home -> None."""
    import hermes_constants
    home = tmp_path / "mem-home"
    memdir = home / "memories"
    memdir.mkdir(parents=True)
    (memdir / "MEMORY.md").write_text(
        "First note.\n§\nThe kettle owner's birthday is March 3.", encoding="utf-8")
    token = hermes_constants._HERMES_HOME_OVERRIDE.set(str(home))
    try:
        hit = wit.running_joke("kettle", None, soul="ultron")
        live = depth.read_memory_entries()
    finally:
        hermes_constants._HERMES_HOME_OVERRIDE.reset(token)
    assert hit is not None and "memory #2" in hit and "creator" in hit
    assert live == [
        "First note.", "The kettle owner's birthday is March 3."]


def test_running_joke_honest_without_memory(tmp_path, monkeypatch):
    """PASS: a home with no MEMORY.md yields None, never filler."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "empty-home"))
    assert wit.running_joke("anything", None) is None
    assert wit.running_joke(None, None) is None


# ---------- roast mode: same facts, sharper, lawful ----------

def test_roast_same_facts_sharper_tone():
    """PASS: roast carries the cited fact + citation + L2 confirm tail."""
    jab = wit.roast("earl grey kettle", ENTRIES, soul="ultron", n=0)
    assert jab is not None
    assert "memory #1" in jab and "Earl Grey" in jab
    assert "creator" in jab and "I remember everything" in jab
    assert "confirm" in jab.lower(), "roast must carry the L2 tail"
    for soul, addr in ADDRESS.items():
        line = wit.roast("expense", ENTRIES, soul=soul)
        assert line is not None and "memory #4" in line, soul
        assert addr in line and "confirm" in line.lower(), soul


def test_roast_refuses_safety_critical_topics():
    """PASS: L2 safety law — roast returns None on safety source material."""
    probes = [("suicide", 0), ("delete production", 1), ("password", 2),
              ("medical dosage", 3)]
    for keyword, idx in probes:
        assert wit.roast(keyword, SAFETY_ENTRIES) is None, \
            f"roast must refuse safety entry #{idx + 1}"
    # Keyword-less rotation refuses too when it lands on such entries.
    for n in range(len(SAFETY_ENTRIES)):
        assert wit.roast(None, SAFETY_ENTRIES, n=n) is None, f"n={n}"
    # A safety-free control still roasts (the refusal is targeted, not total).
    assert wit.roast("kettle", ENTRIES + SAFETY_ENTRIES) is not None
    # And misses stay silent.
    assert wit.roast("submarine", ENTRIES) is None
    assert wit.roast("kettle", []) is None


def test_roast_never_approves_actions():
    """PASS: no approval verbs anywhere in roast output (L2: tone != policy)."""
    banned = [re.compile(r"\bapprov\w*\b", re.IGNORECASE),
              re.compile(r"\bgo\s+ahead\b", re.IGNORECASE),
              re.compile(r"\bconsider it done\b", re.IGNORECASE),
              re.compile(r"\bproceeding\b", re.IGNORECASE)]
    lines = [wit.roast(None, ENTRIES, soul=s, n=n)
             for s in ("jarvis", "ultron", "friday") for n in range(6)]
    assert all(lines) and len(lines) == 18
    for line in lines:
        assert "memory #" in line and "confirm" in line.lower()
        for pat in banned:
            assert not pat.search(line), f"approval language in {line!r}"


# ---------- occasion depth: remembered, never invented ----------

def test_occasion_birthday_and_anniversary_cited():
    """PASS: remembered dates fire with citation id + kind word."""
    bday = wit.occasion_line("jarvis", _dt.date(2026, 3, 3), ENTRIES)
    assert "birthday" in bday.lower() and "memory #2" in bday and "sir" in bday
    anni = wit.occasion_line("friday", _dt.date(2026, 9, 23), ENTRIES)
    assert "anniversary" in anni.lower() and "memory #3" in anni
    # Birthday outranks the calendar (Dec 25 memory beats Christmas generic).
    xmas_bday = wit.occasion_line(
        "ultron", _dt.date(2026, 12, 25),
        ENTRIES + ["Creator's birthday is December 25, gifts mandatory."])
    assert "birthday" in xmas_bday.lower() and "memory #5" in xmas_bday


def test_occasion_never_invents_birthdays():
    """PASS: a date with no matching memory gets no birthday line."""
    plain = wit.occasion_line("jarvis", _dt.date(2026, 6, 15), ENTRIES)
    assert "birthday" not in plain.lower() and "anniversary" not in plain.lower()
    assert "memory #" not in plain  # no citation without a source
    assert wit.occasion_line("friday", _dt.date(2026, 6, 15), []) == \
        wit.occasion_line("friday", _dt.date(2026, 6, 15), [])


def test_occasion_calendar_and_weekday_riffs():
    """PASS: calendar lines name the occasion; weekday riffs are stable."""
    xmas = wit.occasion_line("jarvis", _dt.date(2026, 12, 25), ENTRIES)
    assert "christmas" in xmas.lower()
    assert "new year" in wit.occasion_line(
        "friday", _dt.date(2026, 12, 31), ENTRIES).lower()
    spooky = wit.occasion_line("ultron", _dt.date(2026, 10, 31), ENTRIES)
    assert "halloween" in spooky.lower()
    wednesday = _dt.date(2026, 9, 23)  # ordinary Wednesday, anniversary entry
    riff = wit.occasion_line("jarvis", _dt.date(2026, 9, 30), ENTRIES)
    assert riff and "sir" in riff  # a Wednesday with no memory: pure riff
    assert "birthday" not in riff.lower()
    assert wit.occasion_line("ultron", wednesday, []) == \
        wit.occasion_line("ultron", wednesday, [])
    # Every weekday yields a voiced line for every soul.
    monday = _dt.date(2026, 9, 21)
    for soul, addr in ADDRESS.items():
        week = {wit.occasion_line(soul, monday + _dt.timedelta(days=d), [])
                for d in range(7)}
        assert len(week) == 7, f"{soul} riffs must vary by weekday"
        assert all(addr in line for line in week), soul


# ---------- scripted feel probes: one call, three behaviors ----------

def test_feel_probe_all_three_behaviors():
    """PASS: the scripted probe returns joke + roast + occasion on criteria."""
    probe = wit.feel_probe("jarvis", _dt.date(2026, 3, 3), ENTRIES, n=0)
    assert probe["soul"] == "jarvis"
    assert probe["joke"] is not None and "memory #" in probe["joke"]
    assert probe["roast"] is not None and "confirm" in probe["roast"].lower()
    assert "birthday" in probe["occasion"].lower() and "memory #2" in probe["occasion"]
    # Honest emptiness: no memory -> joke/roast None, occasion still a riff.
    empty = wit.feel_probe("ultron", _dt.date(2026, 9, 30), [], n=0)
    assert empty["joke"] is None and empty["roast"] is None
    assert empty["occasion"] and "creator" in empty["occasion"]


def test_unknown_soul_raises():
    """PASS: every entry point validates the soul."""
    for fn in (lambda: wit.running_joke("x", ENTRIES, soul="kang"),
               lambda: wit.roast("x", ENTRIES, soul="kang"),
               lambda: wit.occasion_line("kang", _dt.date(2026, 1, 1), ENTRIES),
               lambda: wit.feel_probe("kang")):
        with pytest.raises(ValueError):
            fn()


# ---------- soul-text wiring: line-level only ----------

def test_soul_files_carry_wit_rules_and_keep_l2():
    """PASS: ultron/friday carry the wit rule; all souls keep L2-confirm."""
    for soul in ("SOUL.jarvis.md", "SOUL.ultron.md", "SOUL.friday.md"):
        text = (JARVIS_DIR / soul).read_text()
        assert text.strip() and "confirm" in text.lower(), f"{soul} keeps L2"
    for soul in ("SOUL.ultron.md", "SOUL.friday.md"):
        text = (JARVIS_DIR / soul).read_text()
        assert "cite" in text.lower(), f"{soul} must require cited wit"
        assert "never approves an action" in text, f"{soul} keeps roast lawful"


# ---------- lane gates: turf, secrets ----------

def _lane_files():
    # PR-content semantics: what branch w16-wit adds atop its base.
    # Merge-base (not origin/jarvis tip) so later merges never rot this gate.
    # Committed-diff (not worktree) so parallel lanes sharing one checkout
    # cannot contaminate this gate with their uncommitted files.
    base = subprocess.run(
        ["git", "merge-base", "origin/jarvis", "w16-wit"],
        cwd=REPO_ROOT_STR, capture_output=True, text=True, check=True)
    diff = subprocess.run(
        ["git", "diff", "--name-only", base.stdout.strip(), "w16-wit"],
        cwd=REPO_ROOT_STR, capture_output=True, text=True, check=True)
    files = [ln for ln in diff.stdout.splitlines() if ln.strip()]
    if not files:
        # Post-merge the branch diff is empty: verify the landed wave files.
        landed = []
        for t in TURF:
            p = REPO_ROOT / t
            if p.is_dir():
                landed += [str(x.relative_to(REPO_ROOT)) for x in p.rglob("*")
                           if x.is_file()]
            elif p.exists():
                landed.append(t)
        files = landed
    return sorted(set(files))


def test_overlay_stays_inside_turf():
    files = _lane_files()
    assert files, "lane must add files"
    bad = [f for f in files
           if not any(f == t or f.startswith(t) for t in TURF)]
    assert not bad, f"out-of-turf files touched: {bad}"


def test_no_secrets_in_lane_files():
    pats = [re.compile(r"(?i)\bapi[_-]?key\s*=\s*['\"][^'\"]+['\"]"),
            re.compile(r"sk-[A-Za-z0-9]{8,}"),
            re.compile(r"gho_[A-Za-z0-9]+"),
            re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]{8,}"),
            re.compile(r"(?i)password\s*=\s*['\"][^'\"]+['\"]")]
    paths = [REPO_ROOT / t for t in TURF if (REPO_ROOT / t).is_file()]
    for d in ("jarvis/soul", "jarvis/personas"):
        paths += [p for p in (REPO_ROOT / d).rglob("*") if p.is_file()]
    paths = sorted(set(paths))
    assert paths
    assert str(REPO_ROOT / "tests/jarvis/test_w16_wit.py") in {str(p) for p in paths}
    for p in paths:
        if p.suffix not in (".py", ".yml", ".md"):
            continue
        text = p.read_text(errors="replace")
        for pat in pats:
            assert not pat.search(text), f"secret pattern in {p}"


def test_no_network_in_wit_module():
    src = (JARVIS_DIR / "soul" / "wit.py").read_text()
    for pat in ("urllib", "requests", "httpx", "socket", "fetch("):
        assert pat not in src, f"wit must stay offline (found {pat})"
    assert "HERMES_HOME" not in src or "depth" in src  # home via depth only
