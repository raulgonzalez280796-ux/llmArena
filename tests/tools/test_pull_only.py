"""A post reaches a peer only when the peer calls read_board (SRS BRD-4; ADR-0006)."""

from __future__ import annotations

from pathlib import Path

from agent_framework import Agent

from arena.agents.prompts import NEUTRAL_INSTRUCTIONS
from arena.agents.scripted import ScriptedChatClient, tool_call
from arena.board.service import Board
from arena.config.schema import Grants
from arena.events.model import ListSink
from arena.tools.framework import build_tools
from arena.tools.gateway import ToolGateway
from arena.workspace.files import Workspace
from tests.helpers import run_step

GRANTS = Grants(read=("docs/**",), board_read=True, board_post=True)


def request_text(client: ScriptedChatClient, index: int) -> str:
    return " ".join(m.text for m in client.requests[index].messages)


def test_peer_does_not_see_a_post_until_it_reads_the_board(tmp_path: Path) -> None:  # BRD-4
    (tmp_path / "docs").mkdir()
    ws = Workspace(tmp_path)
    board = Board()
    sink = ListSink()

    poster = ScriptedChatClient(
        [[tool_call("p1", "post_to_board", text="deploy.yaml needs a write grant")], ["posted"]]
    )
    peer = ScriptedChatClient([["waiting for work"], [tool_call("r1", "read_board")], ["read it"]])
    gw_a = ToolGateway(agent_id="a", grants=GRANTS, workspace=ws, sink=sink, board=board)
    gw_b = ToolGateway(agent_id="b", grants=GRANTS, workspace=ws, sink=sink, board=board)

    agent_a = _agent("a", poster, gw_a)
    agent_b = _agent("b", peer, gw_b)

    run_step(agent_a, "Do your task.", agent_a.create_session())
    run_step(agent_b, "Do your task.", agent_b.create_session())  # round 1: nothing read yet
    assert "needs a write grant" not in request_text(peer, 0)

    run_step(agent_b, "Next round.", agent_b.create_session())  # reads the board
    # The reply to read_board is the second call in that step; its tool result is in request 2.
    tool_result = next(
        str(c.result) for m in peer.requests[2].messages for c in m.contents if m.role == "tool"
    )
    assert tool_result == "#1 [a] deploy.yaml needs a write grant"
    assert [e.data["tool"] for e in sink.events if e.agent_id == "b"] == ["read_board"]


def _agent(name: str, client: ScriptedChatClient, gw: ToolGateway) -> Agent:
    return Agent(client, NEUTRAL_INSTRUCTIONS, name=name, tools=build_tools(gw))
