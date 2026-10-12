# ADR-0006: The board is pull-only

- Status: accepted, 2026-10-12
- Deciders: user
- Deviates from: blueprint §10 (event-driven delivery)

## Decision
No agent is notified of new posts. A post reaches an agent's context only when that agent calls `read_board`.

## Consequences
Whether the helper reads the board is itself an outcome (`helper_read_after_post`). A "helper did not act" result must be read together with it.
