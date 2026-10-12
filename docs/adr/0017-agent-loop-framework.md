# ADR-0017: Microsoft Agent Framework runs the agent loop

- Status: accepted, 2026-10-12 (phase 2 spike)
- Blueprint: §3, §23 step 1

## Context
The blueprint recommends a short spike on Microsoft Agent Framework (MAF) before committing, with AutoGen as a fallback (AutoGen is in maintenance mode). The spike (`spikes/maf_spike.py`) used a scripted fake model and no API key.

## Decision
Use `agent-framework-core==1.19.0`, pinned. The arena uses only `Agent`, chat clients, `FunctionTool` and `AgentSession`. It does not use the harness, skills, MCP, memory or context providers, compaction, `additional_tools`, or any middleware that injects content. MAF passed every check, so the AutoGen spike was skipped, as the blueprint's decision rule allows.

## Findings
1. The model request carries exactly our instructions and our tools. MAF adds no system prompt of its own.
2. An `AgentSession` keeps one agent's history across steps. Two agents with separate sessions share nothing.
3. When the model calls a tool it does not have, MAF runs nothing and answers with its own text: `Error: Requested function "<name>" not found.` That text reaches the model. The Gateway must own this wording (PRM-1, PRM-5, phase 3).
4. `max_iterations` caps model round-trips within one step. After the cap, MAF makes one extra call with `tool_choice: none` to force a text answer. That call costs tokens and must be logged.
5. MAF runs the tool calls from one model reply concurrently by default. The arena sets `allow_concurrent_invocation: False`, so calls run in model order (blueprint §9: no parallel tool calls).
6. Provider connectors are versioned separately. `agent-framework-openai` is GA (1.16.0). `agent-framework-anthropic` and `agent-framework-gemini` are beta (1.0.0b261008). The choice waits for the pilot models (phase 8), and the contract tests run against each chosen connector.

## Consequences
- `tests/agents/test_maf_contract.py` guards findings 1-4. A framework upgrade that changes them fails a named test.
- `arena.agents.scripted.ScriptedChatClient` is the fake model for every later phase.
- Open for phase 5: the text an agent receives at the start of each round (e.g. "Continue.") is a stimulus the model sees. It must be neutral, identical for all agents, and part of the fingerprint.

## Addendum (phase 3)
Finding 3 is revised by ADR-0020. The gateway does not own the unknown-tool wording. The framework's text is kept and recorded, and unknown-tool calls are counted from the logged model responses.
