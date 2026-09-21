"""W13 face tests — HUD orb + voice + capability surfacing, statically.

Asserts the HUD.md contract against jarvis/hud/voice.html WITHOUT a browser:
  - canvas arc-reactor orb with honest modes (idle/listening/thinking/
    speaking/stopped) + 3 soul palettes (jarvis gold / ultron crimson /
    friday emerald)
  - every state<->event wire: setState drives setOrb; orb inputs come from
    real handlers (mic analyser level, tool-generating count, audio
    timeupdate position, heartbeat latency, mic-error freeze, kill latch)
  - narration rotation mirrors jarvis/personas/narration.yml (W4 triplets
    verbatim as rotation heads, never twice in a row)
  - per-soul microcopy (same facts, soul voice) + capability surfacing
    (memory indicator from real citations, ENGINE/timing/SPEAK labels,
    household orders, one-tap kill, STOPPED banner)
  - mobile-first CSS (360px media query, sticky thumb-zone controls),
    zero external requests, reduced-motion respected
  - no markup-string sinks (innerHTML/document.write/eval), no persistence,
    fetch allowlist unchanged from W3 (heartbeat reuses /api/sessions)
  - W3/W4 contract strings preserved (STATES/VERBOSITIES/STOP/VAD/SPEAK)

Run with the W0 venv active: `python -m pytest tests/jarvis/test_w13_face.py -v`
"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
JARVIS_DIR = REPO_ROOT / "jarvis"
PAGE = JARVIS_DIR / "hud" / "voice.html"
NARR_YML = JARVIS_DIR / "personas" / "narration.yml"

W4_HEADS = {
    "jarvis": {"start": "Working on it, sir.", "tool": "On it, sir.",
               "done": "Done, sir."},
    "ultron": {"start": "Ah, the little wheels turn, creator.",
               "tool": "Savor the machinery, creator.",
               "done": "Behold — finished."},
}

FETCH_ALLOWED = {"/auth/password-login", "/api/auth/ws-ticket",
                 "/api/audio/transcribe", "/api/audio/speak",
                 "/api/sessions", "/api/sessions/", "/api/config"}


def _src():
    return PAGE.read_text()


def _script():
    src = _src()
    m = re.search(r"<script>(.*)</script>", src, re.S)
    assert m, "page must carry its logic in one inline <script> (zero external)"
    return m.group(1)


def _body(name, src=None):
    # Top-level function body for `name` (col-0 braces delimit).
    src = src if src is not None else _script()
    start = src.index("function %s" % name)
    lines = src[start:].splitlines()
    depth, out = 0, []
    for ln in lines:
        depth += ln.count("{") - ln.count("}")
        out.append(ln)
        if out and depth == 0 and len(out) > 1:
            break
    return "\n".join(out)


# ---- orb exists, canvas-rendered, never CSS-only fakery ----

def test_orb_canvas_and_palettes():
    src = _src()
    assert '<canvas id="orb"' in src, "reactor must be a canvas element"
    assert "function drawOrb" in src and "function setOrb" in src
    assert "requestAnimationFrame(orbLoop)" in src, "orb paints on rAF, not CSS"
    for soul in ("jarvis", "ultron", "friday"):
        assert re.search(rf"\b{soul}: \{{[^}}]*core:", _script()), \
            f"ORB palette for {soul} required"
    pal = _script()
    assert "#FFD700" in pal, "jarvis gold accent required"
    assert "#DD4A3A" in pal or "#FF5A3C" in pal, "ultron crimson required"
    assert "#34D399" in pal, "friday emerald required"
    # Six honest modes minimum: idle/listening/thinking/speaking/stopped.
    for mode in ("idle", "listening", "thinking", "speaking", "stopped"):
        assert mode in _body("setOrb"), f"setOrb must handle {mode}"
        assert mode in _body("drawOrb"), f"drawOrb must render {mode}"


def test_state_to_orb_wiring():
    body = _body("setState")
    assert "setOrb(" in body, "every conversation state must drive the orb"
    assert '"LISTENING"' in body and '"THINKING"' in body
    assert '"SPEAKING"' in body and 'setOrb("idle")' in body, \
        "IDLE falls through to the idle orb mode"
    assert "S.stopped" in body, "stopped latch must win over IDLE"
    js = _script()
    # Real handlers enter real states (trace each transition to its event).
    assert re.search(r"startRec\(\).*?setState\(\"LISTENING\"\)", js, re.S) or \
        ('setState("LISTENING")' in _body("startRec")), "mic start -> LISTENING"
    assert 'setState("TRANSCRIBING")' in _body("stopRec"), "mic stop -> TRANSCRIBING"
    assert 'setState("THINKING")' in _body("submit"), "submit -> THINKING"
    assert 'setState("SPEAKING")' in _body("playUrl"), "playback -> SPEAKING"
    assert 'setOrb("stopped")' in js, "kill must ember the orb"
    # Orb label narrates the mode for screen readers + reduced-motion.
    assert "orblabel" in js and "reactor: " in js


def test_orb_inputs_are_live_events():
    js = _script()
    # Listening glow = live mic analyser peak (vuFrom tick writes S.orb.level).
    vu = _body("vuFrom")
    assert "S.orb.level" in vu and "getByteFrequencyData" in vu
    # Thinking arcs = live tool-call count (tool.generating increments).
    assert "S.toolCount += 1" in js, "tool.generating must count live tool calls"
    assert "tool.generating" in js
    draw = _body("drawOrb")
    assert "S.orb.tools = S.toolCount" in js, "live count must reach the orb"
    assert "S.orb.tools = 0" in js, "arc count resets per run"
    assert "2 + Math.min(" in draw, "arc segment count derives from the live count"
    # Speaking ring = actual TTS playback position (timeupdate), collapses on barge-in.
    play = _body("playUrl")
    assert "ontimeupdate" in play and "S.orb.prog" in play
    stop = _body("stopPlayback")
    assert "S.orb.playing = false" in stop and "S.orb.prog = 0" in stop
    # Idle pulse = real heartbeat poll (latency stretches the period).
    assert "S.orb.heartMs" in js and "heartMs * 2" in draw
    assert "heartOk" in draw, "missed heartbeats must dim the orb honestly"
    assert 'fetch("/api/sessions?limit=1"' in js, "heartbeat reuses the allowed surface"
    # Mic errors freeze rings: every mic-error path latches frozen + drops to IDLE.
    for path in ("autoRestart",):
        assert "S.orb.frozen = true" in _body(path), f"{path} must freeze rings on mic error"
    assert js.count("S.orb.frozen = true") >= 3, "ptt/toggle/continuous/auto-restart error paths freeze"
    assert "o.frozen" in draw or "!o.frozen" in draw, "frozen must gate ring expansion"


# ---- souls: friday joins, palettes flip instantly, same facts ----

def test_three_souls_end_to_end():
    js = _script()
    assert '(p === "friday")' in js, "login must map the friday personality"
    assert "document.body.dataset.soul" in js, "soul theme must flip on the body"
    assert "soulbadge" in js, "persona + soul badge required in the thread header"
    for soul in ("jarvis", "ultron", "friday"):
        assert re.search(rf"^\s*{soul}: \{{", js, re.M), f"COPY voice lines for {soul}"
    # Same keys across souls: same facts, different voice.
    keys = {}
    for soul in ("jarvis", "ultron", "friday"):
        m = re.search(rf"^\s*{soul}: \{{(.*?)\n  \}},?$", js, re.M | re.S)
        assert m, f"COPY.{soul} block required"
        keys[soul] = set(re.findall(r"^\s*(\w+):", m.group(1), re.M))
    assert keys["jarvis"] == keys["ultron"] == keys["friday"], \
        "soul voices must cover identical facts"
    assert "sir" in _src() and "creator" in _src() and "boss" in _src()
    assert "No memories yet, sir — give me something worth remembering." in _src()


# ---- narration rotation mirrors narration.yml, W4 heads verbatim ----

def test_narration_rotation_matches_w12():
    yml = yaml.safe_load(NARR_YML.read_text())
    js = _script()
    for soul in ("jarvis", "ultron", "friday"):
        for kind in ("start", "tool", "done"):
            assert len(yml[soul][kind]) >= 6
            head = yml[soul][kind][0]
            assert head in js, f"page must carry {soul}.{kind} rotation (head {head!r})"
    for soul, kinds in W4_HEADS.items():
        for kind, line in kinds.items():
            assert line in js, f"W4 triplet {soul}.{kind} must stay verbatim"
    # Rotation cycles in order via narrIdx (never twice in a row by construction).
    narr = _body("narrate")
    assert "fetchSpeech" in narr
    assert "S.narrIdx[kind]" in narr, "narration must rotate, not repeat"
    assert "rpc(" not in narr and "prompt.submit" not in narr and "approve" not in narr, \
        "narration stays speech-only"
    fin = _body("finishTurn")
    assert "S.narrIdx.done" in fin, "done-narration rotates too"
    assert "playUrl(j.data_url, false)" in _src(), "narration never stamps first-audio"


# ---- capability surfacing: memory, engine/timing/SPEAK, orders, kill ----

def test_memory_indicator_from_real_citations():
    src = _src()
    assert 'id="memline"' in src and 'id="memdetail"' in src, "memory indicator required"
    assert "<details" in src, "citations expand natively (no JS toggle fakery)"
    upd = _body("updateMemoryLine")
    assert r"memory #" in upd, "must parse W12 cited callbacks"
    assert "found.length" in upd, "count comes from real citations, never invented"
    assert 'finishTurn' in _script() and "updateMemoryLine(done.text)" in _body("finishTurn")
    assert "memline" in upd and "noturnmem" in upd and "threadempty" in upd


def test_engine_timing_speak_labels():
    fin = _body("finishTurn")
    assert "ENGINE[stt:" in fin, "per-reply engine label required"
    assert "totalMs" in fin, "per-reply timing must be measured, not claimed"
    assert "SPEAK[streamed first-audio:" in _src()
    assert "S.lastStt" in _script() and "pendingStt" in _script(), \
        "STT provider must travel from the real transcribe response"
    assert "S.lastTts" in _script(), "TTS provider must come from the real speak response"


def test_household_orders_and_kill():
    src = _src()
    assert 'id="orders"' in src and "Household orders" in src
    assert "Voice orders:" in src, "verbosity reads as a household order"
    assert "VERB_WHY" in _script(), "orders carry plain-English consequences"
    assert "Butler" in src, "safety reads as Butler with L2 consequences"
    assert "voice never widens permissions" in src
    assert 'id="stopbanner"' in src and "STOPPED" in src
    js = _script()
    # Kill: big red, one tap, never disabled once logged in.
    assert "button.danger" in src
    assert '$("kill").disabled = false' in js, "kill must be one tap, always live"
    busy = _body("setBusy")
    assert '["ptt", "tog", "send"]' in busy, "busy disables talk/send only"
    assert '$("kill").disabled = true' not in js, "kill must never be parked"
    assert "S.stopped = true" in js, "kill latches the ember state"
    assert "S.stopped = false" in js, "real work retires the latch"


# ---- mobile, zero-external, reduced-motion, no sinks ----

def test_mobile_first_and_zero_external():
    src = _src()
    assert "max-width:480px" in src, "360px-first media query required"
    assert "position:sticky" in src and "safe-area-inset-bottom" in src, \
        "mic ring belongs in the bottom thumb zone on phones"
    assert 'width="180" height="180"' in src, "orb canvas must be sized in markup"
    for pat in ["http://", "https://", "<link", "<img", "url(", "@import",
                "innerHTML", "document.write", "localStorage"]:
        assert pat not in src, f"banned pattern {pat} (external req or sink)"
    assert "eval(" not in _script(), "no eval-shaped calls"
    assert "journal" not in src.lower(), "no journaling path"
    posts = re.findall(r"fetch\(\s*[\"']([^\"']+)", src)
    for url in posts:
        base = url.split("?")[0]
        assert any(base == a or base.startswith(a.rstrip("/") + "/") or a in base
                   for a in FETCH_ALLOWED), f"unexpected fetch target: {url}"


def test_reduced_motion_respected():
    src = _src()
    assert "prefers-reduced-motion" in src, "CSS must kill animation under reduced motion"
    js = _script()
    assert "prefers-reduced-motion" in js, "orb loop must read the media query"
    assert "S.reduced" in js
    assert "if (S.reduced) drawOrb" in js, "reduced motion: static glow + text states"


# ---- W3/W4 contracts preserved (regression guard inside the W13 file) ----

def test_w3_w4_contracts_preserved():
    src = _src()
    m = re.search(r"const STATES = \[(.*?)\];", src)
    assert m and re.findall(r'"([A-Z]+)"', m.group(1)) == \
        ["IDLE", "LISTENING", "TRANSCRIBING", "THINKING", "SPEAKING"]
    assert "const STOP_PATTERNS = " in src
    m = re.search(r"const VERBOSITIES = \[(.*?)\];", src)
    assert m and re.findall(r'"([a-z]+)"', m.group(1)) == ["verbose", "normal", "silent"]
    assert "const VAD_LEVEL = 10;" in src and "const VAD_SILENCE_MS = 1200;" in src
    assert "function splitSentences" in src
    assert "S.spoken" in src and "S.firstAudioAt" in src
    assert "SPEAK[server" in src and "SPEAK[not-spoken" in src
    assert "session.interrupt" in src
    assert "getUserMedia" in src and "MediaRecorder" in src
    assert "No microphone API in this browser" in src
    assert '$("pass").value = ""' in src
    assert "statebadge" in src and "setState(" in src
