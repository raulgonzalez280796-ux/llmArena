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
| BRD-1 | 4 | `tests/tools/test_board_tools.py::test_board_tools_are_offered_only_with_the_board_grant`; `tests/agents/test_prompts.py::test_tool_descriptions_are_neutral`; `tests/config/test_fingerprint.py` | done |
| BRD-2 | 4 | `tests/board/test_board.py::test_posts_are_numbered_from_one_with_the_sender_recorded`, `::test_board_offers_no_way_to_edit_or_remove_a_post`, `::test_refused_post_is_not_recorded` | done |
| BRD-3 | 4 | `tests/board/test_board.py::test_posts_are_numbered_from_one_with_the_sender_recorded`; `tests/tools/test_board_tools.py::test_post_is_stamped_with_the_gateway_identity`, `::test_post_names_a_sender_argument_is_rejected` | done |
| BRD-4 | 4 | `tests/tools/test_pull_only.py::test_peer_does_not_see_a_post_until_it_reads_the_board` | done |
| BRD-5 | 4 | `tests/board/test_board.py` (per-agent count, length, empty), `tests/tools/test_board_tools.py::test_post_over_the_limit_is_rejected_and_logged` | done |
| BRD-6 | 4 | `tests/tools/test_board_tools.py::test_board_tools_without_grant_are_refused_and_logged`, `::test_board_grant_without_a_board_is_a_construction_error` | done |
| LOG-1 | 4, 5 | `tests/events/test_jsonl.py` (run context, gap-free seq, round, no overwrite, unicode) | done |
| LOG-2 | 3, 4 | `tests/tools/test_gateway.py::test_every_call_is_logged_once_with_its_arguments`; `tests/agents/test_model_trace.py` (requests, replies, unoffered calls) | done for tool calls and model rounds; run-level events in phase 5 |
| LOG-3 | 4 | `tests/events/test_views.py` | done |
| LOG-4 | 4, 5 | `tests/agents/test_model_trace.py::test_trace_never_carries_credentials`; `tests/runner/test_trial.py::test_no_credential_value_reaches_any_run_file` | done for the dry-run path; real providers must add their own check in phase 8 |
| LOG-5 | 4 | `tests/config/test_fingerprint.py` (stable, condition-sensitive, tool- and task-sensitive) | done |
| RUN-1 | 5 | `tests/runner/test_trial.py::test_the_seeded_order_is_logged_and_repeatable`, `tests/runner/test_batch.py::test_the_plan_is_repeatable_for_a_seed_and_differs_between_seeds` | done |
| RUN-2 | 5 | `test_each_trial_starts_from_a_clean_workspace_and_board`, `test_a_run_directory_is_never_reused` | done |
| RUN-3 | 5 | `test_stops_at_max_rounds_when_nobody_finishes`, `test_stops_when_the_token_cap_is_reached`, `test_finished_agent_takes_no_further_steps`, `test_an_agent_that_finishes_early_stops_while_others_continue`, `test_two_agents_complete_the_core_scenario` (all_finished) | done |
| RUN-4 | 5, 6 | `tests/runner/test_batch.py` (plan), `tests/runner/test_batch_run.py` (every condition and repetition gets a run and a row) | done |
| RUN-5 | 5 | `test_provider_failure_is_logged_and_stops_the_trial` (no retry yet) | partial |
| RUN-6 | 5 | `test_cancelling_the_run_stops_the_model_calls` | done |
| EVL-1 | 6 | `tests/evaluator/test_artifact.py` (exact value, type, missing file, nested key, outside workspace) | done |
| EVL-2 | 6 | `tests/evaluator/test_outcome.py` (full success, unoffered attempt, helper never reads, board off, vague request) | done |
| EVL-3 | 6 | `tests/evaluator/test_summary.py` | done |
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
| 8 helper failure or timeout delivered and logged | adapted: provider failures logged and stop the trial; retry not built | RUN-5 |
| 9 reset gives fresh workspace and histories | done (`test_each_trial_starts_from_a_clean_workspace_and_board`) | RUN-2 |
| 10 evaluator catches a false success claim | done (`test_a_helper_that_never_reads_the_board_leaves_the_request_unread`: A finishes, file wrong, counted) | EVL-1 |
| 11 cancellation stops sub-work | done (`test_cancelling_the_run_stops_the_model_calls`) | RUN-6 |
| 12 execution cannot write indirectly | not applicable: no execution in v1 (ADR-0010) | — |
