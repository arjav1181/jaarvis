#!/usr/bin/env bash
# ensure-curator.sh — curator ON with Jarvis skills pinned (W5).
#
# Usage: HERMES_HOME=/path/to/home jarvis/curator/ensure-curator.sh
#
# 1. Sets curator.enabled=true (standing rule: curator ON).
# 2. For each skill in pins.txt: `hermes curator adopt` (hands unmanaged
#    skills over; no-op if already managed), then `hermes curator pin`
#    (hard-fences against auto-archival and skill_manage).
# 3. Prints `hermes curator status` as proof. Never runs a mutating review
#    pass (proof runs use --dry-run explicitly, by hand).
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
: "${HERMES_HOME:=$HOME/.jarvis}"
export HERMES_HOME

hermes config set curator.enabled true
echo "ensure-curator: enabled=$(hermes config get curator.enabled)"

while IFS= read -r skill || [ -n "$skill" ]; do
  case "$skill" in ""|\#*) continue ;; esac
  if ! hermes curator adopt "$skill" >/dev/null 2>&1; then
    echo "ensure-curator: adopt $skill: already managed or refused (see below)"
    hermes curator adopt "$skill" 2>&1 | head -n 2
  fi
  hermes curator pin "$skill" 2>&1 | head -n 2
done < "$HERE/pins.txt"

echo "=== curator status ==="
hermes curator status 2>&1 | head -n 30
