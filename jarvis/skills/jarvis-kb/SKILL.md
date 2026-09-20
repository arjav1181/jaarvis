---
name: jarvis-kb
description: "search my docs (Jarvis knowledge-base: frozen pack PRD/TRD/ARCHITECTURE/SKILLS/CONNECTORS)."
version: 1.0.0
author: Jarvis pack (/learn pass over frozen Node docs)
license: MIT
platforms: [linux, macos]
x-jarvis-tier: L0
x-jarvis-trigger: "search my docs"
x-jarvis-source: /learn over frozen docs (see references/)
metadata:
  hermes:
    tags: [jarvis, authored, l0, knowledge-base]
    related_skills: [morning-brief, ci-watchdog]
---

# jarvis-kb

One knowledge-base skill learned from the frozen Jarvis pack docs
(`references/` holds verbatim copies of the five design docs only; the
frozen pack's credential files are NEVER included — this skill carries
no secrets).

Read-only. Answer from these docs and cite the file + section.

## What lives here

- `references/PRD.md` — product requirements: personas, tiers (L0/L1/L2),
  safety rules (L2 always confirms, even Ultron; narration never approves).
- `references/TRD.md` — technical requirements: harness rendering, auth
  (loopback token-free by default, LAN needs `config.api_token`), redaction.
- `references/ARCHITECTURE.md` — pack layout: adapters, skills-src,
  commands-src, hooks, memory, scenes.
- `references/SKILLS.md` — skill catalog: triggers, tiers, scenes
  (good-morning, focus-mode, ship-it, movie-night, shutdown).
- `references/CONNECTORS.md` — connector inventory and states.

## Rules

1. Quote the exact section that answers the question; never paraphrase a
   safety rule loosely.
2. Safety rules are unchanged by persona: L2 always confirms, narration
   never approves, actuator skills stay confirmable.
3. If the docs don't cover it, say so — never fabricate pack behavior.
4. This skill never writes, sends, or approves anything (L0).
