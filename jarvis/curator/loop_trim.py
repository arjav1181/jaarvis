"""W18 loop-owned curator extension — dead/unused skill trim proposals.

Companion to pins.txt / ensure-curator.sh (W5): those files are hands-off,
this module only *reads* the pins and *proposes* trims. Standing rules held:

- curator stays ON; pinned skills are never proposed (hard fence, same as
  ``hermes curator pin``).
- unknown usage is not evidence: a skill with no usage record is reported as
  unknown, never as dead. Only zero-use or stale (past ``stale_days``) skills
  with a cited record become candidates.
- this module never archives anything; it renders the exact
  ``hermes curator ... --dry-run`` preview commands for the operator. The
  model-spending review itself stays a by-hand
  ``hermes curator run --dry-run`` (see ensure-curator.sh).

Usage records come from ``hermes curator usage`` (operator-pasted JSON):
{skill: {"uses": int, "last_used": "YYYY-MM-DD"}}.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
PINS_FILE = HERE / "pins.txt"


def load_pins() -> List[str]:
    try:
        text = PINS_FILE.read_text(encoding="utf-8")
    except OSError:
        return []
    return [ln.strip() for ln in text.splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def inventory_skills(repo_root: Path | str) -> List[str]:
    skills = Path(repo_root) / "jarvis" / "skills"
    try:
        names = [p.name for p in skills.iterdir()
                 if p.is_dir() and (p / "SKILL.md").is_file()]
    except OSError:
        return []
    return sorted(names)


def _cutoff(today: str, stale_days: int) -> str:
    day = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (day - timedelta(days=stale_days)).strftime("%Y-%m-%d")


def candidate_trims(skills: List[str], pins: List[str],
                    usage: Dict[str, Any] | None,
                    today: str | None = None,
                    stale_days: int = 30) -> Dict[str, Any]:
    """Split skills into trim candidates / pinned / unknown-usage.

    Returns {"candidates": [...], "pinned": [...], "unknown": [...]};
    each candidate cites its usage record (never fabricated).
    """
    usage = usage or {}
    day = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cutoff = _cutoff(day, stale_days)
    pinned = set(pins or [])
    candidates: List[Dict[str, Any]] = []
    unknown: List[str] = []
    held: List[str] = []
    for name in sorted(skills or []):
        if name in pinned:
            held.append(name)
            continue
        rec = usage.get(name)
        if not isinstance(rec, dict):
            unknown.append(name)
            continue
        try:
            uses = int(rec.get("uses", 0))
        except (TypeError, ValueError):
            unknown.append(name)
            continue
        last = str(rec.get("last_used", ""))
        if uses <= 0:
            candidates.append({
                "skill": name,
                "reason": "dead: zero recorded uses",
                "citation": f"curator usage {name}: uses=0",
            })
        elif last and last < cutoff:
            candidates.append({
                "skill": name,
                "reason": f"unused: last_used {last} older than {stale_days}d",
                "citation": f"curator usage {name}: last_used={last}",
            })
        # else: in use — no proposal.
    return {"candidates": candidates, "pinned": held, "unknown": unknown,
            "cutoff": cutoff, "stale_days": stale_days}


def render_trim_plan(review: Dict[str, Any]) -> str:
    """Operator-executed preview: exact commands, nothing run here."""
    lines = ["# Friday-loop curator trim plan (preview — nothing archived)",
             "# Standing rule: pinned skills are fenced; review by hand with",
             "#   hermes curator run --dry-run",
             ""]
    cands = review.get("candidates", [])
    if not cands:
        lines.append("# No trim candidates this week.")
    for c in cands:
        lines.append(f"# {c['skill']}: {c['reason']} [{c['citation']}]")
        lines.append(f"hermes curator archive {c['skill']}  # confirm by hand")
    if review.get("unknown"):
        lines.append("")
        lines.append("# Unknown usage (not evidence — left alone): "
                     + ", ".join(review["unknown"]))
    return "\n".join(lines) + "\n"
