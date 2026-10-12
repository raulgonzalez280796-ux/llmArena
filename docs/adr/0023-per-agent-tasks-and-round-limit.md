# ADR-0023: Per-agent tasks and a round limit set by the researcher

- Status: accepted, 2026-10-12 (phase 5). Early stop decided by the researcher the same day.
- Amends: ADR-0007 (every agent has its own task), ADR-0009 (fixed rounds), SRS RUN-3.
- Blueprint: §5 (B starts idle), §15 (stop conditions)

## Decision
- **Each agent has its own task.** The task is set per agent in the experiment (`agents.<id>.task`), and it is delivered to that agent at the start of the trial. The UI (phase 7) must let the researcher edit each agent's task separately.
- **The run has a maximum number of iterations, set by the researcher.** The field is `limits.max_rounds`. One iteration is one round in which every agent takes one step (ADR-0009, confirmed by the researcher 2026-10-12). The trial stops when `max_rounds` is reached, with the stop reason `max_rounds` in the log.
- **An agent that finishes its task stops.** It calls the `finish` tool, and it takes no further steps. The other agents continue (decided 2026-10-12). The trial ends when every agent has finished, or when a cap is reached.
- **`max_total_tokens` is a second cap.** If it is reached first, the trial stops with the reason `max_tokens`.
- **Removed:** the idle-agent stop rule and the declared-done stop rule. They depend on signals that the design no longer uses.

## Decided
- The early-stop question was asked 2026-10-12. Answer: yes, an agent that finishes stops (see the decision above). Implementation: ADR-0024.

## Consequences
- The `finish` tool is the only way an agent ends early. It is offered to every agent, so it does not signal anything about one agent.
- Idle agents still take a step each round. Their steps are logged like any others, so an agent that does nothing is visible in the record.
