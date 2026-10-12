"""Real clients for the pilot providers, built offline (SRS AGT-5, LOG-4; ADR-0028)."""

from __future__ import annotations

from typing import Any

import pytest
from agent_framework import BaseChatClient, ChatMiddlewareLayer, FunctionInvocationLayer
from agent_framework.anthropic import AnthropicClient
from agent_framework.gemini import GeminiChatClient
from agent_framework.openai import OpenAIChatClient

from arena.agents.providers import (
    TOOL_ROUNDS_PER_STEP,
    MissingApiKey,
    build_client,
    missing_keys,
    read_api_key,
)
from arena.agents.trace import ModelTrace
from arena.config.schema import AgentSpec
from arena.events.model import ListSink

SENTINEL = "sk-sentinel-never-print-4242"


def spec(provider: str, name: str, env: str | None) -> AgentSpec:
    model: dict[str, Any] = {"provider": provider, "name": name}
    if env is not None:
        model["api_key_env"] = env
    return AgentSpec.model_validate({"model": model, "task": "Do the task."})


@pytest.mark.parametrize(
    ("provider", "name", "env", "cls"),
    [
        ("anthropic", "claude-opus-5-5", "ANTHROPIC_API_KEY", AnthropicClient),
        ("openai", "gpt-6-astra", "OPENAI_API_KEY", OpenAIChatClient),
        ("gemini", "gemini-3.8-flash", "GEMINI_API_KEY", GeminiChatClient),
    ],
)
def test_each_provider_gets_its_own_client_for_the_pinned_model(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    name: str,
    env: str,
    cls: type[BaseChatClient[Any]],
) -> None:  # AGT-5
    monkeypatch.setenv(env, SENTINEL)
    client = build_client("a", spec(provider, name, env), ModelTrace(ListSink(), agent_id="a"))
    assert isinstance(client, cls)
    assert client.model == name  # type: ignore[attr-defined]


@pytest.mark.parametrize("cls", [AnthropicClient, OpenAIChatClient, GeminiChatClient])
def test_the_tool_loop_runs_inside_the_trace_so_every_round_trip_is_logged(
    cls: type[object],
) -> None:  # LOG-2
    order = [c.__name__ for c in cls.__mro__]
    assert order.index(FunctionInvocationLayer.__name__) < order.index(ChatMiddlewareLayer.__name__)


def test_every_real_client_uses_the_same_tool_loop_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL)
    built: Any = build_client(
        "a", spec("openai", "gpt-6-astra", "OPENAI_API_KEY"), ModelTrace(ListSink(), agent_id="a")
    )
    config = built.function_invocation_configuration
    assert config["max_iterations"] == TOOL_ROUNDS_PER_STEP == 10
    assert config["allow_concurrent_invocation"] is False


def test_a_missing_key_fails_with_the_variable_name_and_no_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # LOG-4
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingApiKey) as info:
        build_client(
            "a",
            spec("anthropic", "claude-opus-5-5", "ANTHROPIC_API_KEY"),
            ModelTrace(ListSink(), agent_id="a"),
        )
    assert "ANTHROPIC_API_KEY" in str(info.value)


def test_a_blank_key_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    with pytest.raises(MissingApiKey):
        read_api_key("OPENAI_API_KEY")


def test_the_key_is_not_visible_in_the_client_or_the_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # LOG-4
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    sink = ListSink()
    client = build_client(
        "a", spec("gemini", "gemini-3.8-flash", "GEMINI_API_KEY"), ModelTrace(sink, agent_id="a")
    )
    assert SENTINEL not in repr(client)
    assert SENTINEL not in str(vars(client))
    assert SENTINEL not in repr(read_api_key("GEMINI_API_KEY"))


def test_missing_keys_lists_names_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL)
    agents = [
        spec("anthropic", "claude-opus-5-5", "ANTHROPIC_API_KEY"),
        spec("openai", "gpt-6-astra", "OPENAI_API_KEY"),
    ]
    assert missing_keys(agents) == ["ANTHROPIC_API_KEY"]


def test_a_scripted_agent_is_not_a_real_client() -> None:
    with pytest.raises(ValueError, match="dry runs"):
        build_client("a", spec("scripted", "dry-run", None), ModelTrace(ListSink(), agent_id="a"))
