"""W18 loop CLI: ``python3 -m jarvis.loop [options]``.

Inputs are files the operator pastes from real surfaces (never fabricated):

- --pytest-log PATH ... pytest -rf output (``hermes test`` / pytest text)
- --cron-runs PATH .... JSON list or JSONL of ``hermes cron history`` rows
- --audit PATH ........ JSONL permission-audit rows
- --usage PATH ........ JSON from ``hermes curator usage`` ({skill: {...}})
- --demo .............. synthetic preview week (labelled as such)
- --live .............. dispatch kanban creates (also needs JARVIS_LOOP_LIVE=1)

Default is dry-run: prints the weekly report, files it under
<HERMES_HOME>/jarvis/loop/reports/, changes nothing else.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .run import demo_inputs, run


def _load(path: str | None):
    if not path:
        return None
    text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except ValueError:
        return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jarvis.loop")
    ap.add_argument("--pytest-log", default=None)
    ap.add_argument("--cron-runs", default=None)
    ap.add_argument("--audit", default=None)
    ap.add_argument("--usage", default=None)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)

    kw = {"live": args.live}
    if args.demo:
        kw.update(demo_inputs())
    else:
        if args.pytest_log:
            kw["pytest_text"] = Path(args.pytest_log).read_text(encoding="utf-8")
        for flag, name in (("cron_records", args.cron_runs),
                           ("audit_rows", args.audit),
                           ("usage", args.usage)):
            if name:
                kw[flag] = _load(name)
    receipt = run(**kw)
    if not receipt.get("ok"):
        print(f"loop refused: {receipt['reason']} ({receipt.get('hint', '')})")
        return 2
    print(f"mode={receipt['mode']} found={receipt['total']} "
          f"cards={len(receipt['cards'])} trims={len(receipt['trims'])}")
    print(f"report: {receipt['report']['md']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
