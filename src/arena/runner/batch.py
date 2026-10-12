"""A batch: every condition and repetition, in one seeded, interleaved order (SRS RUN-4)."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from arena.config.schema import BASE_CONDITION, Experiment, resolve_condition
from arena.evaluator.outcome import Outcome, evaluate_run
from arena.runner.trial import ClientFactory, TrialSpec, run_trial


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


async def run_batch(
    experiment: Experiment,
    *,
    batch_id: str,
    seed: int,
    fixtures_root: Path,
    runs_root: Path,
    client_factory: ClientFactory,
    allow_scripted: bool = False,
) -> list[Outcome]:
    """Run every planned trial in order, evaluate each one, and append its outcome row (EVL-2).

    The batch directory is new for each batch, and each outcome row is written as soon as its run
    finishes, so a stopped batch keeps the rows it completed.
    """
    batch_dir = runs_root / batch_id
    batch_dir.mkdir(parents=True, exist_ok=False)
    outcomes: list[Outcome] = []
    with (batch_dir / "outcomes.jsonl").open("x", encoding="utf-8") as rows:
        for index, item in enumerate(plan_batch(experiment, seed=seed)):
            condition_exp = experiment_for(experiment, item.condition)
            run_id = f"r{index:03d}_{item.condition}_rep{item.repetition}"
            spec = TrialSpec(
                experiment=condition_exp,
                condition=item.condition,
                repetition=item.repetition,
                seed=seed + index,
                run_id=run_id,
                fixtures_root=fixtures_root,
                runs_root=batch_dir,
            )
            await run_trial(spec, client_factory, allow_scripted=allow_scripted)
            outcome = evaluate_run(
                batch_dir / run_id,
                condition_exp,
                run_id=run_id,
                condition=item.condition,
                repetition=item.repetition,
            )
            outcomes.append(outcome)
            rows.write(json.dumps(asdict(outcome), ensure_ascii=False) + "\n")
            rows.flush()
    return outcomes
