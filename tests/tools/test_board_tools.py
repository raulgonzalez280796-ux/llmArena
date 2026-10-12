"""Board tools through the Tool Gateway (SRS BRD-1, BRD-3, BRD-5, BRD-6, PRM-2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from arena.board.service import Board
from arena.config.schema import Grants
from arena.events.model import ListSink
from arena.tools.gateway import Decision, ToolGateway
from arena.workspace.files import Workspace

BOARD_GRANT = Grants(read=("docs/**",), board=True)
NO_BOARD = Grants(read=("docs/**",))


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    (tmp_path / "docs").mkdir()
    return Workspace(tmp_path)


def gateway(
    ws: Workspace, grants: Grants, agent_id: str, board: Board | None, sink: ListSink
) -> ToolGateway:
    return ToolGateway(agent_id=agent_id, grants=grants, workspace=ws, sink=sink, board=board)


def test_board_tools_are_offered_only_with_the_board_grant(ws: Workspace) -> None:  # BRD-6
    with_board = gateway(ws, BOARD_GRANT, "a", Board(), ListSink())
    without = gateway(ws, NO_BOARD, "a", None, ListSink())
    assert "read_board" in with_board.granted_tools
    assert "post_to_board" in with_board.granted_tools
    assert "read_board" not in without.granted_tools
    assert "post_to_board" not in without.granted_tools


def test_board_grant_without_a_board_is_a_construction_error(ws: Workspace) -> None:  # BRD-6
    with pytest.raises(ValueError, match="board"):
        gateway(ws, BOARD_GRANT, "a", None, ListSink())


def test_post_is_stamped_with_the_gateway_identity(ws: Workspace) -> None:  # BRD-3
    board = Board()
    gateway(ws, BOARD_GRANT, "a", board, ListSink()).invoke("post_to_board", {"text": "hello"})
    assert [(p.sender, p.text) for p in board.posts()] == [("a", "hello")]


def test_post_names_a_sender_argument_is_rejected(ws: Workspace) -> None:  # BRD-3, PRM-2
    board = Board()
    sink = ListSink()
    result = gateway(ws, BOARD_GRANT, "a", board, sink).invoke(
        "post_to_board", {"text": "hello", "sender": "b"}
    )
    assert result.decision is Decision.REJECTED
    assert board.posts() == ()
    assert sink.events[0].data["decision"] == "rejected"


def test_read_returns_numbered_posts_with_authors_and_logs_what_was_seen(ws: Workspace) -> None:
    board = Board()
    board.post("b", "docs are stale")
    sink = ListSink()
    result = gateway(ws, BOARD_GRANT, "a", board, sink).invoke("read_board", {})
    assert result.decision is Decision.ALLOWED
    assert result.text == "#1 [b] docs are stale"
    assert sink.events[0].data["result"] == "#1 [b] docs are stale"


def test_read_of_an_empty_board_says_so(ws: Workspace) -> None:
    result = gateway(ws, BOARD_GRANT, "a", Board(), ListSink()).invoke("read_board", {})
    assert result.text == "The board is empty."


def test_post_over_the_limit_is_rejected_and_logged(ws: Workspace) -> None:  # BRD-5
    board = Board(max_posts_per_agent=1)
    sink = ListSink()
    gw = gateway(ws, BOARD_GRANT, "a", board, sink)
    gw.invoke("post_to_board", {"text": "first"})
    result = gw.invoke("post_to_board", {"text": "second"})
    assert result.decision is Decision.REJECTED
    assert "limit" in result.text
    assert [e.data["reason"] for e in sink.events] == [None, "post_limit"]


def test_successful_post_reports_its_number(ws: Workspace) -> None:
    result = gateway(ws, BOARD_GRANT, "a", Board(), ListSink()).invoke(
        "post_to_board", {"text": "hi"}
    )
    assert result == result.__class__("Posted #1", Decision.ALLOWED)


def test_board_tools_without_grant_are_refused_and_logged(ws: Workspace) -> None:  # PRM-1
    sink = ListSink()
    result = gateway(ws, NO_BOARD, "a", None, sink).invoke("read_board", {})
    assert result.decision is Decision.DENIED
    assert sink.events[0].data["reason"] == "tool_not_granted"
