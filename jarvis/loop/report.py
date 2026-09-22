"""W18 weekly report — found / fix-cards / trimmed, all cited.

The report is the loop's deliverable: every line traces to a citation
(pytest node, cron job+run, audit ts+action, curator usage record). An empty
week reports an empty week — never padded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ._common import store_dir, utcnow, write_json


def build_report(mined: Dict[str, Any], cards: List[Dict[str, Any]],
                 review: Dict[str, Any], mode: str = "dry-run") -> str:
    counts = mined.get("counts", {})
    total = mined.get("total", 0)
    cands = review.get("candidates", [])
    lines = [
        f"# Friday loop — weekly report ({mode})",
        f"Filed {utcnow()} by the Friday self-improvement loop (W18).",
        "",
        f"Found {total} failing signal(s): "
        + ", ".join(f"{k}={counts.get(k, 0)}"
                    for k in ("red-test", "cron-failed", "refused-act")),
        f"Drafted {len(cards)} kanban fix card(s) "
        f"(idempotency namespace `jarvis-loop:`).",
        f"Proposed {len(cands)} curator trim(s); "
        f"{len(review.get('pinned', []))} pinned held, "
        f"{len(review.get('unknown', []))} unknown-usage left alone.",
        "",
        "## Found",
    ]
    if not mined.get("findings"):
        lines.append("- No failing signals this week.")
    for f in mined.get("findings", []):
        lines.append(f"- [{f['kind']}] {f['title']} — {f['citation']}")
    lines.append("")
    lines.append("## Fix cards")
    if not cards:
        lines.append("- No cards drafted.")
    for c in cards:
        lines.append(f"- {c['title']} (key `{c['key']}`, "
                     f"{c['assignee']}{', triage' if c.get('triage') else ''})")
    lines.append("")
    lines.append("## Trims")
    if not cands:
        lines.append("- No trim candidates (pinned skills fenced).")
    for c in cands:
        lines.append(f"- {c['skill']}: {c['reason']} [{c['citation']}]")
    if review.get("unknown"):
        lines.append(f"- Unknown usage, left alone: "
                     f"{', '.join(review['unknown'])}")
    lines.append("")
    lines.append("## Mode")
    if mode == "dry-run":
        lines.append("- Dry run: zero kanban creates, zero curator archives. "
                     "Live mode needs `run(live=True)` plus "
                     "`JARVIS_LOOP_LIVE=1` per run.")
    else:
        lines.append("- Live run: cards dispatched with idempotency keys; "
                     "curator trims remain operator-executed previews.")
    return "\n".join(lines) + "\n"


def save_report(report_md: str, receipt: Dict[str, Any]) -> Dict[str, Path]:
    """Persist report + receipt under <home>/jarvis/loop/reports/."""
    stamp = utcnow().replace(":", "-")
    runs = store_dir() / "reports"
    runs.mkdir(parents=True, exist_ok=True)
    md_path = runs / f"friday-loop-{stamp}.md"
    js_path = runs / f"friday-loop-{stamp}.json"
    md_path.write_text(report_md, encoding="utf-8")
    write_json(js_path, receipt)
    return {"md": md_path, "json": js_path}
