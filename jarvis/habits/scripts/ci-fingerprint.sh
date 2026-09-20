#!/usr/bin/env bash
# ci-fingerprint.sh — stable CI fingerprint for the cron monitor gate.
#
# Runs each tick BEFORE the agent. Unchanged stdout (exact-bytes hash)
# suppresses the agent run entirely; changed stdout injects a
# MONITOR CHANGE DETECTED diff into the ci-watchdog prompt.
#
# Contract: output must be STABLE — repo, branch, latest run ids, statuses,
# conclusions. No timestamps, no durations, no run counters. If gh is
# unavailable the output is the constant string "gh-unavailable" (also
# stable — no flapping, no agent spam).
set -u

cd /home/runner/workspace/hermes-fork || { echo "gh-unavailable"; exit 0; }

if ! command -v gh >/dev/null 2>&1; then
  echo "gh-unavailable"
  exit 0
fi

# Latest 5 runs on jarvis + open PR checks; sorted, timestamp-free.
{
  gh run list --branch jarvis --limit 5 \
    --json databaseId,status,conclusion,headBranch,workflowName \
    --jq 'sort_by(.databaseId) | .[] | "\(.databaseId) \(.headBranch) \(.workflowName) \(.status) \(.conclusion)"' 2>/dev/null \
    || echo "gh-unavailable"
} | sort
