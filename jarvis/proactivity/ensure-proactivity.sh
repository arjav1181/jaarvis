#!/usr/bin/env sh
# ensure-proactivity.sh — install the W8 proactivity + snapshot jobs (idempotent).
# New jobs only; W5 habits files are never touched. Respects HERMES_HOME
# (defaults to the live TEST home). Usage: ensure-proactivity.sh
set -u
: "${HERMES_HOME:=/home/runner/.jarvis-test}"
export HERMES_HOME
REPO="/home/runner/workspace/hermes-fork"
BIN="$REPO/jarvis/bin"

has_job() {
  hermes cron list 2>/dev/null | grep -q -F "$1" || return 1
}

mk_job() {
  # mk_job NAME SCHEDULE PROMPT...
  name="$1"; schedule="$2"; shift 2
  if has_job "$name"; then
    echo "$name: ok (already installed)"
    return 0
  fi
  # shellcheck disable=SC2086
  hermes cron create --name "$name" --deliver local --failure-deliver local \
    --model auto/best-reasoning --provider custom \
    --workdir "$REPO" "$schedule" "$*" >/dev/null 2>&1 \
    && echo "$name: installed" \
    || echo "$name: FAILED (see hermes cron list)"
}

mk_job "jarvis-snapshot" "*/30 * * * *" \
  "Run the suit-diagnostics snapshot: HERMES_HOME=$HERMES_HOME PATH=/home/runner/.venvs/jarvis-w0/bin:\$PATH $BIN/jarvis-doctor-snapshot. Report one line (doctor ok/issues, tests passed/failed, snapshot written). If the snapshot runner itself fails, say so in one line and stop. Never send, post, or merge anything."

mk_job "speak-brief" "5 7 * * *" \
  "Speak the morning brief unless the house is silent: HERMES_HOME=$HERMES_HOME PATH=/home/runner/.venvs/jarvis-w0/bin:\$PATH $BIN/jarvis-speak --brief. Report one line (SPOKEN path+bytes, or SILENCED). Never send, post, or merge anything."

mk_job "watchdog-voice-alerts" "5,35 * * * *" \
  "Check for speak-worthy CI changes: HERMES_HOME=$HERMES_HOME PATH=/home/runner/.venvs/jarvis-w0/bin:\$PATH $BIN/jarvis-watchdog-alert. Report one line (alert spoken, or quiet). Never send, post, or merge anything."

hermes cron doctor 2>&1 | tail -n 2 || true
