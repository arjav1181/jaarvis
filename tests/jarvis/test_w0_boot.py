"""W0 boot tests — fork pin + rename + soul + default-profile safety.

Covers prompt.md W0 task 6:
  - rename-map files exist (jarvis/ overlay)
  - SOUL installed in the TEST profile only
  - persona config parses with the {jarvis, ultron} stub
  - default ~/.hermes profile untouched
  - `jarvis --help` works (renamed entry)

Isolation: every subprocess gets an explicit HERMES_HOME pointing at a tmp
dir, so the tests never create ~/.jarvis or ~/.hermes as a side effect.
Run with the W0 venv active: `python -m pytest tests/jarvis/test_w0_boot.py -v`
"""

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
JARVIS_DIR = REPO_ROOT / "jarvis"
TEST_HOME = Path(os.environ.get("JARVIS_TEST_HOME", str(Path.home() / ".jarvis-test")))


def test_rename_map_files_exist():
    for rel in ("UPSTREAM_PIN.md", "RENAME_MAP.md", "bin/jarvis",
                "SOUL.jarvis.md", "personalities.yml"):
        assert (JARVIS_DIR / rel).is_file(), f"missing overlay file: jarvis/{rel}"


def test_upstream_pin_matches_checkout():
    pin = (JARVIS_DIR / "UPSTREAM_PIN.md").read_text()
    assert "NousResearch/hermes-agent" in pin
    m = re.search(r"\b[0-9a-f]{40}\b", pin)
    assert m, "UPSTREAM_PIN.md must record the full 40-char HEAD SHA"
    # Post-W1-repair the history is unshallowed: the pin must be an ancestor
    # of the checkout (it was the W0 shallow boundary / upstream tip).
    r = subprocess.run(["git", "merge-base", "--is-ancestor", m.group(0), "HEAD"],
                       cwd=REPO_ROOT, capture_output=True)
    assert r.returncode == 0, "pinned SHA must be an ancestor of the checkout"


def test_shim_is_executable_passthrough():
    shim = JARVIS_DIR / "bin" / "jarvis"
    assert shim.stat().st_mode & stat.S_IXUSR, "jarvis/bin/jarvis must be executable"
    text = shim.read_text()
    assert "HERMES_HOME" in text and ".jarvis" in text
    assert "exec hermes" in text, "shim must passthrough to hermes (kept working underneath)"


def test_soul_installed_in_test_profile_only():
    installed = TEST_HOME / "SOUL.md"
    assert installed.is_file(), f"SOUL.md not installed in TEST profile {TEST_HOME}"
    source = (JARVIS_DIR / "SOUL.jarvis.md").read_text()
    assert installed.read_text() == source, "TEST SOUL.md must equal jarvis/SOUL.jarvis.md"
    assert "Jarvis" in source


def test_persona_config_parses():
    cfg_path = TEST_HOME / "config.yaml"
    assert cfg_path.is_file(), f"config.yaml missing in TEST profile {TEST_HOME}"
    cfg = yaml.safe_load(cfg_path.read_text())
    personas = (cfg.get("agent") or {}).get("personalities") or {}
    assert set(("jarvis", "ultron")) <= set(personas), "agent.personalities needs jarvis+ultron"
    assert personas["jarvis"].strip(), "jarvis persona must be non-empty"
    # W1: ultron is a real entry (the W0 TODO stub is superseded; see test_w1_souls).
    assert "TODO" not in personas["ultron"], "ultron stub must be gone since W1"


def test_default_profile_untouched():
    default_home = Path.home() / ".hermes"
    assert not default_home.exists(), (
        f"default profile {default_home} must not exist in W0 "
        "(TEST profile is the only home W0 may touch)")


def test_jarvis_help_entry_works(tmp_path):
    hermes = shutil.which("hermes")
    assert hermes, "hermes entrypoint must be on PATH (activate the W0 venv)"
    env = dict(os.environ, HERMES_HOME=str(tmp_path / "probe-home"),
               PATH=os.pathsep.join([str(Path(hermes).parent),
                                      os.environ.get("PATH", "")]))
    proc = subprocess.run([str(JARVIS_DIR / "bin" / "jarvis"), "--help"],
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "chat" in proc.stdout, "jarvis --help must list the chat command"
