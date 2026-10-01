"""Azure OpenAI Realtime API — true bidirectional voice conversation.

Uses WebSocket to stream audio in both directions. Sub-second latency.
Model: gpt-realtime-2.1-mini on Azure.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import struct
from pathlib import Path

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth import decode_jwt
from app.models import Agent, Conversation, Message

logger = structlog.get_logger()

router = APIRouter(tags=["realtime-call"])


@router.websocket("/api/realtime-call/{agent_id}")
async def realtime_call(websocket: WebSocket, agent_id: str):
    """WebSocket realtime voice call using Azure OpenAI Realtime API.

    Protocol:
    1. Client sends: {"type": "auth", "token": "..."}
    2. Server sends: {"type": "ready"}
    3. Client sends raw audio chunks (base64 PCM16 24kHz mono)
    4. Server forwards to Azure Realtime, streams audio responses back
    5. Server sends transcripts for both sides
    6. Client sends: {"type": "end"} to hang up
    """
    await websocket.accept()

    settings = websocket.app.state.settings
    engine = websocket.app.state.engine
    session_factory = websocket.app.state.session_factory

    azure_ws = None
    try:
        # Step 1: Authenticate
        auth_msg = await websocket.receive_json()
        if auth_msg.get("type") != "auth":
            await websocket.send_json({"type": "error", "message": "Send auth first"})
            await websocket.close()
            return

        payload = decode_jwt(auth_msg["token"], settings.secret_key)
        if not payload:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close()
            return

        user_id = payload["sub"]

        logger.info("realtime_call_auth_ok", user_id=user_id)

        # Get realtime config from database (set via Settings page)
        from app.app_settings import get_setting

        async with session_factory() as settings_session:
            realtime_url = await get_setting(settings_session, "realtime_url")
            realtime_key = await get_setting(settings_session, "realtime_key")

        logger.info("realtime_call_config", url=realtime_url[:50] if realtime_url else "none")
        logger.info("realtime_call_key", has_key=bool(realtime_key))
        logger.debug("realtime_call_key_len", key_len=len(realtime_key))

        async with session_factory() as session:
            # Load agent
            result = await session.execute(
                select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)
            )
            agent = result.scalar_one_or_none()
            if not agent:
                await websocket.send_json({"type": "error", "message": "Agent not found"})
                await websocket.close()
                return

            # Use existing conversation or create new one for this call
            client_conv_id = auth_msg.get("conversation_id")
            if client_conv_id:
                conv_result = await session.execute(
                    select(Conversation).where(
                        Conversation.id == client_conv_id,
                        Conversation.agent_id == agent_id,
                    )
                )
                conversation = conv_result.scalar_one_or_none()
                if not conversation:
                    conversation = Conversation(
                        agent_id=agent_id,
                        title="Voice call",
                        conversation_type="call",
                    )
                    session.add(conversation)
                    await session.commit()
                    await session.refresh(conversation)
            else:
                conversation = Conversation(
                    agent_id=agent_id,
                    title="Voice call",
                    conversation_type="call",
                )
                session.add(conversation)
                await session.commit()
                await session.refresh(conversation)

            await websocket.send_json({
                "type": "ready",
                "agent_name": agent.name,
                "conversation_id": conversation.id,
            })

            # Build context from previous messages in this conversation
            prev_msgs = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
            )
            prev_history = prev_msgs.scalars().all()
            context_summary = ""
            if prev_history:
                recent = prev_history[-10:]  # Last 10 messages
                context_summary = "\n\nPrevious conversation context:\n"
                for m in recent:
                    context_summary += f"- {m.role}: {m.content[:150]}\n"

            # If no realtime key, fall back to pipeline mode
            if not realtime_key:
                logger.info("realtime_call_pipeline_fallback")
                await _pipeline_call(
                    websocket, session, agent, conversation, user_id
                )
                return

            # Connect to Azure OpenAI Realtime API
            import websockets

            logger.info("realtime_call_connecting")
            headers = {
                "api-key": realtime_key,
                "openai-beta": "realtime=v1",
            }

            async with websockets.connect(
                realtime_url,
                additional_headers=headers,
                close_timeout=3,
                open_timeout=10,
            ) as azure_ws:
                logger.info("realtime_call_connected")

                # Build tool registry using shared service (same tools as chat)
                from app.services import build_tool_registry

                registry = await build_tool_registry(session, user_id)
                rt_tools = []
                tool_instances = {}
                for _name, tool in registry._tools.items():
                    rt_tools.append({
                        "type": "function",
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    })
                    tool_instances[tool.name] = tool

                logger.info("realtime_call_tools", tools=[t['name'] for t in rt_tools])

                # Configure the session (GA API format)
                await azure_ws.send(json.dumps({
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "instructions": agent.system_prompt + context_summary,
                        "audio": {
                            "input": {
                                "format": {
                                    "type": "audio/pcm",
                                    "rate": 24000,
                                },
                                "turn_detection": {
                                    "type": "server_vad",
                                    "threshold": 0.5,
                                    "prefix_padding_ms": 300,
                                    "silence_duration_ms": 500,
                                },
                            },
                            "output": {
                                "format": {
                                    "type": "audio/pcm",
                                    "rate": 24000,
                                },
                            },
                        },
                        "output_modalities": ["audio"],
                        "tools": rt_tools,
                        "max_output_tokens": "inf",
                    },
                }))

                logger.info("realtime_call_session_configured")

                # Wait for session.created/updated from Azure
                first_msg = await asyncio.wait_for(azure_ws.recv(), timeout=5)
                first_event = json.loads(first_msg)
                logger.info(
                    "realtime_call_first_event",
                    event_type=first_event.get('type', 'unknown'),
                )

                # Three tasks: client→azure, azure→client, proactive→client
                async def proactive_to_client():
                    """Push proactive notifications as audio mid-call."""
                    event_bus = getattr(websocket.app.state, "event_bus", None)
                    if not event_bus:
                        return
                    subscription = event_bus.subscribe(user_id)
                    try:
                        while True:
                            event = await subscription.get(timeout=5.0)
                            if event is None:
                                continue
                            # Convert notification to speech
                            from app.edge_tts_provider import edge_tts_synthesize

                            text = f"{event.title}. {event.body}"
                            logger.info(
                                "realtime_call_proactive",
                                title=event.title,
                            )
                            audio = await edge_tts_synthesize(text[:500])
                            wav = _pcm16_to_wav(audio, 24000)
                            await websocket.send_json({
                                "type": "audio_wav",
                                "data": base64.b64encode(wav).decode(),
                            })
                            await websocket.send_json({
                                "type": "response_done",
                                "text": f"💡 {event.title}: {event.body}",
                            })
                    except Exception:
                        pass
                    finally:
                        subscription.close()

                async def client_to_azure():
                    try:
                        while True:
                            msg = await websocket.receive_json()
                            if msg.get("type") == "end":
                                break
                            if msg.get("type") == "audio":
                                # Convert webm→PCM16 24kHz for Azure Realtime
                                import subprocess
                                import tempfile

                                audio_bytes = base64.b64decode(msg["data"])
                                logger.debug("realtime_call_audio_received", size=len(audio_bytes))
                                with tempfile.NamedTemporaryFile(
                                    suffix=".webm", delete=False
                                ) as f:
                                    f.write(audio_bytes)
                                    tmp_in = f.name
                                try:
                                    result = subprocess.run(
                                        [
                                            "ffmpeg", "-y", "-i", tmp_in,
                                            "-ar", "24000", "-ac", "1",
                                            "-f", "s16le", "-acodec", "pcm_s16le",
                                            "pipe:1",
                                        ],
                                        capture_output=True,
                                        timeout=10,
                                    )
                                    if result.returncode == 0 and result.stdout:
                                        # Only send if enough audio (>2400 bytes = 100ms at 24kHz)
                                        if len(result.stdout) > 2400:
                                            pcm_b64 = base64.b64encode(
                                                result.stdout
                                            ).decode()
                                            logger.debug(
                                                "realtime_call_pcm_sent",
                                                size=len(result.stdout),
                                            )
                                            await azure_ws.send(json.dumps({
                                                "type": "input_audio_buffer.append",
                                                "audio": pcm_b64,
                                            }))
                                            await azure_ws.send(json.dumps({
                                                "type": "input_audio_buffer.commit",
                                            }))
                                    else:
                                        logger.warning(
                                            "realtime_call_ffmpeg_error",
                                            returncode=result.returncode,
                                        )
                                finally:
                                    Path(tmp_in).unlink(missing_ok=True)
                    except WebSocketDisconnect:
                        pass

                async def azure_to_client():
                    full_response = ""
                    audio_chunks: list[bytes] = []
                    try:
                        async for raw in azure_ws:
                            event = json.loads(raw)
                            etype = event.get("type", "")
                            logger.debug("realtime_call_azure_event", event_type=etype)

                            if etype == "response.output_audio.delta":
                                # Collect audio on server side
                                pcm = base64.b64decode(event.get("delta", ""))
                                audio_chunks.append(pcm)

                            elif etype == "response.output_audio_transcript.delta":
                                full_response += event.get("delta", "")
                                await websocket.send_json({
                                    "type": "response_transcript",
                                    "text": full_response,
                                })

                            elif etype == "response.output_audio_transcript.done":
                                text = event.get("transcript", full_response)
                                session.add(Message(
                                    conversation_id=conversation.id,
                                    role="assistant",
                                    content=text,
                                ))
                                await session.commit()
                                full_response = text

                            elif etype == "response.done":
                                # Build WAV on server and send as one blob
                                if audio_chunks:
                                    pcm_all = b"".join(audio_chunks)
                                    wav = _pcm16_to_wav(pcm_all, 24000)
                                    wav_b64 = base64.b64encode(wav).decode()
                                    logger.info("realtime_call_wav_sent", size=len(wav))
                                    await websocket.send_json({
                                        "type": "audio_wav",
                                        "data": wav_b64,
                                    })
                                    audio_chunks = []
                                await websocket.send_json({
                                    "type": "response_done",
                                    "text": full_response,
                                })
                                full_response = ""

                            elif etype == "conversation.item.input_audio_transcription.completed":
                                text = event.get("transcript", "")
                                logger.info("realtime_call_user_transcript", text_len=len(text))
                                await websocket.send_json({
                                    "type": "user_transcript",
                                    "text": text,
                                })
                                session.add(Message(
                                    conversation_id=conversation.id,
                                    role="user",
                                    content=text,
                                ))
                                await session.commit()

                            elif etype == "response.function_call_arguments.done":
                                # Azure wants to call a tool
                                call_id = event.get("call_id", "")
                                fn_name = event.get("name", "")
                                fn_args = event.get("arguments", "{}")
                                logger.info("realtime_call_tool_call", tool=fn_name)

                                tool = tool_instances.get(fn_name)
                                if tool:
                                    try:
                                        args = json.loads(fn_args)
                                        result_text = await tool.execute(args)
                                    except Exception as e:
                                        result_text = json.dumps({"error": str(e)})
                                else:
                                    result_text = json.dumps({"error": f"Unknown tool: {fn_name}"})

                                logger.info(
                                    "realtime_call_tool_result",
                                    tool=fn_name,
                                    result_len=len(result_text),
                                )

                                # Send result back to Azure
                                await azure_ws.send(json.dumps({
                                    "type": "conversation.item.create",
                                    "item": {
                                        "type": "function_call_output",
                                        "call_id": call_id,
                                        "output": result_text,
                                    },
                                }))
                                # Trigger a new response
                                await azure_ws.send(json.dumps({
                                    "type": "response.create",
                                }))

                            elif etype == "error":
                                err = event.get("error", {})
                                err_msg = err.get("message", str(err))
                                # Buffer-too-small is non-fatal, just log it
                                if "buffer too small" in err_msg.lower():
                                    logger.debug(
                                        "realtime_call_buffer_small",
                                    )
                                else:
                                    logger.warning(
                                        "realtime_call_azure_error",
                                        error=err_msg,
                                    )
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": err_msg,
                                    })

                    except Exception:
                        pass

                # Run all three tasks
                await asyncio.gather(
                    client_to_azure(),
                    azure_to_client(),
                    proactive_to_client(),
                    return_exceptions=True,
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import traceback

        traceback.print_exc()
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await engine.dispose()


async def _pipeline_call(
    websocket: WebSocket,
    session,  # noqa: ANN001
    agent,  # noqa: ANN001
    conversation,  # noqa: ANN001
    user_id: str,
) -> None:
    """Fallback pipeline mode: Whisper STT → LLM → Edge TTS."""
    from app.edge_tts_provider import edge_tts_synthesize
    from app.local_stt import transcribe_local
    from app.tools import create_default_registry

    tools = create_default_registry()
    messages = [{"role": "system", "content": agent.system_prompt}]

    while True:
        msg = await websocket.receive_json()
        if msg.get("type") == "end":
            await websocket.send_json({"type": "ended"})
            break

        if msg.get("type") == "audio":
            audio_bytes = base64.b64decode(msg["data"])

            await websocket.send_json({"type": "status", "text": "Listening..."})
            user_text = await transcribe_local(audio_bytes)

            if not user_text.strip():
                continue

            await websocket.send_json({"type": "user_transcript", "text": user_text})
            messages.append({"role": "user", "content": user_text})

            # Save user message
            session.add(Message(
                conversation_id=conversation.id,
                role="user",
                content=user_text,
            ))
            await session.commit()

            await websocket.send_json({"type": "status", "text": "Thinking..."})

            # Get LLM response
            from sqlalchemy import select as sel

            from app.agent_loop_anthropic import run_anthropic_stream
            from app.models import Provider

            prov_result = await session.execute(
                sel(Provider).where(Provider.id == agent.provider_id)
            )
            provider = prov_result.scalar_one_or_none()

            full_response = ""
            if provider and provider.api_format == "anthropic":
                async for event in run_anthropic_stream(
                    base_url=provider.base_url,
                    api_key=provider.api_key_encrypted,
                    model=provider.model,
                    messages=messages,
                    tools=tools,
                    system_prompt=agent.system_prompt,
                ):
                    if event["type"] in ("token", "done"):
                        if event["type"] == "done":
                            full_response = event["content"]
                        else:
                            full_response += event["content"]

            messages.append({"role": "assistant", "content": full_response})
            await websocket.send_json({"type": "response_done", "text": full_response})

            session.add(Message(
                conversation_id=conversation.id,
                role="assistant",
                content=full_response,
            ))
            await session.commit()

            # TTS
            await websocket.send_json({"type": "status", "text": "Speaking..."})
            audio_out = await edge_tts_synthesize(full_response[:2000])
            await websocket.send_json({
                "type": "audio_mp3",
                "data": base64.b64encode(audio_out).decode(),
            })


def _pcm16_to_wav(pcm_data: bytes, sample_rate: int) -> bytes:
    """Wrap raw PCM16 mono in a WAV header."""
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = len(pcm_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_data
