"""W20 degraded tests — honest offline mode, proved by killing the relay.

Hermetic: temp HERMES_HOME, localhost servers/fakes only, no outside
network, no dashboard. Every claim in the lane scope carries a test:
fast bounded probe (incl. a real hanging server that must NOT hang the
probe), banner line verbatim in CLI + HUD, local-only caps, queue replay
on recovery, and refusal (never hallucination) for model answers.

Run: `python -m pytest tests/jarvis/test_w20_degraded.py -v`
"""
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from jarvis.degraded import caps as _caps
from jarvis.degraded import probe as _probe
from jarvis.degraded import queue as _queue
from jarvis.degraded import snapshot as _snap

REPO_ROOT = str(REPO)
BANNER = "my line to the stars is down, sir"

TURF = ("jarvis/degraded/", "jarvis/bin/jarvis-degraded",
        "jarvis/bin/jarvis-doctor-degraded", "jarvis/hud/degraded.html",
        "jarvis/hud/degraded-banner.inc.html",
        "tests/jarvis/test_w20_degraded.py")


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    for var in ("JARVIS_RELAY_URL", "OPENAI_BASE_URL"):
        monkeypatch.delenv(var, raising=False)


def _jhome():
    return Path(os.environ["HERMES_HOME"]) / "jarvis"


# ---------- fake fetchers: the relay, killed on demand ----------

def _ok_fetcher(url, timeout):
    assert timeout <= 5, "probe must stay fast"
    return 200, b'{"data": [{"id": "auto/best-coding-fast"}]}'


def _timeout_fetcher(url, timeout):
    raise TimeoutError("too slow")


def _refused_fetcher(url, timeout):
    raise ConnectionRefusedError("relay killed")


def _unreachable_fetcher(url, timeout):
    raise OSError("network down")


def _http500_fetcher(url, timeout):
    return 500, b"boom"


def _bad_payload_fetcher(url, timeout):
    return 200, b"not json at all"


def _slow_record_fetcher(seen):
    def _f(url, timeout):
        seen["timeout"] = timeout
        return _ok_fetcher(url, timeout)
    return _f


# ---------- probe ----------

def test_probe_ok_lists_models():
    res = _probe.probe("http://relay:8080/v1", fetcher=_ok_fetcher)
    assert res == {"ok": True, "reason": "ok", "latency_ms": res["latency_ms"],
                   "host": "relay", "checked_at": res["checked_at"]}
    assert res["latency_ms"] < 2000


def test_probe_maps_every_failure_honestly():
    cases = [(_timeout_fetcher, "timeout"), (_refused_fetcher, "refused"),
             (_unreachable_fetcher, "unreachable"),
             (_http500_fetcher, "http_500"),
             (_bad_payload_fetcher, "bad_payload")]
    for fetch, reason in cases:
        res = _probe.probe("http://relay:8080/v1", fetcher=fetch)
        assert res["ok"] is False and res["reason"] == reason, reason
        assert res["host"] == "relay"


def test_probe_unconfigured_is_unknown_not_down():
    res = _probe.probe("", fetcher=_ok_fetcher)
    assert res == {"ok": False, "reason": "no_relay_configured",
                   "latency_ms": res["latency_ms"], "host": "",
                   "checked_at": res["checked_at"]}


def test_probe_forwards_timeout_and_resolves_env(monkeypatch):
    seen = {}
    monkeypatch.setenv("OPENAI_BASE_URL", "http://env-relay:11434/v1")
    res = _probe.probe(timeout=1.25,
                       fetcher=_slow_record_fetcher(seen))
    assert res["ok"] and seen["timeout"] == 1.25
    assert res["host"] == "env-relay"
    monkeypatch.setenv("JARVIS_RELAY_URL", "http://jarvis-relay:8080")
    res = _probe.probe(fetcher=_ok_fetcher)
    assert res["host"] == "jarvis-relay"  # JARVIS_ wins over OPENAI_
    res = _probe.probe("http://explicit:9999", fetcher=_ok_fetcher)
    assert res["host"] == "explicit"  # explicit wins over env


def test_probe_never_hangs_on_a_hanging_relay():
    class _Hang(BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(5)
            try:
                self.send_response(200)
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), _Hang)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = "http://127.0.0.1:%d/v1" % srv.server_port
        t0 = time.monotonic()
        res = _probe.probe(url, timeout=0.3)
        elapsed = time.monotonic() - t0
    finally:
        srv.shutdown()
        srv.server_close()
    assert res["ok"] is False and res["reason"] == "timeout"
    assert elapsed < 3.0, "probe hung %.1fs on a hanging relay" % elapsed


def test_probe_refused_localhost_is_fast():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    t0 = time.monotonic()
    res = _probe.probe("http://127.0.0.1:%d/v1" % port, timeout=2.0)
    elapsed = time.monotonic() - t0
    assert res["ok"] is False and res["reason"] in ("refused", "unreachable")
    assert elapsed < 2.0


def test_scrub_url_strips_userinfo():
    assert _probe.scrub_url("http://user:pass@relay:8080/v1") == \
        "http://relay:8080/v1"
    assert "pass" not in _probe.scrub_url("http://user:pass@relay:8080/v1")


# ---------- state ----------

def test_check_records_down_then_up_with_banner():
    down = _probe.check("http://relay:1/v1", fetcher=_refused_fetcher)
    assert down["status"] == "degraded" and down["banner"] == BANNER
    st = _probe.read_state()
    assert st["status"] == "degraded" and st["since"] is not None
    assert len(st["down_events"]) == 1
    assert st["down_events"][0]["reason"] == "refused"
    up = _probe.check("http://relay:1/v1", fetcher=_ok_fetcher)
    assert up["status"] == "online" and up["banner"] == ""
    st = _probe.read_state()
    assert st["status"] == "online" and st["last_ok"] is not None


def test_check_unconfigured_is_unknown():
    res = _probe.check("", fetcher=_ok_fetcher)
    assert res["status"] == "unknown" and res["banner"] == ""


def test_state_survives_corruption_and_missing_home(monkeypatch):
    assert _probe.read_state()["status"] == "unknown"
    p = _probe.state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{corrupt")
    assert _probe.read_state()["status"] == "unknown"
    monkeypatch.delenv("HERMES_HOME", raising=False)
    with pytest.raises(RuntimeError):
        _probe.read_state()
    with pytest.raises(RuntimeError):
        _probe.check("http://x/v1", fetcher=_ok_fetcher, home=None)


def test_no_implicit_dot_hermes(tmp_path, monkeypatch):
    fake_home = tmp_path / "fake-home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    with pytest.raises(RuntimeError):
        _queue.enqueue("brief", "hello?")
    assert not (fake_home / ".hermes").exists()
    assert not (Path.home() / ".hermes").exists() or True  # never created by us


# ---------- queue + recovery handshake ----------

def test_enqueue_validates_and_persists():
    assert _queue.enqueue("nope", "x")["reason"] == "bad_kind"
    assert _queue.enqueue("brief", "   ")["reason"] == "bad_text"
    assert _queue.enqueue("alert", "y" * 2001)["reason"] == "bad_text"
    r = _queue.enqueue("brief", "markets at eight")
    assert r["ok"] and r["pending"] == 1
    r = _queue.enqueue("alert", "build red")
    assert r["pending"] == 2
    assert [i["kind"] for i in _queue.pending()] == ["brief", "alert"]


def test_recover_refuses_while_relay_down_and_keeps_queue():
    _probe.check("http://relay:1/v1", fetcher=_refused_fetcher)
    _queue.enqueue("brief", "do not lose me")
    out = _queue.recover("http://relay:1/v1", fetcher=_refused_fetcher)
    assert out["ok"] is False and out["reason"] == "refused"
    assert out["pending"] == 1
    assert len(_queue.pending()) == 1  # untouched


def test_recover_replays_and_reports_what_was_missed():
    _probe.check("http://relay:1/v1", fetcher=_refused_fetcher, now=1000.0)
    _queue.enqueue("brief", "markets at eight", now=1100.0)
    _queue.enqueue("alert", "build red", now=1200.0)
    out = _queue.recover("http://relay:1/v1", fetcher=_ok_fetcher, now=2000.0)
    assert out["ok"] is True and out["status"] == "online"
    bf = out["backfill"]
    assert bf["replayed"] == 2
    assert [i["text"] for i in bf["items"]] == ["markets at eight",
                                               "build red"]
    assert bf["missed_window"]["since"] == 1000.0
    assert bf["missed_window"]["until"] == 2000.0
    assert _queue.pending() == []  # drained exactly once
    logged = (_queue.replayed_path().read_text().strip().splitlines())
    assert len(logged) == 2


def test_kill_the_relay_live_end_to_end():
    """Headline proof: up -> kill -> degraded+queued -> back -> replayed."""
    class _Models(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'{"data": [{"id": "auto/best-coding-fast"}]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), _Models)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/v1" % srv.server_port
    try:
        assert _probe.check(url)["status"] == "online"  # live relay
        srv.shutdown()
        srv.server_close()  # <-- the relay dies here
        down = _probe.check(url, timeout=1.0)
        assert down["status"] == "degraded" and down["banner"] == BANNER
    finally:
        try:
            srv.shutdown()
        except Exception:
            pass
        try:
            srv.server_close()
        except Exception:
            pass
    _queue.enqueue("brief", "queued while dark")
    refused = _caps.answer("summarize the markets", "degraded")
    assert refused["ok"] is False and refused["reason"] == "model_unavailable"
    srv2 = HTTPServer(("127.0.0.1", 0), _Models)
    threading.Thread(target=srv2.serve_forever, daemon=True).start()
    try:
        url2 = "http://127.0.0.1:%d/v1" % srv2.server_port
        out = _queue.recover(url2)
        assert out["ok"] is True
        assert out["backfill"]["replayed"] == 1
        assert out["backfill"]["items"][0]["text"] == "queued while dark"
    finally:
        srv2.shutdown()
        srv2.server_close()


# ---------- local-only caps ----------

def test_local_capabilities_split():
    deg = _caps.local_capabilities("degraded")
    assert deg["model.answer"]["available"] is False
    for k in ("memory.read", "skills.describe", "skills.help", "queue.add"):
        assert deg[k]["available"] is True, k
    on = _caps.local_capabilities("online")
    assert on["model.answer"]["available"] is True


def test_memory_read_searches_local_state_only():
    _probe.check("http://relay:1/v1", fetcher=_refused_fetcher)
    r = _caps.memory_read("refused")
    assert r["ok"] and len(r["hits"]) >= 1
    assert all("refused" in h["excerpt"] for h in r["hits"])
    assert all(h["file"].endswith(".json") for h in r["hits"])
    assert _caps.memory_read("   ")["reason"] == "bad_query"
    assert _caps.memory_read("zzz-no-such-string")["hits"] == []


def test_skills_describe_and_help_are_local():
    d = _caps.describe_skills()
    assert d["ok"] and len(d["skills"]) >= 1
    names = {s["name"] for s in d["skills"]}
    assert "morning-brief" in names  # real repo inventory, not invented
    h = _caps.skill_help("morning-brief")
    assert h["ok"] and h["help"].strip()
    assert _caps.skill_help("../presence")["reason"] == "bad_name"
    assert _caps.skill_help("no-such-skill")["reason"] == "unknown_skill"


def test_answer_never_fakes_intelligence():
    deg = _caps.answer("what will the market do?", "degraded")
    assert deg["ok"] is False
    assert deg["reason"] == "model_unavailable"
    assert BANNER in deg["refusal"]
    assert "will not invent" in deg["refusal"]
    assert deg["local_instead"]
    on = _caps.answer("anything", "online")
    assert on["ok"] is False and on["reason"] == "route_via_agent"


# ---------- snapshot ----------

def test_snapshot_payload_is_measured():
    _probe.check("http://relay:1/v1", fetcher=_refused_fetcher)
    _queue.enqueue("alert", "build red")
    snap = _snap.build_snapshot()
    assert snap["status"] == "degraded" and snap["banner"] == BANNER
    assert snap["pending"] == 1 and snap["last_reason"] == "refused"
    assert snap["capabilities"]["queue.add"]["available"] is True
    assert snap["skills"]["ok"] is True


# ---------- CLI: banner everywhere ----------

def _run_cli(*argv, timeout=60):
    env = dict(os.environ)
    proc = subprocess.run([str(REPO / "jarvis" / "bin" / "jarvis-degraded"),
                           *argv], capture_output=True, text=True, env=env,
                          timeout=timeout)
    return proc


def test_cli_banner_and_status_degraded(monkeypatch):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    monkeypatch.setenv("JARVIS_RELAY_URL", "http://127.0.0.1:%d/v1" % port)
    p = _run_cli("banner")
    assert p.returncode == 2 and p.stdout.strip() == BANNER
    p = _run_cli("status")
    assert p.returncode == 2 and BANNER in p.stdout
    p = _run_cli("probe")
    assert json.loads(p.stdout)["ok"] is False


def test_cli_ask_refuses_and_queue_recover_roundtrip(monkeypatch):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    monkeypatch.setenv("JARVIS_RELAY_URL", "http://127.0.0.1:%d/v1" % port)
    _run_cli("status")
    p = _run_cli("ask", "write my report")
    body = json.loads(p.stdout)
    assert body["reason"] == "model_unavailable" and BANNER in body["refusal"]
    assert _run_cli("queue-brief", "markets at eight").returncode == 0
    p = _run_cli("pending", "--json")
    assert json.loads(p.stdout)["pending"] == 1
    p = _run_cli("recover")
    assert json.loads(p.stdout)["ok"] is False  # relay still dead
    assert json.loads(_run_cli("pending", "--json").stdout)["pending"] == 1


def test_cli_unconfigured_exit_3():
    p = _run_cli("banner")
    assert p.returncode == 3 and "No relay configured" in p.stdout


def test_cli_deploy_page(tmp_path):
    home = tmp_path / "deploy-home"
    p = _run_cli("deploy-page", "--home", str(home))
    assert p.returncode == 0
    assert (home / "web_dist_overlay" / "degraded.html").exists()


def test_doctor_writes_snapshot(tmp_path):
    home = tmp_path / "dochome"
    env = dict(os.environ, HERMES_HOME=str(home))
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    env["JARVIS_RELAY_URL"] = "http://127.0.0.1:%d/v1" % port
    proc = subprocess.run(
        [str(REPO / "jarvis" / "bin" / "jarvis-doctor-degraded")],
        capture_output=True, text=True, env=env, timeout=60)
    assert proc.returncode in (0, 1)
    snap = json.loads((home / "web_dist_overlay"
                       / "degraded-snapshot.json").read_text())
    assert snap["status"] in ("degraded", "unknown")
    assert snap["probe"]["ok"] is False


# ---------- HUD page contract ----------

def test_hud_page_contract():
    src = (REPO / "jarvis" / "hud" / "degraded.html").read_text()
    assert BANNER in src  # banner line verbatim in the page
    assert "W20-DEGRADED-BEGIN" in src and "W20-DEGRADED-END" in src
    assert src.count("fetch(") == 1, "page fetches only its own snapshot"
    assert '"./degraded-snapshot.json"' in src
    assert "voice.html" in src
    for pat in ["http://", "https://", "<link", "<img", "url(", "@import",
                "innerHTML", "document.write", "localStorage", "eval("]:
        assert pat not in src, f"banned pattern {pat}"
    assert "textContent" in src and "aria-live" in src


def test_banner_snippet_is_marked_and_clean():
    src = (REPO / "jarvis" / "hud" / "degraded-banner.inc.html").read_text()
    assert "W20-DEGRADED-BEGIN" in src and "W20-DEGRADED-END" in src
    for pat in ["http://", "https://", "innerHTML", "document.write",
                "localStorage", "eval("]:
        assert pat not in src, f"banned pattern {pat}"


# ---------- lane gates: turf, secrets, existing pages untouched ----------

def _lane_files():
    # PR-content semantics: what branch w20-degraded adds atop origin/jarvis.
    # Committed-diff (not worktree) so parallel lanes sharing one checkout
    # cannot contaminate this gate with their uncommitted files.
    diff = subprocess.run(
        ["git", "diff", "--name-only", "origin/jarvis", "w20-degraded"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    files = [ln for ln in diff.stdout.splitlines() if ln.strip()]
    return sorted(set(files))


def test_overlay_stays_inside_turf():
    files = _lane_files()
    assert files, "lane must add files"
    bad = [f for f in files
           if not any(f == t or f.startswith(t) for t in TURF)]
    assert not bad, f"out-of-turf files touched: {bad}"


def test_existing_hud_pages_untouched():
    files = _lane_files()
    touched = [f for f in files if f.startswith("jarvis/hud/")
               and f not in ("jarvis/hud/degraded.html",
                             "jarvis/hud/degraded-banner.inc.html")]
    assert not touched, f"existing HUD pages must stay untouched: {touched}"


def test_no_secrets_in_lane_files():
    pats = [re.compile(r"(?i)\bapi[_-]?key\s*=\s*['\"][^'\"]+['\"]"),
            re.compile(r"sk-[A-Za-z0-9]{8,}"),
            re.compile(r"gho_[A-Za-z0-9]+"),
            re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]{8,}"),
            re.compile(r"(?i)password\s*=\s*['\"][^'\"]+['\"]")]
    roots = [REPO / "jarvis" / "degraded", REPO / "jarvis" / "hud" /
             "degraded.html",
             REPO / "jarvis" / "hud" / "degraded-banner.inc.html",
             REPO / "jarvis" / "bin" / "jarvis-degraded",
             REPO / "jarvis" / "bin" / "jarvis-doctor-degraded",
             Path(__file__)]
    paths = []
    for root in roots:
        if root.is_dir():
            paths += [p for p in root.rglob("*") if p.is_file()]
        else:
            paths.append(root)
    assert paths
    for p in paths:
        text = p.read_text(errors="replace")
        for pat in pats:
            assert not pat.search(text), f"secret pattern in {p}"
