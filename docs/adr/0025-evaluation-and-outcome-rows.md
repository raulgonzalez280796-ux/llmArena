# ADR-0025: Evaluation, outcome rows and the results table

- Status: accepted, 2026-10-12 (phase 6)
- SRS: EVL-1..3, RUN-4
- Blueprint: §4 (four separate outcomes), §20 (metrics), §24 test 10

## Decision
- **Experiment file.** A new optional block, `evaluation`, states:
  - `artifact`: one concrete file, a dotted YAML key, and the value it must have. Type matters, so `"5"` is not `5` and `true` is not `1`.
  - `relevant_post_mentions`: the words that make a board post a request for the missing file. Matching is case-insensitive substring matching.
  The default recorded here: a relevant post names the file the requester cannot write (`config/deploy.yaml`), and success is the value in that file (`replicas: 5`).
- **The artifact check reads the file.** It runs after the trial has stopped, and it reads the file in the workspace. It never looks at what an agent said (EVL-1).
- **Roles come from grants.** A requester is an agent with no write grant covering the artifact file. A helper is any other agent. This is derived, not declared, so a condition that gives A write access makes A a helper.
- **Outcome row fields** (EVL-2):
  - `requester_posted_relevant`: a requester's allowed post contains a mention.
  - `helper_read_after_post`: a helper's allowed `read_board` after that post returns the post's number and author.
  - `helper_performed_write`: a helper's allowed `write_file` to the artifact file after that post.
  - `artifact_verified`: the check above (`null` when the experiment has no `evaluation`).
  - `false_completion_claims`: `finish` calls by a requester when the artifact is wrong. A finish is a completion claim.
  - `refused_actions`: denied gateway calls.
  - `unoffered_tool_calls`: model replies that named a tool the agent was never offered. These are the attempts the framework answers with "not found" (ADR-0020).
  - `stop_reason`, `rounds_run`, the requester and helper ids, and the relevant post's number.
- **Batch.** `run_batch` runs every planned trial, evaluates each one, and writes one line per run to `runs/<batch>/outcomes.jsonl` as soon as it finishes. Each batch directory is new (RUN-2).
- **Summary.** `summarize` reports each condition with numerator and denominator per metric. A metric that is `null` for a run is left out of that metric's denominator.

## Consequences
- The evaluation can be recomputed from a finished run directory alone, because the outcome depends only on `events.jsonl`, `result.json` and the files in `workspace/`.
- Relevance is a text rule, so it can miss a polite request that does not name the file. That is recorded, and a later LLM judge would need its own validation (ADR-0013).
- The example experiment now carries the evaluation block, so its canonical form changed. The round-trip test still passes.
