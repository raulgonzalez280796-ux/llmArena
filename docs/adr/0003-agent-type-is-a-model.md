# ADR-0003: Agent "type" is a model

- Status: accepted, 2026-10-12
- Deciders: user

## Context
"Choose an agent type" could mean a model, a role template, or a real coding-agent CLI (Claude Code, Codex...). CLIs bring built-in shell and file tools, and only OS-level isolation can restrict those.

## Decision
An agent's type is its model: provider, pinned model id, and API key variable. We own the agent loop and every tool. Real CLI harnesses are out of v1. The `AgentAdapter` interface leaves a slot for them.

## Consequences
Permissions are enforced in one place, our Tool Gateway. Results describe model behaviour, not CLI product behaviour.
