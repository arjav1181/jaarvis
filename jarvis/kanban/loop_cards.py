"""W18 loop-owned kanban extension — fix cards with contracts.

Companion to jarvis-ops.json / PR_CONTRACTS.md (W5): those files are
hands-off, this module only *builds* new cards in their image, so loop cards
always import clean (``PR contract:`` in the body, ``owner/repo`` contract
target, unique idempotency keys under the ``jarvis-loop:`` namespace — never
colliding with the ``jarvis-ops:`` seeds).

Routing: red tests and failed cron runs go to ``jarvis-worker`` (execute the
fix); refused acts go to ``jarvis-orchestrator`` as triage (a refusal is a
judgment call for a human, never a worker's solo fix).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

BOARD = "jarvis-ops"
PR_TARGET = "arjav1181/jaarvis"
KEY_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_SLUG_BAD = re.compile(r"[^A-Za-z0-9_.-]+")

WORKER = "jarvis-worker"
ORCHESTRATOR = "jarvis-orchestrator"

MAX_CARDS = 10

CONTRACT_PROSE = (
    "PR contract: deliver as a PR to `jaarvis`, base `jarvis` — never push "
    "to `jarvis`. Body carries proofs (what changed, command output pasted, "
    "test lines). `tests/jarvis/` green on the branch; relevant upstream "
    "suites green. Secrets scan clean; `~/.hermes` absent; status "
    "overlay-only. Merge only when green; red CI is a report, never a merge."
)

KIND_ROUTE = {
    "red-test": {"assignee": WORKER, "priority": 1, "skills": ["test-runner"]},
    "cron-failed": {"assignee": WORKER, "priority": 1, "skills": ["ci-watchdog"]},
    "refused-act": {"assignee": ORCHESTRATOR, "priority": 2, "skills": []},
}


def slug(text: str) -> str:
    s = _SLUG_BAD.sub("-", (text or "").strip().lower()).strip("-.")
    return (s or "item")[:80]


def build_fix_cards(findings: List[Dict[str, Any]],
                    max_cards: int = MAX_CARDS) -> List[Dict[str, Any]]:
    """One card per finding; overflow folds into a single triage card."""
    cards: List[Dict[str, Any]] = []
    for f in findings or []:
        route = KIND_ROUTE.get(f.get("kind", ""), KIND_ROUTE["refused-act"])
        key = f"jarvis-loop:{f.get('kind', 'item')}:{slug(str(f.get('id', '')))}"
        triage = route["assignee"] == ORCHESTRATOR
        body = (
            f"Friday-loop finding ({f.get('kind', '?')}): {f.get('title', '?')}\n"
            f"Citation: {f.get('citation', '?')}\n"
            f"Detail: {f.get('detail', '—')}\n"
            f"{CONTRACT_PROSE}"
        )
        cards.append({
            "key": key,
            "title": f"[loop] {f.get('title', 'unnamed finding')}"[:140],
            "body": body,
            "assignee": route["assignee"],
            "priority": route["priority"],
            "skills": list(route["skills"]),
            "triage": triage,
            "idempotency_key": key,
            "completion_contract": PR_TARGET,
        })
    if len(cards) > max(1, max_cards):
        kept = cards[:max(1, max_cards) - 1]
        rest = cards[max(1, max_cards) - 1:]
        kept.append({
            "key": "jarvis-loop:overflow:rest-of-week",
            "title": f"[loop] {len(rest)} further findings (triage batch)",
            "body": ("Friday-loop overflow: more findings than the per-run "
                     f"card cap ({max_cards}). Citations:\n"
                     + "\n".join(f"- {c['title']} [{c['body'].splitlines()[1]}]"
                                 for c in rest)
                     + f"\n{CONTRACT_PROSE}"),
            "assignee": ORCHESTRATOR,
            "priority": 2,
            "skills": [],
            "triage": True,
            "idempotency_key": "jarvis-loop:overflow:rest-of-week",
            "completion_contract": PR_TARGET,
        })
        return kept
    return cards


def validate_card(card: Dict[str, Any],
                  skills: set | None = None) -> List[str]:
    """Mirror the W5 board-spec assertions so loop cards import clean."""
    errors: List[str] = []
    for k in ("key", "title", "body", "assignee", "priority",
              "idempotency_key", "completion_contract"):
        if not card.get(k) and card.get(k) != 0:
            errors.append(f"card missing {k}")
    if card.get("assignee") not in (WORKER, ORCHESTRATOR):
        errors.append(f"unknown assignee {card.get('assignee')!r}")
    if not KEY_RE.fullmatch(str(card.get("completion_contract", ""))):
        errors.append("completion_contract must be owner/repo")
    if "PR contract:" not in str(card.get("body", "")):
        errors.append("body must carry the PR contract line")
    if "Citation:" not in str(card.get("body", "")):
        errors.append("body must cite its finding")
    if skills is not None:
        unknown = set(card.get("skills", [])) - set(skills)
        if unknown:
            errors.append(f"unknown skills {sorted(unknown)}")
    return errors


def to_create_args(card: Dict[str, Any], board: str = BOARD) -> List[str]:
    """argv for ``hermes kanban --board <b> create ...`` (dry-run prints)."""
    args = ["hermes", "kanban", "--board", board, "create", card["title"],
            "--body", card["body"], "--assignee", card["assignee"],
            "--priority", str(card["priority"]),
            "--idempotency-key", card["idempotency_key"],
            "--completion-contract", card["completion_contract"]]
    for s in card.get("skills", []):
        args += ["--skill", s]
    if card.get("triage"):
        args.append("--triage")
    return args
