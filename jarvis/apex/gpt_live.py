"""GPT-Live delegation as opt-in mouth (W7 apex).

Upstream ships full-duplex OpenAI gpt-live-1 WebRTC (browser holds media,
server exchanges SDP). This overlay is the consent gate — the mouth is never
default:

- status   -> disabled unless an explicit opt-in record exists.
- enable   -> prints the COST DISCLOSURE, requires --i-accept-costs AND an
  OPENAI_API_KEY in env; writes a timestamped opt-in record. No key, no
  enable (credential boundary, honest-absent).
- disable  -> removes the opt-in record. The mouth closes immediately.

Disclosure text is part of the contract: enable refuses to proceed without
the flag, and the flag's name states what it means.
"""

from __future__ import annotations

from typing import Any, Dict

from ._common import read_json, store_dir, utcnow, write_json

COST_DISCLOSURE = (
    "GPT-LIVE COST DISCLOSURE — read before enabling:\n"
    "1. Full-duplex realtime voice bills per audio minute on your OpenAI key\n"
    "   (input + output tokens), even when nobody is speaking.\n"
    "2. Hermes stays the brain: session.delegation.created -> prompt.submit\n"
    "   keeps every tool call inside the audited agent loop. The mouth only\n"
    "   talks; it never acts alone.\n"
    "3. This is NEVER the default mouth. Disable any time: jarvis-gpt-live disable.\n"
    "4. Self-hosted relay note: audio SDP passes through your relay; the\n"
    "   OpenAI key used here must be yours, never the shared relay key."
)

OPTIN_NAME = "gpt-live.optin.json"


def status(env: Dict[str, str]) -> Dict[str, Any]:
    rec = read_json(store_dir() / OPTIN_NAME, None)
    key = bool((env.get("OPENAI_API_KEY") or "").strip())
    return {
        "enabled": rec is not None,
        "optin": rec,
        "openai_key_present": key,
        "mode": "gpt-live-1 full-duplex (upstream voice_live) behind Hermes brain"
                if rec else "default mouth (chained STT->agent->TTS)",
        "checked_at": utcnow(),
    }


def enable(env: Dict[str, str], accept_costs: bool = False) -> Dict[str, Any]:
    if not accept_costs:
        return {"ok": False, "reason": "costs_not_accepted",
                "disclosure": COST_DISCLOSURE,
                "hint": "re-run with --i-accept-costs after reading the above"}
    if not (env.get("OPENAI_API_KEY") or "").strip():
        return {"ok": False, "reason": "credential_absent",
                "disclosure": COST_DISCLOSURE,
                "hint": "set OPENAI_API_KEY, then re-run with --i-accept-costs"}
    rec = {"enabled_at": utcnow(), "costs_accepted": True,
           "note": "opt-in mouth; Hermes brain retained"}
    write_json(store_dir() / OPTIN_NAME, rec)
    return {"ok": True, "optin": rec}


def disable() -> Dict[str, Any]:
    p = store_dir() / OPTIN_NAME
    was = p.exists()
    try:
        p.unlink()
    except OSError:
        pass
    return {"ok": True, "was_enabled": was, "disabled_at": utcnow()}
