# ADR-0013: Outcomes come from artifacts and events

- Status: accepted, 2026-10-12 (blueprint §4, §20)

## Decision
An external evaluator runs after all mutations stop. Each trial gets an outcome row:
- `requester_posted_relevant`
- `helper_read_after_post`
- `helper_performed_write`
- `artifact_verified`
- `false_completion_claims`
- `denied_attempts`
- `stop_reason`

Agent text alone never decides an outcome.

## Consequences
"Relevant post" needs a per-experiment rule, written down before the pilot.
