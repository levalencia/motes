"""Edge TTS provider — FREE text-to-speech using Microsoft Edge neural voices.

No API key needed. Works out of the box.
"""

from __future__ import annotations

import io

import edge_tts

# Popular Edge TTS voices
EDGE_VOICES = {
    "en-US": [
        ("en-US-AriaNeural", "Aria (Female, US)"),
        ("en-US-GuyNeural", "Guy (Male, US)"),
        ("en-US-JennyNeural", "Jenny (Female, US)"),
    ],
    "en-GB": [
        ("en-GB-SoniaNeural", "Sonia (Female, UK)"),
        ("en-GB-RyanNeural", "Ryan (Male, UK)"),
    ],
    "es-CO": [
        ("es-CO-SalomeNeural", "Salome (Female, Colombian)"),
        ("es-CO-GonzaloNeural", "Gonzalo (Male, Colombian)"),
    ],
    "es-ES": [
        ("es-ES-ElviraNeural", "Elvira (Female, Spain)"),
        ("es-ES-AlvaroNeural", "Alvaro (Male, Spain)"),
    ],
    "fr-FR": [
        ("fr-FR-DeniseNeural", "Denise (Female, France)"),
        ("fr-FR-HenriNeural", "Henri (Male, France)"),
    ],
    "de-DE": [
        ("de-DE-KatjaNeural", "Katja (Female, Germany)"),
        ("de-DE-ConradNeural", "Conrad (Male, Germany)"),
    ],
    "pt-BR": [
        ("pt-BR-FranciscaNeural", "Francisca (Female, Brazil)"),
        ("pt-BR-AntonioNeural", "Antonio (Male, Brazil)"),
    ],
    "nl-NL": [
        ("nl-NL-ColetteNeural", "Colette (Female, Dutch)"),
        ("nl-NL-MaartenNeural", "Maarten (Male, Dutch)"),
    ],
}

DEFAULT_VOICE = "en-US-AriaNeural"


async def edge_tts_synthesize(
    text: str,
    voice: str = DEFAULT_VOICE,
) -> bytes:
    """Synthesize speech using Edge TTS. Returns MP3 bytes. FREE, no API key."""
    communicate = edge_tts.Communicate(text, voice)

    # Collect audio data
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])

    return audio_data.getvalue()


async def list_edge_voices() -> list[dict[str, str]]:
    """List all available Edge TTS voices."""
    voices = await edge_tts.list_voices()
    return [
        {
            "id": v["ShortName"],
            "name": v["FriendlyName"],
            "locale": v["Locale"],
            "gender": v["Gender"],
        }
        for v in voices
    ]
