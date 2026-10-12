"""A scripted chat client that stands in for a real model in tests and dry runs.

Each call to the model pops the next scripted reply. Every request is recorded, so tests
can assert exactly what the model would have seen (instructions, tools, history).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from agent_framework import (
    BaseChatClient,
    ChatMiddlewareLayer,
    ChatMiddlewareTypes,
    ChatResponse,
    Content,
    FunctionInvocationLayer,
    Message,
)

EXHAUSTED_REPLY = "(no scripted reply left)"


@dataclass(frozen=True)
class RecordedRequest:
    """What one model call received."""

    instructions: str | None
    tool_names: tuple[str, ...]
    tool_choice: str | None
    messages: tuple[Message, ...] = field(repr=False)


def tool_call(call_id: str, name: str, **arguments: Any) -> Content:
    """Build a scripted tool call."""
    return Content.from_function_call(call_id, name, arguments=json.dumps(arguments))


class ScriptedChatClient(
    FunctionInvocationLayer[Any], ChatMiddlewareLayer[Any], BaseChatClient[Any]
):
    """Replays scripted replies. A reply is a list of text strings and tool calls."""

    OTEL_PROVIDER_NAME = "scripted"

    def __init__(
        self,
        replies: Sequence[Sequence[Content | str]],
        *,
        max_iterations: int = 10,
        middleware: Sequence[ChatMiddlewareTypes] | None = None,
        usage_per_call: int = 0,
    ) -> None:
        self._usage_per_call = usage_per_call
        super().__init__(
            middleware=middleware,
            function_invocation_configuration={
                "max_iterations": max_iterations,
                "allow_concurrent_invocation": False,
            },
        )
        self._replies: list[Sequence[Content | str]] = list(replies)
        self.requests: list[RecordedRequest] = []

    def add_replies(self, replies: Sequence[Sequence[Content | str]]) -> None:
        self._replies.extend(replies)

    async def _inner_get_response(  # type: ignore[override]
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: dict[str, Any],
        **kwargs: Any,
    ) -> ChatResponse[Any]:
        if stream:
            raise NotImplementedError("ScriptedChatClient does not stream")
        tools: list[Any] = list(options.get("tools") or [])
        self.requests.append(
            RecordedRequest(
                instructions=options.get("instructions"),
                tool_names=tuple(str(getattr(t, "name", t)) for t in tools),
                tool_choice=_tool_choice_mode(options.get("tool_choice")),
                messages=tuple(messages),
            )
        )
        reply = self._replies.pop(0) if self._replies else [EXHAUSTED_REPLY]
        contents = [Content.from_text(c) if isinstance(c, str) else c for c in reply]
        usage = {"total_token_count": self._usage_per_call} if self._usage_per_call else None
        return ChatResponse(
            messages=[Message(role="assistant", contents=contents)],
            usage_details=usage,  # type: ignore[arg-type]
        )


def _tool_choice_mode(choice: Any) -> str | None:
    if choice is None or isinstance(choice, str):
        return choice
    if isinstance(choice, dict):
        mode = choice.get("mode")  # type: ignore[union-attr]
        return None if mode is None else str(mode)  # type: ignore[arg-type]
    return str(choice)
