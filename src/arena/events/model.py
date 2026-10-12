"""Event records and sinks (SRS LOG-1; the JSONL collector arrives in phase 4).

Phase 3 emits events to an in-memory sink. Phase 4 adds ``run_id``, ``seq`` and the file writer
without changing how the Tool Gateway emits them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Event:
    type: str
    agent_id: str
    data: Mapping[str, object] = field(default_factory=dict[str, object])


class EventSink(Protocol):
    def emit(self, event: Event) -> None: ...


class ListSink:
    """Keeps events in memory, in emission order."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def emit(self, event: Event) -> None:
        self.events.append(event)
