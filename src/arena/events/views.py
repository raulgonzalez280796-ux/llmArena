"""Read a run file and view one agent's reasoning chain (SRS LOG-3; ADR-0012).

The chain is a filter over the run file, not a copy. Nothing is written back.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_run(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def agent_chain(records: list[dict[str, Any]], agent_id: str) -> list[dict[str, Any]]:
    return [r for r in records if r["agent_id"] == agent_id]
