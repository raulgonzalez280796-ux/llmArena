# ADR-0002: v1 UI configures and launches experiments

- Status: accepted, 2026-10-12
- Deciders: user
- Deviates from: blueprint §23 ("no frontend before one trial works end to end")

## Context
The user wants to choose models and grant tools in a UI before agents are deployed.

## Decision
v1 ships a local web app (localhost, one user, no login). It edits experiment YAML files, saves and loads them, launches batches, lists runs, and opens a finished trial's per-agent view and outcome row. There is no live view in v1. The UI is built in phase 7, after the engine works end to end, so the blueprint's ordering concern still holds.

## Consequences
The YAML file stays the single source of truth. The UI must save byte-identical files (UI-2).
