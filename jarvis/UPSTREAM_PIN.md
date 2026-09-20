# Upstream pin — W0

- Upstream: `https://github.com/NousResearch/hermes-agent` (MIT license)
- Clone mode: shallow, `git clone --depth 1` (full history is ~38k commits — do NOT full-clone)
- Pinned HEAD SHA: `9573f44ca5416022f5c0095580e47b5e23d56e71`
- Pinned on: 2026-09-20 (`main` branch tip at clone time)
- Fork branch: `jarvis`
- Remotes (W0 end-state):
  - `upstream` → `https://github.com/NousResearch/hermes-agent.git` (read-only mirror of upstream; never push here)
  - `origin` → `https://github.com/arjav1181/jaarvis` (our fork remote; set in W0 §6 step)

Verify:

```bash
git rev-parse HEAD
git remote -v
```

## W0 push note (orphan root)

`branch jarvis` on `origin` (jaarvis) is an **orphan root commit** snapshotting
this tree, NOT a continuation of upstream history. Reason: GitHub's unpack
rejects pushes whose history bottoms out at a shallow boundary
(`remote unpack failed ... did not receive expected object <parent-of-pin>`),
and W0 forbids fetching full history (~38k commits). Provenance is preserved:
the pin above + local branch `jarvis-shallow` (2-commit shallow chain:
`9573f44` + W0 overlay commit). Future merge-trains will reconcile with
upstream history at train time (W6), not by backfilling it here.
