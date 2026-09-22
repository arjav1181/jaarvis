# Friday self-improvement loop (W18)

Friday reviews the week:

1. **Mine failures** — red tests (`pytest -rf` text), failed cron runs
   (`hermes cron history` rows), refused acts (permission-audit rows).
2. **Draft fix cards** — one kanban card per finding on `jarvis-ops`, each
   carrying the PR contract and its citation (`jarvis-loop:` idempotency
   namespace; refused acts route to the orchestrator as triage).
3. **Propose curator trims** — dead (`uses=0`) or stale skills from
   `hermes curator usage`; pinned skills are fenced, unknown usage is left
   alone, archives are operator-executed previews only.
4. **File the weekly report** — found / fix-cards / trimmed, every line
   cited, under `<HERMES_HOME>/jarvis/loop/reports/`.

## Mode discipline

Dry-run is the default: zero kanban creates, zero curator archives. Live
needs **two keys per run** — `--live` on the command line (or
`run(live=True)`) **plus** `JARVIS_LOOP_LIVE=1` in the environment. Either
missing → the run is refused and nothing executes.

```bash
# Real dry-run over this week's evidence (nothing changes):
export HERMES_HOME=/home/runner/workspace/.rig-home
python3 -m pytest tests/jarvis/ -rf -q > /tmp/opencode/pytest-week.txt
python3 -m jarvis.loop --pytest-log /tmp/opencode/pytest-week.txt

# Preview with synthetic evidence (labelled demo):
python3 -m jarvis.loop --demo

# Live (explicit operator flag per run):
JARVIS_LOOP_LIVE=1 python3 -m jarvis.loop --pytest-log ... --live
```

## Files

- `miners.py` — pure parsers (hermetic, no subprocess/network).
- `run.py` — orchestrator + two-key live gate.
- `report.py` — cited weekly report builder + receipt store.
- `__main__.py` — operator CLI.
- `weekly-review.example.json` — Friday job-shaped spec (install by hand;
  `jarvis/habits/` is another lane's turf).
- `../kanban/loop_cards.py` — loop-owned card builder (W5 board files
  untouched).
- `../curator/loop_trim.py` — loop-owned trim proposals (pins untouched).
