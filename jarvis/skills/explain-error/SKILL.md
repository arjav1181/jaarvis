---
name: explain-error
description: "what does this error mean (Jarvis pack skill, ported)."
version: 1.0.0
author: Jarvis pack (ported from frozen Node skills-src)
license: MIT
platforms: [linux, macos]
x-jarvis-tier: L0
x-jarvis-trigger: "what does this error mean"
x-jarvis-source: skills-src/explain-error/SKILL.md
metadata:
  hermes:
    tags: [jarvis, ported, l0]
    related_skills: []
---
# explain-error

Explain a failure without changing anything (read-only).

1. Quote the exact error line and the command that produced it.
2. Name the file and line that threw, and what it was trying to do.
3. Give the most likely cause first, then two alternatives ranked by likelihood.
4. Suggest the smallest next check (a log tail, a `--check`, a single scoped test).
5. Do not propose irreversible actions; this skill never writes.
