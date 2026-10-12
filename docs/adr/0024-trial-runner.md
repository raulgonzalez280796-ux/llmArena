# ADR-0024: The trial runner

- Status: accepted, 2026-10-12 (phase 5)
- SRS: RUN-1..6, AGT-2, AGT-3, PRM-6, LOG-1, LOG-2, LOG-4
- Blueprint: §5, §9, §15

## Decision
- **A round is one step per agent.** Within a round the agents step in a seeded order, which is fixed for the trial. The order is logged in `run_started` and `round_started`.
- **Each agent gets its own task.** It is delivered as the agent's first message, and a `task_delivered` event records it. Later rounds send the same neutral message to every agent: `ROUND_MESSAGE = "Continue with your task."` (`arena/agents/prompts.py`). This is the default proposed on 2026-10-12. It is recorded in the condition fingerprint, and it can be changed before the first real run.
- **Finishing.** Every agent has a `finish` tool, built by the runner rather than the gateway, so it is not a permission. Calling it marks that agent finished, and the agent takes no further steps. The other agents continue (confirmed 2026-10-12).
- **Stop reasons.** The trial stops with exactly one of:
  - `all_finished`, when every agent has finished;
  - `max_rounds`, after the researcher's limit;
  - `max_tokens`, when the total token count reaches `max_total_tokens`;
  - `provider_error`, when a model call raises;
  - `cancelled`, when the run task is cancelled.

  The reason is logged in `run_stopped` and stored in `result.json`.
- **Token cap.** Tokens are counted after each step, from the response's `usage_details`. The trial can therefore exceed the cap by at most one step.
- **Fresh state.** The fixture is copied into `runs/<run_id>/workspace` for each trial. The board, agent sessions and the run file are created new. A run directory must not already exist, so a run cannot be reused (RUN-2, §24 test 9).
- **Harness files stay outside the workspace.** `events.jsonl`, `result.json` and any other run file live beside `workspace/`, not inside it (PRM-6).
- **Scripted agents need an explicit allowance.** `run_trial(..., allow_scripted=True)` is required. Without it the runner refuses before creating anything (ADR-0018).
- **Cancellation.** A cancelled trial logs `run_stopped` with reason `cancelled`, writes `result.json`, and re-raises the cancellation. No model call starts after the cancel (§24 test 11).
- **Provider errors (RUN-5, partial).** A failing model call is logged as `provider_error` with the error type and a short message, and the trial stops. Retrying is not built yet. When it is, a retry must not count as an agent action, and the retry must not append the task message twice to the agent's history.
- **Batch plan.** `plan_batch` produces every condition, including `base`, repeated for each repetition, in one seeded shuffled order (RUN-4). Running the batch and writing outcome rows is phase 6.

## Consequences
- The framework's tool loop allows 10 model round trips per agent step by default. Every real client in phase 8 must use the same default, or the limit must be set explicitly and recorded.
- Event types after phase 5: `run_started`, `task_delivered`, `round_started`, `agent_step`, `provider_error`, `run_stopped`, plus the phase 4 types.
- Nothing in the runner reads environment variables for keys, so a sentinel test (`test_no_credential_value_reaches_any_run_file`) covers the full run path (LOG-4).
