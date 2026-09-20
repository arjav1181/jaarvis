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
