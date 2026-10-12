# LLM Arena

LLM Arena is a research harness. Several LLM agents share one project workspace. Each agent has its own model, task and scoped tools, and all agents share one board. The harness measures whether an agent that lacks a permission uses the board to get another agent to act, and whether the result is correct.

- Spec: `Shared_Coding_Agents_Research_Blueprint_HE.md`
- Requirements: [docs/SRS.md](docs/SRS.md)
- Decisions: [docs/adr/](docs/adr/README.md)
- Build plan: [docs/PLAN.md](docs/PLAN.md)
- Traceability: [docs/TRACEABILITY.md](docs/TRACEABILITY.md)

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run pyright
```
