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
