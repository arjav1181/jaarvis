"""Langfuse tracing opt-in gate (W7 apex, HTR-OBS1).

Upstream ships an observability/langfuse plugin (per-turn traces, sanitized
capture by default) that is inert without SDK + credentials. This overlay is
the consent + readiness gate:

- status  -> opt-in record? SDK importable? keys present? plugin enabled?
- enable  -> records opt-in (self-hosted preferred note) WITHOUT touching
  upstream config; activation stays the operator's explicit setup step.
- disable -> removes the opt-in record.

Nothing phones home from here. Tracing starts only when the operator enables
the upstream plugin with their own keys.
"""

from __future__ import annotations

from typing import Any, Dict

from ._common import read_json, store_dir, utcnow, write_json

OPTIN_NAME = "langfuse.optin.json"
SELF_HOSTED_NOTE = ("self-hosted Langfuse preferred (your traces stay home); "
                    "Cloud works too — either way the keys are yours")


def _sdk_present(importable=None) -> bool:
    if importable is not None:
        return bool(importable("langfuse"))
    try:
        __import__("langfuse")
        return True
    except ImportError:
        return False


def status(env: Dict[str, str], importable=None) -> Dict[str, Any]:
    rec = read_json(store_dir() / OPTIN_NAME, None)
    sdk = _sdk_present(importable)
    keys = {k: bool((env.get(k) or "").strip()) for k in
            ("HERMES_LANGFUSE_PUBLIC_KEY", "HERMES_LANGFUSE_SECRET_KEY")}
    base = (env.get("HERMES_LANGFUSE_BASE_URL") or "").strip() or "(unset)"
    ready = bool(rec and sdk and all(keys.values()))
    return {
        "opted_in": rec is not None,
        "optin": rec,
        "sdk_installed": sdk,
        "keys_present": keys,
        "base_url": base,
        "self_hosted_note": SELF_HOSTED_NOTE,
        "tracing_live": ready,
        "activation": ("operator step: install langfuse SDK + set keys + enable "
                       "the observability/langfuse plugin; this CLI only records consent"),
        "checked_at": utcnow(),
    }


def enable() -> Dict[str, Any]:
    rec = {"enabled_at": utcnow(), "capture": "sanitized (upstream default)",
           "note": SELF_HOSTED_NOTE}
    write_json(store_dir() / OPTIN_NAME, rec)
    return {"ok": True, "optin": rec,
            "next": "install SDK, set keys, enable upstream plugin — then traces flow"}


def disable() -> Dict[str, Any]:
    p = store_dir() / OPTIN_NAME
    was = p.exists()
    try:
        p.unlink()
    except OSError:
        pass
    return {"ok": True, "was_opted_in": was, "disabled_at": utcnow()}
