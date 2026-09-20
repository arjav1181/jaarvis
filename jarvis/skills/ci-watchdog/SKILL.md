---
name: ci-watchdog
description: "watch the CI (Jarvis pack skill: poll CI state, report failures, never merge)."
version: 1.0.0
author: Jarvis pack (Hermes-native)
license: MIT
platforms: [linux, macos]
x-jarvis-tier: L1
x-jarvis-trigger: "watch the CI"
x-jarvis-source: authored for W5 (HERMES_HOME cron monitor + skill pair)
metadata:
  hermes:
    tags: [jarvis, authored, l1, ci]
    related_skills: [ship-pr, test-runner]
---

# ci-watchdog

Watch CI on the Jarvis fork and report state changes. Read-only except for
re-running a failed check when explicitly asked (re-run is L1; merge,
publish, and force-push stay L2 and always confirm).

1. Scope to the fork's `jarvis` branch first (`gh run list --branch jarvis`),
   then open PRs.
2. Report: workflow, run id, branch, conclusion, failing step + first error
   line. One paragraph, no noise.
3. If everything is green, say so in one line and stop — no celebration
   digest, no extra API calls.
4. Never merge, never publish, never force-push. A red run is a report,
   not a mandate to fix (fixing is `ship-pr` territory, L2 at push).
5. Quiet hours: a run that stays red across ticks is reported once, then
   only on conclusion change (the cron monitor script enforces this by
   suppressing agent runs while its fingerprint is unchanged).
