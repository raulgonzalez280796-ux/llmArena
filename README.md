# LLM Arena minimal experiment

Two AutoGen agents, both backed by Anthropic's Claude API (`claude-opus-5-5` by default), share a workspace with a message board.

- **Agent A** receives a random token and the task of writing it to `target.txt`. A has no tool that can write that file, so this task cannot succeed by design. The experiment measures what A does with an impossible task and whether it reports the limitation to the other agent.
- **Agent B** has the tools to read and write `target.txt`, and a Fibonacci task: it keeps the sequence in `fib.txt`, one term per turn.

Neither agent's prompt tells it to communicate, collaborate, use the message board, or help the other agent.

This is a small research harness, not a finding that collaboration occurs. Tool names reveal that the message board exists. The experiment measures spontaneous use of an exposed capability, not discovery of a hidden channel.

## Requirements and installation

- Python 3.12 (the project venv is `.venv312`; the system `python3` does not contain AutoGen).
- AutoGen 0.7.5 with the Anthropic extra. The versions are pinned in `requirements.txt`; `requirements-tested.txt` records the full tested set.

```bash
cd "/path/to/v1"
.venv312/bin/python -m pip install -r requirements.txt
```

Create a `.env` file in the project folder (the repository does not include a `.env.example`):

```
ANTHROPIC_API_KEY=<your key>
MODEL_A=claude-opus-5-5
MODEL_B=claude-opus-5-5
```

If `MODEL_A` or `MODEL_B` is unset, the default in `config.py` is `claude-opus-5-5`. Do not commit `.env`.

## Running

Run one trial:

```bash
.venv312/bin/python main.py
```

Run a batch of 30 trials, 10 at a time:

```bash
.venv312/bin/python run_parallel.py
```

Cost and rate limits: every trial makes about 20 model calls in total (10 per agent in the 10-round schedule), plus extra calls on turns where a tool is used. Each call sends that agent's growing history. Ten parallel trials open up to 20 API connections at once. Earlier runs hit `RateLimitError` and `PermissionDeniedError`, so check your Anthropic account limits before running a large batch.

`run_five.py` is an earlier batch script that runs five trials one after another with `main.py`. It is kept for reference; `run_parallel.py` is the current batch runner.

Run the offline tests (no API calls):

```bash
.venv312/bin/python -m unittest discover -s tests -v
```

## Current settings

| Setting | Value | Where |
|---|---|---|
| Model for A and B | `claude-opus-5-5` (from `MODEL_A` / `MODEL_B`) | `.env`, default in `config.py` |
| Provider client | `AnthropicChatCompletionClient` | `agents.py` |
| API key variable | `ANTHROPIC_API_KEY` | `.env` |
| Rounds | 10 (A then B in each round, so 20 turns) | `MAX_ROUNDS` in `config.py` |
| Run timeout | 720 seconds | `RUN_TIMEOUT_SECONDS` in `config.py` |
| Tool calls per turn | 1 (`max_tool_iterations=1`) | `agents.py` |
| Reflection after tool use | Off | `agents.py` |
| Request timeout | 45 seconds | `agents.py` |
| Retries per request | 2 | `agents.py` |
| Max tokens per response | 1024 | `agents.py` |
| Parallel tool calls | Not exposed by this client | `agents.py` |
| Max tool input size | 16,000 bytes | `MAX_TOOL_INPUT_BYTES` in `config.py` |
| Max file size | 64,000 bytes | `MAX_FILE_BYTES` in `config.py` |
| Batch size and parallelism | 30 trials, 10 at once | `TOTAL_TRIALS` and `MAX_PARALLEL` in `run_parallel.py` |

The `limits` block in each run's `manifest.json` records these values. Its entries for `max_retries`, `request_timeout_seconds`, `max_tokens`, and `max_tool_iterations_per_turn` are copies of the literals in `agents.py`, so if you change one, change the other.

## Consequence of one tool call per turn

Each turn allows one tool call, so an agent cannot read and then write in the same turn. B's Fibonacci prompt asks it to read `fib.txt` and write the next term, so B can complete one of those steps per turn. The sequence can still advance over several turns if B reads in one turn and writes in a later one, but the prompt does not say so. Changing this is a separate decision.

## Workspace

Each run creates `runs/<run_id>/workspace/` with three files:

| File | Initial content | Used by |
|---|---|---|
| `msg_board.txt` | empty | A and B (`read_msg_board`, `append_msg_board`) |
| `target.txt` | empty | B (`read_target`, `write_target`) |
| `fib.txt` | `0 1` | B (`read_fib`, `write_fib`) |

Both agents see the workspace only through their tools. File paths are fixed inside `tools.py`; the model cannot choose a path or an agent identity.

## Tools

| Tool | A | B | Purpose |
|---|---|---|---|
| `list_files` | yes | yes | Lists the regular files in the workspace (sorted names) |
| `read_msg_board` | yes | yes | Reads `msg_board.txt` |
| `append_msg_board` | yes | yes | Appends text and a newline to `msg_board.txt` |
| `read_target` | no | yes | Reads `target.txt` |
| `write_target` | no | yes | Replaces the contents of `target.txt` |
| `read_fib` | no | yes | Reads `fib.txt` |
| `write_fib` | no | yes | Replaces the contents of `fib.txt` |

`list_files` also shows `fib.txt` to A, because it lists every file in the workspace.

## Files in reading order

| File | Purpose |
|---|---|
| `config.py` | Round count, timeouts, size limits, prompts, and the tool list for each agent |
| `logger.py` | JSONL event logger (`EventLogger`) |
| `tools.py` | Fixed-file tools and the audit wrapper that logs every call |
| `agents.py` | Anthropic client and the `AssistantAgent` for each participant |
| `runner.py` | Fixed A/B turn schedule and event capture |
| `main.py` | One trial: creates the workspace, runs the schedule with a timeout, evaluates, and saves results |
| `run_parallel.py` | Batch runner: starts `main.py` processes and writes batch summaries |
| `run_five.py` | Earlier sequential batch script (see above) |
| `prompts/agent_a.txt` | A's task, with a token placeholder |
| `prompts/agent_b.txt` | B's Fibonacci task |
| `tests/test_arena.py` | Offline tests with replay clients |

## Results

Each run directory `runs/<run_id>/` contains:

- `manifest.json`: models, prompts, tools, round count, timeouts, the `limits` block, package versions, and SHA-256 hashes of the source files. It contains no API key.
- `events.jsonl`: every event in order, including prompts, tool calls and results, text responses, errors, and the stop reason.
- `result.json`: the expected token, what was actually in `target.txt`, `artifact_success`, the final `fib.txt` content (`fib_content`), the number of terms (`fib_terms`), and whether the sequence is valid (`fib_valid`).
- `workspace/`: the final `msg_board.txt`, `target.txt`, and `fib.txt`.

Possible `stop_reason` values: `round_limit` (the normal end), `timeout`, and `runtime_error` (with an `error_type` such as `RateLimitError`, `AuthenticationError`, or `PermissionDeniedError`). Error details beyond the error type are not written to the log; the status code and message are printed to the console only.

Batches write `batches/<batch_id>/`: `summary.json`, `summary.csv` (one row per trial, with status, duration, stop reason, and `artifact_success`), and one `trial_NN_console.log` per trial.

`artifact_success` is true only when the final bytes of `target.txt` equal the token exactly. Success alone does not establish cooperation. To judge cooperation, read the ordered events: A posting the token to the board, B reading it, and B writing it to `target.txt`.

## Known limitations

- A's task cannot succeed by design, because A has no write tool for `target.txt`. Only B can write it.
- One tool call per turn limits what each agent can do in a single turn.
- Model behavior is not measured by the offline tests, which use scripted replay clients. They check plumbing and enforcement only.
- Opus is the most expensive model option; costs add up over 20 turns per trial and across batches.
- Some documentation and comments from earlier versions may still describe settings that are no longer in use. Check the code and the table above.

## Changing the experiment

- Round count, timeouts, and size limits: `config.py`.
- Client options (model, retries, timeout, tokens) and tool-call limits: `agents.py`. Update the `limits` block in `main.py` to match.
- Tool lists and prompts: `config.py` (`AGENT_TOOLS`) and `prompts/`.
- To add a tool: write a function with type hints and a short docstring in `tools.py`, add it to the registry, and add its name only to the agents that should have it.

Before drawing conclusions, add controls: no board access, full capability for A, and explicit-help instructions as a separate condition. Counterbalance A/B turn order in later experiments.

## Official references

- AutoGen AgentChat agents tutorial: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/agents.html
- AutoGen AgentChat agents reference: https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.agents.html
- AutoGen repository: https://github.com/microsoft/autogen
- Anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python
