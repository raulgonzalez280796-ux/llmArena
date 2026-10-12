# Build plan

The build runs in eight phases. Work stops after each phase, and each phase ends with a local commit (ADR-0016). Phases 1 and 2 are complete.

1. **Foundations.**
   - `uv` project on Python 3.12, `git init` (ask first), ruff, pyright and pytest.
   - `docs/SRS.md` built from this plan, ADR-0001… for D1–D10 and the defaults, and a traceability table.
   - Done when the empty test suite and lint pass.
2. **Framework spike** (blueprint §23 step 1).
   - Microsoft Agent Framework first, AutoGen as fallback.
   - One agent, one local tool, a fake model client.
   - One real call only if the user supplies a key.
   - Done when an ADR records the chosen framework.
3. **Config + Gateway + workspace.**
   - Schema, YAML round-trip, scoped file tools and path canonicalization.
   - Done when §24 tests 1–3 pass (unauthorized tool, spoofed identity, traversal and symlink).
4. **Board + events.**
   - Board service and tools, JSONL collector and the per-agent view.
   - Done when sender stamping holds, posts are append-only, and every call, including denials, is logged.
5. **Runner.**
   - Rounds, seeded order, budgets, stop rules, fresh trial reset.
   - Done when one end-to-end trial runs with fake models: A is denied, A posts, B reads, B writes, the evaluator passes. §24 tests 4, 9 and 11 also pass.
6. **Evaluator + conditions.**
   - Outcome rows and conditions × repetitions.
   - Done when a 2-condition × 3-repetition batch runs on fake models and produces a results table.
7. **UI.**
   - Experiment editor (agents, model, tasks, grants with path scopes, board on/off), save/load YAML, launch, run list, per-agent log view.
   - Done when an experiment made in the UI is byte-identical to the hand-written YAML and runs.
8. **Pilot with real models.**
   - Ask first: which models, whose keys, and the cost cap.
   - Run 4 conditions × 5 repetitions.

