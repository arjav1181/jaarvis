"""W20 snapshot — HUD payload for the degraded page. Stdlib only."""
import time

from . import caps as _caps
from . import probe as _probe
from . import queue as _queue


def build_snapshot(base_url="", timeout=_probe.PROBE_TIMEOUT_S, fetcher=None,
                   home=None, now=None, repo_root=None):
    """Probe-free by default when a fetcher is given; honest either way.

    Runs a live probe (bounded) unless the caller passes ``fetcher`` (tests
    and the doctor script pass fakes / real probe respectively). The page
    renders exactly this payload — every line measured, never claimed.
    """
    now = now if now is not None else time.time()
    st = _probe.read_state(home)
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "banner": _probe.BANNER_LINE if st["status"] == _probe.STATUS_DEGRADED else "",
        "status": st["status"],
        "since": st.get("since"),
        "last_check": st.get("last_check"),
        "last_reason": st.get("last_reason"),
        "host": st.get("host"),
        "latency_ms": st.get("latency_ms"),
        "pending": len(_queue.pending(home)),
        "capabilities": _caps.local_capabilities(st["status"]),
        "skills": _caps.describe_skills(repo_root),
    }
