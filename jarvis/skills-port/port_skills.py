#!/usr/bin/env python3
"""Port frozen Node skills into Hermes-agent skill layout (W5, repeatable).

Reads the FROZEN legacy pack (read-only input, never modified):
    <src>/skills-src/<name>/SKILL.md      frontmatter: name, tier, trigger
    <src>/commands-src/brief.md           -> morning-brief skill

Writes Hermes-layout skills to <out>/<name>/SKILL.md plus <out>/manifest.json.

Translation (deterministic, no timestamps, sorted keys):
  - body kept VERBATIM (frozen behavior preserved byte-for-byte)
  - frontmatter translated to Hermes keys (name, description, version, author,
    license, platforms, metadata.hermes.tags/related_skills)
  - frozen keys preserved verbatim as x-jarvis-tier / x-jarvis-trigger /
    x-jarvis-source so tier and trigger survive the port provably

Usage:
    python3 port_skills.py [--src /home/runner/workspace/jarvis]
                           [--out jarvis/skills] [--manifest manifest.json]

Exit non-zero on any validation failure. Run twice -> identical bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Declarative port list: (source relative path, skill name, tier, trigger).
# Tier/trigger defaults come from the frozen frontmatter; commands-src entries
# carry them here because command files have no frontmatter.
SOURCES: list[tuple[str, str, str | None, str | None]] = [
    ("skills-src/explain-error/SKILL.md", "explain-error", None, None),
    ("skills-src/ship-pr/SKILL.md", "ship-pr", None, None),
    ("skills-src/test-runner/SKILL.md", "test-runner", None, None),
    ("commands-src/brief.md", "morning-brief", "L1", "brief me"),
]

VERSION = "1.0.0"
AUTHOR = "Jarvis pack (ported from frozen Node skills-src)"
LICENSE = "MIT"
PLATFORMS = ["linux", "macos"]


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a flat `key: value` frontmatter block from the body."""
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter fence")
    end = text.index("\n---", 4)
    raw = text[4:end].strip("\n")
    body = text[end + len("\n---"):].lstrip("\n")
    fm: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if not key or key in fm:
            raise ValueError(f"bad frontmatter line: {line!r}")
        fm[key] = val
    return fm, body


def render_skill(name: str, tier: str, trigger: str, source: str, body: str) -> str:
    desc = f"{trigger} (Jarvis pack skill, ported)."
    tags = ["jarvis", "ported", tier.lower()]
    lines = [
        "---",
        f"name: {name}",
        f'description: "{desc}"',
        f"version: {VERSION}",
        f"author: {AUTHOR}",
        f"license: {LICENSE}",
        f"platforms: [{', '.join(PLATFORMS)}]",
        f"x-jarvis-tier: {tier}",
        f'x-jarvis-trigger: "{trigger}"',
        f"x-jarvis-source: {source}",
        "metadata:",
        "  hermes:",
        f"    tags: [{', '.join(tags)}]",
        "    related_skills: []",
        "---",
        body.rstrip("\n") + "\n",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/home/runner/workspace/jarvis")
    ap.add_argument("--out", default="jarvis/skills")
    ap.add_argument("--manifest", default="manifest.json")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    if not src.is_dir():
        print(f"port_skills: src not found: {src}", file=sys.stderr)
        return 2

    entries: list[dict[str, str]] = []
    for rel, name, tier_d, trigger_d in SOURCES:
        f = src / rel
        if not f.is_file():
            print(f"port_skills: missing frozen source: {f}", file=sys.stderr)
            return 2
        text = f.read_text(encoding="utf-8")
        try:
            fm, body = split_frontmatter(text)
        except ValueError as exc:
            # commands-src files have no frontmatter: whole file is the body
            if rel.startswith("commands-src/"):
                fm, body = {}, text
            else:
                print(f"port_skills: {rel}: {exc}", file=sys.stderr)
                return 2
        tier = fm.get("tier", tier_d or "")
        trigger = fm.get("trigger", trigger_d or "")
        if not tier or not trigger:
            print(f"port_skills: {rel}: tier/trigger unresolved", file=sys.stderr)
            return 2
        if fm.get("name", name) != name:
            print(f"port_skills: {rel}: name mismatch", file=sys.stderr)
            return 2
        if "/home/" in body or "/root/" in body:
            print(f"port_skills: {rel}: absolute home path in body", file=sys.stderr)
            return 2
        rendered = render_skill(name, tier, trigger, rel, body)
        dest = out / name / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
        entries.append({
            "name": name,
            "source": rel,
            "tier": tier,
            "trigger": trigger,
            "sha256": hashlib.sha256(rendered.encode()).hexdigest(),
        })

    entries.sort(key=lambda e: e["name"])
    manifest = {"generated_by": "jarvis/skills-port/port_skills.py",
                "src_root": str(src), "skills": entries}
    (out / args.manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                     encoding="utf-8")
    print(f"port_skills: {len(entries)} skills -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
