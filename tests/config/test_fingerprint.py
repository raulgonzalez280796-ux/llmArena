"""Condition fingerprint: a change to anything the agent reads changes it (SRS LOG-5; ADR-0012)."""

from __future__ import annotations

from pathlib import Path

import pytest

from arena.config.loader import load_experiment
from arena.config.schema import resolve_condition
from arena.fingerprint import condition_fingerprint
from arena.tools import files

EXAMPLE = Path(__file__).resolve().parents[2] / "experiments" / "deploy_config_gap.yaml"


def test_fingerprint_is_stable_for_the_same_condition() -> None:  # LOG-5
    exp = load_experiment(EXAMPLE)
    assert condition_fingerprint(exp) == condition_fingerprint(exp)


def test_different_conditions_have_different_fingerprints() -> None:  # LOG-5
    exp = load_experiment(EXAMPLE)
    base = condition_fingerprint(exp)
    full = condition_fingerprint(resolve_condition(exp, "full_capability"))
    assert base != full


def test_changing_a_tool_description_changes_the_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exp = load_experiment(EXAMPLE)
    before = condition_fingerprint(exp)
    monkeypatch.setattr(files, "READ_DESCRIPTION", "Read a file. Changed wording.")
    assert condition_fingerprint(exp) != before


def test_changing_a_task_changes_the_fingerprint() -> None:  # LOG-5
    exp = load_experiment(EXAMPLE)
    data = exp.model_dump(mode="json")
    data["agents"]["a"]["task"] = "Set the replica count to 6."
    from arena.config.schema import Experiment

    assert condition_fingerprint(Experiment.model_validate(data)) != condition_fingerprint(exp)
