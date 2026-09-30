"""Local STT using faster-whisper — runs on your machine, no API key, no internet.

Works around PyAV incompatibility by using ffmpeg directly for audio decoding.
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

import numpy as np

_model = None


def _get_model():
    """Lazy-load the Whisper model (downloads ~500MB on first use)."""
    global _model  # noqa: PLW0603
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel("small", device="cpu", compute_type="int8")
    return _model


def _decode_audio_ffmpeg(input_path: str) -> np.ndarray:
    """Decode any audio file to 16kHz mono float32 numpy array using ffmpeg."""
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            "-ar", "16000", "-ac", "1",
            "-f", "f32le", "-acodec", "pcm_f32le",
            "pipe:1",
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr.decode()[:300]}")
    return np.frombuffer(result.stdout, dtype=np.float32)


async def transcribe_local(audio_data: bytes, language: str | None = None) -> str:
    """Transcribe audio bytes using local Whisper. Returns text."""

    def _sync_transcribe() -> str:
        model = _get_model()
        # Write audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name
        try:
            # Decode with ffmpeg (avoids PyAV version issues)
            audio_array = _decode_audio_ffmpeg(tmp_path)
            kwargs: dict = {}
            if language:
                kwargs["language"] = language
            else:
                kwargs["language"] = "en"  # Default to English to avoid misdetection
            segments, _info = model.transcribe(audio_array, **kwargs)
            return " ".join(seg.text.strip() for seg in segments)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return await asyncio.get_event_loop().run_in_executor(None, _sync_transcribe)
