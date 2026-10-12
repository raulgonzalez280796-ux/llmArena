"""A batch runs every planned trial and writes one outcome row per run (SRS RUN-4, EVL-2)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from arena.config.loader import load_experiment
from arena.config.schema import Experiment
from arena.runner.batch import run_batch
from tests.runner.test_trial import factory_from

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "experiments" / "deploy_config_gap.yaml"


@pytest.fixture
def small(tmp_path: Path) -> Experiment:
    exp = load_experiment(EXAMPLE)
    data = exp.model_dump(mode="json", exclude_none=True)
    data["repetitions"] = 2
    data["limits"]["max_rounds"] = 2
    import yaml

    from arena.config.loader import parse_experiment

    return parse_experiment(yaml.safe_dump(data, sort_keys=False))


def test_every_condition_and_repetition_gets_a_run_and_an_outcome_row(
    tmp_path: Path, small: Experiment
) -> None:  # RUN-4
    outcomes = asyncio.run(
        run_batch(
            small,
            batch_id="batch_1",
            seed=11,
            fixtures_root=ROOT / "fixtures",
            runs_root=tmp_path / "runs",
            client_factory=factory_from({}),
            allow_scripted=True,
        )
    )
    assert len(outcomes) == 3 * 2
    rows = [
        json.loads(line)
        for line in (tmp_path / "runs" / "batch_1" / "outcomes.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 6
    assert {(r["condition"], r["repetition"]) for r in rows} == {
        (c, r) for c in ("base", "full_capability", "board_off") for r in (1, 2)
    }
    assert all(r["stop_reason"] == "max_rounds" for r in rows)


def test_a_batch_directory_is_never_reused(tmp_path: Path, small: Experiment) -> None:  # RUN-2
    kwargs = dict(
        batch_id="batch_1",
        seed=11,
        fixtures_root=ROOT / "fixtures",
        runs_root=tmp_path / "runs",
        client_factory=factory_from({}),
        allow_scripted=True,
    )
    asyncio.run(run_batch(small, **kwargs))  # type: ignore[arg-type]
    with pytest.raises(FileExistsError):
        asyncio.run(run_batch(small, **kwargs))  # type: ignore[arg-type]
