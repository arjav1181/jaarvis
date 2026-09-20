# jarvis-ops — orchestrator/worker profiles + PR contracts (W5)

Board: `jarvis-ops` ("Jarvis ops queue"). Spec: `jarvis-ops.json`.
Applied by `ensure-kanban.sh` (idempotent; `--board` always explicit;
global current board never flipped; workers never auto-dispatched).

## Profiles

| Profile | Role | Routing signal (description) |
|---|---|---|
| `jarvis-orchestrator` | orchestrator | Decomposes ops goals into small contracted tasks, routes by worker description, owns review + unblock. Never executes task work directly. |
| `jarvis-worker` | worker | Executes one contracted task at a time in the fork, runs scoped tests, delivers as PR with proofs. Asks on ambiguity; L2 always confirms. |

The kanban decomposer routes by profile description, so these texts ARE
the routing config — keep them literal, keep them short.

## PR contracts (every task's `completion_contract`)

The contract field is the publication target — `arjav1181/jaarvis` on every
task — with required CI gates built into the mechanism. The prose contract
lives in the task body (opening post):

1. Deliver as a PR to `jaarvis`, base `jarvis` — never push to `jarvis`.
2. Body carries proofs: what changed, command output pasted, test lines.
3. `tests/jarvis/` green on the branch; relevant upstream suites green.
4. Secrets scan clean; `~/.hermes` absent; status overlay-only.
5. Merge only when green; red CI is a report, never a merge.

## Standing rules (unchanged)

- `unblock` is orchestrator-only; workers mark blocked and wait.
- One task per worker at a time; consecutive-failures cap respected.
- Narration never approves; L2 always confirms, even Ultron.
