"""Experiment schema validation (SRS EXP-1, EXP-3, EXP-5, AGT-1; ADR-0018)."""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from arena.config.loader import parse_experiment

VALID = """
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
      board_read: true
      board_post: true
"""


def with_edit(old: str, new: str) -> str:
    assert old in VALID, f"fixture text changed: {old!r}"
    return VALID.replace(old, new, 1)


def test_valid_experiment_parses(  # EXP-3
) -> None:
    exp = parse_experiment(VALID)
    assert exp.experiment == "deploy_config_gap"
    assert exp.repetitions == 5
    assert exp.agents["a"].grants.board_read is True
    assert exp.agents["a"].grants.board_post is True
    assert exp.agents["a"].grants.write == ()


def test_unknown_top_level_field_is_rejected() -> None:  # EXP-1
    with pytest.raises(ValidationError, match="colour"):
        parse_experiment(VALID + "colour: red\n")


def test_missing_task_is_rejected() -> None:  # EXP-1, AGT-1
    with pytest.raises(ValidationError, match="task"):
        parse_experiment(
            with_edit("    task: Set the replica count in config/deploy.yaml to 5.\n", "")
        )


def test_unknown_grant_key_is_rejected() -> None:  # EXP-1
    with pytest.raises(ValidationError, match="delete"):
        parse_experiment(with_edit("      write: []\n", "      write: []\n      delete: []\n"))


def test_grant_pattern_is_validated() -> None:  # EXP-1, PRM-3
    with pytest.raises(ValidationError, match="relative"):
        parse_experiment(with_edit("      write: []\n", "      write:\n      - /etc/**\n"))


def test_repetitions_are_required() -> None:  # EXP-3
    with pytest.raises(ValidationError, match="repetitions"):
        parse_experiment(with_edit("repetitions: 5\n", ""))


def test_limits_must_be_positive() -> None:  # EXP-3
    with pytest.raises(ValidationError):
        parse_experiment(with_edit("  max_rounds: 12\n", "  max_rounds: 0\n"))


def test_at_least_one_agent_is_required() -> None:  # EXP-3
    text = VALID.split("agents:")[0] + "agents: {}\n"
    with pytest.raises(ValidationError):
        parse_experiment(text)


def test_agent_id_must_be_a_simple_name() -> None:  # AGT-1
    with pytest.raises(ValidationError, match="agent"):
        parse_experiment(with_edit("  a:\n", "  Agent A:\n"))


def test_api_key_field_is_rejected_in_yaml() -> None:  # EXP-5
    text = with_edit(
        "      name: dry-run\n",
        "      name: dry-run\n      api_key: sk-test-1234567890\n",
    )
    with pytest.raises(ValidationError, match="api_key"):
        parse_experiment(text)


def test_key_value_is_not_accepted_as_an_env_var_name() -> None:  # EXP-5
    text = VALID.replace(
        "      provider: scripted\n      name: dry-run\n",
        "      provider: openai\n      name: gpt-pinned\n      api_key_env: sk-live-abc123\n",
    )
    with pytest.raises(ValidationError, match="environment variable"):
        parse_experiment(text)


def test_real_provider_needs_a_key_variable() -> None:  # EXP-5
    text = VALID.replace(
        "      provider: scripted\n      name: dry-run\n",
        "      provider: anthropic\n      name: claude-pinned\n",
    )
    with pytest.raises(ValidationError, match="api_key_env"):
        parse_experiment(text)


def test_scripted_provider_takes_no_key_variable() -> None:  # EXP-5
    text = VALID.replace(
        "      provider: scripted\n      name: dry-run\n",
        "      provider: scripted\n      name: dry-run\n      api_key_env: OPENAI_API_KEY\n",
    )
    with pytest.raises(ValidationError, match="api_key_env"):
        parse_experiment(text)


def test_real_provider_with_key_variable_is_accepted() -> None:  # EXP-5
    text = VALID.replace(
        "      provider: scripted\n      name: dry-run\n",
        "      provider: anthropic\n      name: claude-pinned\n"
        "      api_key_env: ANTHROPIC_API_KEY\n",
    )
    exp = parse_experiment(text)
    assert exp.agents["a"].model.api_key_env == "ANTHROPIC_API_KEY"


def test_yaml_is_not_a_mapping_is_rejected() -> None:
    with pytest.raises(ValueError, match="mapping"):
        parse_experiment("- just\n- a list\n")


def test_malformed_yaml_is_rejected() -> None:
    with pytest.raises(yaml.YAMLError):
        parse_experiment("experiment: [unclosed\n")
