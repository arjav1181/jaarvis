#!/usr/bin/env bash
# ensure-loop.sh — prove the Friday loop (W18) is wired, dry-run only.
#
# Usage: jarvis/loop/ensure-loop.sh
#
# 1. Runs the loop's hermetic suite (tests/jarvis/test_w18_loop.py).
# 2. Runs a synthetic demo pass (labelled demo, temp HERMES_HOME) and prints
#    the filed report path.
# Never dispatches kanban creates, never archives skills, never needs --live.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
cd "$REPO"
export HERMES_HOME="${HERMES_HOME:-$(mktemp -d)/loop-proof}"

python3 -m pytest "$REPO/tests/jarvis/test_w18_loop.py" -q || exit 1
python3 -m jarvis.loop --demo || exit 1
echo "ensure-loop: wired (dry-run only; live needs --live + JARVIS_LOOP_LIVE=1)"
