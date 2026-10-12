"""One JSONL file per run, with one sequence for every event (SRS LOG-1; ADR-0012)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import IO, Self

from arena.events.model import Event


class JsonlSink:
    """Writes each event as one JSON line. Refuses to overwrite an existing run file."""

    def __init__(self, path: Path, *, run_id: str, condition: str, repetition: int) -> None:
        self._handle: IO[str] = path.open("x", encoding="utf-8")
        self._run_id = run_id
        self._condition = condition
        self._repetition = repetition
        self._seq = 0
        self.round: int | None = None

    def emit(self, event: Event) -> None:
        self._seq += 1
        record = {
            "run_id": self._run_id,
            "condition": self._condition,
            "repetition": self._repetition,
            "round": self.round,
            "seq": self._seq,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": event.type,
            "agent_id": event.agent_id,
            "data": dict(event.data),
        }
        self._handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
