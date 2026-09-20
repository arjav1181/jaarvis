# JARVIS — Technical Requirements Document (TRD)
**v0.3 PACK | 2026-09-19 | Companions: PRD.md, ARCHITECTURE.md, BUILD_PLAN.md, CONNECTORS.md**

MUST/SHOULD/MAY. IDs `JTR-xxx`. Pack-only: no daemon, no model calls, no hosted backend. MIT.

## 1. Install contract (bless pack, 3 engines)

- JTR-INST1 (MUST): `bless` idempotent; detects {claude, opencode, codex} × {present, missing}; renders pack into each present harness's native locations; skips missing with hint. `unbless` removes only `managed-by-jarvis` keys; `doctor` verifies clean.
- JTR-INST2 (MUST): Home `~/.jarvis/{skills-src/,commands-src/,hooks/,bin/,pack/connectors/,memory/{journal/,vectors.db},creds/(0600),personas/,routines/,hud/,config.yml}`. Harness dirs hold RENDERED copies only — source of truth is `~/.jarvis/`, so `bless` re-renders upgrades losslessly and never clobbers user files (3-way merge, backup).
- JTR-INST3 (MUST): `doctor` checks: runtimes, mic/speaker probe, each harness (paths writable, hooks registered, MCP reachable), memory writable, voice models present, per-connector status table. Non-zero exit + fix hints.
- JTR-INST4 (MUST): Offline-tolerant except model/OAuth downloads (resumable + checksummed). `connect --wave N` / `connect <name>` / `connect list` manage waves.

## 2. Engine adapters (renderers, not runtimes)

- JTR-ENG1 (MUST): `adapters/{claude,opencode,codex}.ts` implement `detect(), renderPack(), removePack(), verify()` mapping shared sources → native paths (skill dirs, command files, hook configs, MCP config blocks). Pin exact paths per harness version in `adapters/paths.yml`.
- JTR-ENG2 (MUST): Fixtures per engine version (`fixtures/{claude,opencode,codex}/`); CI renders + verifies against fixture homes; unknown versions warn + render best-effort, never fail the harness.
- JTR-ENG3 (MUST): Capability matrix doc'd + probed: hooks? (pre/post tool, session start/end), MCP? slash-commands? headless run? Gaps get fallback rows (e.g. no pre-tool hook → L2 double-ask lives in skill text).
- JTR-ENG4 (SHOULD): `jarvis engine use <x>` sets preferred harness for routines/headless runs; interactive sessions always respect whichever harness the user opened.

## 3. Voice (scripts + hooks, no daemon)

- JTR-VOX1 (MUST): `jarvis-listen` (wake "Hey Jarvis" + VAD + STT local faster-whisper + PTT `--ptt` fallback) prints transcribed text for piping into a harness session; `jarvis-speak "<text>"` / response-hook pipes answers to local TTS (Piper, jarvis|ultron voices).
- JTR-VOX2 (MUST): Barge-in: keypress/VAD event kills `jarvis-speak` <500ms. `voice.enabled` toggle stops listeners. Cloud STT/TTS only when `voice.cloud=true`, per-call warn log.
- JTR-VOX3 (MUST): Fixture wavs in `fixtures/audio/`; CI tests STT→text→hook without any mic.
- JTR-VOX4 (SHOULD): Spoken L2 confirm: hook speaks the danger + waits for "yes" token before the tool proceeds (where harness hook supports pause).

## 4. Skills, commands, hooks, scripts

- JTR-SKILL1 (MUST): Single-source skills `skills-src/<name>/SKILL.md` (+ optional `script.sh`); renderer adapts frontmatter per engine. ~15 curated W1: `fix-flake, ship-pr, morning-brief, explain-error, test-runner, scaffold-connector, …`.
- JTR-CMD1 (MUST): Slash-commands `/jarvis, /ultron, /brief, /overnight, /remember, /forget, /connect, /doctor` rendered per engine's command format.
- JTR-HOOK1 (MUST): Hooks shipped: `session-start` (persona overlay + memory recall inject), `pre-tool-use` (L2 confirm gate), `post-response` (TTS emit + memory capture draft), `session-end` (memory store, redacted). Each hook MUST be <300ms when idle, MUST fail-open (exit 0, log, never block coding).
- JTR-HOOK2 (MUST): L2 gate list (`shared/destructive.yml`: push --force, deploys, migrates, refunds, publishes, rm -rf, …) enforced in hook where supported + mirrored as skill instruction (defense in depth).
- JTR-SCRIPT1 (MUST): `bin/` scripts: `listen, speak, remember, forget, search-memory, hud, routine-run, connect, mcp-{add,list,test}, doctor, stop`. All `--help`, all JSON-capable (`--json`).

## 5. Connectors (MCPs + scripts + skills)

- JTR-CONN1 (MUST): Connector bundle `pack/connectors/<id>/{connector.yml,tools.json,SKILL.md,SCOPES.md,tests/}` declares: wave, tier per tool (L0/L1/L2), MCP server cmd + auth kind, skill text, fixtures.
- JTR-CONN2 (MUST): `connect <id>` performs OAuth/key flow, writes creds to vault + MCP block into each present harness config (namespaced, marked). `disconnect` removes blocks + deletes local creds + prints remote-revoke link.
- JTR-CONN3 (MUST): W1 ships connected-local (no OAuth): git/gh/tests/scaffolds/fetch/browser/memory. W2+ each have stub fixtures so CI passes with zero accounts.
- JTR-MCP1 (MUST): `mcp add/list/test`; broken MCP = disabled + doctor hint, harness session unaffected.

## 6. Credentials vault

- JTR-CRED1 (MUST): `creds/` 0600 or OS keychain; minimal scopes per `SCOPES.md`; never in logs/prompts/memory (hook redaction pre-write); `disconnect` purges local.
- JTR-CRED2 (MUST): Redaction list `shared/redact.yml` (50+ canary-tested patterns) applied by memory hooks + `hud` log renderer.

## 7. Memory (hooks + scripts, shared across engines)

- JTR-MEM1 (MUST): `memory/journal/*.md` (human truth) + `vectors.db` (P0: SQLite FTS keyword index fallback; sqlite-vec 384-d local embeddings deferred). `session-end` hook drafts {fact, source, repo}; `remember/forget/search` CLIs manage; `session-start` hook injects top-5 + recent-3 (token-capped, shows "5 memories used").
- JTR-MEM2 (MUST): Connector facts tagged (`source: gmail|gh|…`); retention 180d unless pinned; `export --to second-brain` writes `second-brain/raw/jarvis-*.md`.

## 8. HUD (file-tail viewer, no backend)

- JTR-HUD1 (MUST): `jarvis hud` serves static `hud/` on 127.0.0.1:4040 reading transcript tails + journal + routine logs + connector status files. SSE optional via file-watch; every line maps to a real file (no theater).
- JTR-HUD2 (MUST): Pages: live, tasks/receipts, chat-link (deep-links into harnesses, not a chat backend), connectors, routines, settings (edits `config.yml`), kill switch (`stop --now` kills listeners/timers + writes `paused` flag hooks honor).
- JTR-API1 (MUST): `POST /api/voice/utterance` (audio → faster-whisper if present else honest `{engine:"no-stt"}`), `POST /api/speak` (text → Piper jarvis|ultron wav bytes else honest `{spoken:false}`), `GET /api/chat` (multi-turn sessions, persona + recall injected + shown, token-capped, REAL headless harness `opencode → claude → codex`, absent → `{error:"no-harness"}`), `GET /api/events` SSE (snapshot + heartbeat, reconnect-safe), `POST /api/stop` (paused flag + BARGE/STOP log line). Audio bodies capped at 5MB; mic audio deleted after STT unless `transcripts.store_audio: true`. No fixture fallbacks in runtime paths.
- JTR-AUTH1 (MUST, P2): loopback default token-free; `--lan` binds off-loopback ONLY with `config.api_token` (generated once, shown once, file 0600); all `/api/*` → 401 without it (Bearer header or `?token=`, the latter for SSE). Caddy+TLS recipe + Tailscale guide documented; zero open ports by default.
- JTR-LAT1 (MUST, P2): utterance → spoken-reply start <5s on loopback (batch pipeline; no streaming STT/TTS in P2). Measured on stub pipeline here; re-measure with local engines on target hardware.
- JTR-RUN1 (MUST): headless harness runs execute ONLY L0/L1 tools: cwd-pinned to a scratch dir (default `/tmp/jarvis-run`, `JARVIS_RUN_DIR` override), hard timeout (default 120s, `JARVIS_RUN_TIMEOUT` override), reply capped at 2000 chars. ANY L2-class act (patterns in `shared/destructive.yml`) is REFUSED pre-spawn with a `needs-approval` receipt entry — no pre-approval windows, no exceptions.
- JTR-RUN2 (MUST): every headless run appends a receipt `{ts, kind, session, engine, result, ms}` to `memory/receipts/receipts.json`; STT/TTS report millisecond timings. No harness CLI on PATH → honest `{error:"no-harness"}`.
- JTR-VOX5 (MUST): voices install via `install/voice-engines.sh` (pinned `faster-whisper` + `piper-tts`, one base-int8 STT model, two Piper voices, checksums in `versions.lock`, self-test prints `VOICE-OK`) into `~/.jarvis/voices/` (`JARVIS_VOICES` override). Absent engines → honest `{engine:"no-stt"}` / `{spoken:false}`; fixture audio NEVER substitutes in runtime paths.

## 9. Routines (cron + headless harness runs)

- JTR-ROUT1 (MUST): `routine add/list/run/rm`; triggers cron/interval/manual/voice; runner invokes preferred harness headless with the routine skill; L2 steps confirm per policy (pre-approval windows default OFF).
- JTR-ROUT2 (MUST): Built-ins: `morning-brief, overnight-worker, ci-watchdog, inbox-triage(drafts-only)`. Missed runs logged, never silent; all killable.
- JTR-ROUT3 (MUST): Scenes engine: named chains in `scenes/*.yml` (`good-morning, focus-mode, ship-it, movie-night, shutdown`); `scene <name>` runs the chain under the same L0–L2 gates.
- JTR-SENSE1 (SHOULD, W3–W4): Senses are explicit-only (screenshot/cam/mic-record never ambient); meeting audio stored 7d default then pruned unless pinned.
- JTR-MANS1 (MUST, W5): Mansion wave default OFF (`mansion.enabled=false`); LAN-only endpoints; actuators L2-confirmable; `doctor` shows mansion status separately.
- JTR-META1 (MUST, W6): `pack-sync` uses the user's own git remote (URL in config, never a Jarvis cloud); `pack-update` re-renders + prints changelog; `dry-run` flag narrates without executing (asserted in tests: zero tool calls).
- JTR-META2 (SHOULD): `jarvis-wrapped` builds weekly digest from receipts + memory (local render, shareable PNG card only on explicit export).

## 10. NFRs + testing

Perf: hooks <300ms idle · recall inject <150ms @10k · bless <10min · `hud` TTFB <200ms local. Reliability: fail-open hooks, backups for every render + file patch, `unbless` restores. Privacy: loopback-only, cloud voices opt-in, no telemetry.
Tests: adapter render matrix (3 engines × fixtures) · hook fail-open suite · redaction canaries · L2-gate matrix (3 modes × destructive list) · mcp bad-server resilience · golden voice-to-code + golden brief on stubbed connectors · bless/unbless timer. Coverage ≥80% on hooks/redaction/renderers.

## 11. TR ↔ phases

P0 bless render 3 engines · P1 voice scripts · P2 hud · P3 memory hooks · P4 skills+modes+W1 · P5 W2+routines · P6 W3 (+senses/devops) · P7 W4+MCP (+life) · P8 W5 mansion + W6 meta · P9 viral ship. (BUILD_PLAN.)
