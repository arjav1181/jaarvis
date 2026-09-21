"""W1 souls + skins tests — personalities, skins, voices, toggle, repair.

Covers prompt.md W1 tasks 2-4 + 6 (toggle/flip proof lives in 5, pasted):
  - personalities parse as REAL entries (no TODO stubs)
  - skins parse + inherit the upstream default through upstream load_skin()
  - voices.yml validates (verified provider IDs, sane speeds)
  - toggle flips the effective soul via upstream resolve_ephemeral_system_prompt()
  - orphan repaired (merge-base resolves, no shallow file)
  - no core files touched (diff vs upstream/main is overlay-only)
  - jarvis-persona helper flips personality+skin in an isolated home

Hermetic: skin/helper tests run against tmp HERMES_HOMEs, never ~/.jarvis.
Run with the W0 venv active: `python -m pytest tests/jarvis/ -v`
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
JARVIS_DIR = REPO_ROOT / "jarvis"

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
EDGE_VOICE = re.compile(r"^[a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural$")
# OpenAI TTS voice IDs verified against the platform TTS docs (this wave).
OPENAI_VOICES = {"alloy", "ash", "ballad", "coral", "echo", "fable",
                 "nova", "onyx", "sage", "shimmer", "verse", "marin", "cedar"}

PERSONA_TO_SKIN = {"jarvis": "jarvis-gold", "ultron": "ultron-crimson"}


def _load_personalities():
    return yaml.safe_load((JARVIS_DIR / "personalities.yml").read_text())["agent"]["personalities"]


def test_personalities_are_real():
    personas = _load_personalities()
    assert set(("jarvis", "ultron")) <= set(personas)
    for name, text in personas.items():
        assert isinstance(text, str) and text.strip(), f"{name} must be non-empty text"
        assert "TODO" not in text, f"{name} must not be a stub in W1"
    assert "sir" in personas["jarvis"]
    assert "creator" in personas["ultron"]
    # L2-confirm standing rule identical for both souls (prompt is not policy).
    assert "confirm" in personas["jarvis"].lower()
    assert "confirm" in personas["ultron"].lower()


def test_soul_files_match_personalities():
    for soul, persona in (("SOUL.jarvis.md", "jarvis"), ("SOUL.ultron.md", "ultron")):
        text = (JARVIS_DIR / soul).read_text()
        assert text.strip(), f"{soul} must be non-empty"
        assert "confirm" in text.lower(), f"{soul} must carry the L2-confirm rule"


def _load_skin_through_upstream(skin_name, home):
    """Install repo skins into an isolated home and load via upstream code."""
    import hermes_cli.skin_engine as engine
    skins_dir = Path(home) / "skins"
    skins_dir.mkdir(parents=True, exist_ok=True)
    for src in (JARVIS_DIR / "skins").glob("*.yaml"):
        shutil.copy(src, skins_dir / src.name)
    # Re-point the engine at the isolated home for this call.
    import hermes_constants
    token = hermes_constants._HERMES_HOME_OVERRIDE.set(str(home))
    try:
        return engine.load_skin(skin_name)
    finally:
        hermes_constants._HERMES_HOME_OVERRIDE.reset(token)


def test_skins_parse_and_inherit(tmp_path):
    from hermes_cli.skin_engine import load_skin as _  # noqa: F401  (import check)
    default_keys = None
    import hermes_constants
    token = hermes_constants._HERMES_HOME_OVERRIDE.set(str(tmp_path))
    try:
        from hermes_cli.skin_engine import load_skin
        default_keys = set(load_skin("default").colors.keys())
    finally:
        hermes_constants._HERMES_HOME_OVERRIDE.reset(token)
    for skin_name, brand in (("jarvis-gold", "Jarvis"), ("ultron-crimson", "Ultron")):
        raw = yaml.safe_load((JARVIS_DIR / "skins" / f"{skin_name}.yaml").read_text())
        assert raw["name"] == skin_name
        for key, value in raw.get("colors", {}).items():
            assert HEX_COLOR.match(str(value)), f"{skin_name} colors.{key} not #rrggbb"
        verbs = (raw.get("spinner") or {}).get("thinking_verbs") or []
        assert len(verbs) >= 4, f"{skin_name} needs calm/aggressive verbs"
        skin = _load_skin_through_upstream(skin_name, tmp_path / skin_name)
        assert skin.get_branding("agent_name") == brand
        # Inherit: merged colors cover the default key set.
        assert default_keys <= set(skin.colors.keys()), f"{skin_name} must inherit default colors"


def test_ultron_banner_present():
    raw = yaml.safe_load((JARVIS_DIR / "skins" / "ultron-crimson.yaml").read_text())
    assert raw.get("banner_logo", "").strip(), "ultron-crimson needs its menacing banner"


def test_voices_map_valid():
    voices = yaml.safe_load((JARVIS_DIR / "personas" / "voices.yml").read_text())
    assert set(("jarvis", "ultron")) <= set(voices)
    assert voices["jarvis"]["edge"]["voice"] == "en-GB-RyanNeural"  # live-list verified
    assert voices["ultron"]["edge"]["voice"] == "en-US-ChristopherNeural"  # live-list verified
    for soul, entry in voices.items():
        edge = entry.get("edge") or {}
        assert EDGE_VOICE.match(edge.get("voice", "")), f"{soul} edge voice ID malformed"
        assert 0.5 <= float(edge.get("speed", 1.0)) <= 2.0, f"{soul} edge speed out of range"
        assert (entry.get("openai") or {}).get("voice") in OPENAI_VOICES
    # ElevenLabs Adam ID = upstream code default (verified in tts_tool_providers.py).
    assert voices["jarvis"]["elevenlabs"]["voice_id"] == "pNInz6obpgDQGcFmaJgB"


def test_toggle_flips_effective_soul():
    from hermes_cli.personality import resolve_ephemeral_system_prompt
    personas = _load_personalities()
    base = {"agent": {"personalities": personas}, "display": {}}
    jarvis_cfg = {**base, "display": {"personality": "jarvis"}}
    ultron_cfg = {**base, "display": {"personality": "ultron"}}
    jarvis_text = resolve_ephemeral_system_prompt(jarvis_cfg)
    ultron_text = resolve_ephemeral_system_prompt(ultron_cfg)
    assert "sir" in jarvis_text and "creator" not in jarvis_text
    assert "creator" in ultron_text and "sir" not in ultron_text
    assert jarvis_text != ultron_text


def _has_upstream_ref():
    r = subprocess.run(["git", "rev-parse", "--verify", "upstream/main"],
                       cwd=REPO_ROOT, capture_output=True)
    return r.returncode == 0


@pytest.mark.skipif(not _has_upstream_ref(), reason="needs upstream/main ref (W1 repair clone)")
def test_orphan_repaired():
    assert not (REPO_ROOT / ".git" / "shallow").exists(), "history must be unshallowed"
    r = subprocess.run(["git", "merge-base", "--is-ancestor", "upstream/main", "HEAD"],
                       cwd=REPO_ROOT, capture_output=True)
    assert r.returncode == 0, "upstream/main must be an ancestor of HEAD (merge works)"


@pytest.mark.skipif(not _has_upstream_ref(), reason="needs upstream/main ref (W1 repair clone)")
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


def test_persona_helper_flips_personality_and_skin(tmp_path):
    hermes = shutil.which("hermes")
    assert hermes, "hermes entrypoint must be on PATH (activate the W0 venv)"
    home = tmp_path / "flip-home"
    env = dict(os.environ, HERMES_HOME=str(home),
               PATH=os.pathsep.join([str(Path(hermes).parent),
                                      os.environ.get("PATH", "")]))
    for persona, skin in PERSONA_TO_SKIN.items():
        proc = subprocess.run([str(JARVIS_DIR / "bin" / "jarvis-persona"), persona],
                              capture_output=True, text=True, env=env, timeout=120)
        assert proc.returncode == 0, proc.stderr[-2000:]
        assert f"persona:" in proc.stdout and persona in proc.stdout
        cfg = yaml.safe_load((home / "config.yaml").read_text())
        assert cfg["display"]["personality"] == persona
        assert cfg["display"]["skin"] == skin
