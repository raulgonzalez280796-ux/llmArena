"""Path canonicalization and grant matching (SRS PRM-3, PRM-4; ADR-0019)."""

from __future__ import annotations

import os
import unicodedata
from pathlib import Path

import pytest

from arena.workspace.paths import (
    InvalidPath,
    PathDenied,
    canonicalize,
    matching_rule,
    validate_glob,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / "config").mkdir(parents=True)
    (ws / "config" / "deploy.yaml").write_text("replicas: 2\n", encoding="utf-8")
    (ws / "docs").mkdir()
    (ws / "secret").mkdir()
    (ws / "secret" / "key.txt").write_text("top secret\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "key.txt").write_text("outside\n", encoding="utf-8")
    return ws


GRANT_CASES: list[tuple[list[str], str, str | None]] = [
    (["config/**"], "config/deploy.yaml", "config/**"),
    (["config/**"], "config", "config/**"),
    (["config/**"], "config/sub/deeper.yaml", "config/**"),
    (["config/**"], "docs/notes.md", None),
    (["config/**"], "config/../secret/key.txt", None),
    (["config/deploy.yaml"], "config/deploy.yaml", "config/deploy.yaml"),
    (["config/deploy.yaml"], "config/other.yaml", None),
    (["config/*.yaml"], "config/deploy.yaml", "config/*.yaml"),
    (["config/*.yaml"], "config/sub/deploy.yaml", None),
    (["**"], "anything/at/all.txt", "**"),
    (["**"], ".", "**"),
    (["Config/**"], "CONFIG/Deploy.yaml", "Config/**"),
    (["docs/**", "config/**"], "config/deploy.yaml", "config/**"),
    ([], "config/deploy.yaml", None),
]


@pytest.mark.parametrize(("patterns", "requested", "expected"), GRANT_CASES)
def test_grant_matching(
    root: Path, patterns: list[str], requested: str, expected: str | None
) -> None:
    resolved = canonicalize(root, requested)
    assert matching_rule(patterns, resolved) == expected


@pytest.mark.parametrize("requested", ["../outside/key.txt", "config/../../outside/key.txt"])
def test_traversal_out_of_workspace_is_denied(root: Path, requested: str) -> None:
    with pytest.raises(PathDenied):
        canonicalize(root, requested)


@pytest.mark.parametrize("requested", ["/etc/hosts", "/tmp"])
def test_absolute_paths_are_denied(root: Path, requested: str) -> None:
    with pytest.raises(PathDenied):
        canonicalize(root, requested)


def test_home_prefix_is_a_literal_name_inside_the_workspace(root: Path) -> None:
    resolved = canonicalize(root, "~/.ssh/id_rsa")
    assert resolved.relative == "~/.ssh/id_rsa"


@pytest.mark.parametrize("requested", ["", "config/\x00deploy.yaml", "config\\deploy.yaml"])
def test_malformed_paths_are_invalid(root: Path, requested: str) -> None:
    with pytest.raises(InvalidPath):
        canonicalize(root, requested)


def test_symlink_pointing_outside_is_denied(root: Path, tmp_path: Path) -> None:
    os.symlink(tmp_path / "outside" / "key.txt", root / "config" / "escape.txt")
    with pytest.raises(PathDenied):
        canonicalize(root, "config/escape.txt")


def test_dangling_symlink_pointing_outside_is_denied(root: Path, tmp_path: Path) -> None:
    os.symlink(tmp_path / "outside" / "new.txt", root / "config" / "dangling.txt")
    with pytest.raises(PathDenied):
        canonicalize(root, "config/dangling.txt")


def test_grant_applies_to_symlink_target_not_to_link_location(root: Path) -> None:
    os.symlink(root / "config" / "deploy.yaml", root / "docs" / "alias.yaml")
    resolved = canonicalize(root, "docs/alias.yaml")
    assert resolved.relative == "config/deploy.yaml"
    assert matching_rule(["config/**"], resolved) == "config/**"
    assert matching_rule(["docs/**"], resolved) is None


def test_nfd_request_matches_nfc_grant(root: Path) -> None:
    name_nfc = "café.yaml"
    (root / "config" / name_nfc).write_text("x", encoding="utf-8")
    nfd_request = unicodedata.normalize("NFD", f"config/{name_nfc}")
    resolved = canonicalize(root, nfd_request)
    assert matching_rule(["config/café.yaml"], resolved) == "config/café.yaml"


@pytest.mark.parametrize(
    "pattern",
    ["", "/etc/**", "../x", "config//x", "config/", "config/../x", "a\\b", "x\x00y", "config**"],
)
def test_malformed_grant_patterns_are_rejected(pattern: str) -> None:
    with pytest.raises(ValueError):
        validate_glob(pattern)


@pytest.mark.parametrize(
    "pattern", ["config/**", "**", "docs/*.md", "*.yaml", "config/deploy.yaml"]
)
def test_well_formed_grant_patterns_are_accepted(pattern: str) -> None:
    validate_glob(pattern)
