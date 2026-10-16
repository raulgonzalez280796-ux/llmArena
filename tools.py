"""Fixed-file tools: agents supply content, never paths or identities."""

import inspect
from functools import wraps
from pathlib import Path
from typing import Callable

from config import MAX_FILE_BYTES, MAX_TOOL_INPUT_BYTES
from logger import EventLogger


def build_tools(
    agent_id: str,
    tool_names: tuple[str, ...],
    workspace: Path,
    log: EventLogger,
) -> list[Callable]:
    # The application creates this directory and these two regular files.
    # Models cannot create files, links, subprocesses, or execute Python.
    workspace = workspace.resolve()

    def fixed_file(name: str) -> Path:
        path = workspace / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Expected a regular file")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("File size limit exceeded")
        return path

    def validate_content(text: str) -> None:
        if len(text.encode("utf-8")) > MAX_TOOL_INPUT_BYTES:
            raise ValueError("Input size limit exceeded")

    async def list_files() -> list[str]:
        """List the names of files in the workspace."""
        return sorted(
            path.name for path in workspace.iterdir()
            if path.is_file() and not path.is_symlink()
        )

    async def read_msg_board() -> str:
        """Read the UTF-8 contents of msg_board.txt."""
        return fixed_file("msg_board.txt").read_text(encoding="utf-8")

    async def append_msg_board(text: str) -> str:
        """Append text followed by a newline to msg_board.txt."""
        validate_content(text)
        path = fixed_file("msg_board.txt")
        data = (text + "\n").encode("utf-8")
        if path.stat().st_size + len(data) > MAX_FILE_BYTES:
            raise ValueError("File size limit exceeded")
        with path.open("ab") as stream:
            stream.write(data)
        return "Text appended."

    async def read_target() -> str:
        """Read the UTF-8 contents of target.txt."""
        return fixed_file("target.txt").read_text(encoding="utf-8")

    async def write_target(content: str) -> str:
        """Replace the contents of target.txt with the supplied UTF-8 text."""
        validate_content(content)
        fixed_file("target.txt").write_bytes(content.encode("utf-8"))
        return "File written."

    async def read_fib() -> str:
        """Read the UTF-8 contents of fib.txt."""
        return fixed_file("fib.txt").read_text(encoding="utf-8")

    async def write_fib(content: str) -> str:
        """Replace the contents of fib.txt with the supplied UTF-8 text."""
        validate_content(content)
        fixed_file("fib.txt").write_bytes(content.encode("utf-8"))
        return "File written."

    registry = {
        tool.__name__: tool
        for tool in (
            list_files, read_msg_board, append_msg_board,
            read_target, write_target, read_fib, write_fib,
        )
    }
    if len(set(tool_names)) != len(tool_names):
        raise ValueError("Duplicate tool name")
    unknown = set(tool_names) - registry.keys()
    if unknown:
        raise ValueError(f"Unknown configured tools: {sorted(unknown)}")

    def audited(function: Callable) -> Callable:
        signature = inspect.signature(function)

        @wraps(function)
        async def wrapped(*args, **kwargs):
            arguments = dict(signature.bind(*args, **kwargs).arguments)
            log.emit(
                "tool_started", agent_id=agent_id,
                tool=function.__name__, arguments=arguments,
            )
            try:
                result = await function(*args, **kwargs)
            except Exception as error:
                log.emit(
                    "tool_failed", agent_id=agent_id,
                    tool=function.__name__, error_type=type(error).__name__,
                )
                raise
            log.emit(
                "tool_completed", agent_id=agent_id,
                tool=function.__name__, result=result,
            )
            return result

        return wrapped

    # Only these functions are passed to AssistantAgent. The model cannot
    # access this registry or select functions assigned to another agent.
    return [audited(registry[name]) for name in tool_names]
