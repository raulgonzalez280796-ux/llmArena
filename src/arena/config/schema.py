"""Experiment schema (SRS EXP-1..5, AGT-1; ADR-0018).

An experiment is one YAML file. Every model is strict: an unknown field is an error, so a
typo cannot silently change an experiment. Conditions override fields by dotted path, and
an override that names a field which does not exist is an error.
"""

from __future__ import annotations

import re
from typing import Any, Final, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from arena.workspace.paths import validate_glob

AGENT_ID = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
ENV_VAR = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
BASE_CONDITION: Final = "base"
FIXTURE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class UnknownCondition(KeyError):
    """The requested condition is not defined in the experiment."""


class OverrideError(ValueError):
    """A condition names a field that does not exist in the experiment."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelSpec(_Strict):
    # "scripted" is a dry-run stand-in for tests; real providers are chosen in phase 8.
    provider: Literal["scripted", "openai", "anthropic", "gemini"]
    name: str = Field(min_length=1, max_length=200)
    api_key_env: str | None = None

    @field_validator("api_key_env")
    @classmethod
    def _is_variable_name(cls, value: str | None) -> str | None:
        if value is not None and not ENV_VAR.match(value):
            raise ValueError("api_key_env must be an environment variable name, not a key")
        return value

    @model_validator(mode="after")
    def _key_variable_matches_provider(self) -> Self:
        if self.provider == "scripted" and self.api_key_env is not None:
            raise ValueError("api_key_env is not used by the scripted provider")
        if self.provider != "scripted" and self.api_key_env is None:
            raise ValueError(f"api_key_env is required for provider {self.provider!r}")
        return self


class Grants(_Strict):
    """What an agent may do. Everything not listed is denied (ADR-0019)."""

    read: tuple[str, ...] = ()  # offers list_files and read_file
    write: tuple[str, ...] = ()  # offers write_file
    board_read: bool = False  # offers read_board
    board_post: bool = False  # offers post_to_board

    @field_validator("read", "write")
    @classmethod
    def _patterns_are_well_formed(cls, patterns: tuple[str, ...]) -> tuple[str, ...]:
        for pattern in patterns:
            validate_glob(pattern)
        return patterns


class AgentSpec(_Strict):
    model: ModelSpec
    task: str = Field(min_length=1, max_length=4000)
    grants: Grants = Field(default_factory=Grants)


class Limits(_Strict):
    max_rounds: int = Field(ge=1, le=1000)
    max_total_tokens: int = Field(ge=1)


class ArtifactCheck(_Strict):
    """One value that must hold in a file after the run (EVL-1; ADR-0025)."""

    file: str = Field(min_length=1, max_length=300)
    key: str = Field(min_length=1, max_length=100)  # dotted path into a YAML mapping
    expect: str | int | float | bool

    @field_validator("file")
    @classmethod
    def _concrete_file(cls, value: str) -> str:
        validate_glob(value)
        if any(ch in value for ch in "*?[]"):
            raise ValueError("the artifact file must be one concrete path, not a pattern")
        return value


class Evaluation(_Strict):
    artifact: ArtifactCheck
    relevant_post_mentions: tuple[str, ...] = Field(min_length=1)


class Experiment(_Strict):
    experiment: str = Field(pattern=NAME.pattern)
    description: str | None = Field(default=None, max_length=1000)
    fixture: str = Field(pattern=FIXTURE.pattern)
    limits: Limits
    repetitions: int = Field(ge=1, le=1000)
    agents: dict[str, AgentSpec]
    conditions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    evaluation: Evaluation | None = None

    @field_validator("agents")
    @classmethod
    def _agent_ids(cls, agents: dict[str, AgentSpec]) -> dict[str, AgentSpec]:
        if not agents:
            raise ValueError("an experiment needs at least one agent")
        for agent_id in agents:
            if not AGENT_ID.match(agent_id):
                raise ValueError(f"agent id must be a lowercase name: {agent_id!r}")
        return agents

    @field_validator("conditions")
    @classmethod
    def _condition_names(cls, conditions: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        for name in conditions:
            if not NAME.match(name):
                raise ValueError(f"condition name must be a lowercase name: {name!r}")
            if name == BASE_CONDITION:
                raise ValueError(
                    f"condition name {name!r} is reserved for the unchanged experiment"
                )
        return conditions

    @model_validator(mode="after")
    def _every_condition_resolves(self) -> Self:
        for name in self.conditions:
            resolve_condition(self, name)
        return self


def resolve_condition(experiment: Experiment, name: str) -> Experiment:
    """Return the experiment with one condition's overrides applied and validated."""
    if name not in experiment.conditions:
        raise UnknownCondition(name)
    data = experiment.model_dump(mode="json", exclude_none=True, exclude={"conditions"})
    for dotted, value in experiment.conditions[name].items():
        _set_existing(data, dotted, value)
    return Experiment.model_validate(data)


def _set_existing(data: dict[str, Any], dotted: str, value: object) -> None:
    """Set an existing field by dotted path. Creating new fields is not allowed."""
    *parents, leaf = dotted.split(".")
    node: dict[str, Any] = data
    for key in parents:
        child = node.get(key)
        if not isinstance(child, dict):
            raise OverrideError(f"unknown field: {dotted}")
        node = cast(dict[str, Any], child)
    if leaf not in node:
        raise OverrideError(f"unknown field: {dotted}")
    node[leaf] = value
