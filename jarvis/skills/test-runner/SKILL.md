---
name: test-runner
description: "run the failing test (Jarvis pack skill, ported)."
version: 1.0.0
author: Jarvis pack (ported from frozen Node skills-src)
license: MIT
platforms: [linux, macos]
x-jarvis-tier: L1
x-jarvis-trigger: "run the failing test"
x-jarvis-source: skills-src/test-runner/SKILL.md
metadata:
  hermes:
    tags: [jarvis, ported, l1]
    related_skills: []
---
# test-runner

Run the scoped test suite for this repo and explain failures.

1. Run `npm test` from the pack root for adapter render/remove/verify coverage.
2. Run `node test/hud.js` to prove the HUD serves the transcript tail.
3. Run `node --check` on every file under `bin/` before claiming voice work is done.
4. If a test fails, report the failing file, the exact command, and the first error line.
5. Never edit harness-owned files; rendered copies under test roots are disposable.
