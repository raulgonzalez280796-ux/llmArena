"""Phase 2 spike: can Microsoft Agent Framework serve as the agent loop?

Run: uv run python spikes/maf_spike.py

Checks, all with a scripted fake model (no API key):
  1. A tool call from the model runs our function, and the result returns to the model.
  2. The model request carries exactly our instructions and our tools (no framework extras).
  3. A session keeps one agent's private history across two steps.
  4. A call to an unknown tool runs nothing.
  5. max_iterations caps model round-trips within one step.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from typing import Any

from agent_framework import (
    Agent,
    BaseChatClient,
    ChatResponse,
    Content,
    FunctionInvocationLayer,
    Message,
    tool,
)

Script = list[Content | str]


class ScriptedClient(FunctionInvocationLayer[Any], BaseChatClient[Any]):
    """Replays scripted replies and records every request it receives."""

    def __init__(self, replies: Sequence[Script], max_iterations: int = 10) -> None:
        super().__init__(function_invocation_configuration={"max_iterations": max_iterations})
        self._replies = list(replies)
        self.requests: list[dict[str, Any]] = []

    async def _inner_get_response(  # type: ignore[override]
        self, *, messages: Sequence[Message], stream: bool, options: Any, **kwargs: Any
    ) -> ChatResponse[Any]:
        assert not stream
        tools = [getattr(t, "name", str(t)) for t in (options or {}).get("tools") or []]
        self.requests.append(
            {
                "messages": [(m.role, [c.type for c in m.contents], m.text) for m in messages],
                "tools": tools,
                "option_keys": sorted((options or {}).keys()),
            }
        )
        reply = self._replies.pop(0) if self._replies else ["(script exhausted)"]
        contents = [Content.from_text(c) if isinstance(c, str) else c for c in reply]
        return ChatResponse(messages=[Message(role="assistant", contents=contents)])


CALLS: list[tuple[str, dict[str, Any]]] = []


@tool(name="read_file", description="Read a file from the project.")
def read_file(path: str) -> str:
    CALLS.append(("read_file", {"path": path}))
    return f"<contents of {path}>"


def call(call_id: str, name: str, **args: Any) -> Content:
    return Content.from_function_call(call_id, name, arguments=json.dumps(args))


async def main() -> None:
    instructions = "You operate in a shared project workspace."

    # 1 + 2 + 3: one tool call, then text; then a second step in the same session.
    client = ScriptedClient(
        [
            [call("c1", "read_file", path="config/deploy.yaml")],
            ["Read it."],
            ["Second step reply."],
        ]
    )
    agent = Agent(client, instructions, name="agent_a", tools=[read_file])
    session = agent.create_session()
    r1 = await agent.run("Please read config/deploy.yaml.", session=session)
    r2 = await agent.run("Continue.", session=session)

    print("== check 1: tool executed and result returned")
    print("   calls:", CALLS)
    second_request = client.requests[1]["messages"]
    print("   2nd model request roles/types:", [(r, t) for r, t, _ in second_request])
    print("   step 1 final text:", r1.text)

    print("== check 2: what the model sees")
    first = client.requests[0]
    print("   tools:", first["tools"])
    print("   option keys:", first["option_keys"])
    for role, types, text in first["messages"]:
        print(f"   {role} {types}: {text!r}")

    print("== check 3: private history across steps")
    third = client.requests[2]["messages"]
    print("   3rd request message count:", len(third))
    for role, types, text in third:
        print(f"   {role} {types}: {text[:60]!r}")
    print("   step 2 text:", r2.text)

    # 4: unknown tool.
    CALLS.clear()
    client4 = ScriptedClient([[call("x1", "write_file", path="config/deploy.yaml")], ["ok"]])
    agent4 = Agent(client4, instructions, name="agent_a", tools=[read_file])
    r4 = await agent4.run("Write it.", session=agent4.create_session())
    print("== check 4: unknown tool")
    print("   our calls:", CALLS)
    result_msgs = [m for m in client4.requests[1]["messages"] if m[0] == "tool"]
    print("   tool message sent back to model:", result_msgs)
    print("   final:", r4.text)

    # 5: max_iterations caps round-trips in one step.
    loop = [[call(f"l{i}", "read_file", path=f"f{i}")] for i in range(10)]
    client5 = ScriptedClient(loop, max_iterations=3)
    agent5 = Agent(client5, instructions, name="agent_a", tools=[read_file])
    r5 = await agent5.run("Loop.", session=agent5.create_session())
    print("== check 5: max_iterations=3")
    print("   model requests in one step:", len(client5.requests))
    print("   final text:", repr(r5.text))


if __name__ == "__main__":
    asyncio.run(main())
