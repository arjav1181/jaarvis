"""What-if suite schema + safe compute evaluator (W10, HTR-FORE1 "run the numbers").

A suite file is JSON: {name, scenarios[{id, kind, ...}]} with three kinds:

- compute: deterministic numbers, run locally NOW, timed, zero tokens.
  {inputs: {name: number}, expr: "a * 2 + b"} — evaluated under an AST
  whitelist (arithmetic only: no calls, no attributes, no imports). This is
  the batch runner for the numeric half of foresight.
- predict: an authored claim filed to the ledger (idempotent per
  suite/scenario source — reruns never double-file).
- delegate: a judgment scenario for the agent loop. Collected into ONE
  upstream-compatible `delegate_task` tasks-batch payload (tools/
  delegate_tool_tasks.py: goal/tasks shapes, batch quality gate mirrored
  below). Plan-only: execution stays in-agent, the CLI spends nothing.

Suite files are operator-authored; the runner never invents predictions.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

KINDS = ("compute", "predict", "delegate")

# Narrow template-marker detector, mirroring upstream tools/
# delegate_tool_tasks.py (_TEMPLATE_MARKER_RE): subagents cannot resolve
# placeholders, so suites carrying them are refused before any spend.
_TEMPLATE_MARKER_RE = re.compile(
    r"<[A-Za-z][A-Za-z0-9]*(?:[ _-][A-Za-z0-9]+)+>|\{[A-Za-z][A-Za-z0-9]*(?:[ _-][A-Za-z0-9]+)+\}"
)
_MIN_BATCH_GOAL_LEN = 10

_EVAL_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                 ast.Name, ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div,
                 ast.Mod, ast.Pow, ast.UAdd, ast.USub)


def compute_expr(expr: str, inputs: Dict[str, Any]) -> float:
    """Evaluate arithmetic `expr` over numeric `inputs`. Raises ValueError."""
    if not isinstance(expr, str) or not expr.strip() or len(expr) > 500:
        raise ValueError("expr must be a non-empty string (<=500 chars)")
    if not isinstance(inputs, dict) or not inputs:
        raise ValueError("inputs must be a non-empty object")
    vals: Dict[str, float] = {}
    for k, v in inputs.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ValueError(f"input {k!r} must be a number")
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):
            raise ValueError(f"input {k!r} must be finite")
        vals[k] = f
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"bad expr: {e}")
    for node in ast.walk(tree):
        if not isinstance(node, _EVAL_ALLOWED):
            raise ValueError(f"expr forbids {type(node).__name__} (arithmetic only)")
        if isinstance(node, ast.Name) and node.id not in vals:
            raise ValueError(f"unknown input {node.id!r}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("expr constants must be numbers")
    out = eval(compile(tree, "<foresight>", "eval"), {"__builtins__": {}}, vals)  # noqa: S307
    if not isinstance(out, (int, float)) or out != out or abs(out) == float("inf"):
        raise ValueError("expr did not produce a finite number")
    return float(out)


def validate_delegate_tasks(tasks: List[Dict[str, Any]]) -> str | None:
    """Mirror of the upstream batch gate (tools/delegate_tool_tasks.py):
    every task needs a real goal; multi-task fan-outs need >=10-char goals
    and no unexpanded template markers. Returns error or None."""
    for i, t in enumerate(tasks):
        goal = str(t.get("goal", "")).strip()
        if not goal:
            return f"delegate scenario {i} is missing a goal"
        if _TEMPLATE_MARKER_RE.search(goal):
            return (f"delegate scenario {i} carries an unexpanded template "
                    f"marker — substitute the real value first")
        if len(tasks) >= 2 and len(goal) < _MIN_BATCH_GOAL_LEN:
            return (f"delegate scenario {i} goal is too short ({goal!r}) — "
                    f"write >= {_MIN_BATCH_GOAL_LEN} chars")
    return None


def load_suite(path: Path | str) -> Tuple[Dict[str, Any] | None, List[str]]:
    """(suite, []) for a valid suite file, (None, errors) otherwise."""
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return None, [f"suite unreadable: {e}"]
    errors: List[str] = []
    if not isinstance(raw, dict):
        return None, ["suite must be a JSON object"]
    if not str(raw.get("name", "")).strip():
        errors.append("suite needs a name")
    scens = raw.get("scenarios")
    if not isinstance(scens, list) or not scens:
        errors.append("suite needs a non-empty scenarios list")
        return None, errors
    seen = set()
    for i, s in enumerate(scens):
        if not isinstance(s, dict):
            errors.append(f"scenario {i} must be an object")
            continue
        sid = str(s.get("id", "")).strip()
        if not sid or sid in seen:
            errors.append(f"scenario {i} needs a unique id")
            continue
        seen.add(sid)
        kind = s.get("kind")
        if kind not in KINDS:
            errors.append(f"scenario {sid!r}: unknown kind {kind!r}")
            continue
        if kind == "compute":
            if not isinstance(s.get("inputs"), dict) or not s.get("inputs"):
                errors.append(f"scenario {sid!r}: compute needs inputs")
            if not str(s.get("expr", "")).strip():
                errors.append(f"scenario {sid!r}: compute needs expr")
        elif kind == "predict":
            for f in ("question", "predicted", "horizon"):
                if not str(s.get(f, "")).strip():
                    errors.append(f"scenario {sid!r}: predict needs {f}")
            try:
                c = float(s.get("confidence", "x"))
                if not 0.0 <= c <= 1.0:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"scenario {sid!r}: confidence must be 0..1")
        else:  # delegate
            if not str(s.get("goal", "")).strip():
                errors.append(f"scenario {sid!r}: delegate needs a goal")
    if errors:
        return None, errors
    return {"name": str(raw["name"]).strip(), "scenarios": scens}, []
