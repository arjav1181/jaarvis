"""W7 apex tests — hermetic (stub engines, fake adapters, temp HERMES_HOME)."""
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from jarvis.apex import (achievements as ac, compute, discord_vc as vc,
                         gpt_live as gl, langfuse_optin as lf, review,
                         say, snapshot, stt_partials as stt)


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))


# --- GPU ladder ---

def test_ladder_cpu_when_no_gpu():
    r = compute.probe_gpu_ladder(env={},
                                 torch_cuda=lambda: False,
                                 runner=lambda cmd: (False, "nope"))
    assert r["selected"] == "cpu-base" and r["gpu_present"] is False


def test_ladder_cuda_local():
    r = compute.probe_gpu_ladder(env={},
                                 torch_cuda=lambda: True,
                                 runner=lambda cmd: (False, "nope"))
    assert r["selected"] == "cuda-local" and r["gpu_present"] is True


def test_ladder_server_gpu_needs_driver_and_cvd():
    r = compute.probe_gpu_ladder(env={"CUDA_VISIBLE_DEVICES": "0,1"},
                                 torch_cuda=lambda: False,
                                 runner=lambda cmd: (True, "GPU 0: ..."))
    assert r["selected"] == "server-gpu"


def test_ladder_cvd_without_driver_stays_cpu():
    r = compute.probe_gpu_ladder(env={"CUDA_VISIBLE_DEVICES": "0"},
                                 torch_cuda=lambda: False,
                                 runner=lambda cmd: (False, "nope"))
    assert r["selected"] == "cpu-base"


def test_stt_engines_honest_absent():
    r = compute.probe_stt_engines(env={}, importable=lambda n: False)
    assert r["usable"] == [] and r["preferred"] is None


def test_stt_engines_priority():
    r = compute.probe_stt_engines(env={"GROQ_API_KEY": "x"},
                                  importable=lambda n: n == "faster_whisper")
    assert r["preferred"] == "faster-whisper-local"


# --- STT partials ---

def test_partials_stream_with_stub():
    wav = stt.make_test_wav(seconds=1.2)
    calls = []

    def stub(chunk, i):
        calls.append(i)
        return f"w{i}" if i < 2 else ""

    evs = list(stt.stream_partials(wav, stub, window_ms=500))
    partials = [e for e in evs if e["type"] == "partial"]
    finals = [e for e in evs if e["type"] == "final"]
    assert len(partials) == 3 and len(finals) == 1
    assert finals[0]["text"] == "w0 w1"
    assert finals[0]["windows_with_speech"] == 2
    assert all("window_ms" in p for p in partials)
    assert calls == [0, 1, 2]


def test_partials_window_error_does_not_kill_stream():
    wav = stt.make_test_wav(seconds=1.0)

    def bad(chunk, i):
        if i == 0:
            raise RuntimeError("boom")
        return "ok"

    evs = list(stt.stream_partials(wav, bad, window_ms=500))
    kinds = [e["type"] for e in evs]
    assert "window-error" in kinds and evs[-1]["text"] == "ok"


def test_split_wav_rejects_non_16bit():
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(1); w.setframerate(8000)
        w.writeframes(b"\x00" * 800)
    with pytest.raises(ValueError):
        stt.split_wav(buf.getvalue())


# --- Discord VC boundary ---

def test_vc_absent_without_token():
    r = vc.join_plan({}, "123", "u1")
    assert r == {"ok": False, "reason": "credential_absent",
                 "setup_contract": vc.SETUP_CONTRACT}


def test_vc_needs_allowlist_then_gates_caller(monkeypatch):
    monkeypatch.setenv("HERMES_HOME", os.environ["HERMES_HOME"])
    env = {"DISCORD_BOT_TOKEN": "t"}
    assert vc.join_plan(env, "123", "u1")["reason"] == "allowlist_unconfigured"
    vc.set_allowlist(["u1"])
    assert vc.join_plan(env, "123", "u2")["reason"] == "caller_not_allowlisted"
    ok = vc.join_plan(env, "123", "u1")
    assert ok["ok"] and ok["plan"]["steps"][0] == "adapter.join_voice_channel"


def test_vc_fixture_adapter_sequence():
    class FakeAdapter:
        def __init__(self):
            self.calls = []
        def is_in_voice_channel(self):
            self.calls.append("is_in"); return True
        def get_voice_channel_info(self):
            self.calls.append("info"); return {"channel": "123"}
    st = vc.vc_status({"DISCORD_BOT_TOKEN": "t"}, adapter=FakeAdapter())
    assert st["live"] == {"in_channel": True, "info": {"channel": "123"}}


# --- GPT-Live consent gate ---

def test_gptlive_default_disabled():
    assert gl.status({})["enabled"] is False


def test_gptlive_enable_needs_disclosure_and_key():
    r1 = gl.enable({"OPENAI_API_KEY": "k"})
    assert r1["reason"] == "costs_not_accepted" and "per audio minute" in r1["disclosure"]
    r2 = gl.enable({}, accept_costs=True)
    assert r2["reason"] == "credential_absent"
    r3 = gl.enable({"OPENAI_API_KEY": "k"}, accept_costs=True)
    assert r3["ok"] and gl.status({"OPENAI_API_KEY": "k"})["enabled"] is True
    d = gl.disable()
    assert d == {"ok": True, "was_enabled": True, "disabled_at": d["disabled_at"]}
    assert gl.status({})["enabled"] is False


# --- Review preset ---

def test_review_preset_valid():
    preset = review.load_preset()
    chk = review.check_preset(preset)
    assert chk == {"ok": True, "errors": [], "name": "jarvis-review",
                   "checked_at": chk["checked_at"]}
    assert preset["privacy_filter"] == "full"


def test_review_plan_shape():
    p = review.plan(review.load_preset(), "harden the freeze path")
    assert p["ok"] and len(p["steps"][0]["run"]) == 2
    assert p["steps"][1]["privacy_filter"] == "full"
    assert "agent loop" in p["executes_in"]


def test_review_rejects_bad_preset_and_empty_task():
    bad = {"name": "x", "privacy_filter": "none"}
    assert review.check_preset(bad)["ok"] is False
    assert review.plan(review.load_preset(), "  ")["ok"] is False


# --- Langfuse opt-in ---

def test_langfuse_inert_by_default():
    st = lf.status({}, importable=lambda n: False)
    assert st["opted_in"] is False and st["tracing_live"] is False


def test_langfuse_enable_records_consent_not_activation():
    lf.enable()
    st = lf.status({}, importable=lambda n: False)
    assert st["opted_in"] is True and st["tracing_live"] is False
    assert "self-hosted" in st["self_hosted_note"]
    lf.disable()
    assert lf.status({})["opted_in"] is False


# --- Achievements ---

def test_achievements_computed_not_claimed():
    ac.record("brief", at="2026-09-21T06:30:00Z")
    ac.record("watchdog-quiet", at="2026-09-21T12:00:00Z")
    ac.record("moa-review", at="2026-09-22T01:00:00Z")
    s = ac.summary()
    assert set(s["earned"]) >= {"first-light", "early-riser", "night-owl",
                                "watchdog-clean", "reviewer"}
    assert "streak-3" in s["locked"]


def test_achievements_streaks():
    for d in ["2026-09-19", "2026-09-20", "2026-09-21"]:
        ac.record("x", at=f"{d}T12:00:00Z")
    assert "streak-3" in ac.summary()["earned"]


# --- Streaming say ---

def test_say_splits_and_measures():
    seen = []
    res = say.speak_stream("Hello there. How are you? Fine!",
                           speaker=lambda s: (seen.append(s), {"ok": True})[1])
    assert res["sentences"] == 3 and res["all_ok"] is True
    assert seen == ["Hello there.", "How are you?", "Fine!"]
    assert all("ms" in r for r in res["rows"])


def test_say_failure_is_per_sentence():
    def sp(s):
        if "bad" in s:
            raise RuntimeError("tts down")
        return {"ok": True}
    res = say.speak_stream("Good. This is bad. Good.", speaker=sp)
    assert res["sentences"] == 3 and res["all_ok"] is False
    assert res["rows"][1]["ok"] is False and res["rows"][0]["ok"] is True


# --- Snapshot ---

def test_snapshot_builds_and_writes():
    snap = snapshot.build()
    assert snap["ladder"]["selected"] in compute.RUNGS
    assert "review_preset" in snap and "achievements" in snap
    p = Path(os.environ["HERMES_HOME"]) / "jarvis" / "apex" / "apex-snapshot.json"
    assert p.exists() and json.loads(p.read_text())["built_at"] == snap["built_at"]
