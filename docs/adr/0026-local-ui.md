# ADR-0026: The local UI

- Status: accepted, 2026-10-12 (phase 7)
- SRS: UI-1..4
- Blueprint: §23 (no frontend before one trial works end to end; the engine works end to end by phase 6)

## Decision
- **Stack.** FastAPI (serves the JSON API and one static HTML page) and uvicorn, started with `uv run python -m arena.ui`. The page is one file with plain JavaScript and no external scripts or stylesheets. It is bound to `127.0.0.1`, has no login, and is for one researcher.
- **Editing saves canonical YAML.** The UI sends a JSON copy of the experiment. The server validates it with the same schema as the loader and writes it with `dump_experiment`. A file that the UI saves is therefore byte-identical to the canonical form, and the test compares it with the hand-written example.
- **Names are checked before any file is touched.** Experiment names must be lowercase words, and batch and run ids must match a fixed pattern, so a name cannot point outside `experiments/` or `runs/`.
- **Launching.** Launch runs the batch in a background thread with its own event loop, so the page stays responsive. Batch status is held in memory: `running`, `done`, or `error`. After a restart, a batch with outcome rows is shown as `finished`.
- **Real providers are refused.** Launching without the dry-run flag returns 400 with "phase 8". Dry runs use agents with no scripted replies, so they exercise the pipeline and produce rows, but no model is called.
- **Results.** The page shows the results table for each batch, one row per run, and the agent logs for a run. The logs are a filter over the run's `events.jsonl`, one agent at a time (LOG-3).

## Consequences
- Adds two runtime dependencies (`fastapi`, `uvicorn`) and one development dependency (`httpx`, for the API tests). They are installed into the project's own environment, not the system.
- Live monitoring is still absent (ADR-0002). The page polls the batch status once a second until it is no longer running.
