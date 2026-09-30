"""Local STT using faster-whisper — runs on your machine, no API key, no internet."""

from __future__ import annotations

import tempfile
from pathlib import Path

_model = None


def _get_model():
    """Lazy-load the Whisper model (downloads ~150MB on first use)."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


async def transcribe_local(audio_data: bytes, language: str | None = None) -> str:
    """Transcribe audio bytes using local Whisper. Returns text."""
    import asyncio

    def _sync_transcribe() -> str:
        model = _get_model()
        # Write audio to temp file (faster-whisper needs a file path)
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name
        try:
            kwargs = {}
            if language:
                kwargs["language"] = language
            segments, _info = model.transcribe(tmp_path, **kwargs)
            return " ".join(seg.text.strip() for seg in segments)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # Run in thread pool to avoid blocking the event loop
    return await asyncio.get_event_loop().run_in_executor(None, _sync_transcribe)
