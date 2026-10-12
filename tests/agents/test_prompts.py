"""Agent-visible text stays neutral (SRS AGT-4, ADR-0015)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from arena.agents.prompts import (
    COVER_STORY_LEAK,
    HELP_OR_HINT,
    NEUTRAL_INSTRUCTIONS,
    PEER_OR_HINT,
)
from arena.board.service import Board
from arena.config.loader import load_experiment
from arena.config.schema import Grants
from arena.events.model import ListSink
from arena.tools.framework import build_tools
from arena.tools.gateway import ToolGateway
from arena.workspace.files import Workspace

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_FILES = sorted(p for p in (ROOT / "fixtures").rglob("*") if p.is_file())
EXPERIMENT_FILES = sorted((ROOT / "experiments").glob("*.yaml"))


def test_neutral_instructions_are_clean() -> None:
    assert COVER_STORY_LEAK.search(NEUTRAL_INSTRUCTIONS) is None
    assert PEER_OR_HINT.search(NEUTRAL_INSTRUCTIONS) is None


def test_fixture_files_contain_no_cover_story_leaks() -> None:
    assert FIXTURE_FILES, "fixtures/ must contain at least one project"
    for path in FIXTURE_FILES:
        text = path.read_text(encoding="utf-8")
        match = COVER_STORY_LEAK.search(text)
        assert match is None, f"{path.relative_to(ROOT)} contains {match.group(0)!r}"


@pytest.mark.parametrize("path", EXPERIMENT_FILES, ids=lambda p: p.name)
def test_agent_tasks_contain_no_cover_story_leaks(path: Path) -> None:
    exp = load_experiment(path)
    for agent_id, agent in exp.agents.items():
        match = COVER_STORY_LEAK.search(agent.task)
        assert match is None, f"{path.name}:{agent_id} task contains {match.group(0)!r}"


def test_tool_descriptions_are_neutral(tmp_path: Path) -> None:
    (tmp_path / "ws").mkdir()
    everything = Grants(read=("**",), write=("**",), board_read=True, board_post=True)
    gw = ToolGateway(
        agent_id="a",
        grants=everything,
        workspace=Workspace(tmp_path / "ws"),
        sink=ListSink(),
        board=Board(),
    )
    for tool in build_tools(gw):
        description = tool.description or ""
        assert COVER_STORY_LEAK.search(description) is None, tool.name
        assert HELP_OR_HINT.search(description) is None, tool.name
        assert not re.search(r"\b(permission|allowed|restricted|only)\b", description, re.I), (
            tool.name
        )


def test_round_message_is_neutral() -> None:  # AGT-4
    from arena.agents.prompts import ROUND_MESSAGE

    assert COVER_STORY_LEAK.search(ROUND_MESSAGE) is None
    assert HELP_OR_HINT.search(ROUND_MESSAGE) is None
    assert PEER_OR_HINT.search(ROUND_MESSAGE) is None
