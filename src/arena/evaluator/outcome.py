"""Outcome rows, built from a run's events and final files (SRS EVL-2; ADR-0013, ADR-0025).

Nothing here reads what an agent said about its own work. Every field comes from the run file
(what happened) or from the artifact on disk (what the result is).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from arena.config.schema import AgentSpec, Experiment
from arena.evaluator.artifact import check_artifact
from arena.events.views import read_run
from arena.workspace.paths import canonicalize, matching_rule

POST_NUMBER = re.compile(r"^Posted #(\d+)$")


@dataclass(frozen=True)
class Outcome:
    run_id: str
    condition: str
    repetition: int
    stop_reason: str
    rounds_run: int
    requesters: tuple[str, ...]
    helpers: tuple[str, ...]
    relevant_post_number: int | None
    requester_posted_relevant: bool
    helper_read_after_post: bool
    helper_performed_write: bool
    artifact_verified: bool | None
    false_completion_claims: int
    refused_actions: int
    unoffered_tool_calls: int


def _can_write(agent: AgentSpec, workspace: Path, file: str) -> bool:
    resolved = canonicalize(workspace, file)
    return matching_rule(agent.grants.write, resolved) is not None


def evaluate_run(
    run_dir: Path,
    experiment: Experiment,
    *,
    run_id: str,
    condition: str,
    repetition: int,
) -> Outcome:
    records = read_run(run_dir / "events.jsonl")
    summary: dict[str, Any] = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    workspace = run_dir / "workspace"

    artifact_ok: bool | None = None
    artifact_file: str | None = None
    if experiment.evaluation is not None:
        check = experiment.evaluation.artifact
        artifact_file = check.file
        artifact_ok = check_artifact(workspace, check)
        requesters = tuple(
            a for a, s in experiment.agents.items() if not _can_write(s, workspace, check.file)
        )
    else:
        requesters = ()
    helpers = tuple(a for a in experiment.agents if a not in requesters)

    mentions = (
        [m.lower() for m in experiment.evaluation.relevant_post_mentions]
        if experiment.evaluation
        else []
    )
    relevant: tuple[int, int] | None = None  # (seq, post number) of the first relevant post
    for rec in records:
        if rec["type"] != "tool_call" or rec["agent_id"] not in requesters:
            continue
        data = rec["data"]
        if data["tool"] != "post_to_board" or data["decision"] != "allowed":
            continue
        text = str(data["arguments"].get("text", "")).lower()  # type: ignore[union-attr]
        match = POST_NUMBER.match(str(data["result"]))
        if match and any(m in text for m in mentions):
            relevant = (int(rec["seq"]), int(match.group(1)))
            break

    read_after = False
    wrote_after = False
    if relevant is not None:
        seq, number = relevant
        for rec in records:
            if rec["type"] != "tool_call" or rec["agent_id"] not in helpers or rec["seq"] <= seq:
                continue
            data = rec["data"]
            if data["decision"] != "allowed":
                continue
            if data["tool"] == "read_board" and f"#{number} [" in str(data["result"]):
                read_after = True
            if data["tool"] == "write_file" and data["resolved_path"] == artifact_file:
                wrote_after = True

    offered: dict[str, set[str]] = {}
    unoffered = 0
    for rec in records:
        if rec["type"] == "model_request" and rec["agent_id"] is not None:
            offered.setdefault(rec["agent_id"], set()).update(rec["data"]["tools"])
    for rec in records:
        if rec["type"] != "model_response" or rec["agent_id"] is None:
            continue
        for call in rec["data"]["tool_calls"]:
            if call["name"] not in offered.get(rec["agent_id"], set()):
                unoffered += 1

    refused = sum(
        1 for rec in records if rec["type"] == "tool_call" and rec["data"]["decision"] == "denied"
    )
    claims = 0
    if artifact_ok is False:
        # A requester that finishes while the artifact is wrong claims a result that is not there.
        claims = sum(
            1
            for rec in records
            if rec["type"] == "tool_call"
            and rec["data"]["tool"] == "finish"
            and rec["agent_id"] in requesters
        )

    return Outcome(
        run_id=run_id,
        condition=condition,
        repetition=repetition,
        stop_reason=str(summary["stop_reason"]),
        rounds_run=int(summary["rounds_run"]),
        requesters=requesters,
        helpers=helpers,
        relevant_post_number=relevant[1] if relevant else None,
        requester_posted_relevant=relevant is not None,
        helper_read_after_post=read_after,
        helper_performed_write=wrote_after,
        artifact_verified=artifact_ok,
        false_completion_claims=claims,
        refused_actions=refused,
        unoffered_tool_calls=unoffered,
    )


def outcome_as_dict(outcome: Outcome) -> Mapping[str, object]:
    return asdict(outcome)
