"""Anthropic Messages API agent loop with tool calling and streaming."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from app.tools import ToolRegistry

logger = structlog.get_logger()

MAX_TOOL_ROUNDS = 10


async def run_anthropic_stream(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: ToolRegistry,
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    system_prompt: str = "",
    session: Any = None,
    agent_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Run Anthropic Messages API with streaming. Same event format as OpenAI loop."""
    url = base_url.rstrip("/") + "/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    # Convert tool schemas to Anthropic format
    tool_schemas = []
    for tool in tools.list_tools():
        tool_schemas.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        })

    # Separate system from messages (Anthropic uses top-level system)
    anthropic_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        else:
            anthropic_messages.append(msg)

    for _round in range(MAX_TOOL_ROUNDS):
        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if tool_schemas:
            payload["tools"] = tool_schemas

        try:
            full_text = ""
            tool_uses: list[dict[str, Any]] = []
            current_tool_input = ""
            current_tool_name = ""
            current_tool_id = ""

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.send(
                    client.build_request("POST", url, json=payload, headers=headers),
                    stream=True,
                )
                if resp.status_code != 200:
                    body = await resp.aread()
                    err = f"HTTP {resp.status_code}: {body.decode()[:500]}"
                    yield {"type": "error", "message": err}
                    return

                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = event.get("type", "")

                    if event_type == "content_block_start":
                        block = event.get("content_block", {})
                        if block.get("type") == "tool_use":
                            current_tool_id = block.get("id", "")
                            current_tool_name = block.get("name", "")
                            current_tool_input = ""

                    elif event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            full_text += text
                            yield {"type": "token", "content": text}
                        elif delta.get("type") == "input_json_delta":
                            current_tool_input += delta.get(
                                "partial_json", ""
                            )

                    elif event_type == "content_block_stop":
                        if current_tool_name:
                            tool_uses.append({
                                "id": current_tool_id,
                                "name": current_tool_name,
                                "input": current_tool_input,
                            })
                            current_tool_name = ""

                    elif event_type == "message_stop":
                        pass

                await resp.aclose()

            # No tool calls — done
            if not tool_uses:
                yield {"type": "done", "content": full_text}
                return

            # Build assistant message with tool_use blocks
            content_blocks: list[dict[str, Any]] = []
            if full_text:
                content_blocks.append({"type": "text", "text": full_text})
            for tu in tool_uses:
                try:
                    input_obj = json.loads(tu["input"]) if tu["input"] else {}
                except json.JSONDecodeError:
                    input_obj = {}
                content_blocks.append({
                    "type": "tool_use",
                    "id": tu["id"],
                    "name": tu["name"],
                    "input": input_obj,
                })

            anthropic_messages.append({
                "role": "assistant",
                "content": content_blocks,
            })

            # Execute tools
            tool_results = []
            for tu in tool_uses:
                try:
                    args = json.loads(tu["input"]) if tu["input"] else {}
                except json.JSONDecodeError:
                    args = {}

                yield {"type": "tool_call", "name": tu["name"], "arguments": args}

                tool = tools.get(tu["name"])
                if tool is None:
                    result = json.dumps({"error": f"Unknown tool: {tu['name']}"})
                else:
                    # Approval gate
                    if session and agent_id:
                        from app.approvals import (
                            ActionRisk,
                            classify_action,
                            create_approval_request,
                        )

                        risk = await classify_action(session, agent_id, tu["name"])
                        if risk == ActionRisk.FORBIDDEN:
                            result = json.dumps({"error": f"Tool '{tu['name']}' is forbidden"})
                            yield {"type": "tool_result", "name": tu["name"], "result": result}
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tu["id"],
                                "content": result,
                            })
                            continue
                        elif risk == ActionRisk.NEEDS_APPROVAL:
                            approval = await create_approval_request(
                                session, agent_id, tu["name"], json.dumps(args),
                            )
                            yield {
                                "type": "approval_needed",
                                "approval_id": approval.id,
                                "tool_name": tu["name"],
                                "arguments": args,
                            }
                            import asyncio

                            from app.approvals import ApprovalStatus

                            approved = False
                            for _ in range(60):
                                await asyncio.sleep(5)
                                session.expire(approval)
                                await session.refresh(approval)
                                if approval.status == ApprovalStatus.APPROVED:
                                    approved = True
                                    break
                                elif approval.status == ApprovalStatus.DENIED:
                                    break
                            if not approved:
                                result = json.dumps({
                                    "status": "denied",
                                    "message": "User denied or timed out",
                                })
                                yield {"type": "tool_result", "name": tu["name"], "result": result}
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tu["id"],
                                    "content": result,
                                })
                                continue
                    # Safe or approved — execute
                    try:
                        result = await tool.execute(args)
                    except Exception as exc:
                        result = json.dumps({"error": f"Tool error: {exc}"})

                yield {"type": "tool_result", "name": tu["name"], "result": result}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": result,
                })

            anthropic_messages.append({
                "role": "user",
                "content": tool_results,
            })

            names = [tu["name"] for tu in tool_uses]
            logger.info(
                "agent_tool_round", round=_round + 1, tools_called=names
            )

        except httpx.TimeoutException:
            yield {"type": "error", "message": "LLM provider timed out"}
            return
        except Exception as exc:
            yield {"type": "error", "message": f"Agent loop error: {exc}"}
            return

    yield {
        "type": "error",
        "message": f"Exceeded max tool rounds ({MAX_TOOL_ROUNDS})",
    }
