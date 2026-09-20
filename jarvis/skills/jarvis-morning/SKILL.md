---
name: jarvis-morning
description: "brief me (Jarvis morning bundle: brief + CI + memory in one pass)."
version: 1.0.0
author: Jarvis pack (Hermes-native bundle)
license: MIT
platforms: [linux, macos]
x-jarvis-tier: L1
x-jarvis-trigger: "brief me"
x-jarvis-source: authored bundle over morning-brief + ci-watchdog + jarvis-kb
metadata:
  hermes:
    tags: [jarvis, authored, l1, bundle, morning]
    related_skills: [morning-brief, ci-watchdog, jarvis-kb]
---

# jarvis-morning

The morning bundle. One pass, three parts, spoken-short. Never sends,
posts, or merges anything while briefing (L2 stays gated).

1. **Recall** (`morning-brief`): today's memory — open work, yesterday's
   tail, anything flagged overnight.
2. **CI** (`ci-watchdog`): `jarvis` branch state in one line; open PRs only
   if red or awaiting review.
3. **Orientation** (`jarvis-kb`): if the day's first question touches pack
   behavior, answer from the frozen docs and cite them.

Output shape: three bullets (Recall / CI / Focus), then one suggested
first action. Under 60 seconds spoken. The cron `morning-brief` job runs
this skill with continuity on, so each brief dedupes against the last.
