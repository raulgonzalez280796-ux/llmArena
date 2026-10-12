"""The finish tool: an agent's way to end its own work (SRS RUN-3; ADR-0023).

Every agent gets it, so it reveals nothing about any one agent. It is not a gateway tool: it
changes the runner's state for this agent only, and it is logged like any other tool call.
"""

from __future__ import annotations

from collections.abc import Callable

from agent_framework import FunctionTool, tool

from arena.events.model import Event, EventSink

FINISH_TOOL_NAME = "finish"
FINISH_DESCRIPTION = "Mark your task as finished. Give a short report of what you did."
FINISHED_TEXT = "Finished."


def build_finish_tool(
    agent_id: str,
    sink: EventSink,
    on_finish: Callable[[str], None],
) -> FunctionTool:
    @tool(name="finish", description=FINISH_DESCRIPTION)
    def finish(report: str) -> str:
        on_finish(report)
        sink.emit(
            Event(
                type="tool_call",
                agent_id=agent_id,
                data={
                    "tool": "finish",
                    "arguments": {"report": report},
                    "decision": "allowed",
                    "reason": None,
                    "resolved_path": None,
                    "matching_rule": None,
                    "result": FINISHED_TEXT,
                },
            )
        )
        return FINISHED_TEXT

    return finish
