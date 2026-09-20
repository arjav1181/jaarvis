# JARVIS — Skill Catalog
**v0.4 | 2026-09-19 | Every skill = one `skills-src/<name>/SKILL.md` rendered to all 3 harnesses. Trigger = what you say. Tier = L0/L1/L2.**

## Core (ships in W1 pack)
| Skill | Trigger | Does |
|---|---|---|
| `test-runner` | "run the failing test" | detects runner, runs scoped tests, explains failure |
| `fix-flake` | "this test is flaky" | retry/isolate/quarantine loop + fix PR |
| `explain-error` | "what does this error mean" | stack → cause → 3 fixes ranked |
| `ship-pr` | "ship it" | test→commit→push→PR→watch CI (L2 at push) |
| `code-review` | "review this" | diff review with severity + suggested patches |
| `scaffold` | "scaffold X" | templates: connector/skill/route/component |
| `morning-brief` | "brief me" | calendar+gmail+GH+CI → spoken + HUD card |
| `remember` / `forget` | "remember X" | memory writes via scripts |

## Dev depth (W1–W3)
| Skill | Trigger | Does |
|---|---|---|
| `incident-responder` | "prod is sad" | logs+k8s+CI triage → fix branch (never auto-applies) |
| `perf-profiler` | "why is this slow" | profile, flamegraph pointers, top-3 wins |
| `sql-doctor` | "this query is slow" | EXPLAIN, index advice, migration draft (L2) |
| `api-tester` | "test this endpoint" | curl/openapi calls, contract check |
| `dep-updater` | "update deps" | outdated scan → per-dep PRs with changelogs |
| `release-notes` | "cut a release" | commits→notes→tag→GH release draft (L2) |
| `regex-wizard` | "match strings like…" | build + explain + test-table for regex |
| `mock-generator` | "mock this API" | fixture server + stub data from OpenAPI/traffic |
| `sec-scan` | "is this safe" | secret/pattern audit via redaction lists |

## Comms & life (W2)
| Skill | Trigger | Does |
|---|---|---|
| `inbox-triage` | "triage my inbox" | drafts replies + labels, you approve (L2 at send) |
| `meeting-scribe` | "scribe this call" | record→transcribe→summary→actions→memory |
| `calendar-tetris` | "fit a 1:1 tomorrow" | free-busy solve + invite draft (L2) |
| `thread-summarizer` | "summarize this thread" | slack/discord/gmail digest |
| `doc-reader` | "read this PDF/contract" | parse (pdf/docx/xlsx) → brief + risks |
| `paper-digest` | "digest this paper" | academic summary + key figures + citations |
| `trip-planner` | "plan 3 days in Goa" | itinerary + links, bookings stay manual (L2) |
| `weekly-review` | "weekly review" | commits+calendar+memory → wins/debts/focus |

## Senses (W3–W4)
| Skill | Trigger | Does |
|---|---|---|
| `screen-watch` | "watch the deploy" | screenshot poll + OCR → alert on change/error |
| `cam-note` | "whiteboard this" | camera frame → notes → memory (explicit only) |
| `doc-rag` | "search my docs" | local PDF/wiki semantic search + cited answer |
| `change-radar` | "watch this page" | fetch diff → alert + summary |

## Mansion — smart home (W5, all local-first, opt-in)
| Skill | Trigger | Does |
|---|---|---|
| `lights-scene` | "movie night" | Home Assistant/Hue scenes via local API (L1) |
| `home-status` | "house report" | sensors/doors/power summary |
| `power-watch` | "watch the power" | usage thresholds → alert + routine |
| Note | every actuator = L2-confirmable; `mansion` master toggle, default OFF |

## Meta — Jarvis about Jarvis (W6)
| Skill | Trigger | Does |
|---|---|---|
| `jarvis-tour` | "show me around" | interactive capability walkthrough |
| `jarvis-wrapped` | "what did you do" | weekly digest: tasks, saves, receipts (shareable card) |
| `dry-run` | "dry-run: wipe tmp" | narrates every step, executes nothing |
| `connector-doctor` | "why is gmail broken" | per-connector diagnose + re-connect |
| `pack-sync` | "sync my machines" | push/pull `~/.jarvis` via YOUR git remote (no cloud) |
| `pack-update` | "update jarvis" | semver pack upgrade, re-render, changelog |
| `scene` | "good morning / focus mode / ship-it" | named routine chains, user-editable `scenes/*.yml` |
| `focus-guard` | "focus for 1 hour" | mutes non-urgent routines, batches alerts |

## Scenes (routine chains, `scenes/*.yml`)
`good-morning` (brief + agenda + top PR) · `focus-mode` (guard + queue) · `ship-it` (test→PR→CI→notes) · `movie-night` (lights + DND) · `shutdown` (stop timers + daily log).
