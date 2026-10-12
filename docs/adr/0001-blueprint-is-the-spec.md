# ADR-0001: The blueprint is the spec

- Status: accepted, 2026-10-12
- Deciders: user

## Context
The earlier spec (`LLM_ARENA_BUILD_SPEC.md`), its Inspect-based code and ADRs 0001-0026 were deleted. The user supplied `Shared_Coding_Agents_Research_Blueprint_HE.md`.

## Decision
The blueprint is the spec. Where the user's explicit decisions differ from it, the user wins. Each difference has its own ADR that names the blueprint section it changes. The build restarts from scratch, and ADR numbering restarts at 0001.

## Consequences
Earlier decisions are not carried over unless an ADR here restates them.
