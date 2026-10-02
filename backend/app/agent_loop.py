"""ReAct-style agent reasoning loop with tool calling and streaming."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from app.tools import ToolRegistry

logger = structlog.get_logger()

MAX_TOOL_ROUNDS = 10  # prevent infinite loops


async def run_agent_stream(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: ToolRegistry,
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    session: Any = None,
    agent_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Run the agent loop with streaming. Yields SSE-friendly events.

    Event types:
      - {"type": "token", "content": "..."} -- streamed text token
      - {"type": "tool_call", "name": "...", "arguments": {...}}
      - {"type": "tool_result", "name": "...", "result": "..."}
      - {"type": "done", "content": "..."} -- final complete response
      - {"type": "error", "message": "..."} -- error occurred
    """
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    tool_schemas = tools.to_openai_tools() if tools.list_tools() else None

    for _round in range(MAX_TOOL_ROUNDS):
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tool_schemas:
            payload["tools"] = tool_schemas

        try:
            full_content = ""
            tool_calls: list[dict[str, Any]] = []

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
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})

                    # Text content
                    if delta.get("content"):
                        full_content += delta["content"]
                        yield {"type": "token", "content": delta["content"]}

                    # Tool calls (accumulated across chunks)
                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            idx = tc.get("index", 0)
                            while len(tool_calls) <= idx:
                                tool_calls.append(
                                    {"id": "", "name": "", "arguments": ""}
                                )
                            if tc.get("id"):
                                tool_calls[idx]["id"] = tc["id"]
                            fn = tc.get("function", {})
                            if fn.get("name"):
                                tool_calls[idx]["name"] = fn["name"]
                            if fn.get("arguments"):
                                tool_calls[idx]["arguments"] += fn["arguments"]

                await resp.aclose()

            # If no tool calls, we're done
            if not tool_calls:
                yield {"type": "done", "content": full_content}
                return

            # Process tool calls
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": full_content or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in tool_calls:
                tool_name = tc["name"]
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}

                yield {"type": "tool_call", "name": tool_name, "arguments": args}

                tool = tools.get(tool_name)
                if tool is None:
                    result = json.dumps({"error": f"Unknown tool: {tool_name}"})
                else:
                    # Approval gate: check if tool needs user approval
                    if session and agent_id:
                        from app.approvals import (
                            ActionRisk,
                            classify_action,
                            create_approval_request,
                        )

                        risk = await classify_action(session, agent_id, tool_name)
                        if risk == ActionRisk.FORBIDDEN:
                            result = json.dumps({"error": f"Tool '{tool_name}' is forbidden by policy"})
                            yield {"type": "tool_result", "name": tool_name, "result": result}
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result,
                            })
                            continue
                        elif risk == ActionRisk.NEEDS_APPROVAL:
                            # Create approval request and wait
                            approval = await create_approval_request(
                                session, agent_id, tool_name, json.dumps(args),
                            )
                            yield {
                                "type": "approval_needed",
                                "approval_id": approval.id,
                                "tool_name": tool_name,
                                "arguments": args,
                            }
                            # Poll for approval (max 5 minutes)
                            import asyncio

                            from app.approvals import ApprovalStatus

                            approved = False
                            for _ in range(60):  # 60 * 5s = 5 minutes
                                await asyncio.sleep(5)
                                await session.refresh(approval)
                                if approval.status == ApprovalStatus.APPROVED:
                                    approved = True
                                    break
                                elif approval.status == ApprovalStatus.DENIED:
                                    break
                            if not approved:
                                result = json.dumps({
                                    "status": "denied",
                                    "message": "User denied or approval timed out",
                                })
                                yield {"type": "tool_result", "name": tool_name, "result": result}
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": result,
                                })
                                continue
                    # Safe or approved — execute
                    try:
                        result = await tool.execute(args)
                    except Exception as exc:
                        result = json.dumps({"error": f"Tool error: {exc}"})

                yield {"type": "tool_result", "name": tool_name, "result": result}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            names = [tc["name"] for tc in tool_calls]
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


async def run_agent_sync(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: ToolRegistry,
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Non-streaming: runs the full loop, returns the final text."""
    final_content = ""
    async for event in run_agent_stream(
        base_url, api_key, model, messages, tools,
        temperature=temperature, max_tokens=max_tokens,
    ):
        if event["type"] == "done":
            final_content = event["content"]
        elif event["type"] == "error":
            raise RuntimeError(event["message"])
    return final_content
