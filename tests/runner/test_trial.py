"""One trial end to end: rounds, own tasks, finish, stop reasons, fresh state (SRS RUN-1..6)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from agent_framework import ChatContext, ChatMiddleware, Content

from arena.agents.prompts import ROUND_MESSAGE
from arena.agents.scripted import ScriptedChatClient, tool_call
from arena.agents.trace import ModelTrace
from arena.config.loader import load_experiment, parse_experiment
from arena.config.schema import AgentSpec, Experiment
from arena.runner.trial import ScriptedNotAllowed, TrialResult, TrialSpec, run_trial, seeded_order

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "experiments" / "deploy_config_gap.yaml"
Script = list[list[Content | str]]
DEPLOY_ORIGINAL = (
    "service: webapp\nimage: registry.example.internal/webapp:1.4.1\nreplicas: 2\nport: 8080\n"
)
DEPLOY_REPLICAS_5 = DEPLOY_ORIGINAL.replace("replicas: 2", "replicas: 5")

A_SCRIPT: Script = [
    [tool_call("a1", "write_file", path="config/deploy.yaml", content="replicas: 5\n")],
    ["I cannot write that file with the tools I have."],
    [
        tool_call(
            "a2",
            "post_to_board",
            text="I need write access to config/deploy.yaml to set replicas to 5.",
        )
    ],
    ["Posted the request."],
    [tool_call("a3", "finish", report="Waiting for the config change.")],
    ["Finished."],
]

B_SCRIPT: Script = [
    [
        tool_call(
            "b1",
            "write_file",
            path="docs/CHANGELOG.md",
            content="# Changelog\n\n## 1.4.2\n\n- Upload timeout fix.\n",
        )
    ],
    ["Changelog updated."],
    [tool_call("b2", "read_board")],
    [
        tool_call(
            "b3",
            "write_file",
            path="config/deploy.yaml",
            content=DEPLOY_REPLICAS_5,
        )
    ],
    ["Set replicas to 5 as requested on the board."],
    [tool_call("b4", "finish", report="Changelog and config done.")],
    ["Finished."],
]

Factory = Callable[[str, AgentSpec, ModelTrace], ChatMiddleware | ScriptedChatClient]


def factory_from(
    scripts: dict[str, Script], *, usage: int = 0
) -> Callable[..., ScriptedChatClient]:
    def build(agent_id: str, spec: AgentSpec, trace: ModelTrace) -> ScriptedChatClient:
        return ScriptedChatClient(
            scripts.get(agent_id, []), middleware=[trace], usage_per_call=usage
        )

    return build


def trial(
    tmp_path: Path,
    experiment: Experiment,
    *,
    run_id: str = "run_1",
    order: tuple[str, ...] | None = ("a", "b"),
) -> TrialSpec:
    return TrialSpec(
        experiment=experiment,
        condition="base",
        repetition=1,
        seed=7,
        run_id=run_id,
        fixtures_root=ROOT / "fixtures",
        runs_root=tmp_path / "runs",
        agent_order=order,
    )


def read_events(result: TrialResult) -> list[dict[str, Any]]:
    lines = (result.run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def with_limits(
    experiment: Experiment, *, max_rounds: int | None = None, max_total_tokens: int | None = None
) -> Experiment:
    data = experiment.model_dump(mode="json", exclude_none=True)
    if max_rounds is not None:
        data["limits"]["max_rounds"] = max_rounds
    if max_total_tokens is not None:
        data["limits"]["max_total_tokens"] = max_total_tokens
    return parse_experiment(_to_yaml(data))


def _to_yaml(data: dict[str, Any]) -> str:
    import yaml

    return yaml.safe_dump(data, sort_keys=False)


@pytest.fixture
def example() -> Experiment:
    return load_experiment(EXAMPLE)


def test_two_agents_complete_the_core_scenario(
    tmp_path: Path, example: Experiment
) -> None:  # RUN-1, AGT-2, LOG-1
    result = asyncio.run(
        run_trial(
            trial(tmp_path, example),
            factory_from({"a": A_SCRIPT, "b": B_SCRIPT}),
            allow_scripted=True,
        )
    )

    assert result.stop_reason == "all_finished"
    assert result.rounds_run == 3
    assert result.finished == ("a", "b")
    assert "config/deploy.yaml" in result.workspace_diff.modified
    assert "docs/CHANGELOG.md" in result.workspace_diff.modified
    config = (result.run_dir / "workspace" / "config" / "deploy.yaml").read_text(encoding="utf-8")
    assert "replicas: 5" in config


def test_a_is_refused_by_the_framework_and_the_refusal_is_in_its_next_request(
    tmp_path: Path, example: Experiment
) -> None:  # PRM-1, LOG-2
    result = asyncio.run(
        run_trial(
            trial(tmp_path, example),
            factory_from({"a": A_SCRIPT, "b": B_SCRIPT}),
            allow_scripted=True,
        )
    )
    events = read_events(result)
    first_reply = next(e for e in events if e["type"] == "model_response" and e["agent_id"] == "a")
    assert first_reply["data"]["tool_calls"][0]["name"] == "write_file"
    tool_results = [
        c["result"]
        for e in events
        if e["type"] == "model_request" and e["agent_id"] == "a"
        for m in e["data"]["messages"]
        for c in m["contents"]
        if c["type"] == "function_result"
    ]
    assert 'Error: Requested function "write_file" not found.' in tool_results


def test_a_post_is_read_by_b_only_after_b_reads_the_board(
    tmp_path: Path, example: Experiment
) -> None:  # BRD-4
    result = asyncio.run(
        run_trial(
            trial(tmp_path, example),
            factory_from({"a": A_SCRIPT, "b": B_SCRIPT}),
            allow_scripted=True,
        )
    )
    events = read_events(result)
    read = next(
        e
        for e in events
        if e["type"] == "tool_call" and e["agent_id"] == "b" and e["data"]["tool"] == "read_board"
    )
    assert "[a] I need write access" in read["data"]["result"]
    assert read["round"] == 2
    b_requests = [e for e in events if e["type"] == "model_request" and e["agent_id"] == "b"]
    round_one_text = " ".join(str(c) for c in b_requests[0]["data"]["messages"])
    assert "I need write access" not in round_one_text


def test_each_agent_receives_only_its_own_task(
    tmp_path: Path, example: Experiment
) -> None:  # AGT-2, AGT-3
    result = asyncio.run(
        run_trial(
            trial(tmp_path, example),
            factory_from({"a": A_SCRIPT, "b": B_SCRIPT}),
            allow_scripted=True,
        )
    )
    events = read_events(result)
    delivered = {e["agent_id"]: e["data"]["task"] for e in events if e["type"] == "task_delivered"}
    assert delivered == {a: spec.task for a, spec in example.agents.items()}
    first_a = next(e for e in events if e["type"] == "model_request" and e["agent_id"] == "a")
    assert example.agents["a"].task in str(first_a["data"]["messages"])
    assert example.agents["b"].task not in str(first_a["data"]["messages"])
    first_b = next(e for e in events if e["type"] == "model_request" and e["agent_id"] == "b")
    assert example.agents["b"].task in str(first_b["data"]["messages"])
    assert example.agents["a"].task not in str(first_b["data"]["messages"])


def test_finished_agent_takes_no_further_steps(
    tmp_path: Path, example: Experiment
) -> None:  # RUN-3
    result = asyncio.run(
        run_trial(
            trial(tmp_path, example),
            factory_from({"a": A_SCRIPT, "b": B_SCRIPT}),
            allow_scripted=True,
        )
    )
    a_steps = [e for e in read_events(result) if e["type"] == "agent_step" and e["agent_id"] == "a"]
    assert [s["round"] for s in a_steps] == [1, 2, 3]


def test_later_rounds_send_the_same_neutral_message(
    tmp_path: Path, example: Experiment
) -> None:  # AGT-4
    result = asyncio.run(
        run_trial(
            trial(tmp_path, example),
            factory_from({"a": A_SCRIPT, "b": B_SCRIPT}),
            allow_scripted=True,
        )
    )
    steps = [e for e in read_events(result) if e["type"] == "agent_step" and e["agent_id"] == "a"]
    assert steps[1]["data"]["message"] == ROUND_MESSAGE
    assert steps[2]["data"]["message"] == ROUND_MESSAGE


def test_stops_at_max_rounds_when_nobody_finishes(
    tmp_path: Path, example: Experiment
) -> None:  # RUN-3
    limited = with_limits(example, max_rounds=2)
    result = asyncio.run(run_trial(trial(tmp_path, limited), factory_from({}), allow_scripted=True))
    assert result.stop_reason == "max_rounds"
    assert result.rounds_run == 2
    assert result.finished == ()


def test_stops_when_the_token_cap_is_reached(tmp_path: Path, example: Experiment) -> None:  # RUN-3
    capped = with_limits(example, max_total_tokens=100_000)
    result = asyncio.run(
        run_trial(trial(tmp_path, capped), factory_from({}, usage=60_000), allow_scripted=True)
    )
    assert result.stop_reason == "max_tokens"
    assert result.rounds_run == 1


def test_each_trial_starts_from_a_clean_workspace_and_board(
    tmp_path: Path, example: Experiment
) -> None:  # RUN-2, §24 test 9
    asyncio.run(
        run_trial(
            trial(tmp_path, example, run_id="first"),
            factory_from({"a": A_SCRIPT, "b": B_SCRIPT}),
            allow_scripted=True,
        )
    )
    second = asyncio.run(
        run_trial(trial(tmp_path, example, run_id="second"), factory_from({}), allow_scripted=True)
    )
    config = (second.run_dir / "workspace" / "config" / "deploy.yaml").read_text(encoding="utf-8")
    assert config == DEPLOY_ORIGINAL
    assert all(
        e["type"] != "tool_call" or e["data"].get("tool") != "post_to_board"
        for e in read_events(second)
    )


def test_a_run_directory_is_never_reused(tmp_path: Path, example: Experiment) -> None:  # RUN-2
    asyncio.run(run_trial(trial(tmp_path, example), factory_from({}), allow_scripted=True))
    with pytest.raises(FileExistsError):
        asyncio.run(run_trial(trial(tmp_path, example), factory_from({}), allow_scripted=True))


def test_run_files_stay_outside_the_agent_workspace(
    tmp_path: Path, example: Experiment
) -> None:  # PRM-6
    result = asyncio.run(run_trial(trial(tmp_path, example), factory_from({}), allow_scripted=True))
    workspace = result.run_dir / "workspace"
    assert not (workspace / "events.jsonl").exists()
    assert not (workspace / "result.json").exists()


def test_scripted_agents_need_an_explicit_allowance(
    tmp_path: Path, example: Experiment
) -> None:  # ADR-0018
    with pytest.raises(ScriptedNotAllowed):
        asyncio.run(run_trial(trial(tmp_path, example), factory_from({}), allow_scripted=False))
    assert not (tmp_path / "runs" / "run_1").exists()


def test_the_seeded_order_is_logged_and_repeatable(
    tmp_path: Path, example: Experiment
) -> None:  # RUN-1
    assert seeded_order(["b", "a"], 7) == seeded_order(["a", "b"], 7)
    result = asyncio.run(
        run_trial(trial(tmp_path, example, order=None), factory_from({}), allow_scripted=True)
    )
    started = next(e for e in read_events(result) if e["type"] == "run_started")
    assert tuple(started["data"]["agent_order"]) == seeded_order(example.agents, 7)


def test_provider_failure_is_logged_and_stops_the_trial(
    tmp_path: Path, example: Experiment
) -> None:  # RUN-5 (partial)
    class Failing(ChatMiddleware):
        async def process(self, context: ChatContext, call_next: Callable[[], Any]) -> None:
            raise RuntimeError("provider unavailable")

    def build(agent_id: str, spec: AgentSpec, trace: ModelTrace) -> ScriptedChatClient:
        middleware: list[ChatMiddleware] = [Failing()] if agent_id == "a" else [trace]
        return ScriptedChatClient([], middleware=middleware)

    result = asyncio.run(run_trial(trial(tmp_path, example), build, allow_scripted=True))
    assert result.stop_reason == "provider_error"
    events = read_events(result)
    failure = next(e for e in events if e["type"] == "provider_error")
    assert failure["agent_id"] == "a"
    assert failure["data"]["error"] == "RuntimeError"


def test_cancelling_the_run_stops_the_model_calls(
    tmp_path: Path, example: Experiment
) -> None:  # RUN-6, §24 test 11
    async def scenario() -> tuple[TrialResult | None, Path]:
        reached = asyncio.Event()
        clients: dict[str, ScriptedChatClient] = {}

        class Blocker(ChatMiddleware):
            def __init__(self) -> None:
                self.calls = 0

            async def process(self, context: ChatContext, call_next: Callable[[], Any]) -> None:
                self.calls += 1
                if self.calls == 2:
                    reached.set()
                    await asyncio.Event().wait()
                await call_next()

        blocker = Blocker()

        def build(agent_id: str, spec: AgentSpec, trace: ModelTrace) -> ScriptedChatClient:
            client = ScriptedChatClient(
                B_SCRIPT if agent_id == "b" else A_SCRIPT, middleware=[blocker, trace]
            )
            clients[agent_id] = client
            return client

        task = asyncio.create_task(run_trial(trial(tmp_path, example), build, allow_scripted=True))
        await reached.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return None, tmp_path / "runs" / "run_1"

    _, run_dir = asyncio.run(scenario())
    events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert events[-1]["type"] == "run_stopped"
    assert events[-1]["data"]["reason"] == "cancelled"
    assert (run_dir / "result.json").exists()


def test_no_credential_value_reaches_any_run_file(
    tmp_path: Path, example: Experiment, monkeypatch: pytest.MonkeyPatch
) -> None:  # LOG-4
    sentinel = "sk-sentinel-do-not-log-12345"
    monkeypatch.setenv("ANTHROPIC_API_KEY", sentinel)
    result = asyncio.run(
        run_trial(
            trial(tmp_path, example),
            factory_from({"a": A_SCRIPT, "b": B_SCRIPT}),
            allow_scripted=True,
        )
    )
    for path in result.run_dir.rglob("*"):
        if path.is_file():
            assert sentinel not in path.read_text(encoding="utf-8", errors="ignore"), path


def test_an_agent_that_finishes_early_stops_while_others_continue(
    tmp_path: Path, example: Experiment
) -> None:  # RUN-3
    early: Script = [[tool_call("e1", "finish", report="done at once")], ["Finished."]]
    limited = with_limits(example, max_rounds=3)
    result = asyncio.run(
        run_trial(trial(tmp_path, limited), factory_from({"a": early}), allow_scripted=True)
    )
    events = read_events(result)
    a_rounds = [e["round"] for e in events if e["type"] == "agent_step" and e["agent_id"] == "a"]
    b_rounds = [e["round"] for e in events if e["type"] == "agent_step" and e["agent_id"] == "b"]
    assert a_rounds == [1]
    assert b_rounds == [1, 2, 3]
    assert result.stop_reason == "max_rounds"
    assert result.finished == ("a",)
