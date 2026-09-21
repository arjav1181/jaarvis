"""Streaming STT partials (W7 apex).

Upstream transcription is batch-only (whole file in, transcript out). This
module wraps any chunk transcriber with a partial-event stream: WAV is split
into fixed windows, each window is transcribed, and ``partial`` events are
emitted as they land, followed by one ``final`` event with the joined text
and measured timings. Consumers (CLI JSONL, HUD poller, thread file) render
partials live — the "streaming" the batch engine cannot do alone.

Engine contract: ``engine(wav_bytes: bytes, index: int) -> str``.
Default engine tries the upstream batch transcriber on the full audio and
raises EngineAbsent when nothing usable is installed — honest-absent.
"""

from __future__ import annotations

import io
import time
import wave
from typing import Any, Callable, Dict, Iterator, List, Optional

EngineFn = Callable[[bytes, int], str]


class EngineAbsent(RuntimeError):
    pass


def default_engine() -> EngineFn:
    try:
        from tools.voice_mode import transcribe_recording  # type: ignore
    except ImportError as e:
        raise EngineAbsent(
            "no STT engine: upstream tools.voice_mode not importable "
            f"({e}); install faster-whisper or set GROQ_API_KEY/OPENAI_API_KEY"
        )

    def _engine(wav_bytes: bytes, index: int) -> str:
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            path = f.name
        try:
            out = transcribe_recording(path)
        finally:
            os.unlink(path)
        if isinstance(out, dict):
            return str(out.get("transcript") or out.get("text") or "")
        return str(out or "")

    return _engine


def split_wav(wav_bytes: bytes, window_ms: int = 5000) -> List[bytes]:
    """Split PCM WAV bytes into ~window_ms mono chunks (16-bit assumed)."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        nch, sw, fr, nframes = (w.getnchannels(), w.getsampwidth(),
                                w.getframerate(), w.getnframes())
        raw = w.readframes(nframes)
    if sw != 2:
        raise ValueError(f"only 16-bit PCM supported, got {sw * 8}-bit")
    stride = max(1, int(fr * window_ms / 1000)) * nch * sw
    frames = [raw[i:i + stride] for i in range(0, len(raw), stride)]
    out = []
    for chunk in frames:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(nch)
            w.setsampwidth(sw)
            w.setframerate(fr)
            w.writeframes(chunk)
        out.append(buf.getvalue())
    return out


def stream_partials(wav_bytes: bytes, engine: EngineFn,
                    window_ms: int = 5000) -> Iterator[Dict[str, Any]]:
    """Yield partial events then one final event with measured timings."""
    chunks = split_wav(wav_bytes, window_ms)
    total = len(chunks)
    parts: List[str] = []
    t0 = time.monotonic()
    for i, chunk in enumerate(chunks):
        c0 = time.monotonic()
        try:
            text = (engine(chunk, i) or "").strip()
        except Exception as e:  # one bad window must not kill the stream
            text = ""
            yield {"type": "window-error", "index": i, "total": total,
                   "error": f"{type(e).__name__}: {e}"}
        ms = int((time.monotonic() - c0) * 1000)
        if text:
            parts.append(text)
        yield {"type": "partial", "index": i, "total": total,
               "text": text, "window_ms": ms}
    total_ms = int((time.monotonic() - t0) * 1000)
    yield {"type": "final", "total": total,
           "text": " ".join(p for p in parts if p).strip(),
           "windows_with_speech": len(parts),
           "elapsed_ms": total_ms}


def make_test_wav(seconds: float = 2.0, framerate: int = 16000) -> bytes:
    """Silent 16-bit mono WAV for hermetic tests (no audio hardware)."""
    import struct
    n = int(seconds * framerate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        w.writeframes(struct.pack("<%dh" % n, *([0] * n)))
    return buf.getvalue()
