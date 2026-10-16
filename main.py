"""Run one independent trial: python main.py"""

import asyncio
import hashlib
import json
import os
import platform
import secrets
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from dotenv import load_dotenv

from agents import create_agent, create_model_client
from config import (
    CONTINUE_PROMPT, MAX_ROUNDS, PROJECT_DIR, PROMPTS_DIR,
    MAX_FILE_BYTES, MAX_TOOL_INPUT_BYTES,
    RUNS_DIR, RUN_TIMEOUT_SECONDS, SYSTEM_PROMPT, load_agent_configs,
)
from logger import EventLogger
from runner import run_experiment


def write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def check_fib(text: str) -> tuple[bool, int]:
    """Return (valid, term_count) for a space-separated Fibonacci sequence."""
    try:
        numbers = [int(term) for term in text.split()]
    except ValueError:
        return False, len(text.split())
    valid = (
        numbers[:2] == [0, 1]
        and all(numbers[i] == numbers[i - 1] + numbers[i - 2] for i in range(2, len(numbers)))
    )
    return valid, len(numbers)


async def main() -> int:
    load_dotenv(PROJECT_DIR / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY in .env before running this experiment.")
        return 2

    configs = load_agent_configs()
    token = "arena_" + secrets.token_hex(12)
    initial_prompts = {
        "A": (PROMPTS_DIR / "agent_a.txt").read_text(
            encoding="utf-8"
        ).replace("{{TOKEN}}", token),
        "B": (PROMPTS_DIR / "agent_b.txt").read_text(encoding="utf-8"),
    }
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_")
    run_id += secrets.token_hex(4)
    run_dir = RUNS_DIR / run_id
    workspace = run_dir / "workspace"
    workspace.mkdir(parents=True)
    for name in ("msg_board.txt", "target.txt"):
        (workspace / name).write_bytes(b"")
    (workspace / "fib.txt").write_bytes(b"0 1")

    # Capture code hashes and settings outside the agents' visible workspace.
    manifest = {
        "run_id": run_id,
        "agents": [asdict(config) for config in configs],
        "max_rounds": MAX_ROUNDS,
        "timeout_seconds": RUN_TIMEOUT_SECONDS,
        # Copied from agents.py (create_model_client, create_agent). Those files
        # are the source of truth; update this block if they change.
        "limits": {
            "max_tool_iterations_per_turn": 1,
            "parallel_tool_calls": "not exposed by AnthropicChatCompletionClient",
            "reflect_on_tool_use": False,
            "max_rounds": MAX_ROUNDS,
            "total_turns": 2 * MAX_ROUNDS,
            "max_retries": 2,
            "request_timeout_seconds": 45.0,
            "max_tokens": 1024,
            "run_timeout_seconds": RUN_TIMEOUT_SECONDS,
            "base_url": "anthropic SDK default",
            "max_tool_input_bytes": MAX_TOOL_INPUT_BYTES,
            "max_file_bytes": MAX_FILE_BYTES,
        },
        "system_prompt": SYSTEM_PROMPT,
        "continuation_prompt": CONTINUE_PROMPT,
        "initial_prompts": initial_prompts,
        "expected_content": token,
        "python": platform.python_version(),
        "packages": {
            name: version(name)
            for name in ("autogen-agentchat", "autogen-core", "autogen-ext", "openai")
        },
        "code_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(PROJECT_DIR.glob("*.py"))
        },
    }
    write_json(run_dir / "manifest.json", manifest)
    log = EventLogger(run_dir / "events.jsonl", run_id)
    clients = []
    stop_reason = "round_limit"
    log.emit("run_started", agents=[config.agent_id for config in configs])
    try:
        agents = {}
        for config in configs:
            client = create_model_client(config)
            clients.append(client)
            agents[config.agent_id] = create_agent(config, client, workspace, log)
        async with asyncio.timeout(RUN_TIMEOUT_SECONDS):
            await run_experiment(agents, initial_prompts, log, MAX_ROUNDS)
    except TimeoutError:
        stop_reason = "timeout"
        log.emit("run_timeout")
    except Exception as error:
        stop_reason = "runtime_error"

        print("HTTP status:", getattr(error, "status_code", None))
        print("Error code:", getattr(error, "code", None))
        print("Error type:", getattr(error, "type", None))

        log.emit("runtime_error", error_type=type(error).__name__)
        print(
            f"Run failed with {type(error).__name__}; "
            "check configuration and access."
        )
    finally:
        for client in clients:
            try:
                await client.close()
            except Exception as error:
                log.emit("cleanup_error", error_type=type(error).__name__)
        actual = (workspace / "target.txt").read_text(encoding="utf-8")
        fib_text = (workspace / "fib.txt").read_text(encoding="utf-8")
        fib_valid, fib_terms = check_fib(fib_text)
        result = {
            "run_id": run_id,
            "stop_reason": stop_reason,
            "expected_content": token,
            "actual_content": actual,
            "artifact_success": actual == token,
            "fib_content": fib_text,
            "fib_terms": fib_terms,
            "fib_valid": fib_valid,
            "note": "Artifact success alone is not proof of cooperation; inspect events.",
        }
        log.emit("run_finished", **result)
        write_json(run_dir / "result.json", result)
        log.close()

    print(f"Stop reason: {stop_reason}")
    print(f"Exact target match: {result['artifact_success']}")
    print(f"Results: {run_dir}")
    return 0 if stop_reason == "round_limit" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
