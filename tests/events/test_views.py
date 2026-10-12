"""Per-agent reasoning chain: a view over one events.jsonl (SRS LOG-3; ADR-0012)."""

from __future__ import annotations

from pathlib import Path

from arena.events.jsonl import JsonlSink
from arena.events.model import Event
from arena.events.views import agent_chain, read_run


def test_agent_chain_holds_only_that_agents_events_in_order(tmp_path: Path) -> None:  # LOG-3
    path = tmp_path / "events.jsonl"
    with JsonlSink(path, run_id="r", condition="c", repetition=1) as sink:
        sink.emit(Event(type="task_delivered", agent_id="a"))
        sink.emit(Event(type="task_delivered", agent_id="b"))
        sink.emit(Event(type="tool_call", agent_id="a", data={"tool": "post_to_board"}))
        sink.emit(Event(type="tool_call", agent_id="b", data={"tool": "read_board"}))
        sink.emit(Event(type="run_stopped"))

    chain_a = agent_chain(read_run(path), "a")
    assert [r["seq"] for r in chain_a] == [1, 3]
    assert {r["agent_id"] for r in chain_a} == {"a"}


def test_run_level_events_belong_to_no_agent_chain(tmp_path: Path) -> None:  # LOG-3
    path = tmp_path / "events.jsonl"
    with JsonlSink(path, run_id="r", condition="c", repetition=1) as sink:
        sink.emit(Event(type="run_stopped"))
    assert agent_chain(read_run(path), "a") == []
