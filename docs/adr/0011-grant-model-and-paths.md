# ADR-0011: Grant model and path canonicalization

- Status: accepted, 2026-10-12 (default chosen by the assistant, recorded for review)

## Decision
- Grants deny by default.
- `read` and `write` take path globs relative to the workspace root.
- `write` covers create, overwrite, delete and rename.
- `list` follows `read`.
- Every path is resolved before the check: `..` escapes are rejected, and symlinks are resolved, with links that land outside scope refused.
- The comparison is case-insensitive and Unicode NFC-normalized, because APFS is case-insensitive.
- A refusal returns exactly `Permission denied: <path>`.

## Consequences
The refusal wording is a fixed part of every condition's fingerprint. Wording that names an owner would be a separate, explicit condition.
