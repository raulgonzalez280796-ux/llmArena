"""Event records and sinks (SRS LOG-1; ADR-0012).

The Tool Gateway and the model trace emit events to a sink. ``JsonlSink`` writes them to a run
file and adds the run context (run id, condition, repetition, round, sequence, time).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Event:
    type: str
    agent_id: str | None = None  # None for run-level events
    data: Mapping[str, object] = field(default_factory=dict[str, object])


class EventSink(Protocol):
    def emit(self, event: Event) -> None: ...


class ListSink:
    """Keeps events in memory, in emission order."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def emit(self, event: Event) -> None:
        self.events.append(event)
