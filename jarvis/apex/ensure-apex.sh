#!/usr/bin/env sh
# ensure-apex.sh — install the W7 apex-snapshot job (idempotent).
# New job only; W5 habits and W8 proactivity files are never touched.
# Respects HERMES_HOME (defaults to the live TEST home). Usage: ensure-apex.sh
set -u
: "${HERMES_HOME:=/home/runner/.jarvis-test}"
export HERMES_HOME
REPO="/home/runner/workspace/hermes-fork"
BIN="$REPO/jarvis/bin"

if hermes cron list 2>/dev/null | grep -q -F "jarvis-apex-snapshot"; then
  echo "jarvis-apex-snapshot: ok (already installed)"
else
  # shellcheck disable=SC2086
  hermes cron create --name "jarvis-apex-snapshot" --deliver local --failure-deliver local \
    --model auto/best-reasoning --provider custom \
    --workdir "$REPO" "*/30 * * * *" \
    "Run the apex-beast snapshot: HERMES_HOME=$HERMES_HOME PATH=/home/runner/.venvs/jarvis-w0/bin:\$PATH $BIN/jarvis-doctor-apex > $HERMES_HOME/web_dist_overlay/apex-snapshot.json. Report one line (ladder rung, STT engine, snapshot written). If the runner itself fails, say so in one line and stop. Never send, post, or merge anything." >/dev/null 2>&1 \
    && echo "jarvis-apex-snapshot: installed" \
    || echo "jarvis-apex-snapshot: FAILED (see hermes cron list)"
fi

hermes cron doctor 2>&1 | tail -n 2 || true
