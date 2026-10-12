"""One trial: a fresh workspace, a fresh board and one agent per entry, run in fixed rounds.

Rounds, seeded order, stop reasons and fresh state follow SRS RUN-1..6, with ADR-0023 and
ADR-0024 for the decisions made in phase 5.
"""

from __future__ import annotations

import asyncio
import json
import random
import shutil
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_framework import Agent, AgentResponse, AgentSession, BaseChatClient

from arena.agents.prompts import NEUTRAL_INSTRUCTIONS, ROUND_MESSAGE
from arena.agents.trace import ModelTrace
from arena.board.service import Board
from arena.config.schema import AgentSpec, Experiment
from arena.events.jsonl import JsonlSink
from arena.events.model import Event
from arena.fingerprint import condition_fingerprint
from arena.tools.finish import build_finish_tool
from arena.tools.framework import build_tools
from arena.tools.gateway import ToolGateway
from arena.workspace.files import SnapshotDiff, Workspace, diff_snapshots, snapshot_tree

ClientFactory = Callable[[str, AgentSpec, ModelTrace], BaseChatClient[Any]]


class ScriptedNotAllowed(RuntimeError):
    """A scripted (dry-run) agent was used without an explicit allowance (ADR-0018)."""


@dataclass(frozen=True)
class TrialSpec:
    experiment: Experiment  # already resolved for the condition
    condition: str
    repetition: int
    seed: int
    run_id: str
    fixtures_root: Path
    runs_root: Path
    agent_order: tuple[str, ...] | None = None  # None: seeded order


@dataclass(frozen=True)
class TrialResult:
    run_id: str
    run_dir: Path
    stop_reason: str
    rounds_run: int
    finished: tuple[str, ...]
    workspace_diff: SnapshotDiff
    fingerprint: str


def seeded_order(agent_ids: Iterable[str], seed: int) -> tuple[str, ...]:
    ids = sorted(agent_ids)
    random.Random(seed).shuffle(ids)
    return tuple(ids)


@dataclass(eq=False)
class _Runtime:
    agent: Agent
    session: AgentSession
    task: str
    steps: int = 0
    finished: bool = False
    report: str | None = None


@dataclass(eq=False)
class _State:
    order: tuple[str, ...]
    runtimes: dict[str, _Runtime] = field(default_factory=dict[str, _Runtime])
    stop: str = "error"
    rounds: int = 0
    tokens: int = 0


def _tokens_of(response: AgentResponse[Any]) -> int:
    usage = response.usage_details or {}
    return int(usage.get("total_token_count") or 0)


async def run_trial(
    spec: TrialSpec,
    client_factory: ClientFactory,
    *,
    allow_scripted: bool = False,
) -> TrialResult:
    exp = spec.experiment
    if not allow_scripted and any(a.model.provider == "scripted" for a in exp.agents.values()):
        raise ScriptedNotAllowed("scripted agents are for dry runs; pass allow_scripted=True")
    if set(spec.agent_order or exp.agents) != set(exp.agents):
        raise ValueError("agent_order must list every agent exactly once")

    source = spec.fixtures_root / exp.fixture
    if not source.is_dir():
        raise FileNotFoundError(f"fixture not found: {source}")

    run_dir = spec.runs_root / spec.run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    workspace_dir = run_dir / "workspace"
    shutil.copytree(source, workspace_dir)
    before = snapshot_tree(workspace_dir)

    order = spec.agent_order or seeded_order(exp.agents, spec.seed)
    fingerprint = condition_fingerprint(exp)
    sink = JsonlSink(
        run_dir / "events.jsonl",
        run_id=spec.run_id,
        condition=spec.condition,
        repetition=spec.repetition,
    )
    state = _State(order=order)
    try:
        await _run_rounds(state, spec, client_factory, sink, Workspace(workspace_dir), Board())
    except asyncio.CancelledError:
        state.stop = "cancelled"
        raise
    finally:
        result = _conclude(state, spec, fingerprint, sink, workspace_dir, before)
    return result


async def _run_rounds(
    state: _State,
    spec: TrialSpec,
    client_factory: ClientFactory,
    sink: JsonlSink,
    workspace: Workspace,
    board: Board,
) -> None:
    exp = spec.experiment
    for agent_id in state.order:
        state.runtimes[agent_id] = _build_runtime(
            agent_id, exp.agents[agent_id], client_factory, sink, workspace, board, state
        )

    sink.emit(
        Event(
            type="run_started",
            data={
                "fingerprint": condition_fingerprint(exp),
                "seed": spec.seed,
                "agent_order": list(state.order),
                "fixture": exp.fixture,
                "max_rounds": exp.limits.max_rounds,
                "max_total_tokens": exp.limits.max_total_tokens,
            },
        )
    )
    for agent_id in state.order:
        sink.emit(
            Event(
                type="task_delivered", agent_id=agent_id, data={"task": exp.agents[agent_id].task}
            )
        )

    for round_no in range(1, exp.limits.max_rounds + 1):
        state.rounds = round_no
        sink.round = round_no
        sink.emit(
            Event(type="round_started", data={"round": round_no, "agent_order": list(state.order)})
        )
        for agent_id in state.order:
            runtime = state.runtimes[agent_id]
            if runtime.finished:
                continue
            message = runtime.task if runtime.steps == 0 else ROUND_MESSAGE
            runtime.steps += 1
            try:
                response = await runtime.agent.run(message, session=runtime.session)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                sink.emit(
                    Event(
                        type="provider_error",
                        agent_id=agent_id,
                        data={"error": type(exc).__name__, "message": str(exc)[:500]},
                    )
                )
                state.stop = "provider_error"
                return
            used = _tokens_of(response)
            state.tokens += used
            sink.emit(
                Event(
                    type="agent_step",
                    agent_id=agent_id,
                    data={
                        "round": round_no,
                        "step": runtime.steps,
                        "message": message,
                        "tokens": used,
                        "finished": runtime.finished,
                    },
                )
            )
            if state.tokens >= exp.limits.max_total_tokens:
                state.stop = "max_tokens"
                return
        if all(rt.finished for rt in state.runtimes.values()):
            state.stop = "all_finished"
            return
    state.stop = "max_rounds"


def _build_runtime(
    agent_id: str,
    agent_spec: AgentSpec,
    client_factory: ClientFactory,
    sink: JsonlSink,
    workspace: Workspace,
    board: Board,
    state: _State,
) -> _Runtime:
    gateway = ToolGateway(
        agent_id=agent_id,
        grants=agent_spec.grants,
        workspace=workspace,
        sink=sink,
        board=board if (agent_spec.grants.board_read or agent_spec.grants.board_post) else None,
    )
    trace = ModelTrace(sink, agent_id=agent_id)
    client = client_factory(agent_id, agent_spec, trace)
    runtime_ref: list[_Runtime] = []

    def on_finish(report: str) -> None:
        runtime = runtime_ref[0]
        runtime.finished = True
        runtime.report = report

    tools = [*build_tools(gateway), build_finish_tool(agent_id, sink, on_finish)]
    agent = Agent(client, NEUTRAL_INSTRUCTIONS, name=agent_id, tools=tools)
    runtime = _Runtime(agent=agent, session=agent.create_session(), task=agent_spec.task)
    runtime_ref.append(runtime)
    return runtime


def _conclude(
    state: _State,
    spec: TrialSpec,
    fingerprint: str,
    sink: JsonlSink,
    workspace_dir: Path,
    before: Mapping[str, str],
) -> TrialResult:
    sink.emit(
        Event(
            type="run_stopped",
            data={"reason": state.stop, "rounds_run": state.rounds, "total_tokens": state.tokens},
        )
    )
    sink.close()
    diff = diff_snapshots(before, snapshot_tree(workspace_dir))
    finished = tuple(a for a in state.order if state.runtimes.get(a) and state.runtimes[a].finished)
    result = TrialResult(
        run_id=spec.run_id,
        run_dir=spec.runs_root / spec.run_id,
        stop_reason=state.stop,
        rounds_run=state.rounds,
        finished=finished,
        workspace_diff=diff,
        fingerprint=fingerprint,
    )
    summary: dict[str, Any] = {
        "run_id": result.run_id,
        "condition": spec.condition,
        "repetition": spec.repetition,
        "seed": spec.seed,
        "fingerprint": fingerprint,
        "agent_order": list(state.order),
        "stop_reason": state.stop,
        "rounds_run": state.rounds,
        "total_tokens": state.tokens,
        "finished": list(finished),
        "workspace_diff": {
            "added": list(diff.added),
            "removed": list(diff.removed),
            "modified": list(diff.modified),
        },
    }
    (result.run_dir / "result.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result
