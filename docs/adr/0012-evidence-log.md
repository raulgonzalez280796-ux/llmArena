# ADR-0012: JSONL evidence and condition fingerprints

- Status: accepted, 2026-10-12 (blueprint §19)

## Decision
Each trial writes one JSONL file through a single collector that assigns `seq`. The log covers every tool call (including denials), board posts and reads, model requests and responses, file hashes before and after, the final diff, and the stop reason. A per-agent view is a filter over this one file. Each condition has a fingerprint: hashes of the prompts, tool descriptions and refusal text.

## Consequences
The research schema is ours. Framework telemetry is optional and never the evidence.
