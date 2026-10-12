# ADR-0009: Fixed rounds with a seeded order

- Status: accepted, 2026-10-12
- Deciders: user
- Replaces: blueprint §10 (per-worker queues)

## Decision
A trial runs in rounds. In each round every agent takes one step: one model turn, including its tool calls, up to a per-step cap. The order within a round is a seeded shuffle that is fixed for the trial. The seed and the order are logged.

## Consequences
Trials are reproducible and easy to read. Timing is slightly artificial.
