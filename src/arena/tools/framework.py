"""Every framework tool an agent may be offered, built from its gateway (SRS AGT-5, PRM-1)."""

from __future__ import annotations

from agent_framework import FunctionTool

from arena.tools.board_tools import build_board_tools
from arena.tools.files import build_file_tools
from arena.tools.gateway import ToolGateway


def build_tools(gateway: ToolGateway) -> list[FunctionTool]:
    return [*build_file_tools(gateway), *build_board_tools(gateway)]
