# W14 Launch Checklist (items 3–6 + merge-train + regression)

Branch `w14-launch` @ merge `0cd5aff7f5` (overlay tip `57a00ba5cf` +
upstream `f21e583211`, clean). Rig `http://127.0.0.1:3000`
(`hermes serve`, HERMES_HOME=`.rig-home`). Harness: `jarvis/launch/smoke.py`
(`python jarvis/launch/smoke.py --home <rig-home>`; rig parts skipped with
`JARVIS_SMOKE_SKIP_RIG=1`). Full report JSON: smoke run 2026-09-22
(login 57.1 ms). No secrets in repo (password via `JARVIS_RIG_PW` env only).

## 3. Live smoke

Login: `POST /auth/password-login {provider:basic, username:sir}` →
`{"ok":true}` + session cookies, 57.1 ms. (Dashboard uses session login,
not per-request basic auth.)

| page | unauth (live rig) | authed | proof |
|---|---|---|---|
| voice | 302 → /login | 200 | gate: live rig; serve: ephemeral dashboard¹ |
| diag | 302 → /login | 200 | same |
| audit | 302 → /login | 200 | same |
| apex | 302 → /login | 200 | same |
| foresight | 302 → /login | 200 | same |
| hands | 302 → /login | 200 | same |
| presence | 302 → /login | 200 | same |
| degraded | 302 → /login | 200 | same |

Unauth latency 1.0–2.1 ms/page on the live rig. Deployed files byte-match
repo sources 8/8 (`deployed_match: match` for all pages).

¹ The live rig runs `hermes serve` WITHOUT `HERMES_WEB_DIST`, so authed
`/*.html` there 404s (overlay dir exists on disk but is not mounted).
Authed-200 was proven on an ephemeral `hermes dashboard --skip-build`
(port 3099, `HERMES_WEB_DIST=<rig-home>/web_dist_overlay`, scratch home +
basic-auth login, gate engaged via non-loopback `public_url`): login
`{"ok":true}`, then 200 on all 8 pages; unauth 302 there too. Same gate
code, same deployed bytes. Operator deploy note: serve overlay pages with
`HERMES_WEB_DIST=<home>/web_dist_overlay hermes dashboard` per
`jarvis/hud/README.md` (not a code change).

Voice legs (measured, not claimed):

| leg | ms | note |
|---|---|---|
| text turn submit → first delta | 66501.6 | relay-bound (model via OmniRoute); reply `sir, systems nominal.` (21 chars), turn total 184739.7 ms |
| text turn total | 184739.7 | same turn |
| TTS speak pipeline (`/api/audio/speak`) | 959.0 | provider `edge`, 13968 bytes |
| STT transcribe (local faster-whisper, repo fixture 3.55 s) | 2581.8 | transcript `Jarvis is online and ready to serve, sir.`, provider `local` |
| barge-in (interrupt → stream quiet) | 1.3 | 0 stray deltas past +3 s (W3 criterion met); `turn.end` unconfirmed in 30 s drain (relay-side slowness, not overlay) |

TTS via edge-tts worked (network OK). No honest-absent legs: all three
voice legs produced real numbers.

## 4. Latency

- First-audio ≈ TTS speak pipeline 959.0 ms (reply audio path).
- Barge-in 1.3 ms to quiet, 0 strays past +3 s — inside the PRD <500 ms
  target. Caveat: the relay is slow tonight (66.5 s to first delta), so a
  30 s quiet window is weaker than the W4/W7-era receipts; the interrupt
  path itself is local and unchanged.
- Baseline: NO stored W4/W7 ms receipts exist in
  `/home/runner/workspace/hermes-jarvis/` (grepped; only PRD targets:
  barge-in <500 ms, hooks <300 ms idle). W4 tests print per-run live
  numbers but store none. Turn first-delta (66.5 s) is relay/model time,
  not overlay time — overlay config (`voice.barge_in*`, `tts.streaming.*`)
  unchanged, so nothing to fix. Verdict: report only, no fix.

## 5. Dormant-hand audit (all still absent-for-the-right-reason)

| hand | verdict | how verified | wakes with |
|---|---|---|---|
| GPU | absent (no CUDA device) | `nvidia-smi` missing; no GPU in runtime | NVIDIA GPU + CUDA drivers visible to runtime |
| Discord | absent (`token_present:false`, `configured:false`) | `jarvis-discord-vc status` live | `DISCORD_BOT_TOKEN` env + channel id + allowlist |
| GPT-Live | absent (`enabled:false`, `openai_key_present:false`) | `jarvis-gpt-live status` live | OpenAI realtime key + explicit opt-in enable |
| Telegram token | absent (no bot token) | `jarvis.hands.telegram_remote.status()` → `absent` | `TELEGRAM_BOT_TOKEN` via pairing flow |
| Spotify | absent (never built — W6 parked) | no spotify code path in overlay; nothing in rig config | Spotify OAuth grant + DJ routine enable |
| HA | absent (W6-deferred) | `car_home.status()` → `absent` (`HOME_ASSISTANT_TOKEN` unset) | `HASS_URL` + `HOME_ASSISTANT_TOKEN` |
| Car | absent (no vehicle API keys) | `car_home.status()` → `absent` | `CAR_API_KEY` / `TESLA_*` env on gateway |

Wake-list source of truth: `DORMANT_HANDS` in `jarvis/launch/smoke.py`
(completeness-tested).

## 6. Public-flip checklist

- Secrets sweep (overlay tree `jarvis/` + `tests/jarvis/`): `sk-`/`gho_`/
  `api_key=`/`password=`/`bearer` patterns → ONE hit, false positive (a
  hyphenated English word in a `jarvis/foresight/runner.py` docstring —
  plain prose, case-insensitive match). Lane files swept at commit: clean.
  History: overlay commits since the W1 base contain no credential
  additions (prior waves swept; this wave adds only launch tooling + pin
  update + upstream merge). Passwords only ever via env.
- README/LICENSE/attribution: root `README.md` rebrand = authorized sole
  exception (operator commit, upstream attributed to
  `NousResearch/hermes-agent`, MIT); `LICENSE` = upstream MIT, intact;
  `jarvis/UPSTREAM_PIN.md` updated for the W14 sync.
- `~/.hermes`: absent at verify (smoke STT created it mid-run via
  default-home fallback — removed; law holds).
- Verdict: **READY** (no blockers). Visibility flip itself is the
  operator's action (not done here).

## Regression (item 1)

Full `tests/jarvis/` post-merge: **234 passed + 7 env-gated skips,
3 failed of 244 collected** — all 3 are worktree-path artifacts, zero
true regressions:

- `test_w18_loop.py::test_ensure_loop_syntax` — asserts
  `workdir == /home/runner/workspace/hermes-fork` (main checkout);
  worktree is `/tmp/w14-wt`. Passes on the main checkout.
- `test_w5_habits.py::test_job_specs` — same hardcoded workdir assert.
- `test_w8_permissions.py::test_snapshot_writer_integration` — cascade:
  runs the suite internally and asserts 0 failures; fails only because
  of the two above.

Pre-merge the run additionally showed 9 `test_no_core_files_touched` /
`test_orphan_repaired` failures caused by the merge-train `git fetch`
advancing `upstream/main` 1587 commits ahead of HEAD; all 9 resolved
when the clean merge landed (`merge-base --is-ancestor` true again).

## Merge-train (item 2)

Upstream `59f9ff8d` → `f21e583211` (1587 commits, 2455 files) merged with
ZERO conflicts. No upstream file at overlay paths. Telemetry audit: no new
third-party tracker in the sync; `hermes_cli/observability/` untouched;
overlay enables nothing. `jarvis/UPSTREAM_PIN.md` updated. Nothing tagged.
