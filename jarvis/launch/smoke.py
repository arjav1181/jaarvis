#!/usr/bin/env python3
"""W14 launch smoke: HUD gate checks + rig timing harness.

Re-runnable. Hermetic where possible; every part that touches the live
rig (or slow local models) is skipped when ``JARVIS_SMOKE_SKIP_RIG=1``
(or ``--skip-rig``). No network access in the hermetic path.

Rig auth uses the dashboard session login (NOT per-request basic auth):
``POST /auth/password-login {provider,username,password}`` sets cookies;
subsequent GETs carry the cookie jar.

Credentials NEVER live in this file: password comes from
``JARVIS_RIG_PW`` (or first line of ``JARVIS_RIG_PWFILE``).

Usage:
  python jarvis/launch/smoke.py [--skip-rig] [--report PATH] [--base URL]
  python -m pytest tests/jarvis/test_w14_launch.py -v   # hermetic unit parts

Report JSON keys (see validate_report): pages, login_ms, text_turn,
tts, stt, barge_in, deployed_match.
"""

import argparse
import base64
import http.cookiejar
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

PAGES = ("voice", "diag", "audit", "apex",
         "foresight", "hands", "presence", "degraded")

# Every honest-absent hand re-verified in W14. Single source of truth for
# the wake-list completeness test (tests/jarvis/test_w14_launch.py).
DORMANT_HANDS = (
    {"hand": "GPU", "absent_reason": "no CUDA device on rig/box",
     "wakes_with": "NVIDIA GPU + CUDA drivers visible to the runtime"},
    {"hand": "Discord", "absent_reason": "no bot token / voice channel configured",
     "wakes_with": "DISCORD_BOT_TOKEN + target voice channel id"},
    {"hand": "GPT-Live", "absent_reason": "no realtime API delegation creds",
     "wakes_with": "OpenAI realtime API key + delegation flag"},
    {"hand": "Telegram token", "absent_reason": "no bot token paired",
     "wakes_with": "TELEGRAM_BOT_TOKEN via pairing flow"},
    {"hand": "Spotify", "absent_reason": "no OAuth grant (parked per W6)",
     "wakes_with": "Spotify OAuth client grant + cron DJ routine enable"},
    {"hand": "HA", "absent_reason": "no Home Assistant URL/token (parked per W6)",
     "wakes_with": "HASS_URL + HOME_ASSISTANT_TOKEN (long-lived access token)"},
    {"hand": "Car", "absent_reason": "no vehicle bridge configured",
     "wakes_with": "vehicle API creds + bridge enable"},
)

REPORT_KEYS = ("pages", "login_ms", "text_turn", "tts",
               "stt", "barge_in", "deployed_match")


class SmokeConfigError(RuntimeError):
    pass


# ---------- pure helpers (hermetic, unit-tested) ----------

def page_url(base, name):
    return base.rstrip("/") + "/%s.html" % name


def gate_ok(code):
    """Unauth must gate: redirect to login or an auth error."""
    return code in (301, 302, 303, 307, 308, 401, 403)


def auth_ok(code):
    return code == 200


def load_password():
    pw = os.environ.get("JARVIS_RIG_PW", "").strip()
    if pw:
        return pw
    pwfile = os.environ.get("JARVIS_RIG_PWFILE", "")
    if pwfile:
        try:
            line = Path(pwfile).read_text().strip().splitlines()
        except OSError as exc:
            raise SmokeConfigError("cannot read JARVIS_RIG_PWFILE: %s" % exc)
        if line and line[0].strip():
            return line[0].strip()
    raise SmokeConfigError("set JARVIS_RIG_PW or JARVIS_RIG_PWFILE")


def wake_list():
    return [dict(h) for h in DORMANT_HANDS]


def validate_report(rep):
    """Checklist schema: every key present with the right shape."""
    for key in REPORT_KEYS:
        if key not in rep:
            raise ValueError("report missing key: %s" % key)
    if set(rep["pages"].keys()) != set(PAGES):
        raise ValueError("pages must cover exactly the 8 HUD pages")
    for name, entry in rep["pages"].items():
        for sub in ("unauth", "authed", "unauth_ms", "authed_ms"):
            if sub not in entry:
                raise ValueError("pages[%s] missing %s" % (name, sub))
    for key in ("login_ms",):
        if not isinstance(rep[key], (int, float)):
            raise ValueError("%s must be a number" % key)
    for key in ("text_turn", "tts", "stt", "barge_in"):
        if not isinstance(rep[key], dict):
            raise ValueError("%s must be an object" % key)
    if not isinstance(rep["deployed_match"], dict):
        raise ValueError("deployed_match must be an object")
    return True


# ---------- rig I/O ----------

class Rig:
    def __init__(self, base, password, timeout=15):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        t0 = time.perf_counter()
        req = urllib.request.Request(
            self.base + "/auth/password-login",
            data=json.dumps({"provider": "basic", "username": "sir",
                             "password": password}).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with self.op.open(req, timeout=timeout) as r:
                body = json.load(r)
        except urllib.error.HTTPError as exc:
            raise SmokeConfigError("rig login failed: HTTP %s" % exc.code)
        except Exception as exc:
            raise SmokeConfigError("rig unreachable at %s (%s)" % (base, exc))
        self.login_ms = (time.perf_counter() - t0) * 1000
        if not body.get("ok"):
            raise SmokeConfigError("rig login rejected: %r" % (body,))
        self.cookies = "; ".join(
            "%s=%s" % (c.name, c.value) for c in self.jar)

    def get_code(self, path, authed=True):
        req = urllib.request.Request(self.base + path)
        if authed:
            req.add_header("Cookie", self.cookies)
        opener = self.op if authed else urllib.request.build_opener(
            NoRedirectHandler)
        t0 = time.perf_counter()
        try:
            with opener.open(req, timeout=self.timeout) as r:
                code = r.status
        except RedirectCaught as red:
            code = red.code
        except urllib.error.HTTPError as exc:
            code = exc.code
        ms = (time.perf_counter() - t0) * 1000
        return code, ms

    def rest(self, path, payload, timeout=120):
        req = urllib.request.Request(
            self.base + path, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Cookie": self.cookies})
        t0 = time.perf_counter()
        with self.op.open(req, timeout=timeout) as r:
            body = json.load(r)
        return body, (time.perf_counter() - t0) * 1000


class RedirectCaught(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RedirectCaught(code)


def check_pages(rig):
    out = {}
    for name in PAGES:
        path = "/%s.html" % name
        unauth, unauth_ms = rig.get_code(path, authed=False)
        authed, authed_ms = rig.get_code(path, authed=True)
        out[name] = {"unauth": unauth, "authed": authed,
                     "unauth_ms": round(unauth_ms, 1),
                     "authed_ms": round(authed_ms, 1)}
    return out


def check_deployed_match(home=None):
    """Deployed overlay files byte-match repo sources (rig serves them)."""
    if home is None:
        home = Path(os.environ.get("HERMES_HOME", ""))
    out = {}
    overlay = Path(home) / "web_dist_overlay" if home else None
    for name in PAGES:
        src = REPO / "jarvis" / "hud" / ("%s.html" % name)
        dst = overlay / ("%s.html" % name) if overlay else None
        if not src.is_file():
            out[name] = "repo-missing"
        elif dst is None or not dst.is_file():
            out[name] = "not-deployed"
        elif src.read_bytes() == dst.read_bytes():
            out[name] = "match"
        else:
            out[name] = "differs"
    return out


def text_turn(rig, text="Reply with exactly: sir, systems nominal."):
    """One WS text turn: submit -> first-delta ms + total ms."""
    try:
        import asyncio
        import websockets
    except ImportError:
        return {"skipped": "websockets not installed"}
    return asyncio.run(_turn(rig, text))


async def _turn(rig, text):
    import websockets
    import asyncio
    import json as _json
    req = urllib.request.Request(
        rig.base + "/api/auth/ws-ticket", data=b"{}",
        headers={"Content-Type": "application/json",
                 "Cookie": rig.cookies})
    with rig.op.open(req, timeout=20) as resp:
        tick = _json.load(resp)
    async with websockets.connect(
            rig.base.replace("http", "ws", 1) + "/api/ws?ticket=" + tick["ticket"],
            additional_headers={"Cookie": rig.cookies},
            max_size=8 * 1024 * 1024) as ws:
        await ws.send(_json.dumps({"jsonrpc": "2.0", "id": "w0",
                                   "method": "session.create", "params": {}}))
        sid, t0 = None, asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < 30:
            try:
                f = _json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            except asyncio.TimeoutError:
                continue
            if f.get("id") == "w0" and isinstance(f.get("result"), dict):
                sid = f["result"].get("session_id")
                break
        if not sid:
            return {"error": "no session"}
        await ws.send(_json.dumps({"jsonrpc": "2.0", "id": "w1",
                                   "method": "prompt.submit",
                                   "params": {"session_id": sid, "text": text}}))
        parts, first_ms, t1 = [], None, asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t1 < 180:
            try:
                f = _json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            except asyncio.TimeoutError:
                continue
            if f.get("method") == "event" and f.get("params"):
                typ = f["params"].get("type")
                p = f["params"].get("payload") or {}
                if typ == "message.delta":
                    if first_ms is None:
                        first_ms = (asyncio.get_event_loop().time() - t1) * 1000
                    parts.append(p.get("text", ""))
                if typ in ("turn.end", "turn.error"):
                    break
        total_ms = (asyncio.get_event_loop().time() - t1) * 1000
        reply = "".join(parts)
        return {"reply_chars": len(reply),
                "reply_head": reply[:120],
                "first_delta_ms": round(first_ms, 1) if first_ms else None,
                "total_ms": round(total_ms, 1)}


def tts_speak(rig, text="At your service, sir."):
    body, ms = rig.rest("/api/audio/speak", {"text": text})
    if not body.get("ok") or not body.get("data_url"):
        return {"error": "speak failed", "ms": round(ms, 1)}
    try:
        nbytes = len(base64.b64decode(body["data_url"].split(",", 1)[1]))
    except Exception:
        nbytes = -1
    return {"ms": round(ms, 1), "bytes": nbytes,
            "provider": body.get("provider")}


def stt_local(wav=None):
    """Local faster-whisper transcribe (no network). Slow: rig-gated."""
    from tools.transcription_tools import transcribe_audio
    target = str(wav or (REPO / "tests" / "jarvis" / "fixtures" / "fixture.wav"))
    t0 = time.perf_counter()
    try:
        res = transcribe_audio(target)
    except Exception as exc:
        return {"error": "stt failed: %s" % exc}
    ms = (time.perf_counter() - t0) * 1000
    return {"ms": round(ms, 1),
            "transcript": (res.get("transcript") or "")[:160],
            "provider": res.get("provider"),
            "success": bool(res.get("success"))}


def barge_in(rig):
    """Interrupt a live turn; ms until deltas cease (turn.end/error)."""
    try:
        import asyncio
        import websockets
    except ImportError:
        return {"skipped": "websockets not installed"}
    return asyncio.run(_barge(rig))


async def _barge(rig):
    import websockets
    import asyncio
    import json as _json
    req = urllib.request.Request(
        rig.base + "/api/auth/ws-ticket", data=b"{}",
        headers={"Content-Type": "application/json",
                 "Cookie": rig.cookies})
    with rig.op.open(req, timeout=20) as resp:
        tick = _json.load(resp)
    async with websockets.connect(
            rig.base.replace("http", "ws", 1) + "/api/ws?ticket=" + tick["ticket"],
            additional_headers={"Cookie": rig.cookies},
            max_size=8 * 1024 * 1024) as ws:
        await ws.send(_json.dumps({"jsonrpc": "2.0", "id": "w0",
                                   "method": "session.create", "params": {}}))
        sid, t0 = None, asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < 30:
            try:
                f = _json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            except asyncio.TimeoutError:
                continue
            if f.get("id") == "w0" and isinstance(f.get("result"), dict):
                sid = f["result"].get("session_id")
                break
        if not sid:
            return {"error": "no session"}
        await ws.send(_json.dumps({"jsonrpc": "2.0", "id": "w1",
                                   "method": "prompt.submit",
                                   "params": {"session_id": sid,
                                              "text": "Count very slowly from 1 to 60, one number per line."}}))
        # Wait for the first delta (turn is live), then interrupt.
        # The relay can take >60 s to first delta; wait up to 180 s.
        t1 = asyncio.get_event_loop().time()
        live = False
        while asyncio.get_event_loop().time() - t1 < 180:
            try:
                f = _json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            except asyncio.TimeoutError:
                continue
            if (f.get("method") == "event" and f.get("params") and
                    f["params"].get("type") == "message.delta"):
                live = True
                break
        if not live:
            return {"error": "turn never went live"}
        t2 = asyncio.get_event_loop().time()
        await ws.send(_json.dumps({"jsonrpc": "2.0", "id": "w2",
                                   "method": "session.interrupt",
                                   "params": {"session_id": sid}}))
        # Drain until the turn ends (up to 30 s): record stray deltas.
        # Barge criterion (W3 receipt): no deltas generated past +3 s
        # after the interrupt (in-flight drain only).
        strays, ended, last_ts = [], False, t2
        t3 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t3 < 30:
            try:
                f = _json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            except asyncio.TimeoutError:
                continue
            now = asyncio.get_event_loop().time()
            if f.get("method") == "event" and f.get("params"):
                typ = f["params"].get("type")
                if typ == "message.delta":
                    last_ts = now
                    if (now - t2) * 1000 > 3000:
                        strays.append(round((now - t2) * 1000, 1))
                if typ in ("turn.end", "turn.error"):
                    ended = True
                    last_ts = now
                    break
        return {"barge_ms": round((last_ts - t2) * 1000, 1),
                "turn_ended": ended,
                "stray_deltas_past_3s": strays}


def run(base=None, skip_rig=False, wav=None, home=None):
    base = base or os.environ.get("JARVIS_RIG_BASE", "http://127.0.0.1:3000")
    if home is None:
        home = os.environ.get("JARVIS_SMOKE_HOME", "")
    if skip_rig or os.environ.get("JARVIS_SMOKE_SKIP_RIG") == "1":
        return {"skipped_rig": True, "pages": {},
                "login_ms": 0, "text_turn": {"skipped": "env"},
                "tts": {"skipped": "env"}, "stt": {"skipped": "env"},
                "barge_in": {"skipped": "env"},
                "deployed_match": check_deployed_match(home)}
    password = load_password()
    rig = Rig(base, password)
    report = {
        "pages": check_pages(rig),
        "login_ms": round(rig.login_ms, 1),
        "text_turn": text_turn(rig),
        "tts": tts_speak(rig),
        "stt": stt_local(wav),
        "barge_in": barge_in(rig),
        "deployed_match": check_deployed_match(home),
    }
    validate_report(report)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="W14 launch smoke")
    ap.add_argument("--skip-rig", action="store_true")
    ap.add_argument("--report", default="")
    ap.add_argument("--base", default="")
    ap.add_argument("--home", default="")
    ap.add_argument("--user", default="sir")
    args = ap.parse_args(argv)
    try:
        rep = run(base=args.base or None, skip_rig=args.skip_rig,
                  home=args.home or None)
    except SmokeConfigError as exc:
        print("SMOKE-CONFIG: %s" % exc, file=sys.stderr)
        return 2
    out = json.dumps(rep, indent=2)
    if args.report:
        Path(args.report).write_text(out + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
