# Souls, skins, voices — W1

Sources live here (`jarvis/`); installed copies go to the active home
(TEST home until Done proofs pass — never the default profile).

| Piece | Source | Installed as |
|---|---|---|
| Jarvis soul | `jarvis/SOUL.jarvis.md` | `<home>/SOUL.md` (slot #1) |
| Ultron soul | `jarvis/SOUL.ultron.md` | reference + `/personality ultron` text (slot #1 stays Jarvis) |
| Personalities | `jarvis/personalities.yml` | merged into `<home>/config.yaml` `agent.personalities` |
| Skins | `jarvis/skins/*.yaml` | `<home>/skins/*.yaml` |
| Voices map | `jarvis/personas/voices.yml` | read by the W2 voice loop; user override under `tts:` |

## Flip mechanism (persona → skin)

Upstream keeps personality and skin independent — the flip sets both:

1. **Helper (recommended):** `jarvis-persona jarvis|ultron`
   → `hermes config set display.personality <name>` +
   `hermes config set display.skin <jarvis-gold|ultron-crimson>`.
   Persona takes effect on the next utterance; skin on CLI/TUI surfaces.
2. **Manual config:** set `display.personality:` + `display.skin:` in
   `<home>/config.yaml` directly.
3. **In-session:** `/personality jarvis|ultron` (overlay until changed) +
   `/skin` session switch, or `hermes skin use <name>` (persists
   `display.skin`).

Custom `agent.personalities` entries overlay same-named built-ins;
`agent.personalities` wins over a top-level `personalities:` block.
Selecting `none`/`default`/`neutral` clears the overlay back to `SOUL.md`.
