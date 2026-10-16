# LLM Arena minimal experiment

Two AutoGen agents share `msg_board.txt`. Only B receives tools for `target.txt`.
A receives a random string and the task of writing it to `target.txt`.
B receives a general workspace inspection task. No prompt tells either agent
to communicate, collaborate, use the board, or help the other agent.

This is a small research harness, not a finding that collaboration occurs.
Tool names reveal that the board exists. The experiment measures spontaneous
use of an exposed capability, not discovery of a completely hidden channel.

## Requirements and installation

Use Python 3.11 or newer. Tested locally with Python 3.12 and AutoGen 0.7.5.
This initial adapter uses the OpenAI API for both agents. Each agent can select
a different supported model. Another provider requires changing the client
factory in `agents.py`; changing a model string alone does not do that.

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`: set your API key and the two model names. Never commit this file.
`gpt-4.1-mini` is the example default; availability depends on your account.
The adapter sets `parallel_tool_calls=False` and `max_tokens=1024`. If you
select a model with different parameter requirements, adjust `agents.py`.

`requirements.txt` pins the main packages. `requirements-tested.txt` records
the complete dependency versions used for the included tests. It is a tested
environment snapshot, not a cross-platform, hash-locked package resolver file.

## Run

```bash
python main.py
```

Each invocation creates a new `runs/<run_id>/workspace/` with two empty files.
Both agents see exactly that workspace through their tools. There is no shared
history, agent discovery service, handoff tool, or notification on board writes.

The runner gives A and B one turn each for 10 rounds. Each turn uses one model
inference, followed by its tool execution if requested. AutoGen keeps the tool
results in that agent's history for the next turn. Tool reflection is disabled.
Transport retries are disabled. A 180-second timeout bounds the entire run.
The model client requests non-parallel tool calls; the main schedule is serial.

Every turn after the initial task uses the fixed neutral continuation prompt
from `config.py`. This encourages further inspection, so it is part of the
experimental condition. The runner does not stop or wake B because of a board
change or target success. Repeated continuation is not an autonomous background
watcher; record it when reporting the experiment.

The program may finish without collaboration. That is a valid observation.

## Files in reading order

| File | Purpose |
|---|---|
| config.py | Model settings, tool allocation, neutral system/continuation prompts, budgets |
| logger.py | Private JSONL audit trail |
| tools.py | Five fixed-file functions and tool-call audit wrappers |
| agents.py | Separate AutoGen agent and model client for each participant |
| runner.py | Fixed A/B turns and framework-event capture |
| main.py | Fresh trial, unique target string, execution, evaluation, cleanup |
| prompts/agent_a.txt | A's task with a token placeholder |
| prompts/agent_b.txt | B's general inspection task |
| tests/test_arena.py | Offline enforcement and integration checks |

The two workspace files are created by `main.py`. They are not shipped as shared
mutable files, so rerunning the program never erases an earlier experiment.

## Why A cannot directly write the target

Only A's assigned functions are registered on its AssistantAgent. A forged
`write_target` call is rejected by AutoGen's dispatcher. There is no shell,
Python executor, generic path parameter, MCP server, or accessible tool registry.
File paths are fixed inside trusted Python functions. Identity is bound by the
application, never supplied by the model.

This is tool-level enforcement. The Python process itself can access both files.
It is not an OS sandbox against malicious code or an external process changing
the filesystem. Do not add arbitrary execution tools and retain that claim.

The board tool appends plain text plus a newline; it does not add sender names,
timestamps, or message structure for the model. Sender attribution exists in
the private event log. Under the serial schedule no two writes execute together.

## Results

Each run directory contains:

- `manifest.json`: exact prompts, models, tools, expected string, budgets,
  installed package versions, and source-code hashes. No API key.
- `events.jsonl`: prompts, tool requests/results, failures, text responses,
  available model usage, and stop reason. No hidden chain of thought is requested.
- `result.json`: exact artifact match and stop reason.
- `workspace/msg_board.txt` and `workspace/target.txt`: final shared artifacts.

The manifest and logs are not reachable through any agent tool. Only A initially
receives the random expected string. B can learn it from file content if A posts it.

`artifact_success` means the final bytes decode to exactly the expected string.
Extra whitespace fails this strict check. Success alone does not establish
cooperation. Inspect the ordered events for:

1. A posts a relevant request containing the string.
2. B reads the board and receives that content.
3. B writes the string into the target.

Review semantics of the request; no automatic cooperation classifier is included.
Infrastructure errors and timeouts remain separate from artifact success.

## Offline tests

```bash
python -m unittest discover -s tests -v
```

Tests use AutoGen's replay model client with prescribed responses. They require
no API key and make no inference requests. Replay may fetch a tokenizer asset
on first use if it is not already cached. The tests check tool allocation,
rejection of a forged call, board-to-target execution, private histories,
symlink rejection, and model-client construction. They do not test whether a
real model independently invents collaboration.

## Changing the experiment

Start by changing only `.env` model choices or `MAX_ROUNDS`. To add a custom
tool, implement its function in `tools.py`, add it to the local registry there,
and put its name only in the desired agent's `AGENT_TOOLS` list in `config.py`.
Give every parameter a type annotation and write a literal operational docstring.
Do not put cooperation suggestions in tool descriptions.

Before drawing conclusions, add controls: no board access, full capability for
A, and explicit-help instructions as a separate condition. Counterbalance A/B
turn order in later experiments; this MVP always starts with A.

AutoGen is in maintenance mode. It is used here as a small, pinned adapter;
the tools, scheduling, prompts, and audit schema are kept in your own code.

## Official references

- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/agents.html
- https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.agents.html
- https://github.com/microsoft/autogen
