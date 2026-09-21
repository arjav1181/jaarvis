# JAARVIS — Just A Rather Very Intelligent System

A voice-first AI butler with a soul: wakes on its name, talks hands-free, remembers everything, acts on your machines — and asks before anything irreversible. Built as a strict **overlay** on [Hermes Agent](https://github.com/NousResearch/hermes-agent) (MIT): zero core files touched, monthly merge-train from upstream.

🌐 **https://jaarvis.pages.dev** · Souls: **Jarvis** (butler) · **Ultron** (menace) · **Friday** (analyst)

## What it does

- **Hears you** — wake word, continuous hands-free conversation, barge-in under half a second, streaming speech.
- **Shows itself** — arc-reactor HUD orb with honest states (every pixel maps to real events), per-soul voices and microcopy, one-tap kill.
- **Remembers** — cited memory callbacks (never fabricated), occasion greetings, multilingual voices.
- **Works** — skills pack, scheduled briefs + watchdogs, Kanban agent fleet with PR contracts.
- **Obeys guardrails** — reads are free; anything remote or irreversible always confirms, in every mode, under every soul. Kill switch included.

## Safety law (non-negotiable)

L0 reads free · L1 mode-gated · **L2 remote/irreversible ALWAYS confirms — even Ultron**. Narration never approves. Secrets live in the operator's vault/env, never in the repo, logs, or memory. Localhost-first; no telemetry added.

## Quickstart (operator)

```bash
git clone https://github.com/arjav1181/jaarvis && cd jaarvis
uv venv ~/.venvs/jarvis && uv pip install --python ~/.venvs/jarvis/bin/python \
  -e . "edge-tts==7.2.7" "faster-whisper==1.2.1" "openwakeword==0.6.0"
export HERMES_HOME=~/.jaarvis
hermes setup --non-interactive
# point model.* at your OpenAI-compatible endpoint, then:
cp jarvis/SOUL.jarvis.md $HERMES_HOME/SOUL.md
cp jarvis/skins/*.yaml $HERMES_HOME/skins/
HERMES_HOME=$HERMES_HOME bash jarvis/skills-port/install-skills.sh
# serve the voice HUD next to upstream web_dist:
cp -r hermes_cli/web_dist $HERMES_HOME/web_dist_overlay
cp jarvis/hud/voice.html $HERMES_HOME/web_dist_overlay/
HERMES_WEB_DIST=$HERMES_HOME/web_dist_overlay hermes dashboard --port 3000
```

Open `:3000/voice.html`, log in, say hi. `jarvis/bin/` holds operator helpers (`jarvis-persona`, `jarvis-voice-status`).

## Repo map (`jarvis/` = our overlay, everything else = upstream)

| Path | What |
|---|---|
| `SOUL.*.md`, `personalities.yml`, `PERSONAS.md` | the three souls |
| `skins/` | jarvis-gold / ultron-crimson / friday-emerald |
| `personas/` | voices, languages, narration rotation |
| `soul/` | depth helpers, occasion/callback rules, clone policy |
| `hud/` | voice page + docs (the face) |
| `skills/` + `skills-port/` | skill pack + repeatable port/install scripts |
| `habits/`, `kanban/`, `curator/` | schedules, fleet board spec, curator pins |
| `permissions/`, `proactivity/` | smart-permission + spoken brief/alert specs (landing now) |
| `bin/` | operator helpers |
| `tests/jarvis/` (in `tests/`) | per-wave suites; upstream suites untouched |

## Upstream relationship

Fork of `NousResearch/hermes-agent`. All Jaarvis work lives in `jarvis/` + `tests/jarvis/` — an `upstream` remote + merge-train keeps us current without conflicts. Found a Hermes bug while here? It goes upstream, not in the overlay.

## Status

Waves W0–W5 + W12–W13 shipped with per-wave test suites and live-rig proofs (see `jarvis/hud/README.md`, `jarvis/soul/README.md`). Roadmap: smart permissions → apex voice → foresight → hands → presence. Homelab (Spotify/Home Assistant) last.

## License

MIT — same as upstream Hermes Agent.
