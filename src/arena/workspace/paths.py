"""Path canonicalization and grant matching (SRS PRM-3, PRM-4; ADR-0019).

A request becomes a workspace-relative path only after symlinks and ``..`` are resolved.
Grants are matched against that resolved path, never against the text the agent typed,
so a link cannot reach a location its target is not granted.
"""

from __future__ import annotations

import os
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

_FORBIDDEN_CHARS = ("\x00", "\\")


class PathDenied(Exception):
    """The path is absolute or resolves outside the workspace."""


class InvalidPath(ValueError):
    """The path is malformed (empty, or contains NUL or a backslash)."""


@dataclass(frozen=True)
class ResolvedPath:
    requested: str
    relative: str  # NFC; "" for the workspace root
    absolute: Path  # symlinks resolved
    match_key: str  # NFC + casefold of relative; grants are matched against this

    @property
    def is_root(self) -> bool:
        return self.relative == ""


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def normalize_pattern(pattern: str) -> str:
    """Normalize a grant pattern or path the same way for comparison."""
    return _nfc(pattern).casefold()


def validate_glob(pattern: str) -> None:
    """Raise ValueError if a grant pattern is malformed."""
    if pattern == "" or pattern != pattern.strip():
        raise ValueError(f"grant pattern must be non-empty with no surrounding spaces: {pattern!r}")
    if any(ch in pattern for ch in _FORBIDDEN_CHARS):
        raise ValueError(f"grant pattern contains a forbidden character: {pattern!r}")
    if pattern.startswith("/"):
        raise ValueError(f"grant pattern must be relative to the workspace: {pattern!r}")
    for segment in pattern.split("/"):
        if segment == "":
            raise ValueError(f"grant pattern has an empty segment: {pattern!r}")
        if segment == "..":
            raise ValueError(f"grant pattern must not contain '..': {pattern!r}")
        if "**" in segment and segment != "**":
            raise ValueError(f"'**' must be a whole path segment: {pattern!r}")


def canonicalize(root: Path, requested: str) -> ResolvedPath:
    """Resolve a requested path inside ``root``, or refuse it.

    Raises ``InvalidPath`` for malformed input and ``PathDenied`` when the resolved
    location is outside the workspace.
    """
    if requested == "":
        raise InvalidPath("path must be a non-empty string")
    if any(ch in requested for ch in _FORBIDDEN_CHARS):
        raise InvalidPath("path contains a forbidden character")

    text = _nfc(requested)
    if text.startswith("/"):
        raise PathDenied("absolute path")

    workspace = root.resolve(strict=True)
    real = Path(os.path.realpath(workspace / text))
    try:
        rel = real.relative_to(workspace)
    except ValueError as exc:
        raise PathDenied("resolves outside the workspace") from exc

    relative = _nfc("" if rel == Path(".") else rel.as_posix())
    return ResolvedPath(
        requested=requested,
        relative=relative,
        absolute=real,
        match_key=normalize_pattern(relative),
    )


def matching_rule(patterns: Iterable[str], resolved: ResolvedPath) -> str | None:
    """Return the first grant pattern that matches the resolved path, as written, or None.

    ``**`` matches zero or more whole segments, so ``config/**`` matches ``config`` itself
    and everything below it. ``*`` and ``?`` match within one segment.
    """
    segments = resolved.match_key.split("/") if resolved.match_key else []
    for pattern in patterns:
        if _match(normalize_pattern(pattern).split("/"), segments):
            return pattern
    return None


def _match(pattern: list[str], segments: list[str]) -> bool:
    if not pattern:
        return not segments
    head, rest = pattern[0], pattern[1:]
    if head == "**":
        return any(_match(rest, segments[i:]) for i in range(len(segments) + 1))
    if not segments:
        return False
    return fnmatchcase(segments[0], head) and _match(rest, segments[1:])
