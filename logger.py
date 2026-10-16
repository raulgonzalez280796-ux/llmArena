"""Private JSONL audit log. No file tool can access this path."""

import json
from datetime import datetime, timezone
from pathlib import Path


class EventLogger:
    def __init__(self, path: Path, run_id: str):
        self.run_id = run_id
        self.sequence = 0
        self.stream = path.open("x", encoding="utf-8")

    def emit(self, event_type: str, **data) -> None:
        self.sequence += 1
        record = {
            "run_id": self.run_id,
            "seq": self.sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data,
        }
        self.stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.stream.flush()

    def close(self) -> None:
        self.stream.close()
