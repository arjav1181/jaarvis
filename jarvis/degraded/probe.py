"""W20 probe — relay-down detection with a fast, bounded probe. Stdlib only.

Contract:
  - exactly one HTTP request per probe, hard timeout (default 2.5 s)
  - every failure mode maps to an honest ``reason``; nothing raises
  - no retries inside a probe (callers schedule, the probe never hangs)
  - evidence recorded is host-only: userinfo is stripped before it is stored
  - tests inject ``fetcher`` fakes; production path uses urllib directly
"""
import json
import os
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, urlunparse

BANNER_LINE = "my line to the stars is down, sir"
ONLINE_LINE = "the line to the stars is clear, sir"

PROBE_TIMEOUT_S = 2.5
MODELS_PATH = "/models"
MAX_BODY_BYTES = 65536

STATUS_ONLINE = "online"
STATUS_DEGRADED = "degraded"
STATUS_UNKNOWN = "unknown"


def resolve_relay_url(explicit=None):
    """Relay base URL from explicit arg, then env. Empty string = unconfigured."""
    for cand in (explicit, os.environ.get("JARVIS_RELAY_URL"),
                 os.environ.get("OPENAI_BASE_URL")):
        if cand and str(cand).strip():
            return str(cand).strip().rstrip("/")
    return ""


def scrub_url(url):
    """Return the URL with userinfo removed (safe to store/log)."""
    try:
        parts = urlparse(url)
        netloc = parts.hostname or ""
        if parts.port:
            netloc += ":%d" % parts.port
        return urlunparse((parts.scheme, netloc, parts.path or "",
                           "", "", ""))
    except Exception:
        return ""


def host_of(url):
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _live_fetch(url, timeout):
    req = urllib.request.Request(url.rstrip("/") + MODELS_PATH,
                                 headers={"Accept": "application/json",
                                          "User-Agent": "jarvis-degraded/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(MAX_BODY_BYTES + 1)
        return resp.status, body


def probe(base_url="", timeout=PROBE_TIMEOUT_S, fetcher=None):
    """Probe the relay once. Never raises, never hangs past ``timeout``.

    Returns ``{"ok": bool, "reason": str, "latency_ms": float,
    "host": str, "checked_at": float}``. ``reason`` is one of:
    ok | no_relay_configured | timeout | refused | http_<code> |
    bad_payload | unreachable.
    """
    started = time.monotonic()
    elapsed_ms = lambda: round((time.monotonic() - started) * 1000.0, 1)
    url = resolve_relay_url(base_url)
    if not url:
        return {"ok": False, "reason": "no_relay_configured",
                "latency_ms": elapsed_ms(), "host": "",
                "checked_at": time.time()}
    host = host_of(url)
    fetch = fetcher or _live_fetch
    try:
        status, body = fetch(url, timeout)
    except TimeoutError:
        return {"ok": False, "reason": "timeout", "latency_ms": elapsed_ms(),
                "host": host, "checked_at": time.time()}
    except ConnectionRefusedError:
        return {"ok": False, "reason": "refused", "latency_ms": elapsed_ms(),
                "host": host, "checked_at": time.time()}
    except OSError:
        return {"ok": False, "reason": "unreachable",
                "latency_ms": elapsed_ms(), "host": host,
                "checked_at": time.time()}
    except Exception:
        return {"ok": False, "reason": "unreachable",
                "latency_ms": elapsed_ms(), "host": host,
                "checked_at": time.time()}
    if not isinstance(status, int) or not 200 <= status < 300:
        return {"ok": False, "reason": "http_%s" % status,
                "latency_ms": elapsed_ms(), "host": host,
                "checked_at": time.time()}
    try:
        payload = json.loads((body or b"")[:MAX_BODY_BYTES + 1].decode(
            "utf-8", "replace"))
    except Exception:
        return {"ok": False, "reason": "bad_payload",
                "latency_ms": elapsed_ms(), "host": host,
                "checked_at": time.time()}
    items = payload if isinstance(payload, list) else (
        payload.get("data") if isinstance(payload, dict) else None)
    if not isinstance(items, list):
        return {"ok": False, "reason": "bad_payload",
                "latency_ms": elapsed_ms(), "host": host,
                "checked_at": time.time()}
    return {"ok": True, "reason": "ok", "latency_ms": elapsed_ms(),
            "host": host, "checked_at": time.time()}


def home_dir(home=None):
    h = home or os.environ.get("HERMES_HOME", "")
    if not h:
        raise RuntimeError("HERMES_HOME not set (refusing implicit ~/.hermes)")
    return Path(h)


def state_path(home=None):
    return home_dir(home) / "jarvis" / "degraded-state.json"


def _blank_state():
    return {"status": STATUS_UNKNOWN, "since": None, "last_check": None,
            "last_ok": None, "last_reason": "never_checked", "host": "",
            "latency_ms": None, "down_events": []}


def read_state(home=None):
    p = state_path(home)
    if not p.exists():
        return _blank_state()
    try:
        st = json.loads(p.read_text())
        assert st.get("status") in (STATUS_ONLINE, STATUS_DEGRADED,
                                    STATUS_UNKNOWN)
        assert isinstance(st.get("down_events"), list)
        return st
    except Exception:
        return _blank_state()


def _write_state(home, st):
    p = state_path(home)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1, sort_keys=True))
    tmp.replace(p)
    return p


def check(base_url="", timeout=PROBE_TIMEOUT_S, fetcher=None, home=None,
          now=None):
    """Probe once and persist the degraded/online state. Returns the result."""
    res = probe(base_url=base_url, timeout=timeout, fetcher=fetcher)
    now = now if now is not None else time.time()
    st = read_state(home)
    prev = st["status"]
    nxt = STATUS_ONLINE if res["ok"] else STATUS_DEGRADED
    if res["reason"] == "no_relay_configured":
        nxt = STATUS_UNKNOWN
    if nxt != prev:
        st["status"] = nxt
        st["since"] = now
        if nxt == STATUS_DEGRADED:
            st["down_events"].append({"since": now, "host": res["host"],
                                      "reason": res["reason"]})
            st["down_events"] = st["down_events"][-20:]
    st["last_check"] = now
    st["last_reason"] = res["reason"]
    st["host"] = res["host"]
    st["latency_ms"] = res["latency_ms"]
    if res["ok"]:
        st["last_ok"] = now
    _write_state(home, st)
    out = dict(res)
    out["status"] = st["status"]
    out["banner"] = BANNER_LINE if st["status"] == STATUS_DEGRADED else ""
    return out
