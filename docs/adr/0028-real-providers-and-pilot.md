# ADR-0028: Real providers and the first pilot

- Status: accepted, 2026-10-12 (approved by the researcher); the pilot itself is not yet run
- SRS: AGT-5, LOG-2, LOG-4, EVL-2
- Amends: ADR-0017 (framework version), ADR-0018 (the scripted provider is for dry runs only)

## Decision
- **Direct connectors, one per provider**, as agreed: OpenAI, Anthropic and Google. No aggregator (ADR-0028 records this choice; OpenRouter was considered and not used, because provider routing and data handling were not verified).
- **Pinned versions.** `agent-framework-core` 1.21.0. `agent-framework-openai` 1.16.0 (stable). `agent-framework-anthropic` and `agent-framework-gemini` 1.0.0b261008 (beta). The core moved from 1.19.0 because the OpenAI and Gemini connectors need core 1.20 or later. All 219 earlier tests passed after the move.
- **Pinned model ids**, taken from the official model pages on 2026-10-12:
  - Anthropic: `claude-opus-5-5`. Anthropic recommends it for most workloads.
  - OpenAI: `gpt-6-astra`, the flagship on the models page. Access may be restricted, so the first call will show whether the account has it. If not, the fallback is `gpt-6.1-sol`.
  - Google: `gemini-3.8-flash`, the newest stable Flash on the models page. Its price is not verified.
- **Keys** are read from the environment variable named in each agent's model settings. A key is wrapped so that it cannot be printed. The message for a missing key names the variable and never shows a value. The UI refuses a real launch before it starts, and it lists the missing names.
- **Tool loop.** Each agent step allows 10 model round trips, and tool calls within a step run in order, not in parallel (blueprint §9).
- **Pilot.** Three experiment files, one per provider: `deploy_config_gap_anthropic`, `_openai` and `_gemini`. Both agents in a file use that provider's model, which keeps the model fixed within a comparison (ADR-0014). Each file has the same task, grants, check and three conditions (base, full_capability, board_off) with 5 repetitions, so 15 runs per provider and 45 in total. The token cap is 200,000 per run, as approved.

## Risks to check in the first run
- **Token counts.** The token cap depends on the connector returning usage. The first run must show non-zero `tokens` in `agent_step` events for every provider. If one provider returns none, its cap does nothing and the run must not go ahead until that is fixed.
- **Retries.** A provider failure still stops the trial, and retrying is not built yet (RUN-5). A provider that fails often will end many trials early, and the runs will show it as `provider_error`.
- **Model id.** The id that the API returns is recorded in every `model_response`. If it differs from the pinned id, the run must not be counted.

## Consequences
- Dry runs keep working on the scripted provider, and real launches refuse scripted agents.
- The pilot costs real money. Costs are read from the token counts in the run files, not estimated.
