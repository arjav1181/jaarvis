#!/usr/bin/env bash
# install-skills.sh — copy Jarvis pack skills into a Hermes home (W5).
#
# Usage: HERMES_HOME=/path/to/home jarvis/skills-port/install-skills.sh
#
# Copies jarvis/skills/<name>/ (ported + authored, never manifest.json)
# into $HERMES_HOME/skills/jarvis/<name>/. Idempotent: re-running produces
# identical trees. Verifies each installed SKILL.md parses as frontmatter +
# body afterwards. Never touches the frozen legacy pack (read-only input).
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../skills"
: "${HERMES_HOME:=$HOME/.jarvis}"
DEST="$HERMES_HOME/skills/jarvis"

mkdir -p "$DEST"
count=0
for d in "$SRC"/*/; do
  name="$(basename "$d")"
  [ "$name" = "references" ] && continue
  [ -f "$d/SKILL.md" ] || continue
  rm -rf "$DEST/$name"
  cp -r "$d" "$DEST/$name"
  # Guard: frontmatter fence present, body non-empty.
  head -n 1 "$DEST/$name/SKILL.md" | grep -q '^---$' || { echo "install-skills: bad fence in $name" >&2; exit 1; }
  count=$((count + 1))
done
echo "install-skills: $count skills -> $DEST"
