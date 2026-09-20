# Rename map — `hermes` → `jarvis` (W0)

Overlay-only rename. No repo-wide sed was run; upstream files are byte-identical
(`git status` shows only `jarvis/` + `tests/jarvis/` outside of the clone itself).

| Upstream (`hermes`) | Jarvis (W0) | Mechanism |
|---|---|---|
| `hermes` CLI entry (`hermes_cli.main:main`) | `jarvis/bin/jarvis` shim → `exec hermes "$@"` | Thin shell alias; `hermes` keeps working underneath |
| `~/.hermes` config home | `~/.jarvis` default home | `HERMES_HOME` env var (the supported key per `hermes_constants.py`: context override → `HERMES_HOME` → platform default). Shim sets `HERMES_HOME=${HERMES_HOME:-~/.jarvis}`; an explicit `HERMES_HOME` is always respected (tests use temp/isolated homes) |
| `~/.hermes/SOUL.md` (persona slot #1) | `jarvis/SOUL.jarvis.md` (source) → installed as `SOUL.md` in the active home | File copy into TEST home only in W0 |
| `agent.personalities` custom map | `jarvis/personalities.yml` (source stub: `jarvis`, `ultron`) → merged into TEST home `config.yaml` | Upstream config keys, no new schema |
| Skins under `~/.hermes/skins/` | W1+ (`jarvis-gold`, `ultron-crimson`); NOT in W0 | — |
| Wake/voice/gateway/cron | W2+; NOT in W0 | — |

## Implementation notes

- The shim is POSIX `sh`, `set -u`, no dependencies besides `hermes` on `PATH`
  (W0: `/home/runner/.venvs/jarvis-w0/bin`, symlinked as `<venv>/bin/jarvis` —
  environment setup, not a repo change).
- `jarvis --help` passes through to `hermes --help` (exit 0); verified in W0 proofs.
- W0 TEST profile home: `~/.jarvis-test` via explicit `HERMES_HOME`
  (isolated from BOTH the default `~/.hermes` profile and the future `~/.jarvis` default).
- Default `~/.hermes` profile is never created/touched in W0
  (it did not exist before W0; proven byte-identical-absent after).
- W0 side-effect note (reverted): an early `hermes --version` probe ran WITHOUT
  `HERMES_HOME` set and auto-created a `~/.hermes` skeleton (upstream-default
  `SOUL.md` + cache/update-check files only — verified identical to upstream
  default, no user data). It was removed with `rm -rf ~/.hermes` to restore the
  exact before-state (absent). Standing rule from W0 onward: EVERY
  `hermes`/`jarvis` invocation sets `HERMES_HOME` explicitly
  (TEST home for W0 proofs, `~/.jarvis` for real use).
