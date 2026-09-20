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
