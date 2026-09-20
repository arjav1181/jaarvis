# JARVIS — Architecture (wrapper, not harness)
**v0.3 PACK | 2026-09-19 | Companions: PRD.md, TRD.md, BUILD_PLAN.md, CONNECTORS.md**

One sentence: **Jarvis is a source pack rendered into three harnesses.** The harnesses (Claude Code / OpenCode / Codex) own the model, tool loop, and sandbox. We own the *transformation*: skills, commands, hooks, scripts, MCPs, personas, routines, memory files, HUD viewer. No daemon, no model calls, no backend.

## 1. Big picture

```
                    ┌─── ~/.jarvis/ (SOURCE OF TRUTH) ────┐
                    │ skills-src/ commands-src/ hooks/    │
                    │ bin/ personas/ routines/ memory/    │
                    │ creds/ pack/connectors/ hud/        │
                    └──────┬──────────────┬──────────────┬┘
                     render│          render│         render│  (adapters/, marked keys)
                          ▼                ▼               ▼
                   Claude Code          OpenCode          Codex
                   (native skill/       (native equiv.)   (native equiv.)
                    cmd/hook/MCP)
                          │                │               │
                          └────────┬───────┴───────┬───────┘
                                   ▼               ▼
                          memory/journal + vectors.db (shared by all three)
                          HUD tail-viewer (reads transcripts, no backend)
```

Voice path (scripts, no daemon): `mic → jarvis-listen (wake+VAD+STT) → text → harness session → response hook → jarvis-speak (TTS) → speakers`. PTT bypasses wake. Barge-in kills `jarvis-speak`.

## 2. Repo layout (single MIT repo = the pack factory)

```
jarvis/
 install/jarvis.sh              # bless / unbless / connect --wave
 adapters/{claude,opencode,codex}.ts + paths.yml   # renderers
 skills-src/<name>/SKILL.md     # single-source skills (~15 W1 + waves)
 commands-src/*.md              # /jarvis /ultron /brief /overnight /remember /doctor …
 hooks/{session-start,pre-tool-use,post-response,session-end}.sh
 bin/{listen,speak,remember,forget,search-memory,hud,routine-run,connect,mcp,doctor,stop}
 personas/{jarvis,ultron}.md
 routines/*.yml                 # morning-brief, overnight-worker, ci-watchdog, inbox-triage
 pack/connectors/<id>/{connector.yml,tools.json,SKILL.md,SCOPES.md,tests/}
 memory/ (runtime; journal/ + vectors.db created on bless)
 hud/ (static viewer)
 shared/{destructive.yml,redact.yml,tiers.yml}
 fixtures/{audio,claude,opencode,codex,connectors-stubs}/
```

Install renders `~/.jarvis/` home, then per-engine copies. Upgrades re-render; user files merged, never clobbered.

## 3. Per-engine matrix (pinned in `adapters/paths.yml`, probed by doctor)

| Capability | Claude Code | OpenCode | Codex |
|---|---|---|---|
| Skills | skill dirs | equivalent | equivalent |
| Slash-commands | commands | commands | commands |
| Session-start hook (persona + recall inject) | hook | equiv. | equiv./fallback |
| Pre-tool-use hook (L2 confirm) | hook | equiv. | equiv./skill-text fallback |
| Post-response hook (TTS + memory draft) | hook | equiv. | equiv./fallback |
| MCP servers (connectors) | mcp config | mcp config | mcp config |
| Headless run (routines) | headless cmd | headless cmd | headless cmd |

Rule: gaps get documented fallbacks (skill-text double-ask, polling instead of hooks). Pack degrades to skills-only on unknown versions — never breaks a harness.

## 4. Request path (example: "Hey Jarvis, brief me")

```
"brief me" (voice→STT text, or typed) → harness session starts
→ session-start hook: persona (jarvis|ultron) + memory top-5 injected
→ morning-brief skill: gmail/calendar/gh/CI via MCPs + scripts
→ pre-tool-use hook pauses any L2 (send/post/merge) for yes
→ post-response hook: jarvis-speak + memory draft → session-end stores (redacted)
→ HUD tails the transcript; routine log + receipt saved
```

Modes = persona overlay + hook-gate profile + TTS voice. Sandbox stays the harness's; our L2 list is enforced hook-first, skill-text-second.

## 5. Memory design (shared files, all engines)

`journal/*.md` (human-readable truth) + `vectors.db` (sqlite-vec, 384-d local embeddings, redact-then-embed). Writers: session-end hook + `remember`. Readers: session-start hook (top-5 + recent-3, token-capped). Managers: `forget`, `search-memory`. Export: `second-brain/raw/jarvis-*.md`. Retention 180d unless pinned.

## 6. HUD + browser-voice design (P2)

One homelab server (`bin/hud`, extended — never a second server) serves every device.
Default `127.0.0.1:4040` token-free; `--lan` binds `0.0.0.0` with mandatory
`config.api_token` (401 on `/api/*` without it; page stays public with a token field).

```
phone/laptop/desktop browser ──HTTPS (Caddy, Tailscale-first)──▶ bin/hud ─┬─ hud/ static page
  mic ─MediaRecorder(webm)─▶ POST /api/voice/utterance ─▶ faster-whisper │  (thread, VU, wake,
  ◀ wav bytes ─ POST /api/speak ◀── Piper (jarvis|ultron voices) ────────┤   themes, kill)
  ◀ thread ── GET /api/chat ──▶ REAL harness headless ───────────────────┤
        (opencode run --dir SCRATCH, else claude -p, else codex exec;      │
         persona + recall + thread injected; L2 refused pre-spawn)        │
  ◀ pushes ── GET /api/events (SSE: transcript/receipts/alerts) ─────────┘
  Voices: install/voice-engines.sh → ~/.jarvis/voices/ (venv + base.en + 2 Piper voices).
  Missing engine/CLI = honest {spoken:false} / {text:"",engine:"no-stt"} /
  {error:"no-harness"}, never fake success. No fixtures in runtime paths.
```

Mic audio is STT-processed then deleted unless `transcripts.store_audio: true`.
Chat turns journal via `remember` (redacted); recall injected + counted ("N memories used").
Kill = `POST /api/stop` → listeners/timers stop + `paused` flag hooks check.
Telegram (W2) = remote approvals + chat intake.

## 7. Failure + threat notes

Hook slow/broken → must exit 0 fast (<300ms idle), fail-open, log. Harness upgrade → adapters re-pin, best-effort render + warn. MCP down → disabled + hint. OAuth expired → doctor flag + re-connect. Secrets: redact.yml pre-log/pre-memory; creds 0600/keychain, minimal scopes. LAN HUD needs token. No telemetry, no inbound ports by default.

## 8. Build order

Adapters+paths → hooks (4) → skills/commands W1 → voice scripts → memory scripts → hud → routines → W2 MCPs → W3 → W4 → goldens → harden (unbless/kill) → video+docs. (Dates: BUILD_PLAN.)
