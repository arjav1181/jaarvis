# Voice + wake — W2 (config reference + honest-status notes)

All values below are the TEST-home proven config (`HERMES_HOME=~/.jarvis-test`).
Real-install path: repeat the same `hermes config set` lines with
`HERMES_HOME=~/.jarvis`.

## Wake word ("hey Jarvis")

```bash
hermes config set wake_word.enabled true
hermes config set wake_word.provider openwakeword
hermes config set wake_word.phrase "hey Jarvis"
hermes config set wake_word.sensitivity 0.6
hermes config set wake_word.confirmation_frames 3
hermes config set wake_word.openwakeword.model hey_jarvis
```

Correction to the plan's shorthand: only `hey_hermes` ships as a file
(`tools/wakewords/hey_hermes.{onnx,tflite}`); `hey_jarvis` is an openWakeWord
**built-in name** resolved by the `openwakeword` package (shared feature models
fetch once on first use). Status: `/wake status` (renderer
`CLIVoiceMixin._show_wake_word_status`). This box has no mic (PortAudio
absent), so status is honestly `OFF` + `Microphone capture needs sounddevice +
numpy and a working audio device` — config-correct, no faked listen.

## STT (faster-whisper local first)

Priority local → Groq → OpenAI; no cloud STT keys are set, so `local`
(`base` model) serves. Config: `stt.enabled: true`, `stt.local.model: base`,
VAD + confidence gate on (`no_speech_prob_threshold: 0.6`,
`logprob_threshold: -1.0`). Proven: fixture
`tests/jarvis/fixtures/fixture.wav` ("Jarvis is online and ready to serve,
sir.") → exact transcript via `tools.transcription_tools.transcribe_audio`
in 2630 ms warm (15 s cold incl. model load).

## TTS (Edge default, per-soul voices)

```bash
hermes config set tts.provider edge
hermes config set tts.edge.voice en-GB-RyanNeural      # Jarvis
hermes config set tts.edge.voice en-US-ChristopherNeural  # Ultron
```

Proven via `tools.tts_tool.text_to_speech_tool`: Jarvis line 28,080 B in
1741 ms; Ultron line 35,136 B in 1537 ms (MP3 frames; decode to RIFF/WAVE for
headers). Full per-soul map (incl. OpenAI/ElevenLabs IDs for keyed backends)
in `jarvis/personas/voices.yml`. Fallback chain: Edge (keyless) →
Piper/NeuTTS (local, no key, W2-later) → ElevenLabs/OpenAI (keys).
Absent-backend honesty: no engine ⇒ the tool returns
`success: false` (`spoken:false`-shaped envelope) — never fake audio.

## Barge-in, stop, streaming, hallucination filter

```bash
hermes config set voice.barge_in true
hermes config set voice.barge_in_grace_seconds 0.5
hermes config set voice.barge_in_threshold_multiplier 3.0
hermes config set voice.stop_phrases '["stop"]'
hermes config set tts.streaming.min_len 20
```

Streaming sentence TTS on (`tts.streaming.min_len: 20`). Hallucination
filter: `tools.voice_mode_transcript.is_whisper_hallucination` over a
17-phrase set (`thank you`, `you`, `bye`, … + 8 non-English) plus a
repeat-pattern (`Thank you. Thank you…`); silence-side hardening via Silero
VAD + `condition_on_previous_text: False` + the no-speech/logprob gate.

## Status flags

`jarvis-voice-status` prints live-probed `stt/tts/wake/mic: real|absent` +
active persona/skin. Absent stays absent — the loop degrades to text chat.

## Mic gotchas (human's real-machine run)

- **macOS**: grant Microphone to the terminal/Hermes app (System Settings →
  Privacy & Security → Microphone), then `/wake off` + `/wake on`. Apple
  Silicon: leave `inference_framework` empty (auto → tflite); explicit `onnx`
  arms but never fires (openWakeWord #336) — Hermes coerces with a warning.
- **Windows**: pick the input device explicitly if the default is wrong:
  `hermes config set wake_word.input_device "<name-or-index>"`; exclusive-mode
  mic ownership by another app starves the listener.
- **Remote/HUD mic**: `wake_word.capture: client` + `wake.feed` PCM stream —
  mic stays local, compute remote (homelab topology).
- **Linux**: PortAudio + a default input device are required
  (`sounddevice` must import AND `query_devices()` must list an input).
