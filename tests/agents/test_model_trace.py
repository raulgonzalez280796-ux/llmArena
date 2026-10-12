"""Every model request and reply is logged with its agent (SRS LOG-2; ADR-0020)."""

from __future__ import annotations

import pytest
from agent_framework import Agent, Content, tool

from arena.agents.scripted import ScriptedChatClient, tool_call
from arena.agents.trace import ModelTrace
from arena.events.model import ListSink
from tests.helpers import run_step


@tool(name="read_file", description="Read a file from the project.")
def read_file(path: str) -> str:
    return f"<contents of {path}>"


def make(replies: list[list[Content | str]], sink: ListSink) -> tuple[ScriptedChatClient, Agent]:
    client = ScriptedChatClient(replies, middleware=[ModelTrace(sink, agent_id="a")])
    agent = Agent(client, "You operate in a shared project workspace.", name="a", tools=[read_file])
    return client, agent


def test_request_and_reply_are_logged_with_the_agent_id() -> None:  # LOG-2
    sink = ListSink()
    _, agent = make([["All done."]], sink)
    run_step(agent, "Hello there.", agent.create_session())
    requests = [e for e in sink.events if e.type == "model_request"]
    replies = [e for e in sink.events if e.type == "model_response"]
    assert len(requests) == 1 and len(replies) == 1
    assert {e.agent_id for e in sink.events} == {"a"}
    assert requests[0].data["instructions"] == "You operate in a shared project workspace."
    assert "Hello there." in str(requests[0].data["messages"])
    assert replies[0].data["text"] == "All done."


def test_one_event_pair_per_model_round_trip() -> None:  # LOG-2
    sink = ListSink()
    _, agent = make([[tool_call("c1", "read_file", path="x")], ["done"]], sink)
    run_step(agent, "Go.", agent.create_session())
    assert [e.type for e in sink.events].count("model_request") == 2
    assert [e.type for e in sink.events].count("model_response") == 2


def test_a_call_to_an_unoffered_tool_is_visible_in_the_reply() -> None:  # LOG-2, blueprint §20
    sink = ListSink()
    _, agent = make(
        [[tool_call("w1", "write_file", path="config/deploy.yaml", content="x")], ["ok"]], sink
    )
    run_step(agent, "Go.", agent.create_session())
    first_reply = next(e for e in sink.events if e.type == "model_response")
    assert first_reply.data["tool_calls"] == [
        {"name": "write_file", "arguments": {"path": "config/deploy.yaml", "content": "x"}}
    ]


@pytest.mark.parametrize("key", ["api_key", "authorization"])
def test_trace_never_carries_credentials(key: str) -> None:  # LOG-4
    sink = ListSink()
    _, agent = make([["ok"]], sink)
    run_step(agent, "Go.", agent.create_session())
    assert key not in str([e.data for e in sink.events]).lower()
