"""YAML loading and canonical dumping of experiment files (SRS EXP-1, EXP-2; ADR-0018)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from arena.config.schema import Experiment


class _StrictLoader(yaml.SafeLoader):
    """A safe loader that rejects duplicate mapping keys instead of keeping the last one."""


def _mapping_without_duplicates(
    loader: Any, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_without_duplicates
)


def parse_experiment(text: str) -> Experiment:
    data = yaml.load(text, Loader=_StrictLoader)
    if not isinstance(data, dict):
        raise ValueError("an experiment file must be a YAML mapping")
    return Experiment.model_validate(data)


def load_experiment(path: Path) -> Experiment:
    return parse_experiment(path.read_text(encoding="utf-8"))


def dump_experiment(experiment: Experiment) -> str:
    """The one canonical text form of an experiment. Files in experiments/ must equal it."""
    data = experiment.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10_000,  # never wrap: the canonical form must be one line per value
    )
