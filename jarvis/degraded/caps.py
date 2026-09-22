"""W20 caps — the local-only capability set. Stdlib only.

Available while degraded (no model needed):
  - memory.read .... substring search over local ``$HERMES_HOME/jarvis``
                     JSON state (cited file refs, never invented)
  - skills.describe  repo skill inventory (name/tier/trigger, local metadata)
  - skills.help ..... first section of a skill's SKILL.md (local doc read)
  - queue.add/list . briefs/alerts backlog (see queue.py)

Everything needing a model goes through :func:`answer`, which refuses with
a reason while degraded — never a hallucinated answer.
"""
import json
import re
from pathlib import Path

from . import probe as _probe

REPO = Path(__file__).resolve().parents[2]

_SKILL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
MAX_HITS = 20
MAX_EXCERPT = 280


def local_capabilities(status="degraded"):
    """Advertise what works without a model. Tiers quoted verbatim."""
    degraded = status != _probe.STATUS_ONLINE
    return {
        "status": status,
        "memory.read": {"available": True,
                        "note": "local state search only, no model"},
        "skills.describe": {"available": True,
                            "note": "local inventory only, no model"},
        "skills.help": {"available": True,
                        "note": "local doc read only, no model"},
        "queue.add": {"available": True,
                      "note": "briefs/alerts backlog for replay"},
        "model.answer": {"available": not degraded,
                         "note": "refused while degraded" if degraded
                         else "route via the agent loop"},
    }


def memory_read(query="", home=None):
    """Search local jarvis JSON state for ``query``. Cited excerpts only."""
    q = str(query or "").strip().lower()
    if not q or len(q) > 200:
        return {"ok": False, "reason": "bad_query"}
    try:
        root = _probe.home_dir(home) / "jarvis"
    except RuntimeError:
        return {"ok": False, "reason": "no_home"}
    hits = []
    if not root.exists():
        return {"ok": True, "hits": [], "note": "no local state yet"}
    for p in sorted(root.glob("*.json")):
        try:
            text = p.read_text()
        except OSError:
            continue
        low = text.lower()
        idx = low.find(q)
        if idx < 0:
            continue
        start = max(0, idx - 80)
        excerpt = " ".join(text[start:start + MAX_EXCERPT].split())
        hits.append({"file": p.name, "excerpt": excerpt})
        if len(hits) >= MAX_HITS:
            break
    return {"ok": True, "hits": hits}


def describe_skills(repo_root=None):
    """Local skill inventory from the repo manifest. No model involved."""
    man = Path(repo_root or REPO) / "jarvis" / "skills" / "manifest.json"
    try:
        data = json.loads(man.read_text())
    except (OSError, ValueError):
        return {"ok": False, "reason": "no_manifest"}
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, list):
        return {"ok": False, "reason": "bad_manifest"}
    out = [{"name": s.get("name"), "tier": s.get("tier"),
            "trigger": s.get("trigger")}
           for s in skills if isinstance(s, dict) and s.get("name")]
    return {"ok": True, "skills": out,
            "note": "metadata only — running a skill may need the relay"}


def skill_help(name="", repo_root=None):
    """First section of a skill's SKILL.md. Local read, capped."""
    if not _SKILL_RE.match(str(name or "")):
        return {"ok": False, "reason": "bad_name"}
    doc = (Path(repo_root or REPO) / "jarvis" / "skills" / str(name)
           / "SKILL.md")
    try:
        text = doc.read_text()
    except OSError:
        return {"ok": False, "reason": "unknown_skill"}
    head = text[:2000].split("\n## ", 1)[0].strip()
    return {"ok": True, "name": str(name), "help": head}


def answer(text="", status="degraded"):
    """Model-dependent answers while degraded are refused, never faked."""
    if status != _probe.STATUS_ONLINE:
        return {
            "ok": False,
            "reason": "model_unavailable",
            "refusal": ("%s — I cannot compose an answer without the "
                        "relay, and I will not invent one." % _probe.BANNER_LINE),
            "local_instead": ["memory.read", "skills.describe",
                              "skills.help", "queue.add"],
        }
    return {
        "ok": False,
        "reason": "route_via_agent",
        "refusal": ("The relay is up, but this module never generates "
                    "answers — ask through the agent loop."),
        "local_instead": [],
    }
