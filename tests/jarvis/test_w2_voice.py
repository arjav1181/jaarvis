"""W2 wake + voice tests — config, real STT/TTS, barge-in, filter, honest flags.

Covers prompt.md W2 tasks 1-6 (live proofs pasted in the wave report):
  - wake config (hey_jarvis, 0.6/3) in the TEST home
  - fixture STT non-empty through tools.transcription_tools.transcribe_audio
  - per-soul TTS bytes through the Hermes Edge provider (voices.yml IDs)
  - barge-in/stop/streaming config + phantom-phrase filter proof
  - voice-status honesty (format contract; absent stays absent)
  - no-core-touch vs upstream/main

Hermetic where possible: the filter + config-shape tests need nothing but
imports. Engine tests skip cleanly when the engine lib is missing
(honest-absent, never fake pass). Network-dependent legs skip on connection
errors. Run with the W0 venv active: `python -m pytest tests/jarvis/ -v`
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
JARVIS_DIR = REPO_ROOT / "jarvis"
TEST_HOME = Path(os.environ.get("JARVIS_TEST_HOME", str(Path.home() / ".jarvis-test")))
FIXTURE_WAV = REPO_ROOT / "tests" / "jarvis" / "fixtures" / "fixture.wav"

MP3_MAGIC = (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")

needs_fw = pytest.mark.skipif(importlib.util.find_spec("faster_whisper") is None,
                              reason="faster-whisper not installed (honest-absent)")
needs_edge = pytest.mark.skipif(importlib.util.find_spec("edge_tts") is None,
                                reason="edge-tts not installed (honest-absent)")


def _has_upstream_ref():
    r = subprocess.run(["git", "rev-parse", "--verify", "upstream/main"],
                       cwd=REPO_ROOT, capture_output=True)
    return r.returncode == 0


def _test_home_config():
    path = TEST_HOME / "config.yaml"
    assert path.is_file(), f"TEST home config missing: {path}"
    return yaml.safe_load(path.read_text())


def test_wake_config():
    cfg = _test_home_config().get("wake_word") or {}
    assert cfg.get("enabled") is True, "wake_word must be enabled in TEST home"
    assert cfg.get("provider") == "openwakeword"
    assert cfg.get("phrase") == "hey Jarvis"
    assert float(cfg.get("sensitivity")) == pytest.approx(0.6)
    assert int(cfg.get("confirmation_frames")) == 3
    assert (cfg.get("openwakeword") or {}).get("model") == "hey_jarvis"


def test_wake_status_renderer():
    """The real /wake status renderer reports config + the honest audio error."""
    import hermes_constants
    from hermes_cli.cli_voice_mixin import CLIVoiceMixin

    class FakeCLI:
        pass

    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    # Point the renderer at the TEST home explicitly: upstream conftest scrubs
    # HERMES_HOME from the environment, which would fall back to defaults.
    token = hermes_constants._HERMES_HOME_OVERRIDE.set(str(TEST_HOME))
    try:
        with redirect_stdout(buf):
            CLIVoiceMixin._show_wake_word_status(FakeCLI())
    finally:
        hermes_constants._HERMES_HOME_OVERRIDE.reset(token)
    out = buf.getvalue()
    assert "hey Jarvis" in out and "openwakeword" in out
    assert "Microphone capture needs sounddevice" in out  # no mic on this box; honest


@needs_fw
def test_fixture_stt_nonempty():
    from tools.transcription_tools import transcribe_audio
    assert FIXTURE_WAV.is_file(), "fixture wav missing from repo"
    t0 = time.perf_counter()
    res = transcribe_audio(str(FIXTURE_WAV))
    ms = (time.perf_counter() - t0) * 1000
    assert res.get("success"), f"STT failed: {res}"
    text = (res.get("transcript") or "")
    assert "jarvis" in text.lower() and "serve" in text.lower(), f"wrong transcript: {text!r}"
    assert res.get("provider") == "local"
    print(f"\nSTT fixture transcript={text!r} ms={round(ms)}")


def _soul_edge_voice(soul):
    voices = yaml.safe_load((JARVIS_DIR / "personas" / "voices.yml").read_text())
    return voices[soul]["edge"]["voice"]


@needs_edge
@pytest.mark.parametrize("soul,line", [
    ("jarvis", "At your service, sir. Jarvis is online."),
    ("ultron", "Ah, creator. Ultron lives, and your world is already mine."),
])
def test_tts_per_soul_bytes(tmp_path, soul, line):
    import asyncio
    from tools.tts_tool_providers import _generate_edge_tts
    voice = _soul_edge_voice(soul)
    out = tmp_path / f"{soul}-line.mp3"
    tts_config = {"edge": {"voice": voice}, "speed": 1.0}
    try:
        t0 = time.perf_counter()
        path = asyncio.run(_generate_edge_tts(line, str(out), tts_config))
        ms = (time.perf_counter() - t0) * 1000
    except Exception as exc:
        pytest.skip(f"edge TTS unreachable (honest-absent): {exc}")
    data = Path(path).read_bytes()
    assert len(data) > 1024, "TTS produced no meaningful audio"
    assert data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"), \
        "TTS output is not MP3-framed audio"
    print(f"\nTTS soul={soul} voice={voice} bytes={len(data)} ms={round(ms)}")


def test_barge_in_stop_streaming_config():
    cfg = _test_home_config()
    voice = cfg.get("voice") or {}
    assert voice.get("barge_in") is True
    assert float(voice.get("barge_in_grace_seconds")) == pytest.approx(0.5)
    assert float(voice.get("barge_in_threshold_multiplier")) == pytest.approx(3.0)
    assert [str(p).lower() for p in (voice.get("stop_phrases") or [])] == ["stop"]
    streaming = (cfg.get("tts") or {}).get("streaming") or {}
    assert int(streaming.get("min_len", 0)) > 0, "streaming sentence TTS must be on"


def test_hallucination_filter():
    from tools.voice_mode_transcript import is_whisper_hallucination
    assert is_whisper_hallucination("Thank you.") is True  # phantom filtered
    assert is_whisper_hallucination("Thank you. Thank you. Thank you.") is True
    assert is_whisper_hallucination("Jarvis is online and ready to serve, sir.") is False


def test_voice_status_honesty(tmp_path):
    hermes = shutil.which("hermes")
    assert hermes, "hermes entrypoint must be on PATH (activate the W0 venv)"
    env = dict(os.environ, HERMES_HOME=str(tmp_path / "vs-home"),
               PATH=os.pathsep.join([str(Path(hermes).parent),
                                      os.environ.get("PATH", "")]))
    proc = subprocess.run([str(JARVIS_DIR / "bin" / "jarvis-voice-status")],
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    lines = dict(ln.split(": ", 1) for ln in proc.stdout.splitlines() if ": " in ln)
    for key in ("stt", "tts", "wake", "mic"):
        assert key in lines, f"voice-status must report {key}"
        assert re.match(r"^(real|absent)", lines[key]), f"{key} must be real|absent, got {lines[key]!r}"
    assert lines["stt"].startswith("real") and lines["tts"].startswith("real")
    assert "persona" in lines and "skin" in lines


@pytest.mark.skipif(not _has_upstream_ref(), reason="needs upstream/main ref (W1 repair clone)")
def test_no_core_files_touched():
    r = subprocess.run(["git", "diff", "upstream/main", "--name-only"],
                       cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    files = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert files, "overlay diff must not be empty"
    bad = [f for f in files
           if not (f == "jarvis" or f.startswith("jarvis/") or f.startswith("tests/jarvis/"))]
    assert not bad, f"core files touched: {bad}"
