# JAARVIS — Just A Rather Very Intelligent System

A voice-first AI butler with a soul: wakes on its name, talks hands-free, remembers everything, acts on your machines — and asks before anything irreversible.

🌐 **https://jaarvis.pages.dev** · Souls: **Jarvis** (butler) · **Ultron** (menace) · **Friday** (analyst)

## What it does

- **Hears you** — wake word, continuous hands-free conversation, barge-in under half a second, streaming speech, browser voice HUD with an arc-reactor orb.
- **Shows itself** — holographic HUD (voice, diagnostics, foresight, apex pages), per-soul voices and microcopy, one-tap kill.
- **Remembers** — cited memory callbacks (never fabricated), occasion greetings, multilingual voices.
- **Works** — skills pack, scheduled briefs + watchdogs, foresight simulations with a calibration ledger, Kanban agent fleet with PR contracts.
- **Obeys guardrails** — reads are free; anything remote or irreversible always confirms, in every mode, under every soul. Freeze + break-glass included.

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
cp -r hermes_cli/web_dist $HERMES_HOME/web_dist_overlay
cp jarvis/hud/*.html $HERMES_HOME/web_dist_overlay/
HERMES_WEB_DIST=$HERMES_HOME/web_dist_overlay hermes dashboard --port 3000
```

Open `:3000/voice.html`, log in, say hi. Full operator guide in [`jarvis/README.md`](jarvis/README.md).

## Repo map

All Jaarvis work lives in [`jarvis/`](jarvis/) + [`tests/jarvis/`](tests/jarvis/): souls, skins, voices, HUD, skills, habits, fleet, permissions, foresight — with a test suite per wave. Everything else is the upstream engine, untouched.

## Built on Hermes Agent

Jaarvis is a persona overlay on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research (MIT — see [LICENSE](LICENSE)). An `upstream` remote + merge-train keeps the engine current; all Jaarvis work stays conflict-free in the overlay. Engine bugs go upstream, not here.

## License

MIT.
