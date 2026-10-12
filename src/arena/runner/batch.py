"""A batch: every condition and repetition, in one seeded, interleaved order (SRS RUN-4)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from arena.config.schema import BASE_CONDITION, Experiment, resolve_condition


@dataclass(frozen=True)
class BatchItem:
    condition: str
    repetition: int


def condition_names(experiment: Experiment) -> tuple[str, ...]:
    return (BASE_CONDITION, *experiment.conditions)


def experiment_for(experiment: Experiment, condition: str) -> Experiment:
    return experiment if condition == BASE_CONDITION else resolve_condition(experiment, condition)


def plan_batch(experiment: Experiment, *, seed: int) -> tuple[BatchItem, ...]:
    items = [
        BatchItem(condition=name, repetition=rep)
        for rep in range(1, experiment.repetitions + 1)
        for name in condition_names(experiment)
    ]
    random.Random(seed).shuffle(items)
    return tuple(items)
