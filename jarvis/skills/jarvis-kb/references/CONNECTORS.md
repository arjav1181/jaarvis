# JARVIS — Connector & Capability Universe
**v0.3 PACK | 2026-09-19 | The "can do anything" catalog. Delivery column = how the pack delivers it on Claude Code / OpenCode / Codex (no custom harness).**

Tiers: `L0` read-only free · `L1` local-write mode-gated · `L2` remote/irreversible ALWAYS confirms.
Delivers as: `skill` (SKILL.md) · `cmd` (slash-command) · `hook` (harness hook) · `script` (CLI in `~/.jarvis/bin`) · `mcp` (MCP server config).
Waves: `W1` core → `W2` comms+project+routines → `W3` cloud+data → `W4` media+money+MCP universe.

## A. Code & Ship (W1)
| Connector | Can do | Tier | As |
|---|---|---|---|
| git | status/diff/commit/branch/stash (push = L2) | L1→L2 | skill + script |
| gh CLI | PRs, issues, CI runs, releases | L2 for merge/publish | skill + script |
| tests | npm/bun/pytest/go/vitest/playwright | L1 | skill + `cmd /test` |
| scaffolds | new connector/skill/route/component | L1 | script + skill |
| codemods | bulk rename/refactor, diff preview | L1 | skill |
| CI watcher | `gh run` poll, failure summary, fix branch | L0→L1 | skill + routine |

## B. Machine & OS (W1)
| Connector | Can do | As |
|---|---|---|
| shell/files/processes | exec, patch w/ backup+undo, ps/ports/log tails | harness-native + script |
| cron/timers | install user timers for routines | script |
| notify/screenshot/audio | desktop notify, captures, mic/speaker probe | script (`doctor --audio`) |
| voice loop | `jarvis-listen` (wake+STT→harness) + `jarvis-speak` (TTS hook) + PTT | script + hook |

## C. Web & Research (W1)
| Connector | Can do | As |
|---|---|---|
| fetch/docs/search | pages, Context7 docs, exa/firecrawl search | skill + script |
| monitor | URL/changelog watch → alert | routine + script |
| browser | Playwright snapshot/click/type/test-gen | skill + script |
| download | files w/ hash verify | script |

## D. Comms (W2)
| Connector | Reads | Writes (L2) | As / Auth |
|---|---|---|---|
| Gmail | search/summarize | draft, send | mcp + OAuth vault |
| Calendar | agenda/free-busy | create/invite | mcp + OAuth |
| Slack/Discord | read, summarize | post | mcp + tokens |
| Telegram | read + **remote Jarvis** (commands + L2 approvals) | send | mcp/script + bot token |
| X API | timeline/search | draft, post w/ confirm | mcp + OAuth |

Golden routine skill: `morning-brief` = calendar + Gmail + GH + CI → spoken + HUD card.

## E. Project & Knowledge (W2)
GitHub issues/projects, Linear, Jira, Notion, GDrive/Docs/Sheets (reads L0, writes L2) → **mcp + skills**; second-brain sync → script + skill.

## F. Cloud & Deploy (W3)
Docker (L1, rm = L2), K8s read + status (apply = L2), SSH pinned hosts (L2), AWS/GCP describe-first (mutate L2), Vercel/Render/Fly deploy (L2), Cloudflare/Tailscale (L2) → **mcp + scripts + skills**.

## G. Data (W3)
Postgres/MySQL (SELECT/explain L0, migrate L2 + backup), Redis (flush = typed confirm), SQLite (L1), S3/R2 (put outside scratch = L2), webhooks in/out (signed, allowlisted) → **mcp + scripts**.

## H. Media & Creative (W4)
fal.ai image, hyperframes/remotion render hooks, TTS/BGM/captions, social drafts (publish L2) → skills + scripts reusing your motion stack.

## I. Money & Generic APIs (W4)
Stripe read-first (refund L2 typed), x402 budgets, `connect openapi <url>` generator, declarative `custom/*.yml` REST → mcp + skills.

## J. MCP Universe (W4, infinite tail)
Any MCP server mounts via `jarvis mcp add`; starter set vendored from ECC `mcp-configs/` (attributed); broken server = warn + disable, never breaks a harness session.

## K. Routines (L3, cron + headless harness runs)
morning-brief, overnight-worker (branch→build→test→PR draft), ci-watchdog, inbox-triage (drafts-only), url/dep-watch, nudges. `jarvis routine add/list/run/rm`; every run receipted + logged + killable.

## L. Phone & Remote (flagged, post-W4)
Telegram remote + LAN HUD token (Tailscale first). Never internet-open without auth.

## M. Senses — see & hear the world (W3–W4)
| Connector | Can do | As |
|---|---|---|
| screenshots + OCR | poll window/region, diff, alert on error text | script + `screen-watch` skill |
| camera frames | explicit capture → notes → memory (never ambient) | script, explicit-only |
| meeting audio | record → faster-whisper → summary + actions → memory | script + `meeting-scribe` |
| doc parsing | PDF/DOCX/XLSX → markdown (Nutrient-style patterns) | script + skill |
| local RAG | embeddings over `~/docs` + second-brain → cited answers | script + `doc-rag` |

## N. DevOps depth (W3)
Sentry (issues → fix branch), Grafana (panels → summary), Terraform (plan explainer, apply = L2 + typed), Ansible (playbook run = L2), PostHog (funnels → insight), status pages (probe + alert) → mcp + skills.

## O. Life & personal (W2–W4, all L0-read-first)
RSS/YouTube (transcripts, watch-later digest), podcasts (episode briefs), Strava/fitness exports, price trackers, flight/hotel search (booking stays manual), 1Password/Bitwarden CLI refs (values never logged), bank/CSV finance import + spend digest → mcp + skills. Every money-move = L2 typed.

## P. Mansion — smart home (W5, NEW, local-first, default OFF)
Home Assistant (local API), Hue/ESPHome/Tasmota, power plugs, sensors. Master `mansion.enabled=false` default; every actuator L2-confirmable; all traffic stays on LAN. Skills: `lights-scene, home-status, power-watch` + scenes (`movie-night`).

## Q. Meta — Jarvis about Jarvis (W6, NEW)
`pack-sync` (multi-machine via YOUR git remote, zero cloud), `pack-update` (semver + re-render), `jarvis-wrapped` (weekly digest card), `dry-run` global flag, `connector-doctor`, `jarvis-tour`, scenes engine (`good-morning/focus-mode/ship-it/shutdown` in `scenes/*.yml`), `focus-guard` (DND batching).

## Authoring (5-minute rule)
`jarvis connect new <name>` scaffolds `pack/connectors/<name>/{connector.yml,tools.json,SKILL.md,tests/}` + per-engine render. Promotion bar: manifest + redaction-safe + tier + 3 golden tests + receipt + undo story + docs line.
