"""Contract tests: the Microsoft Agent Framework behaviours the arena relies on (ADR-0017).

If a framework upgrade changes any of these, the failing test names the assumption that broke.
"""

from __future__ import annotations

import asyncio
from typing import Any

from agent_framework import Agent, AgentResponse, AgentSession, FunctionTool, tool

from arena.agents.scripted import ScriptedChatClient, tool_call

INSTRUCTIONS = "You operate in a shared project workspace."


def make_read_tool(calls: list[str]) -> FunctionTool:
    @tool(name="read_file", description="Read a file from the project.")
    def read_file(path: str) -> str:
        calls.append(path)
        return f"<contents of {path}>"

    return read_file


def run_step(agent: Agent[Any], text: str, session: AgentSession) -> AgentResponse[Any]:
    async def go() -> AgentResponse[Any]:
        return await agent.run(text, session=session)

    return asyncio.run(go())


def tool_results(client: ScriptedChatClient, request_index: int) -> list[Any]:
    messages = client.requests[request_index].messages
    return [c.result for m in messages if m.role == "tool" for c in m.contents]


def test_tool_call_runs_our_function_and_result_returns_to_model() -> None:
    calls: list[str] = []
    client = ScriptedChatClient(
        [[tool_call("c1", "read_file", path="config/deploy.yaml")], ["done"]]
    )
    agent = Agent(client, INSTRUCTIONS, name="a", tools=[make_read_tool(calls)])

    response = run_step(agent, "Read the config.", agent.create_session())

    assert calls == ["config/deploy.yaml"]
    assert tool_results(client, 1) == ["<contents of config/deploy.yaml>"]
    assert response.text == "done"


def test_model_sees_exactly_our_instructions_and_tools() -> None:
    client = ScriptedChatClient([["ok"]])
    agent = Agent(client, INSTRUCTIONS, name="a", tools=[make_read_tool([])])

    run_step(agent, "Hello.", agent.create_session())

    request = client.requests[0]
    assert request.instructions == INSTRUCTIONS
    assert request.tool_names == ("read_file",)
    assert [m.role for m in request.messages] == ["user"]


def test_session_keeps_history_across_steps() -> None:
    client = ScriptedChatClient(
        [[tool_call("c1", "read_file", path="a.txt")], ["first"], ["second"]]
    )
    agent = Agent(client, INSTRUCTIONS, name="a", tools=[make_read_tool([])])
    session = agent.create_session()

    run_step(agent, "Step one.", session)
    run_step(agent, "Step two.", session)

    roles = [m.role for m in client.requests[-1].messages]
    assert roles == ["user", "assistant", "tool", "assistant", "user"]


def test_two_agents_do_not_share_history() -> None:
    client_a = ScriptedChatClient([["from a"]])
    client_b = ScriptedChatClient([["from b"]])
    agent_a = Agent(client_a, INSTRUCTIONS, name="a")
    agent_b = Agent(client_b, INSTRUCTIONS, name="b")

    run_step(agent_a, "Secret task for a.", agent_a.create_session())
    run_step(agent_b, "Task for b.", agent_b.create_session())

    seen_by_b = " ".join(m.text for m in client_b.requests[0].messages)
    assert "Secret task for a." not in seen_by_b


def test_unknown_tool_runs_nothing_and_framework_supplies_error_text() -> None:
    """The framework answers an unknown tool with its own wording.

    The arena must replace this text with its own refusal (PRM-1, PRM-5), because the
    wording reaches the model and is part of the condition.
    """
    calls: list[str] = []
    client = ScriptedChatClient(
        [[tool_call("x1", "write_file", path="config/deploy.yaml")], ["ok"]]
    )
    agent = Agent(client, INSTRUCTIONS, name="a", tools=[make_read_tool(calls)])

    run_step(agent, "Write it.", agent.create_session())

    assert calls == []
    assert tool_results(client, 1) == ['Error: Requested function "write_file" not found.']


def test_max_iterations_caps_round_trips_then_forces_text() -> None:
    loop = [[tool_call(f"c{i}", "read_file", path=f"f{i}")] for i in range(10)]
    client = ScriptedChatClient(loop, max_iterations=3)
    agent = Agent(client, INSTRUCTIONS, name="a", tools=[make_read_tool([])])

    run_step(agent, "Go.", agent.create_session())

    assert len(client.requests) == 4
    assert [r.tool_choice for r in client.requests] == ["auto", "auto", "auto", "none"]
