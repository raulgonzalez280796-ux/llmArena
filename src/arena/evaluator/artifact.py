"""External check of the artifact, read from the file after mutations stop (SRS EVL-1; ADR-0025)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from arena.config.schema import ArtifactCheck
from arena.workspace.files import Workspace
from arena.workspace.paths import InvalidPath, PathDenied


def check_artifact(workspace_dir: Path, check: ArtifactCheck) -> bool:
    """True only if the file exists, parses as YAML, and holds exactly the expected value."""
    try:
        resolved = Workspace(workspace_dir).resolve(check.file)
    except (PathDenied, InvalidPath):
        return False
    if not resolved.absolute.is_file():
        return False
    try:
        data: Any = yaml.safe_load(resolved.absolute.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return False
    node: object = data
    for part in check.key.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = cast(dict[str, object], node)[part]
    return type(node) is type(check.expect) and node == check.expect
