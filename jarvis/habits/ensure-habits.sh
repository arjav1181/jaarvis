#!/usr/bin/env bash
# ensure-habits.sh — apply jarvis/habits/jobs/*.json to a Hermes home (W5).
#
# Usage: HERMES_HOME=/path/to/home jarvis/habits/ensure-habits.sh
#
# Idempotent: matches existing jobs by name in $HERMES_HOME/cron/jobs.json;
# creates missing jobs, edits drifted ones (schedule/prompt/skills/model/
# provider/continuity/deliver/workdir/monitor). Installs monitor scripts
# from jarvis/habits/scripts/ into $HERMES_HOME/scripts/. Enforces
# cron.preflight=true (standing rule: preflight ON). Prints a per-job
# created|ok|updated verdict. Mutations go through `hermes cron` CLI only.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
: "${HERMES_HOME:=$HOME/.jarvis}"
export HERMES_HOME

mkdir -p "$HERMES_HOME/scripts"
for s in "$HERE"/scripts/*.sh; do
  cp "$s" "$HERMES_HOME/scripts/"
  chmod +x "$HERMES_HOME/scripts/$(basename "$s")"
done
echo "ensure-habits: monitor scripts -> $HERMES_HOME/scripts/"

if [ "$(hermes config get cron.preflight 2>/dev/null)" != "true" ]; then
  hermes config set cron.preflight true
fi
echo "ensure-habits: cron.preflight=$(hermes config get cron.preflight)"

python3 - "$HERE/jobs" <<'EOF'
import json, subprocess, sys
from pathlib import Path

jobs_dir = Path(sys.argv[1])
store = Path(__import__("os").environ["HERMES_HOME"]) / "cron" / "jobs.json"
existing = {}
if store.is_file():
    try:
        for j in json.loads(store.read_text()).get("jobs", []):
            existing[j.get("name")] = j
    except Exception as exc:
        print(f"ensure-habits: cannot read {store}: {exc}", file=sys.stderr)
        sys.exit(1)

def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ensure-habits: {' '.join(a)} failed:\n{r.stderr}", file=sys.stderr)
        sys.exit(1)
    return r.stdout

for spec_f in sorted(jobs_dir.glob("*.json")):
    spec = json.loads(spec_f.read_text())
    name = spec["name"]
    cur = existing.get(name)
    create_args = [spec["schedule"], spec["prompt"], "--name", name,
                   "--model", spec["model"], "--provider", spec["provider"],
                   "--deliver", spec["deliver"],
                   "--failure-deliver", spec["failure_deliver"],
                   "--workdir", spec["workdir"]]
    for s in spec["skills"]:
        create_args += ["--skill", s]
    if spec.get("continuity"):
        create_args += ["--continuity"]
    if spec.get("monitor_script"):
        create_args += ["--monitor-script", spec["monitor_script"]]
    if cur is None:
        run("hermes", "cron", "create", *create_args)
        print(f"ensure-habits: {name}: created")
        continue
    sched = cur.get("schedule", {})
    sched_expr = sched.get("expr", cur.get("schedule_display")) if isinstance(sched, dict) else sched
    want_cont = ["self"] if spec.get("continuity") else []
    pairs = {"schedule": (sched_expr, spec["schedule"]),
             "prompt": (cur.get("prompt"), spec["prompt"]),
             "model": (cur.get("model"), spec["model"]),
             "provider": (cur.get("provider"), spec["provider"]),
             "deliver": (cur.get("deliver"), spec["deliver"]),
             "failure_deliver": (cur.get("failure_deliver"), spec["failure_deliver"]),
             "workdir": (cur.get("workdir"), spec["workdir"]),
             "monitor_script": (cur.get("monitor_script"), spec["monitor_script"]),
             "continuity": (cur.get("context_from", []), want_cont)}
    drift = [k for k, (a, b) in pairs.items() if a != b]
    if set(cur.get("skills", [])) != set(spec["skills"]):
        drift.append("skills")
    if not drift:
        print(f"ensure-habits: {name}: ok ({cur.get('id')})")
        continue
    edit = ["hermes", "cron", "edit", cur["id"],
            "--schedule", spec["schedule"], "--prompt", spec["prompt"],
            "--model", spec["model"], "--provider", spec["provider"],
            "--deliver", spec["deliver"],
            "--failure-deliver", spec["failure_deliver"],
            "--workdir", spec["workdir"]]
    if spec.get("monitor_script"):
        edit += ["--monitor-script", spec["monitor_script"]]
    for s in spec["skills"]:
        edit += ["--add-skill", s]
    for s in set(cur.get("skills", [])) - set(spec["skills"]):
        edit += ["--remove-skill", s]
    edit += ["--continuity" if spec.get("continuity") else "--no-continuity"]
    run(*edit)
    print(f"ensure-habits: {name}: updated (drift: {','.join(drift)})")
EOF
