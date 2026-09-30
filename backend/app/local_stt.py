"""Local STT using faster-whisper — runs on your machine, no API key, no internet."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

_model = None


def _get_model():
    """Lazy-load the Whisper model (downloads ~150MB on first use)."""
    global _model  # noqa: PLW0603
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def _convert_to_wav(input_path: str) -> str:
    """Convert any audio format to WAV using ffmpeg (whisper needs wav/mp3)."""
    output_path = input_path.rsplit(".", 1)[0] + ".wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            "-ar", "16000", "-ac", "1", "-f", "wav", output_path,
        ],
        capture_output=True,
        timeout=30,
        check=True,
    )
    return output_path


async def transcribe_local(audio_data: bytes, language: str | None = None) -> str:
    """Transcribe audio bytes using local Whisper. Returns text."""

    def _sync_transcribe() -> str:
        model = _get_model()
        # Write audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name
        wav_path = None
        try:
            # Convert to WAV first (faster-whisper handles wav best)
            wav_path = _convert_to_wav(tmp_path)
            kwargs: dict = {}
            if language:
                kwargs["language"] = language
            segments, _info = model.transcribe(wav_path, **kwargs)
            return " ".join(seg.text.strip() for seg in segments)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            if wav_path:
                Path(wav_path).unlink(missing_ok=True)

    return await asyncio.get_event_loop().run_in_executor(None, _sync_transcribe)
