"""Local web UI: edit experiments, launch batches, read results (SRS UI-1..4; ADR-0026).

The UI is for one researcher on localhost. It saves experiments only through the same canonical
dump the tests use, so a file made in the UI is byte-identical to one written by hand.
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

from arena.agents.providers import build_client, missing_keys
from arena.agents.scripted import ScriptedChatClient
from arena.agents.trace import ModelTrace
from arena.config.loader import dump_experiment, parse_experiment
from arena.config.schema import NAME, AgentSpec, Experiment, Grants
from arena.evaluator.outcome import Outcome
from arena.evaluator.summary import render_markdown, summarize
from arena.events.views import agent_chain, read_run
from arena.runner.batch import run_batch
from arena.tools.finish import FINISH_TOOL_NAME
from arena.tools.gateway import offered_tools

STATIC = Path(__file__).parent / "static"
BATCH_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,119}$")
RUN_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,119}$")
AGENT = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


class LaunchBody(BaseModel):
    seed: int = Field(default=1, ge=0, le=2**31)
    dry_run: bool = False


class SaveBody(BaseModel):
    experiment: dict[str, Any]


class ToolsBody(BaseModel):
    grants: Grants


def _dry_run_client(agent_id: str, spec: AgentSpec, trace: ModelTrace) -> ScriptedChatClient:
    # Dry run: every agent gets no scripted replies, so a batch exercises the pipeline only.
    return ScriptedChatClient([], middleware=[trace])


def create_app(root: Path) -> FastAPI:
    experiments_dir = root / "experiments"
    fixtures_dir = root / "fixtures"
    runs_dir = root / "runs"
    runs_dir.mkdir(exist_ok=True)
    statuses: dict[str, str] = {}
    app = FastAPI(title="LLM Arena")

    def experiment_path(name: str) -> Path:
        if not NAME.match(name):
            raise HTTPException(status_code=422, detail="experiment names are lowercase words")
        return experiments_dir / f"{name}.yaml"

    def load(name: str) -> Experiment:
        path = experiment_path(name)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="no such experiment")
        return parse_experiment(path.read_text(encoding="utf-8"))

    def batch_dir(batch_id: str) -> Path:
        if not BATCH_ID.match(batch_id) or not (runs_dir / batch_id).is_dir():
            raise HTTPException(status_code=404, detail="no such batch")
        return runs_dir / batch_id

    def read_outcomes(batch_id: str) -> list[dict[str, Any]]:
        path = batch_dir(batch_id) / "outcomes.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    @app.exception_handler(ValidationError)
    async def _validation_error(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": json.loads(exc.json())})

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/api/experiments")
    def list_experiments() -> dict[str, list[str]]:
        names = (
            sorted(p.stem for p in experiments_dir.glob("*.yaml"))
            if experiments_dir.is_dir()
            else []
        )
        return {"experiments": names}

    @app.post("/api/tools")
    def tool_preview(body: ToolsBody) -> dict[str, list[str]]:
        # The same function the gateway uses, so the page cannot show a different list.
        return {"offered": list(offered_tools(body.grants)), "always": [FINISH_TOOL_NAME]}

    @app.get("/api/fixtures")
    def list_fixtures() -> dict[str, list[str]]:
        names = (
            sorted(p.name for p in fixtures_dir.iterdir() if p.is_dir())
            if fixtures_dir.is_dir()
            else []
        )
        return {"fixtures": names}

    @app.get("/api/experiments/{name}")
    def get_experiment(name: str) -> dict[str, Any]:
        exp = load(name)
        return {
            "name": name,
            "experiment": exp.model_dump(mode="json", exclude_none=True),
            "yaml": dump_experiment(exp),
        }

    @app.put("/api/experiments/{name}")
    def save_experiment(name: str, body: SaveBody) -> dict[str, str]:
        path = experiment_path(name)
        exp = Experiment.model_validate(body.experiment)
        if exp.experiment != name:
            raise HTTPException(
                status_code=422, detail="the experiment field must match the file name"
            )
        text = dump_experiment(exp)
        experiments_dir.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return {"yaml": text}

    @app.post("/api/experiments/{name}/launch")
    def launch(name: str, body: LaunchBody) -> dict[str, str]:
        exp = load(name)
        if body.dry_run:
            factory = _dry_run_client
        else:
            if any(a.model.provider == "scripted" for a in exp.agents.values()):
                raise HTTPException(status_code=400, detail="scripted agents only run as a dry run")
            absent = missing_keys(list(exp.agents.values()))
            if absent:
                # Names only: the values are never read back or shown.
                raise HTTPException(
                    status_code=400, detail="environment variables not set: " + ", ".join(absent)
                )
            factory = build_client
        if not (fixtures_dir / exp.fixture).is_dir():
            raise HTTPException(
                status_code=400, detail=f"fixture {exp.fixture!r} is not in fixtures/"
            )
        batch_id = f"{name}-{uuid.uuid4().hex[:8]}"
        statuses[batch_id] = "running"

        def work() -> None:
            try:
                asyncio.run(
                    run_batch(
                        exp,
                        batch_id=batch_id,
                        seed=body.seed,
                        fixtures_root=fixtures_dir,
                        runs_root=runs_dir,
                        client_factory=factory,
                        allow_scripted=body.dry_run,
                    )
                )
                statuses[batch_id] = "done"
            except Exception as exc:
                statuses[batch_id] = f"error: {type(exc).__name__}: {exc}"

        threading.Thread(target=work, daemon=True).start()
        return {"batch_id": batch_id}

    @app.get("/api/batches")
    def list_batches() -> dict[str, list[dict[str, str]]]:
        found = sorted((p.name for p in runs_dir.iterdir() if p.is_dir()), reverse=True)
        return {"batches": [{"batch_id": b, "status": statuses.get(b, "finished")} for b in found]}

    @app.get("/api/batches/{batch_id}")
    def get_batch(batch_id: str) -> dict[str, Any]:
        rows = read_outcomes(batch_id)
        outcomes = [Outcome(**row) for row in rows]
        return {
            "batch_id": batch_id,
            "status": statuses.get(batch_id, "finished"),
            "outcomes": rows,
            "table": render_markdown(summarize(outcomes)) if outcomes else "",
        }

    @app.get("/api/batches/{batch_id}/runs/{run_id}/agents/{agent_id}")
    def get_agent_chain(batch_id: str, run_id: str, agent_id: str) -> dict[str, Any]:
        base = batch_dir(batch_id)
        if not RUN_ID.match(run_id) or not AGENT.match(agent_id) or not (base / run_id).is_dir():
            raise HTTPException(status_code=404, detail="no such run or agent")
        records = read_run(base / run_id / "events.jsonl")
        return {"run_id": run_id, "agent_id": agent_id, "events": agent_chain(records, agent_id)}

    return app
