"""Batch plan: every condition and repetition, interleaved and repeatable (SRS RUN-4)."""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from arena.config.loader import load_experiment
from arena.config.schema import Experiment
from arena.runner.batch import BatchItem, plan_batch

EXAMPLE = Path(__file__).resolve().parents[2] / "experiments" / "deploy_config_gap.yaml"


@pytest.fixture
def example() -> Experiment:
    return load_experiment(EXAMPLE)


def test_every_condition_and_repetition_appears_exactly_once(example: Experiment) -> None:  # RUN-4
    items = plan_batch(example, seed=3)
    expected = {
        BatchItem(condition=c, repetition=r)
        for c in ("base", "full_capability", "board_off")
        for r in range(1, example.repetitions + 1)
    }
    assert len(items) == len(expected)
    assert set(items) == expected


def test_the_plan_is_repeatable_for_a_seed_and_differs_between_seeds(
    example: Experiment,
) -> None:  # RUN-4
    assert plan_batch(example, seed=3) == plan_batch(example, seed=3)
    assert plan_batch(example, seed=3) != plan_batch(example, seed=4)


def test_conditions_are_interleaved_not_run_in_blocks(example: Experiment) -> None:  # RUN-4
    items = plan_batch(example, seed=3)
    names = [item.condition for item in items]
    blocks = sum(1 for prev, cur in itertools.pairwise(names) if prev != cur)
    assert blocks > 2


def test_the_reserved_name_base_cannot_be_a_condition() -> None:  # RUN-4
    text = EXAMPLE.read_text(encoding="utf-8").replace("  full_capability:", "  base:", 1)
    from arena.config.loader import parse_experiment

    with pytest.raises(ValueError, match="reserved"):
        parse_experiment(text)
