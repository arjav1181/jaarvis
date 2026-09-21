"""W4 beast-talk tests — continuous loop, narration, streaming partials.

Covers the W4 wave (live proofs pasted in the wave report):
  - state machine (IDLE->LISTENING->TRANSCRIBING->THINKING->SPEAKING) + badge
  - stop-phrases (evaluated from the page source via node; skipped w/o node)
  - verbosity levels + per-soul narration lines, speech-only (no submit path)
  - VAD constants sane + server VAD config explicit in TEST home
  - streaming partials (splitter, first-audio label, narration-excluded stamp)
  - 3-turn fixture proof on one sid (fact, recall, follow-up use)
  - streaming budget measured (submit->first-delta + speak ms)
  - no-core-touch vs upstream/main

Live legs need the :3000 rig + JARVIS_RIG_PWFILE and skip cleanly otherwise.
Run with the W0 venv active: `python -m pytest tests/jarvis/ -v`
"""

import base64
import importlib.util
import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
JARVIS_DIR = REPO_ROOT / "jarvis"
PAGE = JARVIS_DIR / "hud" / "voice.html"
TEST_HOME = Path(os.environ.get("JARVIS_TEST_HOME", str(Path.home() / ".jarvis-test")))

needs_ws = pytest.mark.skipif(importlib.util.find_spec("websockets") is None,
                              reason="websockets lib missing")
needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node missing (regex eval)")


def _has_upstream_ref():
    r = subprocess.run(["git", "rev-parse", "--verify", "upstream/main"],
                       cwd=REPO_ROOT, capture_output=True)
    return r.returncode == 0


def _src():
    return PAGE.read_text()


def test_state_machine():
    src = _src()
    m = re.search(r"const STATES = \[(.*?)\];", src)
    assert m, "STATES list required"
    states = re.findall(r'"([A-Z]+)"', m.group(1))
    assert states == ["IDLE", "LISTENING", "TRANSCRIBING", "THINKING", "SPEAKING"]
    assert "statebadge" in src and "setState(" in src


@needs_node
def test_stop_phrases_from_source():
    src = _src()
    m = re.search(r"const STOP_PATTERNS = (/\^.*?/i);", src)
    assert m, "STOP_PATTERNS required"
    js = f"const STOP_PATTERNS = {m.group(1)};\n" + r"""
const cases = [["stop", true], ["Goodbye!", true], ["that's all.", true],
  ["cancel", true], ["stop the presses", false], ["unstoppable", false],
  ["what is this?", false]];
let bad = [];
for (const [t, want] of cases) if (STOP_PATTERNS.test(t) !== want) bad.push(t);
if (bad.length) { console.error("MISMATCH:" + bad.join("|")); process.exit(1); }
console.log("STOP_OK");"""
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "STOP_OK" in r.stdout, r.stderr[-500:]


def test_verbosity_and_narration_lines():
    src = _src()
    m = re.search(r"const VERBOSITIES = \[(.*?)\];", src)
    assert m and re.findall(r'"([a-z]+)"', m.group(1)) == ["verbose", "normal", "silent"]
    for soul in ("jarvis", "ultron"):
        for kind in ("start", "tool", "done"):
            assert re.search(rf"{soul}:\s*\{{[^}}]*{kind}:", src), \
                f"NARR.{soul}.{kind} required"
    body = src.split("async function narrate", 1)[1].split("\n}\n", 1)[0]
    assert "fetchSpeech" in body, "narration speaks through the audio path"
    assert "rpc(" not in body and "prompt.submit" not in body and "approve" not in body, \
        "narration must be speech-only (no submit/approve path)"


def test_vad_constants():
    src = _src()
    level = int(re.search(r"const VAD_LEVEL = (\d+);", src).group(1))
    ms = int(re.search(r"const VAD_SILENCE_MS = (\d+);", src).group(1))
    assert 1 <= level <= 100 and 500 <= ms <= 5000


def test_server_vad_config():
    cfg = yaml.safe_load((TEST_HOME / "config.yaml").read_text())
    local = ((cfg.get("stt") or {}).get("local")) or {}
    assert cfg.get("stt", {}).get("enabled") is True
    assert local.get("model") == "base" and local.get("vad") is True
    assert int(local.get("vad_min_silence_ms")) == 500
    assert float(local.get("no_speech_prob_threshold")) == pytest.approx(0.6)
    assert float(local.get("logprob_threshold")) == pytest.approx(-1.0)


def test_streaming_partials():
    src = _src()
    assert "function splitSentences" in src
    assert "SPEAK[streamed first-audio:" in src
    assert "S.spoken" in src and "S.firstAudioAt" in src
    # Narration must not stamp first-audio (reply audio only).
    assert "playUrl(j.data_url, false)" in src


class Rig:
    def __init__(self, base, password):
        import http.cookiejar
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        req = urllib.request.Request(
            base + "/auth/password-login",
            data=json.dumps({"provider": "basic", "username": "sir",
                             "password": password}).encode(),
            headers={"Content-Type": "application/json"})
        with self.op.open(req, timeout=20) as r:
            assert r.status == 200
        self.cookies = "; ".join(f"{c.name}={c.value}" for c in self.jar)

    def rest(self, path, timeout=15):
        req = urllib.request.Request(self.base + path,
                                     headers={"Cookie": self.cookies})
        with self.op.open(req, timeout=timeout) as r:
            return json.load(r)


def rig():
    base = os.environ.get("JARVIS_RIG_BASE", "http://127.0.0.1:3000")
    pwfile = os.environ.get("JARVIS_RIG_PWFILE", "")
    password = Path(pwfile).read_text().strip().splitlines()[0] if pwfile else ""
    if not password:
        pytest.skip("no rig password file (JARVIS_RIG_PWFILE) — honest-absent")
    try:
        urllib.request.urlopen(base + "/login", timeout=10).read()
    except Exception as exc:
        pytest.skip(f"rig unreachable at {base} ({exc}) — honest-absent")
    try:
        return Rig(base, password)
    except Exception as exc:
        pytest.skip(f"rig login failed ({exc}) — honest-absent")


@needs_ws
def test_three_turn_fixture_proof():
    import asyncio
    import websockets
    r = rig()

    async def turn(ws, sid, text, n):
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": f"w{n}",
                                  "method": "prompt.submit",
                                  "params": {"session_id": sid, "text": text}}))
        parts, first_ms, t0 = [], None, asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < 180:
            try:
                f = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            except asyncio.TimeoutError:
                pass
            else:
                if f.get("method") == "event" and f.get("params"):
                    typ, p = f["params"].get("type"), f["params"].get("payload") or {}
                    if typ == "message.delta":
                        if first_ms is None:
                            first_ms = (asyncio.get_event_loop().time() - t0) * 1000
                        parts.append(p.get("text", ""))
                    if typ in ("turn.end", "turn.error"):
                        break
                continue
            ss = r.rest("/api/sessions?limit=8")
            hit = next((s for s in ss.get("sessions", [])
                        if (s.get("title") or "") == text[:60]
                        or (s.get("title") or "").startswith(text[:30])), None)
            if hit and not parts:
                msgs = r.rest(f"/api/sessions/{hit['id']}/messages?limit=4")
                a = [m for m in msgs.get("messages", []) if m.get("role") == "assistant"]
                if a and len(str(a[-1].get("text") or "")) > 20:
                    return str(a[-1].get("text")), first_ms
        return "".join(parts), first_ms

    async def run():
        req = urllib.request.Request(
            r.base + "/api/auth/ws-ticket", data=b"{}",
            headers={"Content-Type": "application/json", "Cookie": r.cookies})
        with r.op.open(req, timeout=20) as resp:
            tick = json.load(resp)
        async with websockets.connect(
                f"ws://127.0.0.1:3000/api/ws?ticket={tick['ticket']}",
                additional_headers={"Cookie": r.cookies},
                max_size=8 * 1024 * 1024) as ws:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": "w0",
                                      "method": "session.create", "params": {}}))
            sid, t0 = None, asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - t0 < 30:
                f = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                if f.get("id") == "w0" and isinstance(f.get("result"), dict):
                    sid = f["result"].get("session_id")
                    break
            assert sid, "no session"
            r1, fd1 = await turn(ws, sid, "Remember this: my favorite bird is the Thunderbird.", 1)
            r2, fd2 = await turn(ws, sid, "What is my favorite bird?", 2)
            r3, fd3 = await turn(ws, sid, "Use it in a short sentence about tin birds.", 3)
            return sid, (r1, r2, r3), (fd1, fd2, fd3)

    sid, (r1, r2, r3), fds = asyncio.run(run())
    assert r1.strip(), "turn 1 empty"
    assert "thunderbird" in r2.lower(), f"turn 2 lost recall: {r2!r}"
    assert "thunderbird" in r3.lower(), f"turn 3 lost follow-up: {r3!r}"
    got = [round(f) for f in fds if f]
    print(f"\n3-turn proof sid={sid} first-delta_ms={got}")


def test_streaming_budget():
    r = rig()
    import time
    t0 = time.perf_counter()
    req = urllib.request.Request(
        r.base + "/api/audio/speak",
        data=json.dumps({"text": "At your service, sir."}).encode(),
        headers={"Content-Type": "application/json", "Cookie": r.cookies})
    with r.op.open(req, timeout=120) as resp:
        res = json.load(resp)
    ms = (time.perf_counter() - t0) * 1000
    assert res.get("ok") and res.get("data_url")
    nbytes = len(base64.b64decode(res["data_url"].split(",", 1)[1]))
    assert nbytes > 1024
    print(f"\nspeak pipeline ms={round(ms)} bytes={nbytes} provider={res.get('provider')}")


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
