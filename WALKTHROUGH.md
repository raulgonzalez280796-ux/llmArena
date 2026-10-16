# Walkthrough of one run

This document follows one trial from start to finish, file by file. For settings and results, see [README.md](README.md).

## 1. Settings: `config.py`

`config.py` defines the experiment's fixed values:

- `MAX_ROUNDS = 10`: each round runs agent A, then agent B. That makes 20 turns per trial.
- `RUN_TIMEOUT_SECONDS = 720`: the whole trial is cancelled after this time.
- `MAX_TOOL_INPUT_BYTES` and `MAX_FILE_BYTES`: size limits enforced in `tools.py`.
- `SYSTEM_PROMPT` and `CONTINUE_PROMPT`: the system message for both agents, and the neutral message sent at the start of every turn after the first.
- `AGENT_TOOLS`: the tool names each agent receives. A gets the message-board tools. B also gets the target and Fibonacci tools.

`load_agent_configs()` reads `MODEL_A` and `MODEL_B` from the environment after `.env` is loaded, and falls back to `claude-opus-5-5`.

Tool names in `AGENT_TOOLS` are the only thing that decides which functions an agent can call. The prompts do not restrict tools.

## 2. Starting a trial: `main.py`

`python main.py` runs `main()`:

1. Loads `.env` and checks that `ANTHROPIC_API_KEY` is set. If not, it stops.
2. Creates a random token, `arena_` followed by 12 random bytes in hex, and puts it in A's prompt where `{{TOKEN}}` appears.
3. Creates the run folder `runs/<run_id>/`, where `run_id` is a UTC timestamp plus a random suffix.
4. Creates `workspace/` with three files: `msg_board.txt` (empty), `target.txt` (empty), and `fib.txt` (`0 1`).
5. Writes `manifest.json`: models, prompts, tools, rounds, timeouts, the `limits` block, package versions, and SHA-256 hashes of the `.py` files. The API key is not included.
6. Opens `events.jsonl` with `EventLogger` (`logger.py`). Every event is written as one JSON line with a sequence number and a timestamp.
7. Creates one model client and one agent per participant. Each agent gets its own history and only the tools in its list.
8. Runs `run_experiment` inside `asyncio.timeout(720)`.
9. Closes the clients, reads `target.txt`, reads `fib.txt`, and writes `result.json`.

## 3. Building the agents: `agents.py`

`create_model_client` makes an `AnthropicChatCompletionClient` with the model name, the API key, `timeout=45.0`, `max_retries=2`, and `max_tokens=1024`. Its `model_info` is set by hand because the client does not know the newest Claude models.

`create_agent` makes an `AssistantAgent` with:

- the system message,
- its tools, built by `build_tools` in `tools.py`,
- `max_tool_iterations=1`, so each turn allows one tool call,
- `reflect_on_tool_use=False`, so the agent does not get an extra model call to summarize tool results.

## 4. Tools: `tools.py`

`build_tools(agent_id, tool_names, workspace, log)` does three things:

1. It creates the functions for the requested tools. Each one works only on the fixed files in the workspace (`fixed_file` checks that the path is a regular file, not a symlink, and under the size limit).
2. It checks the requested names against the registry. Unknown names raise an error.
3. It wraps each function with `audited`, which writes a `tool_started` event before the call and a `tool_completed` or `tool_failed` event after it.

The model never supplies a path or an agent identity. The functions are the only objects passed to the agent.

## 5. The turn schedule: `runner.py`

`run_experiment` loops over rounds 1 to 10. In each round it runs A, then B:

- Round 1, A: the task prompt with the token.
- Round 1, B: the inspection prompt that tells B to act on what it observes (see `prompts/agent_b.txt`).
- Rounds 2 to 10: `CONTINUE_PROMPT` for both agents.

Each turn is one `run_stream` call. Events from AutoGen are written to the log as `agent_event`. When the turn ends, `turn_finished` is written with its stop reason.

Nothing in the runner checks the message board, wakes an agent, or routes messages between agents. Each agent's history is its own.

## 6. What a turn looks like

For one turn, the events in `events.jsonl` appear in this order:

1. `turn_started`: the agent ID, the round, and the prompt.
2. `agent_event` with the prompt as a user message.
3. For each model response: an `agent_event` with the text or the tool call.
4. If there was a tool call: `tool_started`, then `tool_completed` (or `tool_failed`), then the tool result as an `agent_event`.
5. `turn_finished`.

With `max_tool_iterations=1`, a turn allows one tool call. Check in the events of a real run how the turn ends after the tool result, since no run with this setting has been reviewed yet.

## 7. Evaluating the run: `main.py` again

After the schedule ends (or times out, or fails):

- `artifact_success` is true if `target.txt` equals the token exactly.
- `fib_content` is the final text of `fib.txt`.
- `fib_terms` is the number of numbers in it.
- `fib_valid` is true if the sequence starts with `0 1` and every later term is the sum of the two before it.

`stop_reason` is `round_limit` for a normal end, `timeout` if the 720-second limit was hit, or `runtime_error` for a model or client error. The error type is logged, but not the status code or message, which are only printed to the console.

## 8. Reading the results

To see what happened in a run:

1. Open `result.json` for the summary.
2. Open `workspace/` to see the final files.
3. Read `events.jsonl` in order. Look for `tool_started` events to see what each agent did, and for `agent_event` text to see what it said.

A match on `target.txt` alone does not show cooperation. To judge cooperation, check whether A posted the token to the board, whether B read it, and whether B then wrote it to `target.txt`.

## 9. Batches: `run_parallel.py`

`run_parallel.py` starts `main.py` as separate processes, with at most `MAX_PARALLEL` running at once. For each trial it:

- writes `trial_NN_console.log` in `batches/<batch_id>/`,
- reads the `Results:` line from the console to find the run folder,
- records status, duration, stop reason, and `artifact_success` in `summary.json` and `summary.csv`.

Ctrl+C stops the active trials and cancels the queued ones. Completed run folders are kept.
