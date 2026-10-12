# ADR-0020: Tool Gateway, offered tools and refusal wording

- Status: accepted, 2026-10-12 (phase 3)
- SRS: PRM-1, PRM-2, PRM-5, PRM-7, LOG-2, AGT-5

## Decision
- **One gateway per agent.** The agent id, grants and workspace are fixed when the gateway is built. Grants are a frozen model, so the gateway cannot change them afterwards (PRM-7). Nothing the model sends can change the identity.
- **Offered tools follow grants.** `list_files` and `read_file` are offered when there is any read grant, and `write_file` when there is any write grant. Tools without a grant are not offered to the model, so the model never learns that they exist (blueprint §13). `build_file_tools` builds only what is granted.
- **Extra arguments are rejected.** Each tool's argument model forbids extra fields, so a model cannot add `agent_id` or `sender` (PRM-2). The rejection is logged and nothing runs.
- **Refusals have one wording.** A refusal returns exactly `Permission denied: <requested path>`, the same for a missing grant, an outside-workspace path and a missing directory grant. The text reveals neither the resolved path nor the grants (PRM-5).
- **Every call is logged.** Each call emits one `tool_call` event with the raw arguments, the decision (`allowed`, `denied`, `rejected`, `error`), the reason, the resolved path, the matching rule and the result text (LOG-2). Phase 4 turns these events into the JSONL log.
- **Calls to unknown or unoffered tools reach the gateway only when called directly.** Through the framework, a call to a tool that was never offered is answered by the framework itself with `Error: Requested function "<name>" not found.`, and it never reaches the gateway.
- **Read and write limits.** Reads and writes are limited to 64,000 bytes. A read over the limit is an error. A write over the limit is rejected.

## Revision of ADR-0017, finding 3
ADR-0017 said the gateway must own the wording for unknown tools. That is not possible without intercepting the framework, and the framework does not expose unknown calls to us. The decision here is to keep the framework's wording. That wording is fixed by the pinned framework version, and it goes into the condition fingerprint.

Unknown or unoffered tool calls are still recorded, from the model responses that phase 4 logs in full (LOG-2). A call that names a tool the agent does not have is counted as an invalid action attempt (blueprint §20).

## Consequences
- The tool descriptions are neutral and checked by `tests/agents/test_prompts.py`.
- `tests/tools/test_framework_tools.py` pins both the offered-tool list and the framework's wording.
