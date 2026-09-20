# habits — cron jobs for the Jarvis fleet (W5)

Canonical specs in `jobs/*.json`, applied idempotently by `ensure-habits.sh`:

```sh
HERMES_HOME=~/.jarvis jarvis/habits/ensure-habits.sh
```

| Job | Schedule | Skill | Deliver | Mode |
|---|---|---|---|---|
| `morning-brief` | `0 7 * * *` | `jarvis-morning` | `bot-chat` (continuable thread) | agent, `--continuity` |
| `ci-watchdog` | `*/30 * * * *` | `ci-watchdog` | `local` | monitor-gated agent (`scripts/ci-fingerprint.sh`) |

Standing rules enforced by the applier: `cron.preflight=true`, model +
provider pinned (`auto/best-reasoning` on `custom`), continuity on (stored
as `context_from: ["self"]`), failure notices to `local`.

`ci-fingerprint.sh` is the monitor gate: stable stdout (repo, branch, run
ids, statuses, conclusions — no timestamps); unchanged output suppresses
the agent run. Lives in the repo here, installed to
`$HERMES_HOME/scripts/` by the applier. Requires `gh` authenticated for
the fork; without it the output is the constant `gh-unavailable` (stable,
no spam).
