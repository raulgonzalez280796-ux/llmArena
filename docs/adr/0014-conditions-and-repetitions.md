# ADR-0014: Experiments are YAML files with conditions and repetitions

- Status: accepted, 2026-10-12 (blueprint §17)

## Decision
An experiment file holds a base setup, named conditions that override fields by path, and a repetition count. Every trial starts from a fresh fixture copy and fresh agent state. Batches interleave conditions. The pilot uses 5 repetitions. Real experiments default to 30.
