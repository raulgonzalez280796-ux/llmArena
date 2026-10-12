# ADR-0005: Board only; no direct messages or discovery

- Status: accepted, 2026-10-12
- Deciders: user
- Deviates from: blueprint §10-12 (broker, `request_work`, `discover_agents`, registry)

## Decision
The only channel between agents is the shared board. v1 has no direct messages, no addressed work requests, and no registry or discovery tool. A post may name an agent in its text. That is free text, not routing.

## Consequences
There is no broker, request ids or idempotency layer. Blueprint §24 tests 5-7 are adapted or dropped (see TRACEABILITY). Public vs private asking cannot be compared in v1.
