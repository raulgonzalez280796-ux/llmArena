# ADR-0016: Engineering process

- Status: accepted, 2026-10-12
- Deciders: user

## Decision
The process is:
- the SRS has numbered requirements with acceptance criteria;
- every decision is an ADR;
- tests are written first;
- a traceability table maps requirements to tests;
- gates (ruff, ruff format, pyright strict, pytest) must pass;
- work stops after each phase, with a local git commit at the end of each phase and no remote.

The assistant asks before installs and before model or cost choices.
