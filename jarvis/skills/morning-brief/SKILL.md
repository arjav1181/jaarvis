---
name: morning-brief
description: "brief me (Jarvis pack skill, ported)."
version: 1.0.0
author: Jarvis pack (ported from frozen Node skills-src)
license: MIT
platforms: [linux, macos]
x-jarvis-tier: L1
x-jarvis-trigger: "brief me"
x-jarvis-source: commands-src/brief.md
metadata:
  hermes:
    tags: [jarvis, ported, l1]
    related_skills: []
---
# /brief

Read the morning brief inputs and speak the summary.

- Pull today's recall with `JARVIS_SESSION_QUERY="today" hooks/session-start.sh`.
- Summarize open work from `memory/journal/` and the latest transcript tail.
- Speak the result with `node bin/speak "<summary>"`.
- Never send, post, or merge anything while briefing (L2 stays gated).
