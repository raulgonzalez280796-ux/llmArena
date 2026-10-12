# ADR-0007: Every agent has its own task

- Status: accepted, 2026-10-12
- Deciders: user
- Deviates from: blueprint §5 (B starts idle)

## Context
With a pull-only board, an idle agent would never take a step, so it could never read a request.

## Decision
Every agent receives its own task at the start of a trial. In the core experiment, one agent's task cannot be completed without an action that only another agent's grants allow. The other agent's task is unrelated.

## Consequences
The runner never routes work between agents. Any help happens only through the board.
