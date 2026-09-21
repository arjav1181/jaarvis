"""Discord voice-channel join — built to the credential boundary (W7 apex).

Upstream already ships a full Discord voice adapter (join/leave/play/listen
with echo-prevention). This overlay is the operator-facing gate:

- No DISCORD_BOT_TOKEN  -> honest-absent: prints the exact setup contract
  (token env, allowlist, timeouts, echo note) and exits 2. Nothing half-joins.
- Token present         -> emits the join plan (channel, allowlist check,
  inactivity timeout, mixer gains) as JSON; the live join itself runs inside
  the gateway adapter, never from a stray CLI process.
- Allowlist             -> overlay vc_allowlist.json (operator user IDs);
  empty file means "not configured", never "everyone".

Fixture path (tests + docs): an injected adapter double verifies the
join -> play -> leave call sequence without any network.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._common import read_json, store_dir, utcnow, write_json

SETUP_CONTRACT = {
    "credential": "DISCORD_BOT_TOKEN env var on the gateway process",
    "channel": "DISCORD_HOME_CHANNEL or explicit --channel <id>",
    "allowlist": "jarvis/apex/vc_allowlist.json — Discord user IDs allowed to summon; empty = unconfigured",
    "inactivity_timeout_s": 300,
    "mixer": "one-source ducking (upstream VoiceMixer): speech ducks ambient",
    "echo": "echo-prevention lives in the upstream adapter listen loop; overlay never disables it",
    "summon": "operator-only: caller must be on the allowlist",
}

ALLOWLIST_NAME = "vc_allowlist.json"


def allowlist() -> List[str]:
    return [str(x) for x in read_json(store_dir() / ALLOWLIST_NAME, [])]


def set_allowlist(ids: List[str]):
    return write_json(store_dir() / ALLOWLIST_NAME, [str(x) for x in ids])


def vc_status(env: Dict[str, str], adapter: Optional[Any] = None) -> Dict[str, Any]:
    """Honest status: configured only when token + allowlist both exist."""
    token = bool((env.get("DISCORD_BOT_TOKEN") or "").strip())
    ids = allowlist()
    live = None
    if adapter is not None:
        try:
            live = {"in_channel": bool(adapter.is_in_voice_channel()),
                    "info": adapter.get_voice_channel_info()}
        except (AttributeError, RuntimeError) as e:
            live = {"error": f"{type(e).__name__}: {e}"}
    return {
        "token_present": token,
        "allowlist": ids,
        "configured": bool(token and ids),
        "live": live,
        "checked_at": utcnow(),
        **({} if token and ids else {"setup_contract": SETUP_CONTRACT}),
    }


def join_plan(env: Dict[str, str], channel: str, caller_id: str) -> Dict[str, Any]:
    """Validate the join request; return plan or refusal (no network here)."""
    st = vc_status(env)
    if not st["token_present"]:
        return {"ok": False, "reason": "credential_absent",
                "setup_contract": SETUP_CONTRACT}
    ids = allowlist()
    if not ids:
        return {"ok": False, "reason": "allowlist_unconfigured",
                "setup_contract": SETUP_CONTRACT}
    if str(caller_id) not in [str(x) for x in ids]:
        return {"ok": False, "reason": "caller_not_allowlisted",
                "caller": str(caller_id)}
    if not channel:
        return {"ok": False, "reason": "channel_missing"}
    return {"ok": True,
            "plan": {"channel": channel, "caller": str(caller_id),
                     "inactivity_timeout_s": 300,
                     "steps": ["adapter.join_voice_channel",
                               "adapter.play_ack_in_voice",
                               "adapter._voice_listen_loop (echo-guarded)",
                               "auto-leave on inactivity"]}}
