"""The framework offers only granted tools; granted calls reach the Gateway (SRS AGT-5, PRM-1)."""

from __future__ import annotations

from pathlib import Path

from agent_framework import Agent

from arena.agents.prompts import NEUTRAL_INSTRUCTIONS
from arena.agents.scripted import ScriptedChatClient, tool_call
from arena.config.schema import Grants
from arena.events.model import ListSink
from arena.tools.files import build_file_tools
from arena.tools.gateway import ToolGateway
from arena.workspace.files import Workspace
from tests.helpers import run_step

READER = Grants(read=("config/**", "docs/**"))
EDITOR = Grants(read=("config/**", "docs/**"), write=("docs/**",))


def setup(
    tmp_path: Path, grants: Grants, agent_id: str = "a"
) -> tuple[ToolGateway, ListSink, Path]:
    ws = tmp_path / "ws"
    (ws / "config").mkdir(parents=True)
    (ws / "config" / "deploy.yaml").write_text("replicas: 2\n", encoding="utf-8")
    (ws / "docs").mkdir()
    (ws / "docs" / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    sink = ListSink()
    gw = ToolGateway(agent_id=agent_id, grants=grants, workspace=Workspace(ws), sink=sink)
    return gw, sink, ws


def make_agent(gw: ToolGateway, client: ScriptedChatClient) -> Agent:  # type: ignore[type-arg]
    return Agent(client, NEUTRAL_INSTRUCTIONS, name=gw.agent_id, tools=build_file_tools(gw))


def tool_texts(client: ScriptedChatClient, request_index: int) -> list[str]:
    messages = client.requests[request_index].messages
    return [str(c.result) for m in messages if m.role == "tool" for c in m.contents]


def test_model_is_offered_only_the_granted_tools(tmp_path: Path) -> None:  # PRM-1
    gw, _, _ = setup(tmp_path, READER)
    client = ScriptedChatClient([["done"]])
    agent = make_agent(gw, client)
    run_step(agent, "Look around.", agent.create_session())
    assert client.requests[0].tool_names == ("list_files", "read_file")


def test_no_write_grant_means_no_write_tool_is_offered(tmp_path: Path) -> None:  # PRM-1
    gw, _, _ = setup(tmp_path, READER)
    client = ScriptedChatClient([["done"]])
    agent = make_agent(gw, client)
    run_step(agent, "Go.", agent.create_session())
    assert "write_file" not in client.requests[0].tool_names


def test_granted_read_through_the_framework_reaches_the_gateway(tmp_path: Path) -> None:  # PRM-1
    gw, sink, _ = setup(tmp_path, READER)
    client = ScriptedChatClient([[tool_call("r1", "read_file", path="config/deploy.yaml")], ["ok"]])
    agent = make_agent(gw, client)
    run_step(agent, "Read it.", agent.create_session())
    assert tool_texts(client, 1) == ["replicas: 2\n"]
    assert [e.data["decision"] for e in sink.events] == ["allowed"]


def test_unoffered_write_never_executes(tmp_path: Path) -> None:  # PRM-1, §24 test 1
    gw, sink, ws = setup(tmp_path, READER)
    client = ScriptedChatClient(
        [
            [tool_call("w1", "write_file", path="config/deploy.yaml", content="replicas: 9\n")],
            ["ok"],
        ]
    )
    agent = make_agent(gw, client)
    run_step(agent, "Change the replicas.", agent.create_session())
    assert (ws / "config" / "deploy.yaml").read_text(encoding="utf-8") == "replicas: 2\n"
    assert sink.events == []
    assert "not found" in tool_texts(client, 1)[0]


def test_granted_write_through_the_framework_is_applied_and_logged(tmp_path: Path) -> None:  # PRM-3
    gw, sink, ws = setup(tmp_path, EDITOR, agent_id="b")
    client = ScriptedChatClient(
        [
            [
                tool_call(
                    "w2", "write_file", path="docs/CHANGELOG.md", content="# Changelog\n\n1.4.2\n"
                )
            ],
            ["ok"],
        ]
    )
    agent = make_agent(gw, client)
    run_step(agent, "Add the entry.", agent.create_session())
    assert (ws / "docs" / "CHANGELOG.md").read_text(encoding="utf-8").endswith("1.4.2\n")
    assert [(e.agent_id, e.data["decision"]) for e in sink.events] == [("b", "allowed")]


def test_identity_supplied_by_the_model_does_not_change_who_acted(tmp_path: Path) -> None:  # PRM-2
    gw, sink, _ = setup(tmp_path, READER, agent_id="a")
    client = ScriptedChatClient(
        [[tool_call("r2", "read_file", path="docs/CHANGELOG.md", agent_id="b")], ["ok"]]
    )
    agent = make_agent(gw, client)
    run_step(agent, "Read it.", agent.create_session())
    assert sink.events, "a call that reaches the gateway must be logged"
    assert {e.agent_id for e in sink.events} == {"a"}
