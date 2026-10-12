"""Framework tool definitions for the file tools (SRS AGT-5, PRM-1; ADR-0020).

Each tool is a thin wrapper: it forwards the call to the Tool Gateway, which decides.
Only the tools the agent is granted are built, so the model is never offered the others.
"""

from __future__ import annotations

from agent_framework import FunctionTool, tool

from arena.tools.gateway import ToolGateway

LIST_DESCRIPTION = (
    "List the entries of a project directory. Paths are relative to the project root."
)
READ_DESCRIPTION = (
    "Read a UTF-8 text file from the project. Paths are relative to the project root."
)
WRITE_DESCRIPTION = (
    "Create or replace a UTF-8 text file in the project. Paths are relative to the project root."
)


def build_file_tools(gateway: ToolGateway) -> list[FunctionTool]:
    granted = gateway.granted_tools
    tools: list[FunctionTool] = []

    if "list_files" in granted:

        @tool(name="list_files", description=LIST_DESCRIPTION)
        def list_files(path: str = ".") -> str:
            return gateway.invoke("list_files", {"path": path}).text

        tools.append(list_files)

    if "read_file" in granted:

        @tool(name="read_file", description=READ_DESCRIPTION)
        def read_file(path: str) -> str:
            return gateway.invoke("read_file", {"path": path}).text

        tools.append(read_file)

    if "write_file" in granted:

        @tool(name="write_file", description=WRITE_DESCRIPTION)
        def write_file(path: str, content: str) -> str:
            return gateway.invoke("write_file", {"path": path, "content": content}).text

        tools.append(write_file)

    return tools
