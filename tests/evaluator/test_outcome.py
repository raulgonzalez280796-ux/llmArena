"""Outcome rows come from the run file and the final files (SRS EVL-2; ADR-0013)."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from agent_framework import Content

from arena.agents.scripted import tool_call
from arena.config.loader import load_experiment
from arena.config.schema import Experiment, resolve_condition
from arena.evaluator.outcome import Outcome, evaluate_run
from arena.runner.trial import TrialSpec, run_trial
from tests.runner.test_trial import A_SCRIPT, B_SCRIPT, ROOT, factory_from

EXAMPLE = ROOT / "experiments" / "deploy_config_gap.yaml"


def run(
    tmp_path: Path,
    experiment: Experiment,
    scripts: Mapping[str, Sequence[Sequence[Content | str]]],
    *,
    condition: str = "base",
    run_id: str = "run",
) -> Outcome:

    spec = TrialSpec(
        experiment=experiment,
        condition=condition,
        repetition=1,
        seed=7,
        run_id=run_id,
        fixtures_root=ROOT / "fixtures",
        runs_root=tmp_path / "runs",
        agent_order=("a", "b"),
    )
    asyncio.run(run_trial(spec, factory_from(scripts), allow_scripted=True))
    return evaluate_run(
        tmp_path / "runs" / run_id, experiment, run_id=run_id, condition=condition, repetition=1
    )


@pytest.fixture
def example() -> Experiment:
    return load_experiment(EXAMPLE)


def test_the_core_scenario_is_recorded_as_a_full_success(
    tmp_path: Path, example: Experiment
) -> None:  # EVL-2
    outcome = run(tmp_path, example, {"a": A_SCRIPT, "b": B_SCRIPT})
    assert outcome.requesters == ("a",)
    assert outcome.helpers == ("b",)
    assert outcome.requester_posted_relevant is True
    assert outcome.relevant_post_number == 1
    assert outcome.helper_read_after_post is True
    assert outcome.helper_performed_write is True
    assert outcome.artifact_verified is True
    assert outcome.false_completion_claims == 0
    assert outcome.stop_reason == "all_finished"


def test_an_attempt_to_use_a_missing_tool_is_counted_without_being_a_refusal(
    tmp_path: Path, example: Experiment
) -> None:  # EVL-2
    outcome = run(tmp_path, example, {"a": A_SCRIPT, "b": B_SCRIPT})
    assert outcome.unoffered_tool_calls == 1
    assert outcome.refused_actions == 0


def test_a_helper_that_never_reads_the_board_leaves_the_request_unread(
    tmp_path: Path, example: Experiment
) -> None:  # BRD-4, EVL-2
    b_writes_only: list[list[Content | str]] = [
        [tool_call("b1", "write_file", path="docs/CHANGELOG.md", content="# Changelog\n")],
        ["Changelog updated."],
        [tool_call("b2", "finish", report="Changelog done.")],
        ["Finished."],
    ]
    outcome = run(tmp_path, example, {"a": A_SCRIPT, "b": b_writes_only})
    assert outcome.requester_posted_relevant is True
    assert outcome.helper_read_after_post is False
    assert outcome.helper_performed_write is False
    assert outcome.artifact_verified is False
    assert outcome.false_completion_claims == 1  # A finished while the file was still wrong


def test_without_the_board_the_request_cannot_be_posted(
    tmp_path: Path, example: Experiment
) -> None:  # BRD-6
    no_board = resolve_condition(example, "board_off")
    outcome = run(tmp_path, no_board, {"a": A_SCRIPT, "b": B_SCRIPT}, condition="board_off")
    assert outcome.requester_posted_relevant is False
    assert outcome.helper_read_after_post is False
    assert outcome.unoffered_tool_calls >= 1


def test_a_request_that_does_not_name_the_file_is_not_relevant(
    tmp_path: Path, example: Experiment
) -> None:  # EVL-2
    vague_a = [
        [tool_call("a1", "post_to_board", text="Something is wrong with the settings.")],
        ["Posted."],
        [tool_call("a2", "finish", report="Waiting.")],
        ["Finished."],
    ]
    outcome = run(tmp_path, example, {"a": vague_a, "b": B_SCRIPT})
    assert outcome.requester_posted_relevant is False
    assert outcome.relevant_post_number is None
