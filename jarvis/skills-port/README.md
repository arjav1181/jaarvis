# skills-port — frozen Node skills → Hermes skills (W5)

Repeatable, deterministic port. The frozen pack (`/home/runner/workspace/jarvis/`)
is read-only input and is never modified.

## Run

```sh
python3 jarvis/skills-port/port_skills.py [--src DIR] [--out DIR]
```

Ports `skills-src/*/SKILL.md` + `commands-src/brief.md` (→ `morning-brief`),
translating frontmatter to Hermes keys (`name, description, version, author,
license, platforms, metadata.hermes.tags/related_skills`) while preserving
`x-jarvis-tier`, `x-jarvis-trigger`, `x-jarvis-source` and the body verbatim.
Writes `manifest.json` (sha256 per skill, no timestamps — run twice,
byte-identical).

## Install

```sh
HERMES_HOME=~/.jarvis jarvis/skills-port/install-skills.sh
```

Copies `jarvis/skills/<name>/` → `$HERMES_HOME/skills/jarvis/<name>/`.
Verify: `hermes skills list --source local`.
