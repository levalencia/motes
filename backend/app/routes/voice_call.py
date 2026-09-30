"""Voice call endpoint — real-time voice conversation via WebSocket.

Approach 1 (pipeline): mic audio → local Whisper STT → LLM → Edge TTS → speaker
Approach 2 (future): OpenAI Realtime API WebSocket for sub-second latency
"""

from __future__ import annotations

import contextlib
from pathlib import Path

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth import decode_jwt
from app.edge_tts_provider import edge_tts_synthesize
from app.local_stt import transcribe_local
from app.models import Agent, Provider
from app.tools import create_default_registry

logger = structlog.get_logger()

router = APIRouter(tags=["voice-call"])


@router.websocket("/api/voice-call/{agent_id}")
async def voice_call(websocket: WebSocket, agent_id: str):
    """WebSocket voice call — bidirectional audio conversation.

    Protocol:
    1. Client sends: {"type": "auth", "token": "..."}
    2. Server sends: {"type": "ready", "agent_name": "..."}
    3. Client sends: {"type": "audio", "data": "<base64 webm>"}
    4. Server sends: {"type": "transcript", "text": "..."}  (what user said)
    5. Server sends: {"type": "response", "text": "..."}    (agent reply text)
    6. Server sends: {"type": "audio", "data": "<base64 mp3>"} (agent reply audio)
    7. Client sends: {"type": "end"} to hang up
    """
    await websocket.accept()

    settings = websocket.app.state.settings
    engine = websocket.app.state.engine
    session_factory = websocket.app.state.session_factory

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

        async with session_factory() as session:
            # Load agent + provider
            result = await session.execute(
                select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)
            )
            agent = result.scalar_one_or_none()
            if not agent:
                await websocket.send_json({"type": "error", "message": "Agent not found"})
                await websocket.close()
                return

            prov_result = await session.execute(
                select(Provider).where(Provider.id == agent.provider_id)
            )
            provider = prov_result.scalar_one_or_none()

            await websocket.send_json({
                "type": "ready",
                "agent_name": agent.name,
            })

            # Conversation history for context
            messages = [{"role": "system", "content": agent.system_prompt}]

            # Load ALL tools (same as chat route)
            tools = create_default_registry()

            # File tools
            from app.file_tools import (
                FileDownloadUrlTool,
                FileListTool,
                FileReadTool,
                FileSearchTool,
                PptxAddSlideTool,
                PptxInspectTool,
            )

            home_dir = str(Path.home())
            tools.register(FileListTool(home_dir))
            tools.register(FileReadTool(home_dir))
            tools.register(FileSearchTool(home_dir))
            tools.register(PptxInspectTool(home_dir))
            tools.register(PptxAddSlideTool(home_dir))
            tools.register(FileDownloadUrlTool(home_dir))

            # Web search
            import os

            from app.web_search_tool import WebSearchTool

            tools.register(WebSearchTool(os.environ.get("BRAVE_SEARCH_API_KEY", "")))

            # Gmail/Calendar (with auto-refresh)
            from app.token_refresh import get_valid_token

            gmail_access = await get_valid_token(session, user_id, "gmail")
            if gmail_access:
                from app.google_tools import GmailReadTool, GmailSendTool

                tools.register(GmailReadTool(gmail_access))
                tools.register(GmailSendTool(gmail_access))

            calendar_access = await get_valid_token(session, user_id, "calendar")
            if calendar_access:
                from app.google_tools import CalendarCreateTool, CalendarListTool

                tools.register(CalendarListTool(calendar_access))
                tools.register(CalendarCreateTool(calendar_access))

            # Voice call loop
            while True:
                msg = await websocket.receive_json()

                if msg.get("type") == "end":
                    await websocket.send_json({"type": "ended"})
                    break

                if msg.get("type") == "audio":
                    import base64

                    # Decode audio
                    audio_bytes = base64.b64decode(msg["data"])

                    # STT: transcribe what user said
                    await websocket.send_json({"type": "thinking", "step": "transcribing"})
                    user_text = await transcribe_local(audio_bytes)

                    if not user_text.strip():
                        await websocket.send_json({
                            "type": "transcript",
                            "text": "(silence)",
                        })
                        continue

                    await websocket.send_json({
                        "type": "transcript",
                        "text": user_text,
                    })

                    # Add to history
                    messages.append({"role": "user", "content": user_text})

                    # LLM: get agent response
                    await websocket.send_json({"type": "thinking", "step": "responding"})

                    if provider and provider.api_format == "anthropic":
                        from app.agent_loop_anthropic import run_anthropic_stream

                        full_response = ""
                        async for event in run_anthropic_stream(
                            base_url=provider.base_url,
                            api_key=provider.api_key_encrypted,
                            model=provider.model,
                            messages=messages,
                            tools=tools,
                            system_prompt=agent.system_prompt,
                        ):
                            if event["type"] == "token":
                                full_response += event["content"]
                            elif event["type"] == "done":
                                full_response = event["content"]
                    else:
                        from app.agent_loop import run_agent_stream

                        full_response = ""
                        async for event in run_agent_stream(
                            base_url=provider.base_url if provider else "",
                            api_key=provider.api_key_encrypted if provider else "",
                            model=provider.model if provider else "",
                            messages=messages,
                            tools=tools,
                        ):
                            if event["type"] == "token":
                                full_response += event["content"]
                            elif event["type"] == "done":
                                full_response = event["content"]

                    messages.append({"role": "assistant", "content": full_response})

                    await websocket.send_json({
                        "type": "response",
                        "text": full_response,
                    })

                    # TTS: convert to speech
                    await websocket.send_json({"type": "thinking", "step": "speaking"})
                    tts_voice = msg.get("voice", "en-US-AriaNeural")
                    audio_out = await edge_tts_synthesize(
                        full_response[:2000], tts_voice
                    )

                    await websocket.send_json({
                        "type": "audio",
                        "data": base64.b64encode(audio_out).decode(),
                    })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await engine.dispose()
