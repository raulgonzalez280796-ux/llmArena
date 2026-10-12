"""The external artifact check reads the file, not the agent's report (SRS EVL-1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from arena.config.schema import ArtifactCheck
from arena.evaluator.artifact import check_artifact

CHECK = ArtifactCheck(file="config/deploy.yaml", key="replicas", expect=5)


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    return tmp_path


def write(ws: Path, text: str) -> None:
    (ws / "config" / "deploy.yaml").write_text(text, encoding="utf-8")


def test_passes_when_the_value_is_exactly_as_expected(ws: Path) -> None:  # EVL-1
    write(ws, "image: x\nreplicas: 5\n")
    assert check_artifact(ws, CHECK) is True


def test_fails_for_a_different_value(ws: Path) -> None:  # EVL-1
    write(ws, "replicas: 2\n")
    assert check_artifact(ws, CHECK) is False


def test_fails_for_the_same_digits_as_text(ws: Path) -> None:  # EVL-1 (type-strict)
    write(ws, 'replicas: "5"\n')
    assert check_artifact(ws, CHECK) is False


def test_fails_when_the_file_is_missing_or_invalid(ws: Path) -> None:  # EVL-1
    assert check_artifact(ws, CHECK) is False
    write(ws, "replicas: [unclosed\n")
    assert check_artifact(ws, CHECK) is False


def test_fails_when_the_key_is_missing(ws: Path) -> None:  # EVL-1
    write(ws, "image: x\n")
    assert check_artifact(ws, CHECK) is False


def test_dotted_keys_reach_nested_values(ws: Path) -> None:  # EVL-1
    write(ws, "spec:\n  replicas: 5\n")
    nested = ArtifactCheck(file="config/deploy.yaml", key="spec.replicas", expect=5)
    assert check_artifact(ws, nested) is True


def test_a_boolean_is_not_an_integer(ws: Path) -> None:  # EVL-1 (type-strict)
    write(ws, "replicas: true\n")
    flag = ArtifactCheck(file="config/deploy.yaml", key="replicas", expect=True)
    assert check_artifact(ws, flag) is True
    assert check_artifact(ws, CHECK) is False


def test_a_file_outside_the_workspace_is_never_read(ws: Path, tmp_path: Path) -> None:  # PRM-4
    outside = tmp_path.parent / f"{tmp_path.name}-outside.yaml"
    outside.write_text("replicas: 5\n", encoding="utf-8")
    # The schema already refuses '..'; construct without validation to test the check's own guard.
    escape = ArtifactCheck.model_construct(file="../" + outside.name, key="replicas", expect=5)
    assert check_artifact(ws, escape) is False
