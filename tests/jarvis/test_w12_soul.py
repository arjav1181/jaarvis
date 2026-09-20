"""W12 soul depth tests — Friday soul, narration rotation, greetings,
cited callbacks, reply shaping, multilingual voices.

Hermetic: home-scoped tests run against tmp HERMES_HOMEs, never ~/.jarvis;
no network (voice IDs are format- + exact-match-checked against the
live-verified list from this wave; the spoken proof lives in the PR body).
Run with the W0 venv active: `python -m pytest tests/jarvis/ -q`
"""

import datetime as _dt
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
JARVIS_DIR = REPO_ROOT / "jarvis"
sys.path.insert(0, str(JARVIS_DIR / "soul"))

import depth

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
EDGE_VOICE = re.compile(r"^[a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural$")
OPENAI_VOICES = {"alloy", "ash", "ballad", "coral", "echo", "fable",
                 "nova", "onyx", "sage", "shimmer", "verse", "marin", "cedar"}

PERSONA_TO_SKIN = {"jarvis": "jarvis-gold", "ultron": "ultron-crimson",
                   "friday": "friday-emerald"}
# Edge IDs live-verified via `edge-tts --list-voices` in this wave.
VERIFIED_EDGE = {
    "jarvis": "en-GB-RyanNeural",
    "ultron": "en-US-ChristopherNeural",
    "friday": "en-IE-EmilyNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "it": "it-IT-ElsaNeural",
    "pt": "pt-BR-FranciscaNeural",
}

W4_NARR = {
    "jarvis": {"start": "Working on it, sir.", "tool": "On it, sir.",
               "done": "Done, sir."},
    "ultron": {"start": "Ah, the little wheels turn, creator.",
               "tool": "Savor the machinery, creator.",
               "done": "Behold — finished."},
}


def _load_personalities():
    return yaml.safe_load((JARVIS_DIR / "personalities.yml").read_text())["agent"]["personalities"]


def test_personalities_include_friday_and_stay_real():
    personas = _load_personalities()
    assert set(("jarvis", "ultron", "friday")) <= set(personas)
    for name, text in personas.items():
        assert isinstance(text, str) and text.strip(), f"{name} must be non-empty text"
        assert "TODO" not in text, f"{name} must not be a stub"
    assert "sir" in personas["jarvis"]
    assert "creator" in personas["ultron"]
    assert "boss" in personas["friday"]
    # L2-confirm + shared depth rules identical for all three souls.
    for name, text in personas.items():
        lowered = text.lower()
        assert "confirm" in lowered, f"{name} must carry the L2-confirm rule"
        assert "rotat" in lowered, f"{name} must instruct narration rotation"
        assert "cite" in lowered or "citing" in lowered, \
            f"{name} must require cited callbacks"


def test_soul_files_match_personalities():
    for soul, persona in (("SOUL.jarvis.md", "jarvis"), ("SOUL.ultron.md", "ultron"),
                          ("SOUL.friday.md", "friday")):
        text = (JARVIS_DIR / soul).read_text()
        assert text.strip(), f"{soul} must be non-empty"
        assert "confirm" in text.lower(), f"{soul} must carry the L2-confirm rule"
    friday = (JARVIS_DIR / "SOUL.friday.md").read_text()
    assert "boss" in friday and "consent" in friday.lower()


def test_friday_skin_parses_and_inherits(tmp_path):
    raw = yaml.safe_load((JARVIS_DIR / "skins" / "friday-emerald.yaml").read_text())
    assert raw["name"] == "friday-emerald"
    for key, value in raw.get("colors", {}).items():
        assert HEX_COLOR.match(str(value)), f"friday-emerald colors.{key} not #rrggbb"
    verbs = (raw.get("spinner") or {}).get("thinking_verbs") or []
    assert len(verbs) >= 4, "friday-emerald needs brisk thinking verbs"
    import hermes_constants
    from hermes_cli.skin_engine import load_skin
    token = hermes_constants._HERMES_HOME_OVERRIDE.set(str(tmp_path))
    try:
        default_keys = set(load_skin("default").colors.keys())
    finally:
        hermes_constants._HERMES_HOME_OVERRIDE.reset(token)
    home = tmp_path / "friday-home"
    skins_dir = home / "skins"
    skins_dir.mkdir(parents=True, exist_ok=True)
    for src in (JARVIS_DIR / "skins").glob("*.yaml"):
        shutil.copy(src, skins_dir / src.name)
    token = hermes_constants._HERMES_HOME_OVERRIDE.set(str(home))
    try:
        skin = load_skin("friday-emerald")
    finally:
        hermes_constants._HERMES_HOME_OVERRIDE.reset(token)
    assert skin.get_branding("agent_name") == "Friday"
    assert default_keys <= set(skin.colors.keys()), "friday-emerald must inherit default colors"


def test_voices_map_valid_with_friday_and_languages():
    voices = yaml.safe_load((JARVIS_DIR / "personas" / "voices.yml").read_text())
    for soul, voice_id in (("jarvis", VERIFIED_EDGE["jarvis"]),
                           ("ultron", VERIFIED_EDGE["ultron"]),
                           ("friday", VERIFIED_EDGE["friday"])):
        entry = voices[soul]
        assert entry["edge"]["voice"] == voice_id, f"{soul} edge voice must be live-verified ID"
        assert EDGE_VOICE.match(entry["edge"]["voice"])
        assert 0.5 <= float(entry["edge"].get("speed", 1.0)) <= 2.0
        assert (entry.get("openai") or {}).get("voice") in OPENAI_VOICES
    langs = yaml.safe_load((JARVIS_DIR / "personas" / "languages.yml").read_text())
    for lang, voice_id in ((k, v) for k, v in VERIFIED_EDGE.items() if len(k) == 2):
        assert langs[lang]["edge"]["voice"] == voice_id, f"lang {lang} must be live-verified ID"
        assert EDGE_VOICE.match(langs[lang]["edge"]["voice"])


def test_toggle_flips_three_ways():
    from hermes_cli.personality import resolve_ephemeral_system_prompt
    personas = _load_personalities()
    base = {"agent": {"personalities": personas}, "display": {}}
    texts = {}
    for soul in ("jarvis", "ultron", "friday"):
        texts[soul] = resolve_ephemeral_system_prompt({**base, "display": {"personality": soul}})
    assert "sir" in texts["jarvis"] and "creator" not in texts["jarvis"]
    assert "creator" in texts["ultron"] and "sir" not in texts["ultron"]
    assert "boss" in texts["friday"]
    assert len({texts["jarvis"], texts["ultron"], texts["friday"]}) == 3


def test_persona_helper_flips_friday(tmp_path):
    hermes = shutil.which("hermes")
    assert hermes, "hermes entrypoint must be on PATH (activate the W0 venv)"
    home = tmp_path / "flip-home"
    env = dict(os.environ, HERMES_HOME=str(home),
               PATH=os.pathsep.join([str(Path(hermes).parent),
                                      os.environ.get("PATH", "")]))
    proc = subprocess.run([str(JARVIS_DIR / "bin" / "jarvis-persona"), "friday"],
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "persona:" in proc.stdout and "friday" in proc.stdout
    cfg = yaml.safe_load((home / "config.yaml").read_text())
    assert cfg["display"]["personality"] == "friday"
    assert cfg["display"]["skin"] == "friday-emerald"
    assert cfg["tts"]["edge"]["voice"] == VERIFIED_EDGE["friday"]


def test_narration_sets_cover_w4_triplets_and_rotate():
    narr = depth.narration_lines()
    assert set(("jarvis", "ultron", "friday")) <= set(narr)
    for soul, kinds in narr.items():
        assert set(("start", "tool", "done")) <= set(kinds)
        for kind, lines in kinds.items():
            assert len(lines) >= 6, f"{soul}.{kind} needs a real rotation set"
            assert all(isinstance(line, str) and line.strip() for line in lines)
            assert len(set(lines)) == len(lines), f"{soul}.{kind} must not repeat a line"
    # W4 voice.html triplets verbatim as rotation heads (W13 swaps source safely).
    for soul, kinds in W4_NARR.items():
        for kind, line in kinds.items():
            assert narr[soul][kind][0] == line, f"{soul}.{kind}[0] must be the W4 line"
    # Deterministic rotation: full cycle + 1 never repeats consecutively.
    for soul in ("jarvis", "ultron", "friday"):
        seq = [depth.milestone(soul, "done", n) for n in range(8)]
        assert all(a != b for a, b in zip(seq, seq[1:]))
        assert depth.milestone(soul, "done", 0) == depth.milestone(soul, "done", 6)
    with pytest.raises(ValueError):
        depth.milestone("kang", "done", 0)
    with pytest.raises(ValueError):
        depth.milestone("jarvis", "dance", 0)


def test_greetings_occasion_aware_and_brief():
    xmas_eve = _dt.datetime(2026, 12, 24, 9, 0)
    assert "christmas" in depth.greet("jarvis", xmas_eve).lower()
    new_year = _dt.datetime(2026, 12, 31, 23, 30)
    assert "new year" in depth.greet("friday", new_year).lower()
    spooky = _dt.datetime(2026, 10, 31, 20, 0)
    assert "spook" in depth.greet("ultron", spooky).lower() \
        or "halloween" in depth.greet("ultron", spooky).lower()
    saturday = _dt.datetime(2026, 9, 26, 10, 0)  # a Saturday
    assert "weekend" in depth.greet("friday", saturday).lower()
    monday = _dt.datetime(2026, 9, 21, 9, 0)  # a Monday
    assert "monday" in depth.greet("jarvis", monday).lower()
    wednesday = _dt.datetime(2026, 9, 23, 14, 0)  # ordinary Wednesday
    plain = depth.greet("jarvis", wednesday)
    assert plain == "Good day, sir."
    assert depth.occasion(_dt.date(2026, 9, 23)) is None
    assert depth.occasion(_dt.date(2026, 12, 25)) == "christmas"
    assert depth.occasion(_dt.date(2027, 1, 1)) == "new-year"
    for soul in ("jarvis", "ultron", "friday"):
        for when in (xmas_eve, saturday, wednesday, _dt.datetime(2026, 9, 23, 2, 0)):
            assert len(depth.greet(soul, when).splitlines()) <= 2
    with pytest.raises(ValueError):
        depth.greet("kang", wednesday)


ENTRIES = [
    "The secret word is Thunderbird.",
    "Sir prefers Earl Grey, Ultron mocked the kettle on 2026-09-10.",
    "Friday filed the expense report without being asked twice.",
]


def test_callback_cites_memory_and_never_fabricates():
    hit = depth.callback("thunderbird secret", ENTRIES, soul="jarvis")
    assert hit is not None
    assert "memory #1" in hit and "Thunderbird" in hit and "sir" in hit
    hit2 = depth.callback("expense report", ENTRIES, soul="friday")
    assert hit2 is not None and "memory #3" in hit2 and "boss" in hit2
    # Misses stay silent — no memory, no callback, never invented.
    assert depth.callback("submarine", ENTRIES) is None
    assert depth.callback("", ENTRIES) is None
    assert depth.callback("thunderbird", []) is None


def test_read_memory_entries_hermetic(tmp_path):
    import hermes_constants
    home = tmp_path / "mem-home"
    memdir = home / "memories"
    memdir.mkdir(parents=True)
    (memdir / "MEMORY.md").write_text("First note.\n§\nSecond note.", encoding="utf-8")
    token = hermes_constants._HERMES_HOME_OVERRIDE.set(str(home))
    try:
        entries = depth.read_memory_entries()
    finally:
        hermes_constants._HERMES_HOME_OVERRIDE.reset(token)
    assert entries == ["First note.", "Second note."]
    assert depth.callback("second", entries) is not None


def test_shape_budgets_by_weight():
    long_text = ("The gateway is up. Latency p95 is 210 milliseconds. "
                 "Three workers report healthy. The dashboard shows all green. "
                 "Two habits delivered twice. Nothing remains except the report.")
    small = depth.shape(long_text, "small")
    assert small == "The gateway is up."
    medium = depth.shape(long_text, "medium")
    assert len(re.findall(r"[.!?]", medium)) <= 3 and len(medium) <= 600
    assert medium.startswith("The gateway is up.")
    assert depth.shape(long_text, "big") == long_text
    assert depth.shape("", "small") == ""
    with pytest.raises(ValueError):
        depth.shape(long_text, "colossal")


def test_voice_for_defaults_and_fallbacks():
    assert depth.voice_for("friday") == VERIFIED_EDGE["friday"]
    assert depth.voice_for("jarvis") == VERIFIED_EDGE["jarvis"]
    assert depth.voice_for("friday", "es") == VERIFIED_EDGE["es"]
    assert depth.voice_for("jarvis", "es-ES") == VERIFIED_EDGE["es"]
    assert depth.voice_for("ultron", "FR") == VERIFIED_EDGE["fr"]
    assert depth.voice_for("friday", "en") == VERIFIED_EDGE["friday"]
    # Unknown language -> soul default, never a guessed ID.
    assert depth.voice_for("friday", "xx") == VERIFIED_EDGE["friday"]
    assert depth.voice_for("jarvis", None) == VERIFIED_EDGE["jarvis"]
    with pytest.raises(ValueError):
        depth.voice_for("kang", "es")


def test_clone_policy_is_docs_only():
    doc = (JARVIS_DIR / "soul" / "VOICE_CLONE.md").read_text()
    assert "consent" in doc.lower()
    assert "not implemented" in doc.lower()


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
