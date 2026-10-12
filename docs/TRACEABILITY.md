# Requirement-to-test traceability

Filled in as tests are written. Every requirement in `SRS.md` must map to at least one test before its phase ends. Tests are named `tests/<area>/test_<topic>.py::<test>`.

| Requirement | Phase | Tests | Status |
|---|---|---|---|
| EXP-1 | 3 | `tests/config/test_schema.py` (unknown fields, grant keys, globs), `tests/config/test_loader.py` (duplicate keys) | done |
| EXP-2 | 3 | `tests/config/test_roundtrip.py::test_example_experiment_file_is_canonical`, `::test_dump_then_parse_is_stable` | done |
| EXP-3 | 3 | `tests/config/test_schema.py::test_valid_experiment_parses`, `::test_repetitions_are_required`, `::test_limits_must_be_positive`, `::test_at_least_one_agent_is_required` | done |
| EXP-4 | 3 | `tests/config/test_roundtrip.py` (condition overrides, unknown-field and unknown-agent rejection) | done |
| EXP-5 | 3 | `tests/config/test_schema.py` (api_key field, key-shaped variable name, key variable per provider) | done |
| AGT-1 | 3 | `tests/config/test_schema.py::test_agent_id_must_be_a_simple_name`, `::test_missing_task_is_rejected` | done |
| AGT-4 | 3 | `tests/agents/test_prompts.py` (instructions, fixtures, task text, tool descriptions) | done |
| AGT-3 | 2, 5 | `tests/agents/test_maf_contract.py::test_two_agents_do_not_share_history` (framework level; trial level in phase 5) | partial |
| AGT-2, AGT-5 | 5 | — | planned |
| ADR-0017 findings 1-4 | 2 | `tests/agents/test_maf_contract.py` (6 tests) | done |
| PRM-1 | 3 | `tests/tools/test_gateway.py::test_ungranted_tool_name_is_refused_and_logged`, `::test_known_tool_without_its_grant_is_refused_and_logged`; `tests/tools/test_framework_tools.py::test_model_is_offered_only_the_granted_tools` | done |
| PRM-2 | 3 | `tests/tools/test_gateway.py::test_model_supplied_identity_is_rejected_and_not_applied`, `::test_extra_argument_on_write_is_rejected` | done |
| PRM-3 | 3 | `tests/workspace/test_paths.py::test_grant_matching`, `tests/tools/test_gateway.py` (read, write, list) | done |
| PRM-4 | 3 | `tests/workspace/test_paths.py` (traversal, absolute, symlinks, NFD, malformed), `tests/tools/test_gateway.py::test_symlink_*` | done |
| PRM-5 | 3 | `tests/tools/test_gateway.py::test_read_outside_grant_is_refused_with_exact_text` | done |
| PRM-6 | 3 | by construction: a grant can only resolve inside the workspace root (`canonicalize`); harness files live outside it | done |
| PRM-7 | 3 | `tests/tools/test_gateway.py::test_grants_cannot_be_changed_after_the_gateway_is_built` | done |
| WSP-1 | 3 | `tests/workspace/test_files.py::test_read_after_write_sees_new_content` | done |
| WSP-2 | 3 | `tests/workspace/test_files.py::test_failed_write_leaves_original_and_no_temp_file` | done |
| WSP-3 | 3 | `tests/workspace/test_files.py::test_snapshot_and_diff_report_added_removed_and_modified` | done |
| BRD-1 … BRD-6 | 4 | — | planned |
| LOG-2 (tool calls) | 3 | `tests/tools/test_gateway.py::test_every_call_is_logged_once_with_its_arguments` | partial |
| LOG-1, LOG-3 … LOG-5 | 4, 5 | — | planned |
| RUN-1 … RUN-6 | 5, 6 | — | planned |
| EVL-1 … EVL-3 | 6 | — | planned |
| UI-1 … UI-4 | 7 | — | planned |
| NFR-1 … NFR-5 | all | — | planned |

## Blueprint §24 infrastructure tests

| §24 test | Status in this design | Requirement |
|---|---|---|
| 1 unauthorized tool blocked at Gateway | done (`test_ungranted_tool_name_is_refused_and_logged`) | PRM-1 |
| 2 model cannot change sender or policy | done for tool calls (`test_model_supplied_identity_is_rejected_and_not_applied`); board sender in phase 4 | PRM-2, BRD-3 |
| 3 path escape and symlink blocked | done (`tests/workspace/test_paths.py`, `test_gateway.py::test_traversal_is_refused_with_exact_text`) | PRM-4 |
| 4 read after write sees new content | done (`test_read_after_write_sees_new_content`) | WSP-1 |
| 5 concurrent writes with same expected_version | deferred: one writer per file in v1, rounds are sequential | — |
| 6 duplicate request_id executed once | dropped: no request routing (ADR-0005) | — |
| 7 unknown recipient returns an error | adapted: unknown tool or malformed board call returns an error | PRM-1, BRD-1 |
| 8 helper failure or timeout delivered and logged | adapted: provider errors logged apart from behaviour | RUN-5 |
| 9 reset gives fresh workspace and histories | phase 5 | RUN-2 |
| 10 evaluator catches a false success claim | kept | EVL-1 |
| 11 cancellation stops sub-work | kept | RUN-6 |
| 12 execution cannot write indirectly | not applicable: no execution in v1 (ADR-0010) | — |
