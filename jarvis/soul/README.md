# Soul depth — W12

Third soul (Friday) + occasion-aware greetings + cited callback humor +
multilingual voices + rotating narration + punchier reply shaping.

## Pieces

| Piece | Source | Installed as |
|---|---|---|
| Friday soul | `jarvis/SOUL.friday.md` | reference + `/personality friday` text (slot #1 stays Jarvis) |
| Personalities (3) | `jarvis/personalities.yml` | merged into `<home>/config.yaml` `agent.personalities` |
| Friday skin | `jarvis/skins/friday-emerald.yaml` | `<home>/skins/friday-emerald.yaml` |
| Voices + languages | `jarvis/personas/voices.yml` + `languages.yml` | read by the voice loop; user override under `tts:` |
| Narration rotation | `jarvis/personas/narration.yml` | read by `soul/depth.py`; W13 swaps the HUD page source to it |
| Depth helpers | `jarvis/soul/depth.py` | `greet / milestone / callback / shape / voice_for` |
| Clone policy | `jarvis/soul/VOICE_CLONE.md` | documented only — no cloning without explicit owner consent |

## Flip

`jarvis-persona friday` → personality `friday` + skin `friday-emerald` +
Edge voice `en-IE-EmilyNeural` (live-list verified 2026-09-20). Same three
halves as W1; take effect on the next utterance.

## Rules the souls share (prompt + code)

- **L2 always-confirms**, all three souls (prompt is not policy).
- **Narration never approves**; milestone lines are speech-only.
- **Callbacks cite memory** (`callback()` returns `None` on a miss — the soul
  must stay silent about the past rather than invent it).
- **Occasions stay to one line**; ordinary days get daypart + at most a
  weekend/Monday tail.
- **Multilingual**: `voice_for(soul, lang)`; unknown language falls back to
  the soul default — never a guessed voice ID.

## Tests

`tests/jarvis/test_w12_soul.py` — hermetic (tmp homes, no network except the
already-proven TTS path which the live proof covers).

# Wit engine — W16

Running jokes, Ultron roast mode, and occasion depth beyond greetings.

| Piece | Source | Installed as |
|---|---|---|
| Wit helpers | `jarvis/soul/wit.py` | `running_joke / roast / occasion_line / feel_probe` |
| Joke templates | `jarvis/personas/narration.yml` (`wit:` sets) | read by `running_joke()`; `{citation}` + `{snippet}` per line |
| Soul wit rules | `jarvis/SOUL.ultron.md`, `jarvis/SOUL.friday.md` | one line each (Jarvis file untouched — W0 profile equality) |

Rules the engine enforces (code, not vibes):

- **Cited or silent**: `running_joke()` and `roast()` return `None` when no
  stored memory matches — the soul stays silent about the past rather than
  inventing it. Every line carries `memory #N` plus quoted words.
- **Roast stays lawful**: `roast()` returns `None` on safety-critical source
  material (harm, destruction, secrets, medical matters), never approves an
  action (no approval verbs in any template), and always carries the L2 tail
  — the soul still confirms before acting.
- **Occasions never fabricated**: birthdays/anniversaries fire only on a
  memory entry that names the kind AND the date; other days get calendar
  lines or day-of-week riffs.

## Tests

`tests/jarvis/test_w16_wit.py` — scripted taste probes with deterministic
PASS criteria (structure / citation / word-lists), hermetic tmp homes.
