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
