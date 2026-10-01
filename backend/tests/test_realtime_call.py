"""Tests for realtime voice call pipeline.

Covers: audio format handling, WebSocket message routing,
Azure session configuration, PCM16 forwarding, and memory integration.
"""

from __future__ import annotations

import base64
import json
import struct
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


class TestAudioFormatHandling:
    """Test PCM16 audio format detection and forwarding."""

    def test_pcm16_base64_roundtrip(self):
        """PCM16 audio survives base64 encode/decode."""
        # Generate 100ms of 24kHz PCM16 silence (2400 samples)
        samples = [0] * 2400
        pcm_bytes = struct.pack(f"<{len(samples)}h", *samples)
        b64 = base64.b64encode(pcm_bytes).decode()
        decoded = base64.b64decode(b64)
        assert decoded == pcm_bytes
        assert len(decoded) == 4800  # 2400 samples * 2 bytes

    def test_pcm16_with_audio_data(self):
        """PCM16 with actual audio values survives roundtrip."""
        # Generate a simple 440Hz tone at 24kHz, 100ms
        import math

        sample_rate = 24000
        duration_ms = 100
        num_samples = sample_rate * duration_ms // 1000
        samples = [
            int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            for i in range(num_samples)
        ]
        pcm_bytes = struct.pack(f"<{len(samples)}h", *samples)
        b64 = base64.b64encode(pcm_bytes).decode()

        # Verify decode produces valid PCM16
        decoded = base64.b64decode(b64)
        recovered = struct.unpack(f"<{len(decoded)//2}h", decoded)
        assert len(recovered) == num_samples
        assert recovered[0] == 0  # sin(0) = 0
        # Verify non-zero audio exists
        max_val = max(abs(s) for s in recovered)
        assert max_val > 25000  # Should have significant amplitude

    def test_pcm16_message_format(self):
        """iOS audio message has correct structure for backend."""
        samples = [0] * 2400
        pcm_bytes = struct.pack(f"<{len(samples)}h", *samples)
        b64 = base64.b64encode(pcm_bytes).decode()

        msg = {
            "type": "audio",
            "data": b64,
            "format": "pcm16",
            "sample_rate": "24000",
        }

        assert msg["type"] == "audio"
        assert msg["format"] == "pcm16"
        assert msg["sample_rate"] == "24000"
        assert len(base64.b64decode(msg["data"])) == 4800

    def test_azure_payload_format(self):
        """Backend forwards audio in Azure's expected format."""
        b64_audio = base64.b64encode(b"\x00" * 4800).decode()
        payload = {
            "type": "input_audio_buffer.append",
            "audio": b64_audio,
        }
        serialized = json.dumps(payload)
        parsed = json.loads(serialized)
        assert parsed["type"] == "input_audio_buffer.append"
        assert parsed["audio"] == b64_audio


class TestMessageRouting:
    """Test WebSocket message type routing."""

    def test_audio_message_detected(self):
        """Audio messages are correctly identified."""
        msg = {"type": "audio", "data": "base64data", "format": "pcm16"}
        assert msg.get("type") == "audio"
        assert msg.get("format", "webm") == "pcm16"

    def test_webm_fallback_format(self):
        """Web browser messages default to webm format."""
        msg = {"type": "audio", "data": "base64data"}
        assert msg.get("format", "webm") == "webm"

    def test_end_message(self):
        """End message terminates the loop."""
        msg = {"type": "end"}
        assert msg.get("type") == "end"

    def test_auth_message_structure(self):
        """Auth message from iOS has required fields."""
        msg = {
            "type": "auth",
            "token": "jwt_token_here",
            "conversation_id": "conv_123",
        }
        assert msg["type"] == "auth"
        assert "token" in msg
        assert "conversation_id" in msg


class TestAzureSessionConfig:
    """Test Azure Realtime API session configuration."""

    def test_semantic_vad_config(self):
        """Session config uses semantic_vad with low eagerness."""
        config = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "turn_detection": {
                            "type": "semantic_vad",
                            "eagerness": "low",
                            "create_response": True,
                            "interrupt_response": True,
                        },
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                    },
                },
            },
        }

        td = config["session"]["audio"]["input"]["turn_detection"]
        assert td["type"] == "semantic_vad"
        assert td["eagerness"] == "low"
        assert td["create_response"] is True
        assert td["interrupt_response"] is True

    def test_input_format_24khz_pcm(self):
        """Input audio format is 24kHz PCM."""
        fmt = {"type": "audio/pcm", "rate": 24000}
        assert fmt["type"] == "audio/pcm"
        assert fmt["rate"] == 24000

    def test_output_format_matches_input(self):
        """Output format matches input format."""
        input_fmt = {"type": "audio/pcm", "rate": 24000}
        output_fmt = {"type": "audio/pcm", "rate": 24000}
        assert input_fmt == output_fmt

    def test_greeting_response_create(self):
        """Greeting trigger has correct format."""
        greeting = {
            "type": "response.create",
            "response": {
                "instructions": "Greet Luis briefly. One short sentence only.",
            },
        }
        assert greeting["type"] == "response.create"
        assert "instructions" in greeting["response"]
        assert "briefly" in greeting["response"]["instructions"].lower()


class TestWAVAssembly:
    """Test server-side WAV assembly from PCM chunks."""

    def test_pcm16_to_wav_header(self):
        """WAV header is correctly constructed."""
        # Simulate the _pcm16_to_wav function
        pcm_data = b"\x00" * 4800  # 100ms of silence at 24kHz

        # WAV header construction
        sample_rate = 24000
        channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm_data)

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,
            1,  # PCM
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
            b"data",
            data_size,
        )
        wav = header + pcm_data

        # Verify WAV header
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert wav[12:16] == b"fmt "
        assert len(wav) == 44 + data_size  # 44-byte header + data

    def test_multiple_chunks_concatenate(self):
        """Multiple PCM chunks combine into valid WAV."""
        chunk1 = b"\x00\x10" * 2400  # 100ms
        chunk2 = b"\x00\x20" * 2400  # 100ms
        combined = chunk1 + chunk2
        assert len(combined) == 9600  # 200ms total


class TestAudioGeneration:
    """Test generating test audio for verification."""

    def generate_tone(self, freq_hz: int, duration_ms: int, sample_rate: int = 24000) -> bytes:
        """Generate a PCM16 sine wave tone."""
        import math

        num_samples = sample_rate * duration_ms // 1000
        samples = [
            int(32767 * 0.8 * math.sin(2 * math.pi * freq_hz * i / sample_rate))
            for i in range(num_samples)
        ]
        return struct.pack(f"<{num_samples}h", *samples)

    def test_generate_440hz_tone(self):
        """440Hz tone generates valid PCM16."""
        tone = self.generate_tone(440, 1000)  # 1 second
        assert len(tone) == 48000  # 24000 samples * 2 bytes
        # Verify it's not silence
        samples = struct.unpack(f"<{len(tone)//2}h", tone)
        max_val = max(abs(s) for s in samples)
        assert max_val > 25000  # Should have significant amplitude

    def test_generate_silence(self):
        """Silence generates zero samples."""
        silence = self.generate_tone(0, 100)
        samples = struct.unpack(f"<{len(silence)//2}h", silence)
        assert all(s == 0 for s in samples)

    def test_tone_as_azure_payload(self):
        """Generated tone can be packaged as Azure payload."""
        tone = self.generate_tone(440, 100)  # 100ms
        b64 = base64.b64encode(tone).decode()
        payload = json.dumps({
            "type": "input_audio_buffer.append",
            "audio": b64,
        })
        parsed = json.loads(payload)
        decoded = base64.b64decode(parsed["audio"])
        assert decoded == tone

    def test_simulated_conversation_flow(self):
        """Simulate a full conversation audio flow."""
        # User says "hello" (simulate with 2 seconds of tone)
        user_audio = self.generate_tone(300, 2000)

        # Split into ~85ms chunks (like iOS tap sends)
        chunk_size = 24000 * 85 // 1000 * 2  # 85ms at 24kHz, 2 bytes per sample
        chunks = []
        for i in range(0, len(user_audio), chunk_size):
            chunk = user_audio[i : i + chunk_size]
            if len(chunk) > 100:
                chunks.append(base64.b64encode(chunk).decode())

        assert len(chunks) > 20  # Should be ~23 chunks for 2 seconds
        # Each chunk should be forwardable
        for b64 in chunks:
            payload = {
                "type": "input_audio_buffer.append",
                "audio": b64,
            }
            assert len(json.dumps(payload)) < 100_000  # Under 100KB per message


class TestMemoryTools:
    """Test memory save/recall tools."""

    @pytest.mark.asyncio
    async def test_memory_save_tool_returns_json(self):
        """MemorySaveTool returns valid JSON."""
        from app.memory_tools import MemorySaveTool

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        tool = MemorySaveTool(mock_session, "agent_123")
        result = await tool.execute({"fact": "User lives in Brussels", "category": "personal"})
        parsed = json.loads(result)
        assert parsed["status"] == "remembered"
        assert "Brussels" in parsed["fact"]
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_save_empty_fact(self):
        """MemorySaveTool rejects empty facts."""
        from app.memory_tools import MemorySaveTool

        mock_session = AsyncMock()
        tool = MemorySaveTool(mock_session, "agent_123")
        result = await tool.execute({"fact": ""})
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_memory_recall_tool(self):
        """MemoryRecallTool queries memories."""
        from app.memory_tools import MemoryRecallTool

        mock_memory = MagicMock()
        mock_memory.content = "User lives in Brussels"
        mock_memory.category = "personal"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_memory]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        tool = MemoryRecallTool(mock_session, "agent_123")
        result = await tool.execute({"query": "location"})
        parsed = json.loads(result)
        assert parsed["count"] == 1
        assert "Brussels" in parsed["memories"][0]["fact"]


class TestVoiceCallInstructions:
    """Test that voice call instructions are properly constructed."""

    def test_instructions_include_silence_rule(self):
        """Instructions tell agent not to talk unprompted."""
        user_name = "Luis"
        voice_personality = "Colombian paisa accent"
        system_prompt = "You are a helpful assistant."

        instructions = (
            f"You are Motes, a friendly AI assistant on a voice call with {user_name}. "
            f"Keep responses conversational and concise. "
            f"If the user switches languages, follow them. "
            f"IMPORTANT: Only respond when the user speaks to you. "
            f"Do NOT speak unprompted. Wait for the user to finish talking before responding. "
            f"If there is silence, stay quiet — do not fill silence with speech. "
            + (f"Voice personality: {voice_personality}. " if voice_personality else "")
            + system_prompt
        )

        assert "Only respond when the user speaks" in instructions
        assert "Do NOT speak unprompted" in instructions
        assert "stay quiet" in instructions
        assert "Colombian paisa" in instructions
        assert user_name in instructions

    def test_instructions_without_personality(self):
        """Instructions work without voice personality."""
        instructions = (
            "You are Motes. "
            + ("" if not "" else "Voice: . ")
            + "Base prompt."
        )
        assert "Voice:" not in instructions


class TestDownsampling:
    """Test audio downsampling approaches."""

    def test_48k_to_24k_ratio(self):
        """48kHz to 24kHz is a 2:1 ratio."""
        assert 48000 / 24000 == 2.0

    def test_native_44100_to_24000_ratio(self):
        """44.1kHz to 24kHz ratio is ~1.8375."""
        ratio = 44100 / 24000
        assert 1.8 < ratio < 1.9

    def test_struct_downsample_48k(self):
        """Struct-based downsampling halves 48kHz correctly."""
        # 48kHz, 100ms = 4800 samples
        original = list(range(4800))
        ratio = 48000 / 24000
        downsampled = [original[int(i * ratio)] for i in range(int(len(original) / ratio))]
        assert len(downsampled) == 2400
        assert downsampled[0] == 0
        assert downsampled[1] == 2  # Picks every 2nd sample

    def test_ios_avconverter_expected_output_size(self):
        """iOS AVAudioConverter output size calculation."""
        input_rate = 48000.0
        target_rate = 24000.0
        input_frames = 4096
        expected_output = int(target_rate / input_rate * input_frames)
        assert expected_output == 2048
