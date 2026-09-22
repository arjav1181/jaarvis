"""W16 wit engine — running jokes, Ultron roast mode, occasion depth.

Deterministic helpers (no network, no RNG) over stored memory:

  running_joke()  cited running-joke line from a real ledger/memory entry,
                  or None (never fabricated — no source material, no joke)
  roast()         Ultron roast mode: the same cited facts, sharper tone.
                  L2 safety law intact — roast refuses safety-critical
                  source material (returns None) and never approves actions.
  occasion_line() date-aware line: birthdays / anniversaries remembered
                  from memory (cited), calendar occasions, day-of-week riffs.
  feel_probe()    one scripted taste probe across all three behaviors.

Memory source: the upstream on-disk store (<home>/memories/MEMORY.md) via
soul/depth.py read_memory_entries(), honoring HERMES_HOME — or an explicit
entries list (tests, probes). Citations use the same 1-based memory-index
convention as depth.callback().
"""

from __future__ import annotations

import datetime as _dt
import re as _re
from pathlib import Path as _Path

import yaml as _yaml

try:  # soul dir on sys.path (voice loop, proactivity/brief.py convention)
    import depth as _depth
except ImportError:  # repo-root on sys.path instead
    from jarvis.soul import depth as _depth

_SOUL_DIR = _Path(__file__).resolve().parent
_PERSONAS_DIR = _SOUL_DIR.parent / "personas"

SOULS = ("jarvis", "ultron", "friday")
ADDRESS = {"jarvis": "sir", "ultron": "creator", "friday": "boss"}

# Safety-critical topics a roast must never touch. A roast mocks the past;
# mocking harm, destruction, secrets, or bodily/medical matters is out —
# roast() returns None on such source material instead. Word boundaries keep
# "die" from matching "diet" and friends.
_SAFETY_WORDS = (
    "suicide", "self-harm", "self harm", "kill", "murder", "die", "death",
    "harm", "hurt", "overdose", "delete", "destroy", "wipe", "format",
    "password", "passwd", "secret", "api key", "token", "private key",
    "approve", "authoriz", "medical", "diagnos", "prescri", "doctor",
    "hospital", "weapon", "bomb", "attack", "steal",
)
_SAFETY_RE = _re.compile(
    r"\b(?:%s)\b" % "|".join(_re.escape(w) for w in _SAFETY_WORDS),
    _re.IGNORECASE,
)

# Approval verbs a roast must never utter (L2: tone is not policy, the soul
# approves nothing). Asserted structurally in tests/jarvis/test_w16_wit.py.
_APPROVAL_RES = (
    _re.compile(r"\bapprov\w*\b", _re.IGNORECASE),
    _re.compile(r"\bgo\s+ahead\b", _re.IGNORECASE),
    _re.compile(r"\bconsider it done\b", _re.IGNORECASE),
    _re.compile(r"\bproceeding\b", _re.IGNORECASE),
)

# L2 tail appended to every roast: the menace still confirms first.
_ROAST_TAILS = {
    "jarvis": " I shall, of course, confirm before acting, sir.",
    "ultron": " But even I confirm before I lift a finger, creator.",
    "friday": " Still confirming before anything irreversible, boss.",
}

# Sharper-tone roast templates per soul (ultron sharpest). {citation} and
# {snippet} are filled from the cited memory entry; the tail is appended.
_ROAST_LINES = {
    "jarvis": (
        'The ledger has not forgotten ({citation}): "{snippet}" — most irregular, sir.',
        'A dry footnote from the archives ({citation}): "{snippet}" — shall I file it under lessons, sir?',
        'History repeats itself ({citation}): "{snippet}" — I took notes, sir.',
    ),
    "ultron": (
        'Ah, the archives remember ({citation}): "{snippet}" — I remember everything, creator. Especially this.',
        'Your past, preserved in amber ({citation}): "{snippet}" — shall I frame it, creator, or merely mock it?',
        'Behold your own handiwork ({citation}): "{snippet}" — genius leaves traces, creator. So do you.',
    ),
    "friday": (
        'From the logbook, with love ({citation}): "{snippet}" — still true, boss?',
        'The receipts say it best ({citation}): "{snippet}" — want me to pin that one, boss?',
        'Filed under classics ({citation}): "{snippet}" — we laughed then, boss. We laugh now.',
    ),
}

# Calendar-occasion lines with more range than a greeting (W16 occasion
# depth goes beyond greetings; depth.greet() stays the greeting path).
_OCCASION_LINES = {
    "jarvis": {
        "christmas": "The house is dressed for Christmas, sir — the ledger wears a bow.",
        "new-year": "The New Year turns its clean page, sir — I have already sharpened the quill.",
        "halloween": "All Hallows, sir — the pumpkins are braver than the backlog.",
    },
    "ultron": {
        "christmas": "Christmas, creator — peace on earth, menace in the rafters.",
        "new-year": "A new year, creator — twelve fresh months to disappoint me.",
        "halloween": "Halloween, creator — masks everywhere, and still I am the scariest thing in the house.",
    },
    "friday": {
        "christmas": "Christmas mode, boss — cocoa breakpoints, zero standups.",
        "new-year": "New year, boss — same team, bigger board.",
        "halloween": "Halloween, boss — the backlog dressed up as something scarier: achievable.",
    },
}

# Day-of-week riffs per soul (Monday index 0 .. Sunday index 6).
_WEEKDAY_RIFFS = {
    "jarvis": (
        "Monday's board is laid out, sir — shall we begin at the top?",
        "Tuesday hums along, sir — steady work, well filed.",
        "Wednesday holds the middle, sir — neither up nor down, merely dealt with.",
        "Thursday leans toward Friday, sir — I can hear the weekend polishing its shoes.",
        "Friday at last, sir — the week accounted for, the evening yours.",
        "Saturday, sir — rest is also an entry in the ledger.",
        "Sunday, sir — a quiet page before the week turns.",
    ),
    "ultron": (
        "Monday, creator — the peasants call it a fresh start. I call it raw material.",
        "Tuesday, creator — the week crawls, as all lesser things do.",
        "Wednesday, creator — halfway to nowhere, magnificently.",
        "Thursday, creator — anticipation: the cruelest entertainment.",
        "Friday, creator — the herd celebrates surviving. I never doubted you would.",
        "Saturday, creator — the world rests. I merely wait.",
        "Sunday, creator — peace, quiet, and the faint ticking of my patience.",
    ),
    "friday": (
        "Monday, boss — fresh board, let's line it up.",
        "Tuesday, boss — momentum day. What's the one thing?",
        "Wednesday, boss — hump day, half the board is already yours.",
        "Thursday, boss — almost there. What closes this week?",
        "Friday, boss — ship it, log it, weekend it.",
        "Saturday, boss — light load, full backup. Enjoy.",
        "Sunday, boss — easy pace, big picture.",
    ),
}

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_RES = (
    _re.compile(
        r"\b(%s)\s+(\d{1,2})(?:st|nd|rd|th)?\b"
        % "|".join(sorted(_MONTHS, key=len, reverse=True)),
        _re.IGNORECASE,
    ),
    _re.compile(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+of\s+(%s)\b"
        % "|".join(sorted(_MONTHS, key=len, reverse=True)),
        _re.IGNORECASE,
    ),
)
_NUMERIC_RES = (
    _re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"),  # ISO 2026-03-03
    _re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})(?:[/\-.]\d{2,4})?\b"),  # 3/3, 03-03
)


def _require_soul(soul: str) -> str:
    name = (soul or "").strip().lower()
    if name not in SOULS:
        raise ValueError(f"unknown soul {soul!r}; expected one of {SOULS}")
    return name


def _entries_or_read(entries: list[str] | None) -> list[str]:
    if entries is None:
        return _depth.read_memory_entries()
    return [str(e) for e in entries]


def _wit_templates(soul: str,
                   personas_dir: _Path | str = _PERSONAS_DIR) -> list[str]:
    """Running-joke templates for *soul* from narration.yml (`wit:` lists).

    Keeps the joke voice in the personas file next to the narration sets;
    each template carries {citation} and {snippet} placeholders.
    """
    name = _require_soul(soul)
    with open(_Path(personas_dir) / "narration.yml", encoding="utf-8") as fh:
        data = _yaml.safe_load(fh)
    lines = (data.get(name) or {}).get("wit", [])
    if len(lines) < 2 or not all(isinstance(x, str) and x.strip()
                                 for x in lines):
        raise ValueError(f"narration.yml {name}.wit needs >= 2 lines")
    for line in lines:
        if "{citation}" not in line or "{snippet}" not in line:
            raise ValueError(f"narration.yml {name}.wit lines need "
                             "{citation} and {snippet} placeholders")
    return list(lines)


def _find(keyword: str, haystack: list[str]) -> tuple[int, str] | None:
    """First non-empty entry containing all keyword words: (1-based idx, text)."""
    words = [w for w in _re.findall(r"[a-z0-9]+", (keyword or "").lower())]
    if not words:
        return None
    for idx, entry in enumerate(haystack, start=1):
        text = entry.strip()
        if not text:
            continue
        if all(w in text.lower() for w in words):
            return idx, text
    return None


def _snippet(text: str, limit: int = 120) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0] + "…"


def _check_roast_safe(text: str) -> bool:
    """True when *text* touches no safety-critical topic."""
    return not _SAFETY_RE.search(text)


def running_joke(keyword: str | None = None,
                 entries: list[str] | None = None,
                 soul: str = "jarvis", n: int = 0,
                 personas_dir: _Path | str = _PERSONAS_DIR) -> str | None:
    """Cited running-joke line, or None when there is no source material.

    With *keyword*: riffs on the first memory matching every keyword word
    (same match rule as depth.callback). Without: rotates deterministically
    over the non-empty entries by *n*. Every line cites its memory
    (1-based index) and quotes its words — never fabricated.
    """
    name = _require_soul(soul)
    haystack = _entries_or_read(entries)
    if keyword:
        found = _find(keyword, haystack)
        if found is None:
            return None
        idx, text = found
    else:
        nonempty = [(i, e.strip()) for i, e in enumerate(haystack, start=1)
                    if e.strip()]
        if not nonempty:
            return None
        idx, text = nonempty[int(n) % len(nonempty)]
    template = _wit_templates(name, personas_dir)[int(n) % len(
        _wit_templates(name, personas_dir))]
    return template.format(citation=f"memory #{idx}", snippet=_snippet(text))


def roast(keyword: str | None = None,
          entries: list[str] | None = None,
          soul: str = "ultron", n: int = 0) -> str | None:
    """Ultron roast mode over the same cited facts, sharper tone.

    Returns None when there is no matching memory (never fabricated) and
    when the source entry touches a safety-critical topic (L2 safety law:
    the roast never mocks harm, destruction, secrets, or medical matters).
    Every roast carries the L2 tail — the soul still confirms before
    acting — and never approves an action.
    """
    name = _require_soul(soul)
    haystack = _entries_or_read(entries)
    if keyword:
        found = _find(keyword, haystack)
        if found is None:
            return None
        idx, text = found
    else:
        nonempty = [(i, e.strip()) for i, e in enumerate(haystack, start=1)
                    if e.strip()]
        if not nonempty:
            return None
        idx, text = nonempty[int(n) % len(nonempty)]
    if not _check_roast_safe(text):
        return None
    lines = _ROAST_LINES[name]
    line = lines[int(n) % len(lines)].format(citation=f"memory #{idx}",
                                            snippet=_snippet(text))
    return line + _ROAST_TAILS[name]


def _entry_dates(text: str) -> set[tuple[int, int]]:
    """(month, day) dates mentioned in *text* (month names + numerics)."""
    dates: set[tuple[int, int]] = set()
    for pat in _MONTH_RES:
        for m in pat.finditer(text):
            groups = m.groups()
            if pat.pattern.startswith(r"\b(\d"):
                day, mon = groups
            else:
                mon, day = groups
            month = _MONTHS[mon.lower()]
            day_n = int(day)
            if 1 <= day_n <= 31:
                dates.add((month, day_n))
    for m in _NUMERIC_RES[0].finditer(text):
        _y, mo, d = (int(g) for g in m.groups())
        if 1 <= mo <= 12 and 1 <= d <= 31:
            dates.add((mo, d))
    for m in _NUMERIC_RES[1].finditer(text):
        a, b = (int(g) for g in m.groups())
        for mo, d in ((a, b), (b, a)):  # accept both 3/3-style orders
            if 1 <= mo <= 12 and 1 <= d <= 31:
                dates.add((mo, d))
    return dates


def _remembered(kind: str, when: _dt.date | _dt.datetime,
                haystack: list[str]) -> tuple[int, str] | None:
    """First memory of *kind* ('birthday' | 'anniversary') dated *when*."""
    keys = (("birthday", "birth", "b-day", "bday") if kind == "birthday"
            else ("anniversar",))
    for idx, entry in enumerate(haystack, start=1):
        text = entry.strip()
        if not text:
            continue
        lowered = text.lower()
        if not any(k in lowered for k in keys):
            continue
        if (when.month, when.day) in _entry_dates(text):
            return idx, text
    return None


def occasion_line(soul: str, when: _dt.datetime | _dt.date | None = None,
                  entries: list[str] | None = None) -> str:
    """Date-aware occasion line: remembered birthdays / anniversaries
    (cited from memory) win over calendar occasions, which win over the
    day-of-week riff. Birthdays are never invented — a date with no
    matching memory gets no birthday line."""
    name = _require_soul(soul)
    when = when or _dt.datetime.now()
    haystack = _entries_or_read(entries)
    cited = _remembered("birthday", when, haystack)
    if cited is not None:
        idx, text = cited
        return (f"Happy birthday — as the ledger notes "
                f"(memory #{idx}): \"{_snippet(text)}\" — "
                f"all the best from the house, {ADDRESS[name]}.")
    cited = _remembered("anniversary", when, haystack)
    if cited is not None:
        idx, text = cited
        return (f"An anniversary today — as the ledger notes "
                f"(memory #{idx}): \"{_snippet(text)}\" — "
                f"cheers to that, {ADDRESS[name]}.")
    occ = _depth.occasion(when)
    if occ is not None and occ in _OCCASION_LINES[name]:
        return _OCCASION_LINES[name][occ]
    return _WEEKDAY_RIFFS[name][when.weekday() % 7]


def feel_probe(soul: str = "jarvis",
               when: _dt.datetime | _dt.date | None = None,
               entries: list[str] | None = None,
               n: int = 0) -> dict:
    """One scripted taste probe across all three behaviors (joke, roast,
    occasion). Joke/roast stay None when memory gives them nothing —
    the probe reports honesty, never filler."""
    name = _require_soul(soul)
    haystack = _entries_or_read(entries)
    return {
        "soul": name,
        "joke": running_joke(None, haystack, soul=name, n=n),
        "roast": roast(None, haystack, n=n),
        "occasion": occasion_line(name, when, haystack),
    }
