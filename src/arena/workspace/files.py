"""Workspace filesystem access used by the Tool Gateway (SRS WSP-1..3; ADR-0019)."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from arena.workspace.paths import ResolvedPath, canonicalize


class WorkspaceError(Exception):
    """An operation failed for a reason the agent may be shown."""


class Workspace:
    """One agent-visible project directory. Every access goes through ``resolve`` first."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise NotADirectoryError(str(root))

    def resolve(self, requested: str) -> ResolvedPath:
        return canonicalize(self.root, requested)

    def read_text(self, resolved: ResolvedPath, *, max_bytes: int) -> str:
        target = resolved.absolute
        if not target.is_file():
            raise WorkspaceError("not a file")
        if target.stat().st_size > max_bytes:
            raise WorkspaceError("file is too large")
        try:
            return target.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError("file is not UTF-8 text") from exc

    def list_dir(self, resolved: ResolvedPath) -> list[tuple[str, bool]]:
        """Return ``(name, is_directory)`` for each entry, sorted by name."""
        if not resolved.absolute.is_dir():
            raise WorkspaceError("not a directory")
        return sorted((entry.name, entry.is_dir()) for entry in os.scandir(resolved.absolute))

    def write_text(self, resolved: ResolvedPath, content: str) -> None:
        """Replace a file atomically: write a temp file in the same directory, then rename it."""
        target = resolved.absolute
        if target.is_dir():
            raise WorkspaceError("is a directory")
        if not target.parent.is_dir():
            raise WorkspaceError("parent directory does not exist")

        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
        fd, temp_name = tempfile.mkstemp(dir=target.parent, prefix=".arena-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, mode)
            os.replace(temp_name, target)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise


def snapshot_tree(root: Path) -> dict[str, str]:
    """Hash every file under ``root``. Symlinks are recorded by their target text."""
    entries: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        for name in [*dirnames, *filenames]:
            path = base / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                entries[rel] = f"symlink -> {os.readlink(path)}"
            elif path.is_file():
                entries[rel] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return entries


@dataclass(frozen=True)
class SnapshotDiff:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    modified: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.modified)


def diff_snapshots(before: Mapping[str, str], after: Mapping[str, str]) -> SnapshotDiff:
    return SnapshotDiff(
        added=tuple(sorted(after.keys() - before.keys())),
        removed=tuple(sorted(before.keys() - after.keys())),
        modified=tuple(sorted(k for k in before.keys() & after.keys() if before[k] != after[k])),
    )
