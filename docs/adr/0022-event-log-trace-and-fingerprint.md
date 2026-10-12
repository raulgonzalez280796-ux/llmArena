# ADR-0022: Event log, model trace and condition fingerprint

- Status: accepted, 2026-10-12 (phase 4)
- SRS: LOG-1..5
- Blueprint: §19 (event schema), §4 (what must be recorded)

## Decision
- **One JSONL file per run**, opened with mode `x`, so a run file is never overwritten. Each line has `run_id`, `condition`, `repetition`, `round`, `seq`, `timestamp` (UTC, ISO 8601), `type`, `agent_id` (null for run-level events) and `data`. `seq` comes from a single counter per run, so the order is total and gap-free (LOG-1).
- **Round.** The runner sets `sink.round` at the start of each round (phase 5). Events before the first round have `round: null`.
- **Model trace.** `ModelTrace` is a framework chat middleware. It writes `model_request` (instructions, tool names, every message with its role and text) and `model_response` (text, function calls with their arguments, model id, finish reason) for each provider round trip (LOG-2).
  - **Composition order matters.** The client must list `FunctionInvocationLayer` before `ChatMiddlewareLayer`. In the other order, the tool loop skips the middleware for every round trip after the first, which was confirmed by a failing test. Real provider clients (phase 8) must use the same order, and `tests/agents/test_model_trace.py` guards it.
  - Unknown or unoffered tool calls therefore appear in `model_response.tool_calls`. Counting them is a phase 6 metric, computed from the log.
- **Agent chain.** `agent_chain(records, agent_id)` filters one run file by agent id. Nothing is copied or written back (LOG-3).
- **Credentials.** Keys are never put in event data. The trace test checks this for the names `api_key` and `authorization`. The full check, scanning a real run for a sentinel key, comes with the first real provider in phase 5 (LOG-4 partial).
- **Fingerprint.** `condition_fingerprint(experiment)` is the SHA-256 of canonical JSON that contains the resolved experiment (without its condition list), the neutral instructions, every tool description, the board limits and the refusal template. Changing any one of them changes the hash (LOG-5). Each run record stores the hash in phase 5.

## Consequences
- Event types in phase 4: `tool_call`, `model_request`, `model_response`. Phase 5 adds the run lifecycle (`run_started`, `task_delivered`, `round_started`, `stop`, `run_stopped`). Phase 6 adds the outcome row.
- Run files contain full prompts and replies. They are kept under `runs/`, which is outside every agent workspace and git-ignored (PRM-6, ADR-0010).
