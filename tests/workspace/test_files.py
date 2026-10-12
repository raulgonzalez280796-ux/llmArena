"""Workspace reads, atomic writes and snapshots (SRS WSP-1..3; ADR-0019)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from arena.workspace.files import Workspace, WorkspaceError, diff_snapshots, snapshot_tree


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "deploy.yaml").write_text("replicas: 2\n", encoding="utf-8")
    return Workspace(tmp_path)


def test_read_after_write_sees_new_content(ws: Workspace) -> None:
    target = ws.resolve("config/deploy.yaml")
    ws.write_text(target, "replicas: 5\n")
    assert ws.read_text(target, max_bytes=1000) == "replicas: 5\n"


def test_write_creates_a_new_file_in_an_existing_directory(ws: Workspace) -> None:
    ws.write_text(ws.resolve("config/new.yaml"), "a: 1\n")
    assert (ws.root / "config" / "new.yaml").read_text(encoding="utf-8") == "a: 1\n"


def test_write_into_missing_directory_is_an_error(ws: Workspace) -> None:
    with pytest.raises(WorkspaceError):
        ws.write_text(ws.resolve("missing/new.yaml"), "x")


def test_failed_write_leaves_original_and_no_temp_file(
    ws: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = ws.resolve("config/deploy.yaml")

    def fail_at_commit(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated failure at commit")

    monkeypatch.setattr(os, "replace", fail_at_commit)
    with pytest.raises(OSError, match="simulated"):
        ws.write_text(target, "replicas: 9\n")

    assert ws.read_text(target, max_bytes=1000) == "replicas: 2\n"
    assert list((ws.root / "config").glob(".arena-*")) == []


def test_reading_a_directory_is_an_error(ws: Workspace) -> None:
    with pytest.raises(WorkspaceError):
        ws.read_text(ws.resolve("config"), max_bytes=1000)


def test_reading_non_utf8_is_an_error(ws: Workspace) -> None:
    (ws.root / "config" / "bin.dat").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(WorkspaceError):
        ws.read_text(ws.resolve("config/bin.dat"), max_bytes=1000)


def test_reading_past_the_size_limit_is_an_error(ws: Workspace) -> None:
    (ws.root / "config" / "big.txt").write_text("a" * 100, encoding="utf-8")
    with pytest.raises(WorkspaceError, match="too large"):
        ws.read_text(ws.resolve("config/big.txt"), max_bytes=10)


def test_snapshot_and_diff_report_added_removed_and_modified(ws: Workspace) -> None:
    (ws.root / "docs").mkdir()
    (ws.root / "docs" / "notes.md").write_text("old\n", encoding="utf-8")
    before = snapshot_tree(ws.root)

    ws.write_text(ws.resolve("config/deploy.yaml"), "replicas: 5\n")
    (ws.root / "docs" / "notes.md").unlink()
    (ws.root / "docs" / "new.md").write_text("new\n", encoding="utf-8")
    after = snapshot_tree(ws.root)

    result = diff_snapshots(before, after)
    assert result.added == ("docs/new.md",)
    assert result.removed == ("docs/notes.md",)
    assert result.modified == ("config/deploy.yaml",)


def test_unchanged_tree_has_empty_diff(ws: Workspace) -> None:
    before = snapshot_tree(ws.root)
    after = snapshot_tree(ws.root)
    assert diff_snapshots(before, after).is_empty


def test_symlink_retarget_shows_as_modified(ws: Workspace, tmp_path: Path) -> None:
    (tmp_path / "other.yaml").write_text("x", encoding="utf-8")
    os.symlink(ws.root / "config" / "deploy.yaml", ws.root / "link.yaml")
    before = snapshot_tree(ws.root)
    os.unlink(ws.root / "link.yaml")
    os.symlink(tmp_path / "other.yaml", ws.root / "link.yaml")
    after = snapshot_tree(ws.root)
    assert diff_snapshots(before, after).modified == ("link.yaml",)
