"""Shared test helpers."""

from __future__ import annotations

import asyncio
from typing import Any

from agent_framework import Agent, AgentResponse, AgentSession


def run_step(agent: Agent[Any], text: str, session: AgentSession) -> AgentResponse[Any]:
    """Run one agent step synchronously."""

    async def go() -> AgentResponse[Any]:
        return await agent.run(text, session=session)

    return asyncio.run(go())
