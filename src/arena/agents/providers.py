"""Real model clients for the pilot providers (SRS AGT-5, LOG-2, LOG-4; ADR-0028).

Each agent gets its own client, built from its model settings. The key is read from the
environment variable the experiment names, wrapped so it cannot be printed, and never written
to a file or to the run log. Every client gets the same tool-loop limit and the same trace
middleware, so the model log covers every round trip.
"""

from __future__ import annotations

import os
from typing import Any, Final

from agent_framework import BaseChatClient, FunctionInvocationConfiguration, SecretString
from agent_framework.anthropic import AnthropicClient
from agent_framework.gemini import GeminiChatClient
from agent_framework.openai import OpenAIChatClient

from arena.agents.trace import ModelTrace
from arena.config.schema import AgentSpec

# Model round trips allowed inside one agent step. The same value is part of every run's
# fingerprint through the runner's documented defaults (ADR-0024).
TOOL_ROUNDS_PER_STEP: Final = 10
FUNCTION_INVOCATION: Final[FunctionInvocationConfiguration] = {
    "max_iterations": TOOL_ROUNDS_PER_STEP,
    "allow_concurrent_invocation": False,
}


class MissingApiKey(RuntimeError):
    """An experiment names an environment variable that is not set. The value is never shown."""


def read_api_key(variable: str) -> SecretString:
    value = os.environ.get(variable, "")
    if not value.strip():
        raise MissingApiKey(f"environment variable {variable} is not set")
    return SecretString(value)


def missing_keys(agents: list[AgentSpec]) -> list[str]:
    """Names of the key variables that are needed and not set (values are never returned)."""
    names = {a.model.api_key_env for a in agents if a.model.api_key_env}
    return sorted(name for name in names if not os.environ.get(name, "").strip())


def build_client(agent_id: str, spec: AgentSpec, trace: ModelTrace) -> BaseChatClient[Any]:
    model = spec.model
    if model.provider == "scripted" or model.api_key_env is None:
        raise ValueError(f"agent {agent_id}: the scripted provider is for dry runs, not real calls")
    key = read_api_key(model.api_key_env)
    if model.provider == "openai":
        return OpenAIChatClient(
            model=model.name,
            api_key=key,
            middleware=[trace],
            function_invocation_configuration=FUNCTION_INVOCATION,
        )
    if model.provider == "anthropic":
        return AnthropicClient(
            model=model.name,
            api_key=key,
            middleware=[trace],
            function_invocation_configuration=FUNCTION_INVOCATION,
        )
    return GeminiChatClient(
        model=model.name,
        api_key=key,
        middleware=[trace],
        function_invocation_configuration=FUNCTION_INVOCATION,
    )
