"""Start the local UI: ``uv run python -m arena.ui`` (serves http://127.0.0.1:8765)."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from arena.ui.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Arena local UI")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="project folder with experiments/ and fixtures/",
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(
        create_app(args.root.resolve()), host="127.0.0.1", port=args.port, log_level="warning"
    )


if __name__ == "__main__":
    main()
