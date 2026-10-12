"""The JSONL collector: one file per run, one sequence, run context on every line (SRS LOG-1)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from arena.events.jsonl import JsonlSink
from arena.events.model import Event


def read_lines(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_every_line_carries_run_context_and_agent_id(tmp_path: Path) -> None:  # LOG-1
    path = tmp_path / "events.jsonl"
    with JsonlSink(path, run_id="run_001", condition="full_capability", repetition=3) as sink:
        sink.emit(Event(type="tool_call", agent_id="a", data={"tool": "read_file"}))
    (record,) = read_lines(path)
    assert record["run_id"] == "run_001"
    assert record["condition"] == "full_capability"
    assert record["repetition"] == 3
    assert record["seq"] == 1
    assert record["agent_id"] == "a"
    assert record["type"] == "tool_call"
    assert record["data"] == {"tool": "read_file"}
    datetime.fromisoformat(str(record["timestamp"]))  # parses as ISO 8601


def test_sequence_is_gap_free_across_agents(tmp_path: Path) -> None:  # LOG-1
    path = tmp_path / "events.jsonl"
    with JsonlSink(path, run_id="r", condition="c", repetition=1) as sink:
        for agent in ("a", "b", "a", None):
            sink.emit(Event(type="x", agent_id=agent))
    assert [r["seq"] for r in read_lines(path)] == [1, 2, 3, 4]


def test_round_number_is_set_by_the_runner(tmp_path: Path) -> None:  # LOG-1
    path = tmp_path / "events.jsonl"
    with JsonlSink(path, run_id="r", condition="c", repetition=1) as sink:
        sink.emit(Event(type="before"))
        sink.round = 2
        sink.emit(Event(type="during", agent_id="a"))
    before, during = read_lines(path)
    assert before["round"] is None
    assert during["round"] == 2


def test_run_file_is_never_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text("existing\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        JsonlSink(path, run_id="r", condition="c", repetition=1)
    assert path.read_text(encoding="utf-8") == "existing\n"


def test_unicode_is_written_as_text_not_escapes(tmp_path: Path) -> None:  # LOG-2
    path = tmp_path / "events.jsonl"
    with JsonlSink(path, run_id="r", condition="c", repetition=1) as sink:
        sink.emit(Event(type="post", agent_id="a", data={"text": "שלום"}))
    assert "שלום" in path.read_text(encoding="utf-8")


def test_values_that_are_not_json_are_an_error_not_silently_dropped(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    with JsonlSink(path, run_id="r", condition="c", repetition=1) as sink, pytest.raises(TypeError):
        sink.emit(Event(type="bad", agent_id="a", data={"when": object()}))
