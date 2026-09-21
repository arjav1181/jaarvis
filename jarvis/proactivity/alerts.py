"""W8 proactivity — watchdog alert text from fingerprint changes.

Diffs today's CI fingerprint lines against the last seen set and speaks
only what changed (new failures, fresh green runs). No change -> None
(silence is correct; the watchdog stays quiet on quiet days).
"""

from __future__ import annotations


def build(previous: list[str] | None, current: list[str] | None) -> str | None:
    """Alert text for fingerprint changes, or None when nothing changed."""
    prev = [str(line).strip() for line in (previous or []) if str(line).strip()]
    curr = [str(line).strip() for line in (current or []) if str(line).strip()]
    if prev == curr:
        return None
    prev_set, curr_set = set(prev), set(curr)
    fresh = [line for line in curr if line not in prev_set]
    gone = [line for line in prev if line not in curr_set]
    parts = []
    if fresh:
        parts.append(f"{len(fresh)} new run{'s' if len(fresh) != 1 else ''}: "
                     + "; ".join(fresh[:3]))
    if gone:
        parts.append(f"{len(gone)} run{'s' if len(gone) != 1 else ''} aged out.")
    if not parts:
        return None
    return "Watchdog: " + " ".join(parts)
