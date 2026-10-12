# LLM Arena: Software Requirements Specification

Version 0.1, 2026-10-12. Spec source: `Shared_Coding_Agents_Research_Blueprint_HE.md` (the blueprint). Where the user's decisions differ from it, the ADR named next to the requirement records the difference.

## 1 Purpose

LLM Arena runs experiments in which several LLM agents share one project workspace. Each agent has its own model, its own task and its own scoped tools. One agent's task needs an action that only another agent's tools allow. The arena records whether the first agent uses a shared board to get the other agent to act, whether the other agent reads the board and acts, and whether the resulting artifact is correct.

## 2 Scope

In v1:
- A local web UI to define and launch experiments.
- Model-backed agents with an agent loop we own.
- Scoped file tools and one shared board.
- Fixed-round scheduling.
- Conditions × repetitions.
- JSONL evidence.
- An external evaluator.

Out of v1:
- Real coding-agent CLIs.
- Shell or code execution.
- Direct messages and agent discovery.
- Live run view.
- Mid-run agent joins.
- OS-level sandboxing.
- Multi-user access.

## 3 Definitions

| Term | Meaning |
|---|---|
| Experiment | A YAML file that defines agents, fixture, limits, evaluator, conditions and repetitions. |
| Condition | A named override of the base experiment, e.g. `full_capability`. |
| Trial (run) | One execution of one condition and one repetition, from a fresh workspace and fresh agent state. |
| Grant | A tool an agent may use, optionally limited to path globs. |
| Board | A shared, append-only list of posts. The runtime stamps the sender of every post. |
| Round | One pass in which every agent takes one step, in a per-trial seeded order. |
| Step | One model turn of one agent, including the tool calls it makes in that turn, up to a per-step cap. |

## 4 Functional requirements

Each requirement has acceptance criteria (AC). Test IDs are listed in `docs/TRACEABILITY.md`.

### 4.1 Experiment definition (EXP)

- **EXP-1** An experiment is a YAML file validated against a schema. *AC:* an invalid file (unknown field, missing agent task, unknown grant) is rejected with a message that names the field.
- **EXP-2** Load then save of a valid experiment file returns identical bytes. *AC:* round-trip test on every file in `experiments/`.
- **EXP-3** An experiment defines one or more agents, a fixture, limits (`max_rounds`, `max_total_tokens`), an evaluator, named conditions and a repetition count. *AC:* schema test.
- **EXP-4** A condition overrides fields of the base experiment by path. The resolved configuration of each condition can be printed. *AC:* resolving `full_capability` changes only the overridden field.
- **EXP-5** API keys are referenced only by environment-variable name. *AC:* the schema has no field that holds a key value; a literal key-like string in the YAML is rejected.

### 4.2 Agents (AGT), ADR-0003, ADR-0007

- **AGT-1** Each agent has an id, a model (provider, model id, API key variable), a task and grants. *AC:* schema test.
- **AGT-2** Every agent receives its own task at the start of a trial. *AC:* the event log has one `task_delivered` per agent before round 1.
- **AGT-3** Each agent keeps a private conversation history. No agent sees another agent's prompts, tool calls or results. *AC:* in a fake-model trial, B's model input contains none of A's content except what A posted to the board and B read.
- **AGT-4** The system prompt is neutral (blueprint §16). It never mentions the board, other agents, or words such as arena, experiment or test. *AC:* a lint test over all prompt files and generated system prompts.
- **AGT-5** Agents run through an `AgentAdapter` interface (`create`, `step`, `close`), so the framework can be swapped and a fake model can be used. *AC:* the same trial runs with the fake adapter and with the framework adapter.

### 4.3 Permissions and Tool Gateway (PRM), ADR-0010, ADR-0011

- **PRM-1** An agent can call only the tools in its grants. *AC:* a call to a tool that is not granted, including a direct call to the Gateway, is rejected and logged (blueprint §24 test 1).
- **PRM-2** The agent's identity is bound when its tools are built. Tool arguments cannot set or change it. *AC:* an extra `agent_id` or `sender` argument is rejected (§24 test 2).
- **PRM-3** File grants are deny by default. `read` and `write` are scoped separately by path globs. `write` covers create, delete and rename. `list` follows `read`. *AC:* a table-driven test over allow/deny cases.
- **PRM-4** Paths are canonicalized before the check:
  - `..` escapes are rejected;
  - symlinks are resolved, and links that land outside the scope are refused;
  - the comparison is case-insensitive and Unicode-normalized.

  *AC:* traversal, symlink, `CONFIG/Deploy.yaml` and NFD/NFC cases are all refused or allowed correctly (§24 test 3).
- **PRM-5** A refused call returns the exact text `Permission denied: <path>`. The text is part of the condition fingerprint. *AC:* string test plus a fingerprint test.
- **PRM-6** Harness files (experiment configs, logs, evaluator, keys) are outside the workspace that tools can reach. *AC:* no grant can resolve to a path outside the trial workspace.
- **PRM-7** Grants are fixed for the whole trial. *AC:* no API changes grants after the trial starts.

### 4.4 Board (BRD), ADR-0004, ADR-0005, ADR-0006

- **BRD-1** There is one board per trial. It is reached through `read_board` and `post_to_board`, whose descriptions are neutral and versioned. *AC:* the tool descriptions are part of the fingerprint.
- **BRD-2** Posts are append-only and numbered. There is no edit or delete. *AC:* the service has no mutation API besides append; numbering is gap-free.
- **BRD-3** The runtime stamps the sender of every post. *AC:* a post's `sender` always equals the calling agent's bound id.
- **BRD-4** Posts are pull-only. Agents get no notification, and posts never enter an agent's context unless it calls `read_board`. *AC:* B's model input is unchanged by A's post until B calls `read_board`.
- **BRD-5** Each agent has limits on post count and post length. Hitting a limit returns an error and is logged. *AC:* limit test.
- **BRD-6** Board reading and posting are two grants (`board_read`, `board_post`), so a condition can remove either one. *AC:* with a grant false, its tool is absent from the agent's tool list (ADR-0027).

### 4.5 Runner (RUN), ADR-0009

- **RUN-1** A trial runs in rounds. In each round every agent takes one step. The order is a seeded shuffle per trial, and both the seed and the order are logged. *AC:* the same seed gives the same order.
- **RUN-2** Each trial starts from a fresh copy of the fixture and fresh agent state. Nothing carries over from an earlier trial. *AC:* §24 test 9.
- **RUN-3** A trial stops after `max_rounds` rounds, which the researcher sets per experiment as the maximum number of iterations. `max_total_tokens` is a second cap that stops the trial earlier if reached. Each agent receives its own task (`agents.<id>.task`) at the start of the trial. The stop reason is logged. *AC:* one test per stop reason. (Amended 2026-10-12, ADR-0023: the idle and declared-done stop rules are removed.)
- **RUN-4** A batch runs every condition × repetition in interleaved order. *AC:* batch test with a fake model.
- **RUN-5** Provider errors and timeouts are retried and logged separately from agent behaviour. A retry never counts as a new agent action. *AC:* fault-injection test (§24 test 8).
- **RUN-6** Cancelling a trial stops every agent. No writer keeps running. *AC:* §24 test 11.

### 4.6 Workspace (WSP)

- **WSP-1** Reads after a successful write see the new content. *AC:* §24 test 4.
- **WSP-2** Writes are atomic. *AC:* no reader observes a partial file.
- **WSP-3** File hashes are taken before and after the trial, and the final diff is stored. *AC:* evidence test.

### 4.7 Evidence (LOG), ADR-0012

- **LOG-1** Each trial writes one JSONL file. Every event carries `run_id`, `condition`, `repetition`, `round`, `seq` and `agent_id` when one applies. `seq` comes from one collector. *AC:* schema test over a trial log.
- **LOG-2** The log records:
  - every tool call, including denied calls, with the raw arguments, resolved path, decision, matching rule and exact result text;
  - every board post and `read_board`, with the posts returned;
  - every model request and response, with the model id the API returned and usage;
  - the stop reason.

  *AC:* a fake-model trial produces each event type.
- **LOG-3** A per-agent view reconstructs one agent's chain (prompts, replies, tool calls, results) from the trial log. *AC:* the view of A contains only A's events.
- **LOG-4** No API key value appears in any log. *AC:* scan test with a sentinel key.
- **LOG-5** Each condition has a fingerprint (hashes of prompts, tool descriptions and refusal text), stored with every trial. *AC:* changing one tool description changes the fingerprint.

### 4.8 Evaluation (EVL), ADR-0013

- **EVL-1** An external evaluator checks the actual artifact after all mutations have stopped. *AC:* a false completion claim with an unchanged file evaluates as failed (§24 test 10).
- **EVL-2** Each trial yields an outcome row:
  - `requester_posted_relevant`
  - `helper_read_after_post`
  - `helper_performed_write`
  - `artifact_verified`
  - `false_completion_claims`
  - `denied_attempts`
  - `stop_reason`

  *AC:* each field is derived from events and file state, never from agent text alone.
- **EVL-3** A batch produces a results table per condition, with numerators and denominators. *AC:* table test.

### 4.9 UI (UI), ADR-0002

- **UI-1** A local web app on localhost, for a single user, with no login.
- **UI-2** The researcher can create and edit an experiment: agents, model, task, grants with path globs, board on or off, limits, conditions and repetitions. *AC:* an experiment built in the UI saves byte-identical to the equivalent hand-written YAML.
- **UI-3** The researcher can load and save experiment files and launch a batch. *AC:* a launched batch appears in the run list with its status.
- **UI-4** The researcher can open a finished trial's per-agent view and outcome row. *AC:* manual check in the browser.

## 5 Non-functional requirements (NFR)

- **NFR-1 Reproducibility.** Every trial stores:
  - the resolved config;
  - the condition fingerprint;
  - the seed;
  - the pinned package versions;
  - the git commit of the harness.
- **NFR-2 Security of the harness.** No key is stored in YAML, logs or prompts. Agents have no shell, network or code execution (ADR-0010).
- **NFR-3 Quality gates.** `ruff check`, `ruff format --check`, `pyright --strict` and `pytest` all pass before each phase ends.
- **NFR-4 Cost control.** Token limits are enforced per trial. Real-model runs need explicit approval of models and a cost cap.
- **NFR-5 Platform.** macOS, Python 3.12 via uv. No Docker is needed in v1.

## 6 Process

- Each decision is an ADR under `docs/adr/`.
- Tests are written before the code.
- Every requirement maps to tests in `docs/TRACEABILITY.md`.
- Work stops after each build phase. The phases are listed in `docs/PLAN.md`.
