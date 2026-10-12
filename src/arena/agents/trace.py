"""Logs every model request and reply through the framework's chat middleware (SRS LOG-2).

The middleware sees each provider round trip, including the rounds forced by the function
invocation limit. It records what the model was sent and what it returned, so a call to a
tool the agent was never offered appears in the reply, even though the framework answers it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from agent_framework import ChatContext, ChatMiddleware, ChatResponse, Content

from arena.events.model import Event, EventSink


def _tool_name(tool: object) -> str:
    return str(getattr(tool, "name", tool))


def _content(content: Content) -> dict[str, object]:
    if content.type == "text":
        return {"type": "text", "text": content.text or ""}
    if content.type == "function_call":
        return {
            "type": "function_call",
            "call_id": content.call_id,
            "name": content.name,
            "arguments": dict(content.parse_arguments() or {}),
        }
    if content.type == "function_result":
        return {
            "type": "function_result",
            "call_id": content.call_id,
            "result": str(content.result or ""),
        }
    return {"type": str(content.type)}


class ModelTrace(ChatMiddleware):
    def __init__(self, sink: EventSink, *, agent_id: str) -> None:
        self._sink = sink
        self._agent_id = agent_id

    async def process(
        self,
        context: ChatContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        options: Mapping[str, Any] = context.options or {}
        tools: list[object] = list(options.get("tools") or [])
        self._sink.emit(
            Event(
                type="model_request",
                agent_id=self._agent_id,
                data={
                    "instructions": options.get("instructions"),
                    "tools": [_tool_name(t) for t in tools],
                    "messages": [
                        {"role": m.role, "contents": [_content(c) for c in m.contents]}
                        for m in context.messages
                    ],
                },
            )
        )
        await call_next()

        text = ""
        calls: list[dict[str, object]] = []
        response = context.result
        if isinstance(response, ChatResponse):
            text = response.text
            for message in response.messages:
                for content in message.contents:
                    if content.type == "function_call":
                        calls.append(
                            {
                                "name": str(content.name or ""),
                                "arguments": dict(content.parse_arguments() or {}),
                            }
                        )
        self._sink.emit(
            Event(
                type="model_response",
                agent_id=self._agent_id,
                data={
                    "text": text,
                    "tool_calls": calls,
                    "model": getattr(response, "model", None),
                    "finish_reason": str(getattr(response, "finish_reason", None)),
                },
            )
        )
