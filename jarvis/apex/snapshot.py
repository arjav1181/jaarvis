"""apex snapshot builder (W7): one JSON resume of the beast's state."""

from __future__ import annotations

import os
from typing import Any, Dict

from . import achievements, compute, discord_vc, gpt_live, langfuse_optin, review
from ._common import store_dir, utcnow, write_json

SNAP_NAME = "apex-snapshot.json"


def build() -> Dict[str, Any]:
    env = dict(os.environ)
    try:
        preset = review.load_preset()
        chk = review.check_preset(preset)
    except SystemExit as e:
        preset, chk = None, {"ok": False, "errors": [str(e)]}
    snap = {
        "ladder": compute.probe_gpu_ladder(),
        "stt_engines": compute.probe_stt_engines(),
        "discord_vc": discord_vc.vc_status(env),
        "gpt_live": gpt_live.status(env),
        "langfuse": langfuse_optin.status(env),
        "review_preset": {"name": (preset or {}).get("name"),
                          "check": chk},
        "achievements": achievements.summary(),
        "built_at": utcnow(),
    }
    write_json(store_dir() / SNAP_NAME, snap)
    return snap
