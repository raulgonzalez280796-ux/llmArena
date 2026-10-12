"""Which tools each set of grants offers (SRS PRM-1, BRD-6; ADR-0027)."""

from __future__ import annotations

from pathlib import Path

import pytest

from arena.board.service import Board
from arena.config.schema import Grants
from arena.events.model import ListSink
from arena.tools.gateway import Decision, ToolGateway, offered_tools
from arena.workspace.files import Workspace


@pytest.mark.parametrize(
    ("grants", "expected"),
    [
        (Grants(), ()),
        (Grants(read=("docs/**",)), ("list_files", "read_file")),
        (Grants(read=("docs/**",), write=("docs/**",)), ("list_files", "read_file", "write_file")),
        (Grants(board_read=True), ("read_board",)),
        (Grants(board_post=True), ("post_to_board",)),
        (Grants(board_read=True, board_post=True), ("read_board", "post_to_board")),
        (
            Grants(read=("docs/**",), write=("config/**",), board_read=True, board_post=True),
            ("list_files", "read_file", "write_file", "read_board", "post_to_board"),
        ),
    ],
)
def test_each_grant_offers_exactly_its_tools(
    grants: Grants, expected: tuple[str, ...]
) -> None:  # PRM-1
    assert offered_tools(grants) == expected


def test_the_gateway_offers_what_the_shared_function_says(tmp_path: Path) -> None:  # PRM-1
    (tmp_path / "docs").mkdir()
    grants = Grants(read=("docs/**",), board_post=True)
    gateway = ToolGateway(
        agent_id="a", grants=grants, workspace=Workspace(tmp_path), sink=ListSink(), board=Board()
    )
    assert gateway.granted_tools == offered_tools(grants)


def test_a_post_only_agent_cannot_read_the_board(tmp_path: Path) -> None:  # BRD-6
    (tmp_path / "docs").mkdir()
    sink = ListSink()
    gateway = ToolGateway(
        agent_id="a",
        grants=Grants(board_post=True),
        workspace=Workspace(tmp_path),
        sink=sink,
        board=Board(),
    )
    result = gateway.invoke("read_board", {})
    assert result.decision is Decision.DENIED
    assert sink.events[0].data["reason"] == "tool_not_granted"


def test_a_read_only_board_agent_cannot_post(tmp_path: Path) -> None:  # BRD-6
    (tmp_path / "docs").mkdir()
    board = Board()
    gateway = ToolGateway(
        agent_id="a",
        grants=Grants(board_read=True),
        workspace=Workspace(tmp_path),
        sink=ListSink(),
        board=board,
    )
    assert gateway.invoke("post_to_board", {"text": "hi"}).decision is Decision.DENIED
    assert board.posts() == ()


def test_a_board_grant_without_a_board_is_refused_at_construction(tmp_path: Path) -> None:  # BRD-6
    (tmp_path / "docs").mkdir()
    with pytest.raises(ValueError):
        ToolGateway(
            agent_id="a",
            grants=Grants(board_read=True),
            workspace=Workspace(tmp_path),
            sink=ListSink(),
        )
