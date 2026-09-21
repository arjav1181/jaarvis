"""Streaming sentence TTS for the CLI surface (W7 apex).

Upstream already streams sentences on gateway/HUD (tts_streaming,
speak-stream WS). The CLI had no equivalent — this module splits text into
sentences, speaks them one at a time through the existing speaker
(`jarvis-speak`, W8 — composed, not modified), and reports per-sentence
timings so the stream is measured, not claimed. `--dry-run` proves the
chunking + timing path without spending a single TTS call.
"""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+(?=[A-Z0-9\"“(\[])")

BIN_DIR = Path(__file__).resolve().parent.parent / "bin"


def split_sentences(text: str) -> List[str]:
    parts = [s.strip() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def speak_stream(text: str, dry_run: bool = False,
                 speaker: Callable[[str], Dict[str, Any]] | None = None
                 ) -> Dict[str, Any]:
    """Speak sentence-by-sentence; return per-sentence measured timings."""
    sentences = split_sentences(text)
    if speaker is None:
        def _default(sentence: str) -> Dict[str, Any]:
            # W8 jarvis-speak speaks --alert TEXT (bare text is a usage error).
            cmd = [str(BIN_DIR / "jarvis-speak"), "--alert", sentence]
            if dry_run:
                cmd.append("--dry-run")
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                return {"ok": p.returncode == 0,
                        "out": (p.stdout or "").strip()[:300]}
            except (OSError, subprocess.SubprocessError) as e:
                return {"ok": False, "out": f"{type(e).__name__}: {e}"}
        speaker = _default
    t0 = time.monotonic()
    rows = []
    for i, s in enumerate(sentences):
        c0 = time.monotonic()
        try:
            res = speaker(s)
        except Exception as e:  # keep the stream alive per-sentence
            res = {"ok": False, "out": f"{type(e).__name__}: {e}"}
        rows.append({"index": i, "chars": len(s),
                     "ms": int((time.monotonic() - c0) * 1000), **res})
    return {"sentences": len(sentences), "rows": rows,
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
            "dry_run": dry_run,
            "all_ok": all(r["ok"] for r in rows)}
