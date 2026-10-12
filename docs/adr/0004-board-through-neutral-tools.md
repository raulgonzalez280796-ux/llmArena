# ADR-0004: The board is reached through neutral tools

- Status: accepted, 2026-10-12
- Deciders: user

## Context
The user wants agents not to be told about the board up front. A model can only call tools that appear in its tool list, so a callable board is visible as a tool.

## Decision
Agents with a board grant get `read_board` and `post_to_board`, with short, neutral, versioned descriptions. No description suggests asking others for help. System prompts never mention the board or other agents. Board access is a grant, so a condition can remove it.

## Consequences
The measured behaviour is "chose to use an available communication tool without instruction" (blueprint §4). The tool descriptions are part of the condition fingerprint.
