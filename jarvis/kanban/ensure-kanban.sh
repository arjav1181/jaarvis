#!/usr/bin/env bash
# ensure-kanban.sh — bring the jarvis-ops board live (W5).
#
# Usage: HERMES_HOME=/path/to/home jarvis/kanban/ensure-kanban.sh
#
# Idempotent: board created once; profiles created once (description set
# every run — cheap and keeps routing signals fresh); tasks matched by
# --idempotency-key so re-runs never duplicate. Always addresses the board
# explicitly (--board); never flips the global current board. Prints the
# board roster as proof. Never dispatches workers (dispatch spends model
# turns; the orchestrator does that by hand, per task).
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
: "${HERMES_HOME:=$HOME/.jarvis}"
export HERMES_HOME
SPEC="$HERE/jarvis-ops.json"

python3 - "$SPEC" <<'EOF'
import json, subprocess, sys

spec = json.loads(open(sys.argv[1]).read())
board = spec["board"]

def run(*a, check=True):
    r = subprocess.run(a, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"ensure-kanban: {' '.join(a)} failed:\n{r.stdout}\n{r.stderr}",
              file=sys.stderr)
        sys.exit(1)
    return r

boards = run("hermes", "kanban", "boards").stdout
if board not in boards:
    run("hermes", "kanban", "boards", "create", board,
        "--description", spec["description"])
    print(f"ensure-kanban: board {board} created")
else:
    print(f"ensure-kanban: board {board} exists")

existing_profiles = run("hermes", "profile", "list").stdout
for p in spec["profiles"]:
    if p["name"] not in existing_profiles:
        run("hermes", "profile", "create", p["name"],
            "--description", p["description"])
        print(f"ensure-kanban: profile {p['name']} created ({p['role']})")
    else:
        run("hermes", "profile", "describe", p["name"], "--text", p["description"])
        print(f"ensure-kanban: profile {p['name']} description refreshed")

for t in spec["tasks"]:
    args = ["hermes", "kanban", "--board", board, "create", t["title"],
            "--body", t["body"], "--assignee", t["assignee"],
            "--priority", str(t["priority"]),
            "--idempotency-key", f"jarvis-ops:{t['key']}",
            "--completion-contract", t["completion_contract"]]
    for s in t.get("skills", []):
        args += ["--skill", s]
    if t.get("triage"):
        args.append("--triage")
    out = run(*args).stdout.strip()
    print(f"ensure-kanban: task {t['key']}: {out.splitlines()[-1] if out else 'ok'}")

print("=== roster ===")
print(run("hermes", "kanban", "--board", board, "list").stdout)
EOF
