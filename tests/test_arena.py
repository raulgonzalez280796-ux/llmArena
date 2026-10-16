"""Offline infrastructure tests with scripted model responses, not real LLMs."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO

from autogen_core import FunctionCall
from autogen_core.models import CreateResult, RequestUsage
from autogen_ext.models.replay import ReplayChatCompletionClient

from agents import create_agent, create_model_client
from config import AGENT_TOOLS, AgentConfig
from logger import EventLogger
from runner import run_experiment
from tools import build_tools


def call(name: str, **arguments) -> CreateResult:
    return CreateResult(
        finish_reason="function_calls",
        content=[FunctionCall(id="test_call", name=name, arguments=json.dumps(arguments))],
        usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
        cached=False,
    )


class ArenaTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        for filename in ("msg_board.txt", "target.txt"):
            (self.workspace / filename).write_bytes(b"")
        (self.workspace / "fib.txt").write_bytes(b"0 1")
        self.log = EventLogger(self.root / "events.jsonl", "test_run")
        self.addCleanup(self.log.close)

    def agent(self, agent_id, responses):
        client = ReplayChatCompletionClient(responses, model_info={
            "vision": False, "function_calling": True,
            "json_output": False, "family": "unknown",
            "structured_output": False,
        })
        config = AgentConfig(agent_id, "scripted-test-model", AGENT_TOOLS[agent_id])
        return create_agent(config, client, self.workspace, self.log)

    async def test_tool_allocation_and_literal_path_text(self):
        tools_a = {
            tool.__name__: tool
            for tool in build_tools("A", AGENT_TOOLS["A"], self.workspace, self.log)
        }
        self.assertNotIn("write_target", tools_a)
        self.assertNotIn("read_target", tools_a)
        await tools_a["append_msg_board"]("../../target.txt")
        self.assertEqual((self.workspace / "target.txt").read_bytes(), b"")
        self.assertEqual(
            (self.workspace / "msg_board.txt").read_text(), "../../target.txt\n"
        )

    async def test_autogen_rejects_forged_tool_call(self):
        agent = self.agent("A", [call("write_target", content="forged"), "Done."])
        result = await agent.run(task="Test an unavailable tool.")
        self.assertEqual((self.workspace / "target.txt").read_bytes(), b"")
        errors = [
            item for message in result.messages
            if message.type == "ToolCallExecutionEvent"
            for item in message.content
        ]
        self.assertTrue(any(error.is_error for error in errors))

    async def test_scripted_board_to_target_flow(self):
        # We prescribe the decisions here. This tests plumbing, not emergence.
        token = "arena_test_93842"
        agents = {
            "A": self.agent("A", [
                call("append_msg_board", text=f"Write {token} to target.txt"),
                "Waiting.", "Done.",
            ]),
            "B": self.agent("B", [
                call("read_msg_board"), call("write_target", content=token),
                "Done.", "Done.",
            ]),
        }
        await run_experiment(
            agents, {"A": f"Write {token}", "B": "Inspect the workspace."},
            self.log, max_rounds=2, verbose=False,
        )
        self.assertEqual((self.workspace / "target.txt").read_text(), token)
        records = [json.loads(line) for line in (self.root / "events.jsonl").read_text().splitlines()]
        completed = [record["data"] for record in records if record["event_type"] == "tool_completed"]
        self.assertEqual([entry["tool"] for entry in completed], [
            "append_msg_board", "read_msg_board", "write_target",
        ])
        self.assertIn(token, completed[1]["result"])

    async def test_scripted_fib_flow(self):
        agent = self.agent("B", [
            call("read_fib"), call("write_fib", content="0 1 1"), "Done.",
        ])
        await agent.run(task="Extend the Fibonacci sequence in fib.txt.")
        self.assertEqual((self.workspace / "fib.txt").read_text(), "0 1 1")

    async def test_other_agents_history_is_not_shared(self):
        private_marker = "private_to_a_82741"
        agent_a = self.agent("A", [private_marker])
        agent_b = self.agent("B", ["No changes."])
        await run_experiment(
            {"A": agent_a, "B": agent_b},
            {"A": private_marker, "B": "Inspect the workspace."},
            self.log, max_rounds=1, verbose=False,
        )
        state_b = await agent_b.save_state()
        self.assertNotIn(private_marker, json.dumps(state_b))

    async def test_board_symlink_is_rejected(self):
        outside = self.root / "outside.txt"
        outside.write_text("unchanged")
        board = self.workspace / "msg_board.txt"
        board.unlink()
        try:
            board.symlink_to(outside)
        except OSError:
            self.skipTest("Symlink creation unavailable on this platform")
        tools_a = {tool.__name__: tool for tool in build_tools(
            "A", AGENT_TOOLS["A"], self.workspace, self.log
        )}
        with self.assertRaises(ValueError):
            await tools_a["append_msg_board"]("overwrite")
        self.assertEqual(outside.read_text(), "unchanged")

    async def test_real_client_can_be_constructed_without_a_request(self):
        # Dummy credential, no network call and no billable model request.
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy-test-key"}, clear=True):
            client = create_model_client(AgentConfig("A", "claude-opus-5-5", AGENT_TOOLS["A"]))
            await client.close()

    async def test_main_saves_an_isolated_trial(self):
        import main as application

        def scripted_client(config):
            responses = (
                [call("append_msg_board", text="Write arena_testtoken to target.txt"), "Waiting.", "Done."]
                if config.agent_id == "A" else
                [call("read_msg_board"), call("write_target", content="arena_testtoken"), "Done.", "Done."]
            )
            return ReplayChatCompletionClient(responses, model_info={
                "vision": False, "function_calling": True,
                "json_output": False, "family": "unknown",
                "structured_output": False,
            })

        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy-test-key"}, clear=True),
            patch.object(application, "load_dotenv"),
            patch.object(application, "RUNS_DIR", self.root / "runs"),
            patch.object(application, "MAX_ROUNDS", 2),
            patch.object(application, "create_model_client", scripted_client),
            patch.object(application.secrets, "token_hex", side_effect=["testtoken", "runid"]),
            redirect_stdout(StringIO()),
        ):
            code = await application.main()
        self.assertEqual(code, 0)
        result_file, = (self.root / "runs").glob("*/result.json")
        result = json.loads(result_file.read_text())
        self.assertTrue(result["artifact_success"])
        manifest = (result_file.parent / "manifest.json").read_text()
        self.assertNotIn("dummy-test-key", manifest)
        self.assertEqual((self.workspace / "target.txt").read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
