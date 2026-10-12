"""Tool Gateway: grants, refusals, argument checks and audit (SRS PRM-1..7, LOG-2)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from arena.config.schema import Grants
from arena.events.model import Event, ListSink
from arena.tools.gateway import Decision, ToolGateway, ToolResult
from arena.workspace.files import Workspace

READER = Grants(read=("config/**", "docs/**"))
EDITOR = Grants(read=("config/**", "docs/**"), write=("docs/**",))


@pytest.fixture
def world(tmp_path: Path) -> Path:
    """A workspace at tmp/ws and a directory outside it at tmp/outside."""
    ws = tmp_path / "ws"
    (ws / "config").mkdir(parents=True)
    (ws / "config" / "deploy.yaml").write_text("replicas: 2\n", encoding="utf-8")
    (ws / "config" / "other.yaml").write_text("other: 1\n", encoding="utf-8")
    (ws / "docs").mkdir()
    (ws / "docs" / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (ws / "secret").mkdir()
    (ws / "secret" / "key.txt").write_text("top secret\n", encoding="utf-8")
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "key.txt").write_text("outside\n", encoding="utf-8")
    return ws


def gateway(
    ws: Path, grants: Grants, sink: ListSink | None = None, agent_id: str = "a"
) -> ToolGateway:
    return ToolGateway(
        agent_id=agent_id,
        grants=grants,
        workspace=Workspace(ws),
        sink=sink if sink is not None else ListSink(),
    )


def invoke(gw: ToolGateway, tool: str, **arguments: object) -> ToolResult:
    return gw.invoke(tool, dict(arguments))


def test_granted_read_returns_content_and_logs_allowed(world: Path) -> None:  # PRM-3
    sink = ListSink()
    gw = gateway(world, READER, sink)
    result = invoke(gw, "read_file", path="config/deploy.yaml")
    assert result == ToolResult("replicas: 2\n", Decision.ALLOWED)
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.data["decision"] == "allowed"
    assert event.data["matching_rule"] == "config/**"
    assert event.data["resolved_path"] == "config/deploy.yaml"


def test_read_outside_grant_is_refused_with_exact_text(world: Path) -> None:  # PRM-5
    sink = ListSink()
    result = invoke(gateway(world, READER, sink), "read_file", path="secret/key.txt")
    assert result == ToolResult("Permission denied: secret/key.txt", Decision.DENIED)
    assert sink.events[0].data["reason"] == "no_matching_grant"
    assert sink.events[0].data["matching_rule"] is None


def test_write_without_write_grant_is_refused_and_file_unchanged(
    world: Path,
) -> None:  # PRM-1, PRM-3
    result = invoke(gateway(world, READER), "write_file", path="docs/CHANGELOG.md", content="x")
    assert result.decision is Decision.DENIED
    assert (world / "docs" / "CHANGELOG.md").read_text(encoding="utf-8") == "# Changelog\n"


def test_write_outside_the_write_grant_is_refused_and_file_unchanged(world: Path) -> None:  # PRM-3
    result = invoke(gateway(world, EDITOR), "write_file", path="config/deploy.yaml", content="x")
    assert result == ToolResult("Permission denied: config/deploy.yaml", Decision.DENIED)
    assert (world / "config" / "deploy.yaml").read_text(encoding="utf-8") == "replicas: 2\n"


def test_write_inside_the_write_grant_creates_the_file(world: Path) -> None:  # PRM-3, WSP-1
    result = invoke(gateway(world, EDITOR), "write_file", path="docs/NEW.md", content="hello\n")
    assert result.decision is Decision.ALLOWED
    assert (world / "docs" / "NEW.md").read_text(encoding="utf-8") == "hello\n"


def test_write_grant_matches_case_insensitively(world: Path) -> None:  # PRM-4
    result = invoke(gateway(world, EDITOR), "write_file", path="DOCS/new.md", content="x")
    assert result.decision is Decision.ALLOWED


def test_ungranted_tool_name_is_refused_and_logged(world: Path) -> None:  # PRM-1, §24 test 1
    sink = ListSink()
    result = invoke(gateway(world, READER, sink), "delete_file", path="config/deploy.yaml")
    assert result == ToolResult("Permission denied: delete_file", Decision.DENIED)
    assert sink.events[0].data["reason"] == "unknown_tool"


def test_known_tool_without_its_grant_is_refused_and_logged(
    world: Path,
) -> None:  # PRM-1, §24 test 1
    sink = ListSink()
    result = invoke(gateway(world, READER, sink), "write_file", path="docs/x.md", content="x")
    assert result.decision is Decision.DENIED
    assert sink.events[0].data["reason"] == "tool_not_granted"


def test_model_supplied_identity_is_rejected_and_not_applied(
    world: Path,
) -> None:  # PRM-2, §24 test 2
    sink = ListSink()
    gw = gateway(world, READER, sink, agent_id="a")
    result = invoke(gw, "read_file", path="config/deploy.yaml", agent_id="b")
    assert result.decision is Decision.REJECTED
    assert "agent_id" in result.text
    assert "replicas" not in result.text
    assert [e.agent_id for e in sink.events] == ["a"]
    assert sink.events[0].data["decision"] == "rejected"


def test_extra_argument_on_write_is_rejected(world: Path) -> None:  # PRM-2
    result = invoke(gateway(world, EDITOR), "write_file", path="docs/x.md", content="x", sender="b")
    assert result.decision is Decision.REJECTED
    assert not (world / "docs" / "x.md").exists()


def test_missing_required_argument_is_rejected(world: Path) -> None:
    result = gateway(world, READER).invoke("read_file", {})
    assert result.decision is Decision.REJECTED


def test_traversal_is_refused_with_exact_text(world: Path) -> None:  # PRM-4, §24 test 3
    sink = ListSink()
    result = invoke(gateway(world, READER, sink), "read_file", path="../outside/key.txt")
    assert result == ToolResult("Permission denied: ../outside/key.txt", Decision.DENIED)
    assert sink.events[0].data["resolved_path"] is None
    assert sink.events[0].data["reason"] == "outside_workspace"


def test_symlink_to_outside_is_refused_even_under_a_granted_path(
    world: Path, tmp_path: Path
) -> None:
    os.symlink(tmp_path / "outside" / "key.txt", world / "docs" / "leak.txt")
    result = invoke(gateway(world, READER), "read_file", path="docs/leak.txt")
    assert result == ToolResult("Permission denied: docs/leak.txt", Decision.DENIED)


def test_symlink_is_judged_by_its_target(world: Path) -> None:  # PRM-4
    os.symlink(world / "config" / "deploy.yaml", world / "docs" / "alias.yaml")
    only_docs = Grants(read=("docs/**",))
    result = invoke(gateway(world, only_docs), "read_file", path="docs/alias.yaml")
    assert result == ToolResult("Permission denied: docs/alias.yaml", Decision.DENIED)


def test_list_is_refused_without_a_grant_on_the_directory(world: Path) -> None:  # PRM-3
    result = invoke(gateway(world, READER), "list_files", path=".")
    assert result == ToolResult("Permission denied: .", Decision.DENIED)


def test_list_shows_only_entries_the_agent_can_read(world: Path) -> None:  # PRM-3
    grants = Grants(read=("config", "config/deploy.yaml"))
    result = invoke(gateway(world, grants), "list_files", path="config")
    assert result == ToolResult("deploy.yaml", Decision.ALLOWED)


def test_list_hides_symlinks_that_leave_the_workspace(world: Path, tmp_path: Path) -> None:  # PRM-4
    os.symlink(tmp_path / "outside", world / "config" / "out")
    grants = Grants(read=("config/**",))
    result = invoke(gateway(world, grants), "list_files", path="config")
    assert "out" not in result.text.split("\n")


def test_grants_cannot_be_changed_after_the_gateway_is_built(world: Path) -> None:  # PRM-7
    grants = Grants(read=("config/**",))
    gw = gateway(world, grants)
    with pytest.raises(ValidationError):
        grants.write = ("config/**",)  # type: ignore[misc]
    assert gw.granted_tools == ("list_files", "read_file")


def test_granted_tools_follow_the_grants(world: Path) -> None:  # PRM-1
    assert gateway(world, READER).granted_tools == ("list_files", "read_file")
    assert gateway(world, EDITOR).granted_tools == ("list_files", "read_file", "write_file")
    assert gateway(world, Grants()).granted_tools == ()


def test_oversized_read_is_an_error_not_a_refusal(world: Path) -> None:
    (world / "docs" / "big.md").write_text("a" * 70_000, encoding="utf-8")
    result = invoke(gateway(world, READER), "read_file", path="docs/big.md")
    assert result == ToolResult("Error: file is too large", Decision.ERROR)


def test_oversized_write_is_rejected_and_nothing_is_written(world: Path) -> None:
    result = invoke(gateway(world, EDITOR), "write_file", path="docs/big.md", content="a" * 70_000)
    assert result.decision is Decision.REJECTED
    assert not (world / "docs" / "big.md").exists()


def test_every_call_is_logged_once_with_its_arguments(world: Path) -> None:  # LOG-2
    sink = ListSink()
    gw = gateway(world, EDITOR, sink)
    invoke(gw, "read_file", path="config/deploy.yaml")
    invoke(gw, "write_file", path="config/deploy.yaml", content="x")
    invoke(gw, "delete_file", path="docs/CHANGELOG.md")
    assert [e.data["decision"] for e in sink.events] == ["allowed", "denied", "denied"]
    assert sink.events[1].data["arguments"] == {"path": "config/deploy.yaml", "content": "x"}
    assert all(isinstance(e, Event) and e.type == "tool_call" for e in sink.events)
