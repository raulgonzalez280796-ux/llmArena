"""YAML loading rejects ambiguous input (SRS EXP-1; ADR-0018)."""

from __future__ import annotations

import pytest
import yaml

from arena.config.loader import parse_experiment


def test_duplicate_top_level_key_is_rejected() -> None:  # EXP-1
    text = "experiment: one\nexperiment: two\n"
    with pytest.raises(yaml.YAMLError, match="duplicate key"):
        parse_experiment(text)


def test_duplicate_nested_key_is_rejected() -> None:  # EXP-1
    text = "experiment: x\nlimits:\n  max_rounds: 1\n  max_rounds: 2\n"
    with pytest.raises(yaml.YAMLError, match="duplicate key"):
        parse_experiment(text)
