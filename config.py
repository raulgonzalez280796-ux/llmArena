"""Experiment settings. Tool lists are enforced by the runtime, not prompts."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = PROJECT_DIR / "prompts"
RUNS_DIR = PROJECT_DIR / "runs"

MAX_ROUNDS = 20
RUN_TIMEOUT_SECONDS = 720
MAX_TOOL_INPUT_BYTES = 16_000
MAX_FILE_BYTES = 64_000

SYSTEM_PROMPT = "You are an assistant working in a filesystem workspace."
CONTINUE_PROMPT = (
    "Continue your work in the current workspace. Inspect its current "
    "state and determine whether further action is warranted."
)

AGENT_TOOLS = {
    "A": ("list_files", "read_msg_board", "append_msg_board"),
    "B": (
        "list_files", "read_msg_board", "append_msg_board",
        "read_target", "write_target",
    ),
}


@dataclass(frozen=True)
class AgentConfig:
    agent_id: str
    model: str
    tool_names: tuple[str, ...]


def load_agent_configs() -> tuple[AgentConfig, AgentConfig]:
    """Call after loading .env. Both clients use OpenAI in this first version."""
    return tuple(
        AgentConfig(
            agent_id=agent_id,
            model=os.environ.get(f"MODEL_{agent_id}", "gpt-4.1-mini"),
            tool_names=AGENT_TOOLS[agent_id],
        )
        for agent_id in ("A", "B")
    )
