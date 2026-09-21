#!/usr/bin/env sh
# ensure-foresight.sh — install the W10 foresight-brief job (idempotent).
# New job only; W5 habits, W8 proactivity, and W7 apex files are never touched.
# Respects HERMES_HOME (defaults to the live TEST home). Usage: ensure-foresight.sh
set -u
: "${HERMES_HOME:=/home/runner/.jarvis-test}"
export HERMES_HOME
REPO="/home/runner/workspace/hermes-fork"
BIN="$REPO/jarvis/bin"

if hermes cron list 2>/dev/null | grep -q -F "jarvis-foresight-brief"; then
  echo "jarvis-foresight-brief: ok (already installed)"
else
  # shellcheck disable=SC2086
  hermes cron create --name "jarvis-foresight-brief" --deliver local --failure-deliver local \
    --model auto/best-reasoning --provider custom \
    --workdir "$REPO" "30 21 * * *" \
    "Run the foresight brief: HERMES_HOME=$HERMES_HOME PATH=/home/runner/.venvs/jarvis-w0/bin:\$PATH $BIN/jarvis-doctor-foresight > $HERMES_HOME/web_dist_overlay/foresight-snapshot.json. Report one line (calibration headline, open/overdue counts, snapshot written). If the runner itself fails, say so in one line and stop. Never send, post, or merge anything." >/dev/null 2>&1 \
    && echo "jarvis-foresight-brief: installed" \
    || echo "jarvis-foresight-brief: FAILED (see hermes cron list)"
fi

hermes cron doctor 2>&1 | tail -n 2 || true
