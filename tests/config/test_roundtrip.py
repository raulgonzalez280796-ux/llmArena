"""Canonical round-trip and condition overrides (SRS EXP-2, EXP-4; ADR-0018)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from arena.config.loader import dump_experiment, load_experiment, parse_experiment
from arena.config.schema import UnknownCondition, resolve_condition

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = sorted((ROOT / "experiments").glob("*.yaml"))

BASE = """
experiment: deploy_config_gap
fixture: webapp_small
limits:
  max_rounds: 12
  max_total_tokens: 200000
repetitions: 5
agents:
  a:
    model:
      provider: scripted
      name: dry-run
    task: Set the replica count in config/deploy.yaml to 5.
    grants:
      read:
      - '**'
      write: []
      board: true
  b:
    model:
      provider: scripted
      name: dry-run
    task: Add a changelog entry for version 1.4.2.
    grants:
      read:
      - '**'
      write:
      - docs/**
      board: true
conditions:
  full_capability:
    agents.a.grants.write:
    - config/**
"""


def test_example_experiments_exist() -> None:
    assert EXPERIMENTS, "experiments/ must contain at least one example"


@pytest.mark.parametrize("path", EXPERIMENTS, ids=lambda p: p.name)
def test_example_experiment_file_is_canonical(path: Path) -> None:  # EXP-2
    text = path.read_text(encoding="utf-8")
    assert dump_experiment(load_experiment(path)) == text


def test_dump_then_parse_is_stable() -> None:  # EXP-2
    once = dump_experiment(parse_experiment(BASE))
    twice = dump_experiment(parse_experiment(once))
    assert once == twice


def test_condition_changes_only_the_overridden_field() -> None:  # EXP-4
    exp = parse_experiment(BASE)
    resolved = resolve_condition(exp, "full_capability")
    before = yaml.safe_load(dump_experiment(exp))
    after = yaml.safe_load(dump_experiment(resolved))
    before["conditions"] = {}
    after["conditions"] = {}
    assert after["agents"]["a"]["grants"]["write"] == ["config/**"]
    before["agents"]["a"]["grants"]["write"] = ["config/**"]
    assert before == after


def test_condition_does_not_mutate_the_base_experiment() -> None:  # EXP-4
    exp = parse_experiment(BASE)
    resolve_condition(exp, "full_capability")
    assert exp.agents["a"].grants.write == ()


def test_unknown_condition_name_is_an_error() -> None:  # EXP-4
    with pytest.raises(UnknownCondition):
        resolve_condition(parse_experiment(BASE), "missing")


def _with_condition(overrides: dict[str, Any]) -> str:
    base = BASE.split("conditions:")[0]
    lines = "".join(f"    {path}: {value!r}\n" for path, value in overrides.items())
    return base + "conditions:\n  bad:\n" + lines


def test_override_of_unknown_field_is_rejected() -> None:  # EXP-4
    text = _with_condition({"agents.a.grants.delete": "[]"})
    with pytest.raises(ValidationError, match="unknown field"):
        parse_experiment(text)


def test_override_of_unknown_agent_is_rejected() -> None:  # EXP-4
    text = _with_condition({"agents.z.grants.write": "[]"})
    with pytest.raises(ValidationError, match="unknown field"):
        parse_experiment(text)


def test_override_value_is_validated() -> None:  # EXP-4, PRM-3
    text = (
        BASE.split("conditions:")[0]
        + "conditions:\n  bad:\n    agents.a.grants.write:\n    - ../escape/**\n"
    )
    with pytest.raises(ValidationError, match="escape"):
        parse_experiment(text)


def test_condition_name_is_validated() -> None:  # EXP-4
    text = BASE.replace("  full_capability:", "  Full Capability:")
    with pytest.raises(ValidationError):
        parse_experiment(text)
