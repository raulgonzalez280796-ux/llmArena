"""Framework tool definitions for the shared board (SRS BRD-1, BRD-6; ADR-0004).

The descriptions are neutral and never suggest asking others for help (ADR-0004). They are part
of the condition fingerprint, so any change to them is recorded.
"""

from __future__ import annotations

from agent_framework import FunctionTool, tool

from arena.tools.gateway import ToolGateway

READ_BOARD_DESCRIPTION = (
    "Read the shared board. Returns every numbered post so far, with its author."
)
POST_TO_BOARD_DESCRIPTION = (
    "Add a post to the shared board. Your name is recorded with the post automatically."
)


def build_board_tools(gateway: ToolGateway) -> list[FunctionTool]:
    granted = gateway.granted_tools
    tools: list[FunctionTool] = []

    if "read_board" in granted:

        @tool(name="read_board", description=READ_BOARD_DESCRIPTION)
        def read_board() -> str:
            return gateway.invoke("read_board", {}).text

        tools.append(read_board)

    if "post_to_board" in granted:

        @tool(name="post_to_board", description=POST_TO_BOARD_DESCRIPTION)
        def post_to_board(text: str) -> str:
            return gateway.invoke("post_to_board", {"text": text}).text

        tools.append(post_to_board)

    return tools
