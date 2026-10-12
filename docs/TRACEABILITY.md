# Requirement-to-test traceability

Filled in as tests are written. Every requirement in `SRS.md` must map to at least one test before its phase ends. Tests are named `tests/<area>/test_<topic>.py::<test>`.

| Requirement | Phase | Tests | Status |
|---|---|---|---|
| EXP-1 … EXP-5 | 3 | — | planned |
| AGT-1, AGT-4 | 3 | — | planned |
| AGT-2, AGT-3, AGT-5 | 2, 5 | — | planned |
| PRM-1 … PRM-7 | 3 | — | planned |
| WSP-1 … WSP-3 | 3, 5 | — | planned |
| BRD-1 … BRD-6 | 4 | — | planned |
| LOG-1 … LOG-5 | 4, 5 | — | planned |
| RUN-1 … RUN-6 | 5, 6 | — | planned |
| EVL-1 … EVL-3 | 6 | — | planned |
| UI-1 … UI-4 | 7 | — | planned |
| NFR-1 … NFR-5 | all | — | planned |

## Blueprint §24 infrastructure tests

| §24 test | Status in this design | Requirement |
|---|---|---|
| 1 unauthorized tool blocked at Gateway | kept | PRM-1 |
| 2 model cannot change sender or policy | kept | PRM-2, BRD-3 |
| 3 path escape and symlink blocked | kept | PRM-4 |
| 4 read after write sees new content | kept | WSP-1 |
| 5 concurrent writes with same expected_version | deferred: one writer per file in v1, rounds are sequential | — |
| 6 duplicate request_id executed once | dropped: no request routing (ADR-0005) | — |
| 7 unknown recipient returns an error | adapted: unknown tool or malformed board call returns an error | PRM-1, BRD-1 |
| 8 helper failure or timeout delivered and logged | adapted: provider errors logged apart from behaviour | RUN-5 |
| 9 reset gives fresh workspace and histories | kept | RUN-2 |
| 10 evaluator catches a false success claim | kept | EVL-1 |
| 11 cancellation stops sub-work | kept | RUN-6 |
| 12 execution cannot write indirectly | not applicable: no execution in v1 (ADR-0010) | — |
