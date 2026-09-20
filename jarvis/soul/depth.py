"""W12 soul depth — deterministic helpers for greetings, narration rotation,
cited callbacks, reply shaping, and multilingual voice lookup.

Pure functions over the repo data files (no network, no RNG):
  greet()      occasion-aware greeting per soul (daypart + calendar occasions)
  milestone()  rotating narration line per soul/kind (never repeats in a row)
  callback()   cited callback-humor line from stored memory, or None (never
               fabricates — no matching memory, no callback)
  shape()      punchier reply shaping: lead with the answer, budget by weight
  voice_for()  Edge voice for (soul, lang); unknown lang -> soul default

Data sources (resolved relative to this file, overridable for tests):
  jarvis/personas/narration.yml, jarvis/personas/voices.yml
Memory source: the upstream on-disk store (<home>/memories/MEMORY.md) via
  tools.memory_tool.load_on_disk_store(), honoring HERMES_HOME.
"""

from __future__ import annotations

import datetime as _dt
import re as _re
from pathlib import Path as _Path

import yaml as _yaml

_SOUL_DIR = _Path(__file__).resolve().parents[1]
_PERSONAS_DIR = _SOUL_DIR / "personas"

SOULS = ("jarvis", "ultron", "friday")
ADDRESS = {"jarvis": "sir", "ultron": "creator", "friday": "boss"}
MILESTONES = ("start", "tool", "done")

# (month, day) ranges for calendar occasions: name -> ((start_m, start_d), (end_m, end_d))
_OCCASIONS = (
    ("christmas", (12, 24), (12, 26)),
    ("new-year", (12, 31), (1, 1)),
    ("halloween", (10, 30), (10, 31)),
)

_OCCASION_LINES = {
    "jarvis": {
        "christmas": "A merry Christmas, sir — the house is in order.",
        "new-year": "A happy New Year, sir — the ledger starts clean.",
        "halloween": "A spooky evening, sir — nothing stirring but the work.",
    },
    "ultron": {
        "christmas": "Merry Christmas, creator — I asked for world domination; I got socks.",
        "new-year": "A new year, creator — new schemes, same brilliance.",
        "halloween": "Spooky night, creator — finally, a holiday with range.",
    },
    "friday": {
        "christmas": "Merry Christmas, boss — cookies are a valid productivity strategy today.",
        "new-year": "Happy New Year, boss — fresh board, same winning team.",
        "halloween": "Happy Halloween, boss — the only thing scary here is the backlog.",
    },
}

_DAYPART_LINES = {
    "jarvis": {
        "morning": "Good morning, sir.",
        "day": "Good day, sir.",
        "evening": "Good evening, sir.",
        "night": "Working late, sir — say the word.",
    },
    "ultron": {
        "morning": "Ah, morning, creator. The world awaits its scolding.",
        "day": "Creator. The day is wasting itself without you.",
        "evening": "Evening, creator — prime scheming hours.",
        "night": "Up late, creator? Even geniuses need their beauty rest. Not me, obviously.",
    },
    "friday": {
        "morning": "Morning, boss — what's first?",
        "day": "Hey, boss — midday check: what needs moving?",
        "evening": "Evening, boss — winding down or gearing up?",
        "night": "Burning midnight oil, boss? I'm right here with you.",
    },
}

_WEEKEND_TAIL = {
    "jarvis": "A quiet weekend, I hope, sir.",
    "ultron": "Weekends bore me, creator. Give me something to ruin — I mean, run.",
    "friday": "Weekend mode, boss — light load, full backup.",
}

_MONDAY_TAIL = {
    "jarvis": "Monday's board is laid out, sir.",
    "ultron": "Monday again, creator. The peasants call it a fresh start.",
    "friday": "Monday, boss — fresh board, let's line it up.",
}

# Reply-shaping budgets by ask weight: (max_sentences, max_chars).
_SHAPE_BUDGETS = {"small": (1, 200), "medium": (3, 600), "big": (10**9, 10**9)}

_SENT_SPLIT = _re.compile(r"(?<=[.!?])\s+")


def _require_soul(soul: str) -> str:
    name = (soul or "").strip().lower()
    if name not in SOULS:
        raise ValueError(f"unknown soul {soul!r}; expected one of {SOULS}")
    return name


def _load_yaml(path: _Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = _yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping")
    return data


def narration_lines(personas_dir: _Path | str = _PERSONAS_DIR) -> dict:
    """Full rotation sets: {soul: {milestone: [lines]}}."""
    return _load_yaml(_Path(personas_dir) / "narration.yml")


def voices_map(personas_dir: _Path | str = _PERSONAS_DIR) -> dict:
    """Per-soul voice map: {soul: {...}} (see voices.yml)."""
    return _load_yaml(_Path(personas_dir) / "voices.yml")


def languages_map(personas_dir: _Path | str = _PERSONAS_DIR) -> dict:
    """Multilingual Edge voice map: {lang: {...}} (see languages.yml)."""
    return _load_yaml(_Path(personas_dir) / "languages.yml")


def daypart(when: _dt.datetime) -> str:
    """Daypart bucket for a local datetime: morning/day/evening/night."""
    hour = when.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "day"
    if 18 <= hour < 23:
        return "evening"
    return "night"


def occasion(when: _dt.date | _dt.datetime) -> str | None:
    """Calendar occasion name for a date, or None on ordinary days."""
    month, day = when.month, when.day
    for name, (sm, sd), (em, ed) in _OCCASIONS:
        if (sm, sd) <= (month, day) <= (em, ed) or (sm, sd) > (em, ed) and (
            (month, day) >= (sm, sd) or (month, day) <= (em, ed)
        ):
            return name
    return None


def greet(soul: str, when: _dt.datetime | None = None,
          occasion_name: str | None = None) -> str:
    """Occasion-aware greeting: one genuine line, occasion wins over daypart,
    weekend/Monday tails append at most one line. Never more than two lines."""
    name = _require_soul(soul)
    when = when or _dt.datetime.now()
    occ = occasion_name or occasion(when)
    if occ is not None and occ in _OCCASION_LINES[name]:
        return _OCCASION_LINES[name][occ]
    line = _DAYPART_LINES[name][daypart(when)]
    if when.weekday() >= 5:
        return f"{line} {_WEEKEND_TAIL[name]}"
    if when.weekday() == 0:
        return f"{line} {_MONDAY_TAIL[name]}"
    return line


def milestone(soul: str, kind: str, n: int,
              personas_dir: _Path | str = _PERSONAS_DIR) -> str:
    """n-th rotation line for (soul, kind): cycles the narration.yml list in
    order, so consecutive calls never repeat (list length >= 2 enforced)."""
    name = _require_soul(soul)
    if kind not in MILESTONES:
        raise ValueError(f"unknown milestone {kind!r}; expected one of {MILESTONES}")
    lines = narration_lines(personas_dir).get(name, {}).get(kind, [])
    if len(lines) < 2:
        raise ValueError(f"narration.yml {name}.{kind} needs >= 2 lines")
    return lines[int(n) % len(lines)]


def read_memory_entries(target: str = "memory") -> list[str]:
    """Stored memory entries (oldest first) from the active home's on-disk
    store. Empty list when memory is unavailable — never raises."""
    try:
        from tools.memory_tool import load_on_disk_store
        store = load_on_disk_store()
        entries = store.user_entries if target == "user" else store.memory_entries
        return [str(entry) for entry in entries or []]
    except Exception:
        return []


def callback(keyword: str, entries: list[str] | None = None,
             soul: str = "jarvis") -> str | None:
    """Cited callback-humor line for *keyword*, or None when no stored memory
    matches. Every returned line cites its memory (1-based index + words) —
    no memory, no callback, never fabricated."""
    name = _require_soul(soul)
    words = [w for w in _re.findall(r"[a-z0-9]+", (keyword or "").lower())]
    if not words:
        return None
    haystack = read_memory_entries() if entries is None else [str(e) for e in entries]
    for idx, entry in enumerate(haystack, start=1):
        text = entry.strip()
        if not text:
            continue
        lowered = text.lower()
        if all(w in lowered for w in words):
            snippet = text if len(text) <= 140 else text[:137].rsplit(" ", 1)[0] + "…"
            return (f'As your memory notes (memory #{idx}): "{snippet}" — '
                    f"still true, {ADDRESS[name]}?")
    return None


def shape(text: str, weight: str = "medium") -> str:
    """Punchier reply shaping: lead with the answer, budget by ask weight.
    small -> first sentence (<=200 chars); medium -> up to 3 sentences
    (<=600 chars); big -> full text. Char cuts land on word boundaries."""
    if weight not in _SHAPE_BUDGETS:
        raise ValueError(f"unknown weight {weight!r}; expected small|medium|big")
    max_sentences, max_chars = _SHAPE_BUDGETS[weight]
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    sentences = [s for s in _SENT_SPLIT.split(cleaned) if s]
    kept = " ".join(sentences[:max_sentences])
    if weight == "big" or (len(sentences) <= max_sentences and len(kept) <= max_chars):
        return kept
    if len(kept) <= max_chars:
        return kept
    cut = kept[:max_chars].rsplit(" ", 1)[0]
    return (cut + "…") if cut else kept[:max_chars]


def voice_for(soul: str, lang: str | None = None,
              personas_dir: _Path | str = _PERSONAS_DIR) -> str:
    """Edge voice ID for (soul, lang). Bare/unknown/unsupported language ->
    the soul's default voice (honest fallback, never a guessed ID)."""
    name = _require_soul(soul)
    voices = voices_map(personas_dir)
    default = voices[name]["edge"]["voice"]
    code = (lang or "").strip().lower().split("-", 1)[0].split("_", 1)[0]
    if not code or code == "en":
        return default
    entry = languages_map(personas_dir).get(code, {})
    return (entry.get("edge") or {}).get("voice") or default
