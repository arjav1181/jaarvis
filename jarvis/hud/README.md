# Jarvis HUD — browser voice page (W3)

Browser is ears + mouth ONLY: mic → `POST /api/audio/transcribe` → transcript
→ `prompt.submit` over `/api/ws` → `message.delta` stream →
`POST /api/audio/speak` → in-page playback. No model/tool logic in the page,
no audio stored server-side (upstream unlinks temp files after each call),
transcripts live in the DOM only (nothing journaled, no localStorage).

## Serving choice (documented per W3 rule 2)

Upstream supports extension without core edits: `WEB_DIST` is overridable via
the `HERMES_WEB_DIST` env var, and the SPA catch-all serves real files first
(`serve_spa` → `FileResponse`), falling back to `index.html` otherwise.
So the page ships as `jarvis/hud/voice.html` (repo source of truth) and is
deployed by copying it next to a copy of the built `web_dist`:

```bash
rm -rf <home>/web_dist_overlay && cp -r hermes_cli/web_dist <home>/web_dist_overlay
cp jarvis/hud/voice.html <home>/web_dist_overlay/voice.html
HERMES_WEB_DIST=<home>/web_dist_overlay hermes dashboard --host 0.0.0.0 --port 3000
```

Same-origin serving means the session cookie + auth gate apply unchanged
(unauth `/voice.html` → 302 to `/login`). A separate static port was rejected:
it would break single-port forwarding and need its own auth story.

## Protocol (all pre-existing upstream surfaces)

- Login: `POST /auth/password-login {provider,username,password}` (cookie).
- Ticket: `POST /api/auth/ws-ticket` → `?ticket=` on `/api/ws`.
- Control: `session.create {}` → sid; `prompt.submit {session_id,text}`;
  kill: `session.interrupt {session_id}`. Events arrive as
  `method:"event", params:{type, payload}` (`message.delta` → `payload.text`).
- Audio: `POST /api/audio/transcribe {data_url,mime_type}` →
  `{ok,transcript,provider}`; `POST /api/audio/speak {text}` →
  `{ok,data_url,mime_type,provider}` (uses server `tts.edge.voice`, flipped
  per soul by `jarvis-persona`).
- Reply-complete: authoritative `turn.end` wins; else 4 s event silence; else
  REST backstop (title-matched thread → stable assistant message).

## Mobile runbook (human's real-device run)

- **HTTPS is mandatory**: `getUserMedia` only exists in secure contexts —
  the Replit-forwarded URL (https) works; plain `http://<lan-ip>` does NOT
  (page falls back to the text box with an explanatory note, never a dead
  button). `localhost` is also a secure context (local testing OK).
- **Permission**: iOS Safari / Android Chrome prompt per site; grant once.
  If blocked: page shows "mic blocked: …" with the OS error text.
- **Viewport**: `meta viewport` + responsive CSS, ≥48 px touch targets,
  `aria-live` thread. Static audit in `test_w3_bvoice.py`; no headless
  emulation exists on this box — real-device checklist: (1) login form fits
  360 px wide, (2) hold-PTT records + VU moves, (3) tap-toggle works one-handed,
  (4) spoken reply audible on speaker, (5) stop-tap cancels <0.5 s.
- **Remote mic (desktop later)**: same idea over `wake_word.capture: client`
  + `wake.feed`; the browser page is the HTTP twin of that path.

## Safety

- Kill button = `session.interrupt` + synchronous `audio.pause()` (measured
  306 ms server-silence, 0 post-interrupt deltas; client pause <5 ms).
- L2 unchanged: voice submits plain-text turns; confirmations still apply.
  No permission logic exists in the page (asserted: no `auth`/`approve`/
  `permission` strings beyond the login form).
- Injection: every render is `textContent` (zero `innerHTML`/`document.write`/
  `eval` in the file — asserted in tests); transcript travels as a JSON
  string into `prompt.submit`, never evaluated.

## W4 — beast talk (continuous hands-free + narration + streaming partials)

- **State machine** (visible badge): `IDLE → LISTENING → TRANSCRIBING →
  THINKING → SPEAKING → LISTENING…` (continuous) or back to `IDLE`.
- **Hands-free loop**: `🔁 Continuous` toggle; reply done → mic reopens by
  itself. Client VAD auto-stops on 1.2 s sub-threshold silence
  (`VAD_LEVEL`/`VAD_SILENCE_MS`; server Silero VAD stays authoritative).
  Stop-phrases (`stop|goodbye|good night|that's all|cancel|never mind`)
  end hands-free instead of submitting — voice AND typed.
- **Narrated work**: milestone speech on `message.start` + tool events +
  turn end, per-soul lines (`NARR.jarvis` crisp / `NARR.ultron`
  theatrical), verbosity `verbose|normal|silent` (start+tools+done /
  start+done / none). Speech-only: narration never submits, never approves,
  shares the output slot (partials win, barge-in kills it).
- **Streaming partials**: complete sentences speak as they arrive (ordered
  queue); turn end speaks only the unspoken remainder, else labels
  `SPEAK[streamed first-audio:Nms]` (first reply-audio play minus submit —
  narration excluded from the stamp).
- **Soul**: read once at login from `/api/config display.personality`
  (drives narration lines; TTS voice itself stays server-side per soul).

## W13 — the face (HUD.md identity spec, this page)

- **Arc-reactor orb** (`<canvas id="orb">`, `setOrb`/`drawOrb`): honest modes
  only — `idle` pulse whose period stretches with a real 30 s heartbeat poll
  (`GET /api/sessions?limit=1`, sends no content; orb dims while heartbeats
  miss), `listening` rings expanded by the LIVE mic analyser peak (any mic
  error latches `frozen` and drops to idle — never fake listening),
  `thinking` arcs whose segment count = the live `tool.generating` count
  (arcs dim after 10 s with no run event = the run stalled), `speaking`
  waveform driven by the real `<audio>` playback position (`ontimeupdate`;
  barge-in collapses it synchronously), `stopped` ember + `STOPPED` banner
  latched by kill until the next real work. Palettes mirror the server skins
  (jarvis gold/blue, ultron crimson/bronze + sharper chorded geometry and a
  slower pulse, friday emerald); the soul flips the palette instantly on the
  same orb. `prefers-reduced-motion` → static glow + text states.
- **Voice of the interface**: every status/note/empty/error line comes from
  a per-soul `COPY` map (same facts, soul tone; Friday `boss`, Ultron menace
  with identical numbers). Empty thread: "No memories yet, sir — give me
  something worth remembering." Mic denial: "The microphone declined, sir —
  check the browser permission." (+ OS error text, all three souls).
- **Capability surfacing**: memory indicator parses W12 cited callbacks
  (`(memory #N)`) out of the just-finished reply into "I recall N relevant
  memories, sir" + native expandable citation list (no citations heard, no
  claim); every reply meta carries `ENGINE[stt:<real> tts:<real>]` providers
  from the actual transcribe/speak responses plus measured wall-clock ms
  beside the existing honest `SPEAK[…]` labels; Household-orders fieldset
  (Voice orders verbose/normal/silent with plain-English consequences, Soul
  allegiance read-only from server config, Safety Butler display-only — L2
  enforcement stays server-side, voice never widens permissions); kill is a
  full-width red reactor-shutdown, one tap, never disabled once logged in.
- **Narration rotation**: `NARR` embeds the `jarvis/personas/narration.yml`
  sets verbatim (W4 triplets as rotation heads — day-one lines unchanged),
  cycling per milestone; speech-only as in W4.
- **Layout**: orb top-center, thread below, controls sticky in the bottom
  thumb-zone under 480 px, 360 px-first, system fonts, zero external requests
  (asserted: no http/links/images/url()/imports), `aria-live` thread + orb
  label, ≥48 px targets.

## W8 — carried face items (suit diagnostics + boot ceremony) + audit page

- **Boot ceremony** (in `voice.html`, post-login): three honest checks —
  power (live `/api/sessions?limit=1` heartbeat), hearing (`micSupported()`
  probe), voice (`S.speak` switch state) — then the per-soul nominal line,
  spoken when speak is on. Every line reports its own outcome; a failed check
  says so in the soul's voice. Speech-only: the ceremony never submits,
  never approves (asserted in `test_w8_permissions.py`).
- **Suit-diagnostics page** (`diag.html`, same-origin + auth gate like the
  voice page): renders `<home>/web_dist_overlay/diag-snapshot.json` —
  `hermes doctor` ok/text, model + provider + personality, `tests/jarvis/`
  passed/failed/green, frozen/silenced/audit counts — with an explicit stale
  warning past 45 min. The snapshot is written every 30 min by the
  `jarvis-snapshot` cron job (`jarvis/bin/jarvis-doctor-snapshot`); every
  field is measured at snapshot time, never claimed.
- **Audit-ledger page** (`audit.html`): renders `audit-snapshot.json`
  (newest-50 rows + counts) with all/allowed/denied/enforced filters.
- Deploy: copy `diag.html` + `audit.html` next to `voice.html` in
  `<home>/web_dist_overlay` (same serving choice as W3 — no new auth story).
  Pages fetch only their own `./*.json` snapshot (asserted: single fetch,
  zero external, text-only rendering).

## W7 — apex beast page

- **Apex page** (`apex.html`, new file, same auth gate): renders
  `<home>/web_dist_overlay/apex-snapshot.json` — GPU ladder rung + evidence,
  STT engine, Discord VC status, GPT-Live / jarvis-review / Langfuse states,
  achievements earned + locked. Written every 30 min by the
  `jarvis-apex-snapshot` job (`jarvis/bin/jarvis-doctor-apex`,
  installed by `jarvis/apex/ensure-apex.sh` — touches no W5/W8 job).
- CLIs (all new, all honest-absent at boundaries): `jarvis-stt-stream`
  (JSONL partials + final with measured per-window ms), `jarvis-apex-say`
  (streaming sentence TTS via `jarvis-speak`, `--dry-run` spends nothing),
  `jarvis-discord-vc` (credential/allowlist gate, exit 2 when absent),
  `jarvis-gpt-live` (cost disclosure + `--i-accept-costs` + key required),
  `jarvis-review` (`jarvis/moa/jarvis-review.json` preset: cheap refs +
  frontier aggregator, privacy full; plan only, execution stays in-agent),
  `jarvis-langfuse` (consent record, never activates), `jarvis-achieve`
  (computed badges over `jarvis/apex/events.jsonl`).
