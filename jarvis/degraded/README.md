# W20 degraded — honest offline mode (lane D)

When the model relay is down, Jarvis says so and keeps only what needs no
model. Banner line (HUD + CLI, verbatim): `my line to the stars is down,
sir`.

## Files (all new, lane-owned)

- `jarvis/degraded/probe.py` — one-shot relay probe (`GET {base}/models`,
  2.5 s default timeout, no retries), host-only evidence, persisted
  online/degraded/unknown state under `$HERMES_HOME/jarvis/`.
- `jarvis/degraded/queue.py` — brief/alert backlog (`degraded-queue.jsonl`)
  + `recover()` handshake: probe must pass before anything replays; the
  report states what was missed (downtime window + items).
- `jarvis/degraded/caps.py` — local-only set: `memory.read` (local JSON
  state search), `skills.describe`/`skills.help` (repo metadata + doc
  reads), and `answer()` which refuses model-dependent questions with a
  reason instead of hallucinating.
- `jarvis/degraded/snapshot.py` — HUD payload builder.
- `jarvis/bin/jarvis-degraded` — CLI: status/banner/probe/ask/
  queue-brief/queue-alert/pending/recover/deploy-page.
- `jarvis/bin/jarvis-doctor-degraded` — writes
  `<home>/web_dist_overlay/degraded-snapshot.json`.
- `jarvis/hud/degraded.html` — HUD page (same-origin + auth gate like the
  other pages; single fetch of its own snapshot; text-only rendering).
- `jarvis/hud/degraded-banner.inc.html` — paste-ready banner snippet.

## Deliberately untouched (declared per lane rules)

Existing HUD pages (`voice.html`, `diag.html`, …) were NOT edited: W13's
page contract pins an exact fetch allowlist for `voice.html`, so splicing a
snapshot fetch into existing pages would red the currently-green W3/W4/W8/
W13 suites this lane may not touch. The include snippet above is the
sanctioned later step.

## Serving choice

Same as W3/W9: copy `degraded.html` next to a copy of the built
`web_dist`, or `jarvis-degraded deploy-page --home <home>`:

```bash
jarvis-degraded deploy-page --home "$HERMES_HOME"
HERMES_WEB_DIST=<home>/web_dist_overlay hermes dashboard --host 0.0.0.0 --port 3000
```

Relay URL resolves from `--url`, then `JARVIS_RELAY_URL`, then
`OPENAI_BASE_URL`. Unset = `unknown`, local caps only, never guessed.
