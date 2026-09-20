---
name: ship-pr
description: "ship it (Jarvis pack skill, ported)."
version: 1.0.0
author: Jarvis pack (ported from frozen Node skills-src)
license: MIT
platforms: [linux, macos]
x-jarvis-tier: L2
x-jarvis-trigger: "ship it"
x-jarvis-source: skills-src/ship-pr/SKILL.md
metadata:
  hermes:
    tags: [jarvis, ported, l2]
    related_skills: []
---
# ship-pr

Ship the current change with tests green and an explicit push confirmation.

1. Run `npm test` and `node --check` on `bin/*`; stop if anything is red.
2. Summarize the diff in one paragraph: what changed and why.
3. Ask for explicit confirmation before `git push`, `gh pr merge`, `gh release publish`, or `npm publish`. These are L2: the pre-tool-use hook must also confirm.
4. After pushing, watch CI with `gh run` and report the first failure verbatim if it goes red.
5. Never force-push, never publish, never merge without the confirmation in step 3.
