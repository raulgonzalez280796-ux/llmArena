"""Tool Gateway: the only route from a tool call to the workspace (SRS PRM-1..7, LOG-2; ADR-0020).

The gateway is built for one agent. Its identity and grants are fixed at construction and
cannot be changed by anything the model sends. Every call is logged, including refusals.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from arena.board.service import (
    Board,
    BoardLimitReached,
    EmptyPost,
    PostTooLong,
)
from arena.config.schema import Grants
from arena.events.model import Event, EventSink
from arena.workspace.files import Workspace, WorkspaceError
from arena.workspace.paths import InvalidPath, PathDenied, ResolvedPath, matching_rule

MAX_READ_BYTES: Final = 64_000
MAX_WRITE_BYTES: Final = 64_000
REFUSAL: Final = "Permission denied: {path}"


class Decision(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"  # refused by a missing grant or an unknown tool; nothing ran
    REJECTED = "rejected"  # malformed call; nothing ran
    ERROR = "error"  # allowed, but the operation failed


@dataclass(frozen=True)
class ToolResult:
    text: str
    decision: Decision


@dataclass(frozen=True)
class _Outcome:
    result: ToolResult
    resolved: str | None = None
    rule: str | None = None
    reason: str | None = None


class _Refused(Exception):
    def __init__(self, resolved: str | None, reason: str) -> None:
        super().__init__(reason)
        self.resolved = resolved
        self.reason = reason


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ListArgs(_Args):
    path: str = "."


class ReadArgs(_Args):
    path: str


class WriteArgs(_Args):
    path: str
    content: str


class BoardReadArgs(_Args):
    pass


class PostArgs(_Args):
    text: str


ARGS: Final[dict[str, type[_Args]]] = {
    "list_files": ListArgs,
    "read_file": ReadArgs,
    "write_file": WriteArgs,
    "read_board": BoardReadArgs,
    "post_to_board": PostArgs,
}


def offered_tools(grants: Grants) -> tuple[str, ...]:
    """The tools an agent with these grants is offered. The UI preview uses this same function."""
    tools: list[str] = []
    if grants.read:
        tools += ["list_files", "read_file"]
    if grants.write:
        tools.append("write_file")
    if grants.board_read:
        tools.append("read_board")
    if grants.board_post:
        tools.append("post_to_board")
    return tuple(tools)


class ToolGateway:
    def __init__(
        self,
        *,
        agent_id: str,
        grants: Grants,
        workspace: Workspace,
        sink: EventSink,
        board: Board | None = None,
    ) -> None:
        if (grants.board_read or grants.board_post) and board is None:
            raise ValueError("a board grant needs a board to be passed to the gateway")
        self._agent_id = agent_id
        self._grants = grants
        self._workspace = workspace
        self._sink = sink
        self._board = board

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def granted_tools(self) -> tuple[str, ...]:
        """The tools this agent may be offered. A tool without a grant is not offered."""
        return offered_tools(self._grants)

    def invoke(self, tool: str, arguments: Mapping[str, object]) -> ToolResult:
        raw = dict(arguments)

        if tool not in ARGS:
            return self._emit(tool, raw, _Outcome(_denied(tool), reason="unknown_tool"))
        if tool not in self.granted_tools:
            return self._emit(tool, raw, _Outcome(_denied(tool), reason="tool_not_granted"))

        try:
            args = ARGS[tool].model_validate(raw)
        except ValidationError as exc:
            names = sorted({".".join(str(p) for p in err["loc"]) for err in exc.errors()})
            text = f"Invalid arguments: {', '.join(names)}"
            return self._emit(
                tool,
                raw,
                _Outcome(ToolResult(text, Decision.REJECTED), reason="invalid_arguments"),
            )

        try:
            outcome = self._run(tool, args)
        except _Refused as refusal:
            outcome = _Outcome(
                _denied_path(_path_of(args)),
                resolved=refusal.resolved,
                reason=refusal.reason,
            )
        except InvalidPath:
            outcome = _Outcome(
                ToolResult("Invalid path", Decision.REJECTED),
                reason="invalid_path",
            )
        return self._emit(tool, raw, outcome)

    def _run(self, tool: str, args: _Args) -> _Outcome:
        if isinstance(args, ListArgs):
            return self._list(args.path)
        if isinstance(args, ReadArgs):
            return self._read(args.path)
        if isinstance(args, WriteArgs):
            return self._write(args)
        if isinstance(args, PostArgs):
            return self._post(args.text)
        return self._read_board()

    # --- authorization -------------------------------------------------------

    def _authorize(self, requested: str, patterns: tuple[str, ...]) -> tuple[ResolvedPath, str]:
        try:
            resolved = self._workspace.resolve(requested)
        except PathDenied as exc:
            raise _Refused(None, "outside_workspace") from exc
        rule = matching_rule(patterns, resolved)
        if rule is None:
            raise _Refused(resolved.relative, "no_matching_grant")
        return resolved, rule

    # --- operations ----------------------------------------------------------

    def _list(self, path: str) -> _Outcome:
        resolved, rule = self._authorize(path, self._grants.read)
        try:
            entries = self._workspace.list_dir(resolved)
        except WorkspaceError as exc:
            return _Outcome(ToolResult(f"Error: {exc}", Decision.ERROR), resolved.relative, rule)

        visible: list[str] = []
        for name, is_dir in entries:
            child = f"{resolved.relative}/{name}" if resolved.relative else name
            try:
                child_resolved = self._workspace.resolve(child)
            except (PathDenied, InvalidPath):
                continue
            if matching_rule(self._grants.read, child_resolved) is None:
                continue
            visible.append(f"{name}/" if is_dir else name)
        return _Outcome(ToolResult("\n".join(visible), Decision.ALLOWED), resolved.relative, rule)

    def _read(self, path: str) -> _Outcome:
        resolved, rule = self._authorize(path, self._grants.read)
        try:
            text = self._workspace.read_text(resolved, max_bytes=MAX_READ_BYTES)
        except WorkspaceError as exc:
            return _Outcome(ToolResult(f"Error: {exc}", Decision.ERROR), resolved.relative, rule)
        return _Outcome(ToolResult(text, Decision.ALLOWED), resolved.relative, rule)

    def _write(self, args: WriteArgs) -> _Outcome:
        resolved, rule = self._authorize(args.path, self._grants.write)
        if len(args.content.encode("utf-8")) > MAX_WRITE_BYTES:
            return _Outcome(
                ToolResult("Error: content is too large", Decision.REJECTED),
                resolved.relative,
                rule,
                reason="content_too_large",
            )
        try:
            self._workspace.write_text(resolved, args.content)
        except (WorkspaceError, OSError) as exc:
            message = (
                str(exc) if isinstance(exc, WorkspaceError) else (exc.strerror or "write failed")
            )
            return _Outcome(
                ToolResult(f"Error: {message}", Decision.ERROR), resolved.relative, rule
            )
        return _Outcome(
            ToolResult(f"File written: {resolved.relative}", Decision.ALLOWED),
            resolved.relative,
            rule,
        )

    # --- board ---------------------------------------------------------------

    def _read_board(self) -> _Outcome:
        assert self._board is not None
        posts = self._board.posts()
        if not posts:
            return _Outcome(ToolResult("The board is empty.", Decision.ALLOWED))
        lines = [f"#{p.number} [{p.sender}] {p.text}" for p in posts]
        return _Outcome(ToolResult("\n".join(lines), Decision.ALLOWED))

    def _post(self, text: str) -> _Outcome:
        assert self._board is not None
        try:
            record = self._board.post(self._agent_id, text)
        except BoardLimitReached:
            message = f"Error: post limit reached ({self._board.max_posts_per_agent} per agent)"
            return _Outcome(ToolResult(message, Decision.REJECTED), reason="post_limit")
        except PostTooLong:
            message = f"Error: post is longer than {self._board.max_post_chars} characters"
            return _Outcome(ToolResult(message, Decision.REJECTED), reason="post_too_long")
        except EmptyPost:
            return _Outcome(
                ToolResult("Error: post is empty", Decision.REJECTED), reason="post_empty"
            )
        return _Outcome(ToolResult(f"Posted #{record.number}", Decision.ALLOWED))

    # --- audit ---------------------------------------------------------------

    def _emit(self, tool: str, arguments: dict[str, object], outcome: _Outcome) -> ToolResult:
        self._sink.emit(
            Event(
                type="tool_call",
                agent_id=self._agent_id,
                data={
                    "tool": tool,
                    "arguments": arguments,
                    "decision": outcome.result.decision.value,
                    "reason": outcome.reason,
                    "resolved_path": outcome.resolved,
                    "matching_rule": outcome.rule,
                    "result": outcome.result.text,
                },
            )
        )
        return outcome.result


def _denied(tool: str) -> ToolResult:
    return ToolResult(f"Permission denied: {tool}", Decision.DENIED)


def _denied_path(path: str) -> ToolResult:
    return ToolResult(REFUSAL.format(path=path), Decision.DENIED)


def _path_of(args: _Args) -> str:
    path = getattr(args, "path", "")
    return path if isinstance(path, str) else ""
