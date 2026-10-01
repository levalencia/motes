"""Memory tool — save and recall facts about the user.

The agent can use this to remember things the user tells it:
'recuerda que vivo en Bruselas' → saves 'User lives in Brussels'
"""

from __future__ import annotations

import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import Memory
from app.tools import Tool

logger = structlog.get_logger()


class MemorySaveTool(Tool):
    """Save a fact about the user to persistent memory."""

    name = "memory_save"
    description = (
        "Save an important fact about the user to memory. Use this when the user "
        "tells you something personal (name, location, preferences, family, work) "
        "or asks you to remember something. Be concise — store facts, not conversations."
    )
    parameters = {
        "type": "object",
        "properties": {
            "fact": {
                "type": "string",
                "description": "The fact to remember, e.g., 'User lives in Brussels'",
            },
            "category": {
                "type": "string",
                "description": "Category: personal, work, preference, family, health, other",
                "enum": ["personal", "work", "preference", "family", "health", "other"],
            },
        },
        "required": ["fact"],
    }

    def __init__(self, session: AsyncSession, agent_id: str):
        self._session = session
        self._agent_id = agent_id

    async def execute(self, arguments: dict) -> str:
        fact = arguments.get("fact", "")
        category = arguments.get("category", "general")
        if not fact:
            return json.dumps({"error": "No fact provided"})

        memory = Memory(
            id=str(uuid.uuid4()),
            agent_id=self._agent_id,
            category=category,
            content=fact,
        )
        self._session.add(memory)
        await self._session.commit()
        logger.info("memory_saved", fact=fact[:50], category=category)
        return json.dumps({"status": "remembered", "fact": fact})


class MemoryRecallTool(Tool):
    """Recall saved facts about the user."""

    name = "memory_recall"
    description = (
        "Search your memory for facts about the user. Use this when you need to "
        "remember something the user told you before, or when context about the user "
        "would help you give a better answer."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for, e.g., 'location', 'family', 'work'",
            },
        },
        "required": ["query"],
    }

    def __init__(self, session: AsyncSession, agent_id: str):
        self._session = session
        self._agent_id = agent_id

    async def execute(self, arguments: dict) -> str:
        query = arguments.get("query", "").lower()
        result = await self._session.execute(
            select(Memory).where(Memory.agent_id == self._agent_id)
        )
        memories = result.scalars().all()

        # Simple keyword matching
        matches = [
            m for m in memories
            if query in m.content.lower() or query in m.category.lower()
        ]
        if not matches:
            # Return all if no specific match
            matches = memories[-10:]  # Last 10

        facts = [{"fact": m.content, "category": m.category} for m in matches]
        return json.dumps({"memories": facts, "count": len(facts)})
