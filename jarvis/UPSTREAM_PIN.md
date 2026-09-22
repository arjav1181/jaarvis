# Upstream pin — W0 pin + W1 repair

- Upstream: `https://github.com/NousResearch/hermes-agent` (MIT license)
- W0 clone: shallow, `git clone --depth 1` at `9573f44ca5416022f5c0095580e47b5e23d56e71` (2026-09-20 `main` tip)
- Fork branch: `jarvis`
- Remotes:
  - `upstream` → `https://github.com/NousResearch/hermes-agent.git` (read-only mirror of upstream; never push here)
  - `origin` → `https://github.com/arjav1181/jaarvis` (our fork remote)
- W1 base: `upstream/main` @ `59f9ff8dbc75b9c4f07ae10174df730f7882a505`
  (replay parents the overlay onto this tip; W0 pin `9573f44c` verified
  ancestor via `git merge-base --is-ancestor`)
- Replayed overlay SHAs (on top of W1 base):
  - `5d939687c3` W0: fork pin + rename + soul + boot proof (6 files, `jarvis/` + `tests/jarvis/`)
  - `0c045da1e6` fix: pin test against shallow boundary after orphan-root push

Verify:

```bash
git rev-parse HEAD
git remote -v
git merge-base jarvis upstream/main   # must resolve (= W1 base tip)
```

## W1 repair procedure (orphan-root repair, W1 task 1)

W0 left origin's `jarvis` as an orphan root (GitHub rejects pushes bottoming
out at a shallow boundary; W0 forbade fetching full history). Repair:

1. `git fetch --unshallow upstream` (repo no longer shallow;
   `git rev-parse --is-shallow-repository` → `false`)
2. `git reset --hard upstream/main` on `jarvis`
   (backup ref `jarvis-pre-repair` kept locally until the repair verified)
3. Re-applied ONLY the overlay paths from the orphan commits
   (`git checkout <orphan-sha> -- jarvis tests/jarvis`) — no core file touched.
   Collision check first: `git ls-tree upstream/main jarvis tests/jarvis`
   returned empty (no upstream file at our overlay paths).
4. Committed replay (`git show --stat` per commit = only `jarvis/` + `tests/jarvis/`)
5. `git push --force-with-lease origin jarvis` (private repo, own branch)

Historical note: the W0-era "orphan-root push" workaround is superseded by
this repair; `git merge upstream/main` works from here on.

## W14 merge-train (2026-09-22, branch `w14-launch`)

- Synced `upstream/main` `59f9ff8dbc75b9c4f07ae10174df730f7882a505`
  → `f21e583211f783fa99ba4e1866cf6babc1d37b39`
  (`chore(desktop): remove the old MCP tab (#119083)`; 1587 commits,
  2455 files).
- Merge applied cleanly: zero conflicts (not even root README).
- Overlay-adjacent check: no upstream file at `jarvis/` or `tests/jarvis/`
  (zero collision); backend churn concentrated in `apps/desktop/*`,
  `website/*`, `hermes_cli/web_routers/*` — overlay API surfaces
  (`/auth/password-login`, `/api/auth/ws-ticket`, `/api/ws`,
  `/api/audio/*`) unchanged in contract.
- Telemetry audit: no new third-party tracker added in range
  (no `segment.io`/amplitude/mixpanel/posthog/ga/hotjar/sentry/datadog
  additions in `+` lines); `hermes_cli/observability/` untouched by the
  sync (pre-existing, consent-gated shared-metrics); overlay enables
  nothing (rig `config.yaml` carries no telemetry keys; overlay docs
  assert "no telemetry added").
- Post-merge: `git merge-base --is-ancestor upstream/main HEAD` → true;
  `tests/jarvis/` green-apart-from-known-worktree-artifacts (see W14
  launch checklist).
- Tags: none (owner tags releases).
