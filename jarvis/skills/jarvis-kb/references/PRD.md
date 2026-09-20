# JARVIS — One Command Turns Claude Code / OpenCode / Codex Into Jarvis
**PRD v0.3 PACK | Status: Heavy-planning draft | Date: 2026-09-19 | License: MIT (planned)**

> `curl -fsSL jarvis.sh | sh` → your harnesses become JARVIS. A **bless pack** — skills, slash-commands, hooks, scripts, MCPs, personas, routines — installed into Claude Code, OpenCode, AND Codex. **We build zero agent harness.** The three harnesses are the runtime (tool loop, model, sandbox); Jarvis is the transformation layer on top.

Full catalog: **`CONNECTORS.md`**. Rules: **`TRD.md`**. How it fits together: **`ARCHITECTURE.md`**. Path: **`BUILD_PLAN.md`**.

## 1. Vision

Every dev already rents three Iron Man suits (Claude Code, OpenCode, Codex) and uses them as fancy autocomplete. JARVIS is the one-command blessing that turns whichever suit you wear into a full butler: voice in/out, memory across sessions, every app connected, proactive routines, HUD — with a switchable JARVIS ↔ ULTRON soul.

Because we ride the harnesses instead of rebuilding them, we get models, tool loops, and sandboxes for free, survive every upstream upgrade, and stay a small MIT repo that blows up instead of a platform that rots.

## 2. Locked decisions

| Decision | Choice |
|---|---|
| What we build | **Pack only: skills + commands + hooks + scripts + MCPs + personas + routines.** No daemon, no custom agent loop, no model proxy |
| Runtime | Claude Code + OpenCode + **Codex** (all three, native locations, adapter per engine at install) |
| Soul | Switchable JARVIS ↔ ULTRON (persona overlays, same safety rules) |
| Voice | Scripts: `jarvis-listen` (wake + STT → injects into harness) + `jarvis-speak` (TTS on response hook) + PTT fallback |
| Memory | Scripts + hooks: markdown journal + SQLite-vec, recall injected via session-start hook |
| HUD | `jarvis hud`: static page tailing harness transcripts + memory (log viewer, zero backend) |
| Safety | Harness pre-tool-use hooks for L2 confirm + conventions; honest limits documented per engine |
| Install | Bless whole machine, per-engine adapters; `doctor` verifies each harness; `unbless` removes only owned keys |
| Tiers | L0 read free · L1 local-write mode-gated · L2 remote/irreversible always-confirms · L3 routines under same gates |
| Waves | W1 code/machine/web/memory → W2 comms+project+routines → W3 cloud+data → W4 media+money+MCP universe |

Reuse: ECC patterns (vendored subset, attributed), `voicebox/` lessons, `second-brain/` as memory export target, root `playwright` + `opencode-ai` deps.

## 3. Users / non-users

You (Claude/OpenCode/Codex user, wants max leverage + showpiece) → indie hackers/streamers (the clip) → small teams later (per-machine bless; sharing = Hive bridge, Phase 6+). Non-users: mobile-only, non-devs, compliance-gated orgs.

## 4. Goals / non-goals

Goals:
- G1: Bless fresh Linux/macOS in <10 min; `doctor` green on every detected harness.
- G2: Voice-to-code AND voice-to-anything ("brief me", "triage inbox", "why is CI red?") through harness-native paths.
- G3: HUD shows live session tails + memory + connectors/routines/settings from files only.
- G4: Memory persists across sessions AND harnesses (same `~/.jarvis/` brain home).
- G5: Connector waves W1→W4 land as MCPs + scripts + skills behind one `jarvis connect` UX.
- G6: L2 always-confirms via hooks on all three harnesses + kill switch stops scripts/timers.
- G7: Routines (brief, overnight worker, CI watchdog) via cron + harness headless runs.

Non-goals (explicit):
- NG1: No custom agent harness/daemon, no model calls of our own, no hosted backend.
- NG2: No team sync (Hive bridge later). NG3: No mobile app, no smart-home hardware.
- NG4: No unconfirmed L2 act on any engine, any mode — even Ultron asks (roasting while asking).

## 5. The one-command promise

```
curl -fsSL https://jarvis.sh | sh
# or: npx jarvis@latest bless
```

MUST: detect OS + Node/Bun + mic + which of the 3 harnesses exist → write `~/.jarvis/` (pack home: skills source, scripts, memory, creds, personas) → render pack into each harness's native locations (skills/commands/hooks/MCP) → `connect --wave 1` → print "Say Hey Jarvis…" + `doctor` green. `unbless` removes only owned keys (marker `managed-by-jarvis`), verified by `doctor`.

## 6. User stories

- US1: "Hey Jarvis, fix the failing test" → STT script → harness codes with Jarvis skills → TTS speaks summary.
- US2: "brief me" → routine skill pulls calendar+Gmail+CI via connectors → spoken + HUD card.
- US3: Open HUD mid-run, see live transcript tail + diff + receipt.
- US4: Mic dead? Same brain over harness chat — zero feature loss.
- US5: Flip Jarvis↔Ultron (`/ultron`), tone + voice change next utterance.
- US6: Flip Butler→Dev→Ultron, hook-gates actually change; L2 still confirms everywhere.
- US7: "how did we fix X?" → memory hook injects last month's real fix into context.
- US8: `jarvis connect gmail` → OAuth → "summarize unread" works on all three harnesses.
- US9: "work this overnight" → cron + headless harness run → morning PR draft + brief.
- US10: Kill switch stops listeners/timers and pauses hooks; `doctor` confirms STOPPED.

## 7. Capability summary (full list: CONNECTORS.md)

- **Code & ship:** git/gh/tests/scaffolds/codemods/CI-watch → skills + `gh` CLI scripts.
- **Machine & OS:** shell/files/processes/cron/notify/screenshot/audio-probe → scripts + hooks.
- **Web & research:** fetch/docs/search/monitor/browser/download → skills + scripts (+Playwright).
- **Comms:** Gmail/Calendar/Slack/Discord/Telegram/X → MCPs + OAuth vault; Telegram doubles as remote control.
- **Project:** GitHub/Linear/Jira/Notion/GDrive/second-brain → MCPs + skills.
- **Cloud & data:** Docker/K8s/SSH/AWS/GCP/Vercel/Cloudflare + PG/Redis/SQLite/S3/webhooks → MCPs + scripts, mutates L2.
- **Media & money:** fal.ai image, hyperframes/remotion hooks, Stripe read-first, x402 budgets, OpenAPI importer, any-MCP mount.
- **Proactive:** morning-brief, overnight-worker, ci-watchdog, inbox-triage, URL-watch, nudges → routines (cron + headless runs).
- **Cross-harness memory:** journal + vectors shared by all three engines.

## 8. Safety (hooks + conventions, honestly scoped)

| Mode | L0 read | L1 local write | L2 remote/irreversible |
|---|---|---|---|
| Butler (default) | free | hook confirms each | hook confirms + preview |
| Dev YOLO | free | free in workspace | hook confirms + preview |
| Ultron | free | free in workspace, chaos narration | hook confirms + preview (roasts while asking) |

Honest limit: hooks are advisory and differ per harness (matrix in ARCHITECTURE §7) — so L2 skills ALSO require the model to ask, defense in depth. Kill: `jarvis stop --now` kills listeners/timers, drops `paused` flag hooks check first. Secrets: redaction in hooks pre-log/pre-memory; tokens in vault only.

## 9. Success metrics

bless-green ≥80% <10min · voice-to-X ≥70% quiet-room · HUD 3x wk1, ≥5 useful recalls · W1 green, ≥3 W2 connected · zero unconfirmed L2 in tests · kill stops loops <10s · 90-sec multi-app demo + MIT.

## 10. Risks

Harness drift (hook/skill formats) → per-engine adapters + fixtures, fail-open (pack degrades to skills-only) · wake-word pain → PTT fallback · mic hell → audio probe + chat-first · OAuth sprawl → one vault + SCOPES docs · hook limits → L2 double-ask (hook + skill instruction) · token burn → step/budget caps in routine runners.

## 11. Open questions

Wake engine pick (spike) · Codex hooks/MCP parity — exact config paths to pin · HUD: pure-static vs tiny file-server script · Telegram-remote in v1 or W2 · Ultron voice: separate pack vs pitch-shift.
