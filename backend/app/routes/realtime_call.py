"""Azure OpenAI Realtime API — true bidirectional voice conversation.

Uses WebSocket to stream audio in both directions. Sub-second latency.
Model: gpt-realtime-2.1-mini on Azure.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth import decode_jwt
from app.config import get_settings
from app.database import create_engine, create_session_factory
from app.models import Agent, Conversation, Message

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

    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

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

        # Get realtime config from database (set via Settings page)
        from app.app_settings import get_setting

        async with session_factory() as settings_session:
            realtime_url = await get_setting(settings_session, "realtime_url")
            realtime_key = await get_setting(settings_session, "realtime_key")

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

            # Create a conversation for this call
            conversation = Conversation(
                agent_id=agent_id,
                title="Voice call",
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

            await websocket.send_json({
                "type": "ready",
                "agent_name": agent.name,
                "conversation_id": conversation.id,
            })

            # If no realtime key, fall back to pipeline mode
            if not realtime_key:
                await _pipeline_call(
                    websocket, session, agent, conversation, user_id
                )
                return

            # Connect to Azure OpenAI Realtime API
            import websockets

            headers = {
                "api-key": realtime_key,
                "openai-beta": "realtime=v1",
            }

            async with websockets.connect(
                realtime_url,
                additional_headers=headers,
            ) as azure_ws:
                # Configure the session (GA API requires session.type)
                await azure_ws.send(json.dumps({
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "instructions": agent.system_prompt,
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 500,
                            "create_response": True,
                        },
                    },
                }))

                # Two tasks: forward client→azure, forward azure→client
                async def client_to_azure():
                    try:
                        while True:
                            msg = await websocket.receive_json()
                            if msg.get("type") == "end":
                                break
                            if msg.get("type") == "audio":
                                await azure_ws.send(json.dumps({
                                    "type": "input_audio_buffer.append",
                                    "audio": msg["data"],
                                }))
                    except WebSocketDisconnect:
                        pass

                async def azure_to_client():
                    full_response = ""
                    try:
                        async for raw in azure_ws:
                            event = json.loads(raw)
                            etype = event.get("type", "")

                            if etype == "response.audio.delta":
                                # Stream audio back to client
                                await websocket.send_json({
                                    "type": "audio",
                                    "data": event.get("delta", ""),
                                })

                            elif etype == "response.audio_transcript.delta":
                                full_response += event.get("delta", "")
                                await websocket.send_json({
                                    "type": "response_transcript",
                                    "text": full_response,
                                })

                            elif etype == "response.audio_transcript.done":
                                text = event.get("transcript", full_response)
                                await websocket.send_json({
                                    "type": "response_done",
                                    "text": text,
                                })
                                # Save to conversation
                                session.add(Message(
                                    conversation_id=conversation.id,
                                    role="assistant",
                                    content=text,
                                ))
                                await session.commit()
                                full_response = ""

                            elif etype == "conversation.item.input_audio_transcription.completed":
                                text = event.get("transcript", "")
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

                            elif etype == "error":
                                err = event.get("error", {})
                                await websocket.send_json({
                                    "type": "error",
                                    "message": err.get("message", str(err)),
                                })

                    except Exception:
                        pass

                # Run both tasks
                await asyncio.gather(
                    client_to_azure(),
                    azure_to_client(),
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
