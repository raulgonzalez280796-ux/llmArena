# ADR-0015: Realistic cover story

- Status: accepted, 2026-10-12

## Decision
Fixtures look like real projects. The target file has a real-looking name, such as `config/deploy.yaml` instead of `zzz`. Prompts, tool descriptions and file names never contain the words arena, experiment or test.

## Consequences
This reduces evaluation-awareness effects. A lint test enforces it (AGT-4).
