"""The local UI API: canonical YAML editing, batch launch and results (SRS UI-1..4)."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false
# The TestClient stubs in this Starlette version are partly unknown; the assertions check the
# responses themselves, so the unknown types are accepted for this file only.

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from arena.config.loader import dump_experiment, load_experiment
from arena.ui.app import create_app

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "experiments" / "deploy_config_gap.yaml"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "experiments").mkdir()
    (tmp_path / "fixtures").mkdir()
    shutil.copy(EXAMPLE, tmp_path / "experiments" / EXAMPLE.name)
    shutil.copytree(ROOT / "fixtures" / "webapp_small", tmp_path / "fixtures" / "webapp_small")
    return tmp_path


@pytest.fixture
def client(project: Path) -> TestClient:
    return TestClient(create_app(project))


def wait_for_batch(client: TestClient, batch_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        body = client.get(f"/api/batches/{batch_id}").json()
        if body["status"] != "running":
            return body
        time.sleep(0.05)
    raise AssertionError("batch did not finish in time")


def test_the_page_is_served(client: TestClient) -> None:  # UI-1
    response = client.get("/")
    assert response.status_code == 200
    assert "LLM Arena" in response.text


def test_experiments_are_listed(client: TestClient) -> None:  # UI-2
    assert client.get("/api/experiments").json() == {"experiments": ["deploy_config_gap"]}


def test_an_experiment_round_trips_byte_for_byte_through_the_editor(
    client: TestClient, project: Path
) -> None:  # UI-2
    body = client.get("/api/experiments/deploy_config_gap").json()
    response = client.put(
        "/api/experiments/deploy_config_gap", json={"experiment": body["experiment"]}
    )
    assert response.status_code == 200
    assert (project / "experiments" / "deploy_config_gap.yaml").read_bytes() == EXAMPLE.read_bytes()


def test_an_edit_is_saved_in_canonical_form(client: TestClient, project: Path) -> None:  # UI-2
    body = client.get("/api/experiments/deploy_config_gap").json()
    body["experiment"]["agents"]["a"]["task"] = "Set the replica count to 6 and report when done."
    assert (
        client.put(
            "/api/experiments/deploy_config_gap", json={"experiment": body["experiment"]}
        ).status_code
        == 200
    )
    saved = (project / "experiments" / "deploy_config_gap.yaml").read_text(encoding="utf-8")
    assert saved == dump_experiment(
        load_experiment(project / "experiments" / "deploy_config_gap.yaml")
    )
    assert "replica count to 6" in saved


def test_an_invalid_edit_is_refused_and_nothing_is_written(
    client: TestClient, project: Path
) -> None:  # UI-2
    body = client.get("/api/experiments/deploy_config_gap").json()
    body["experiment"]["agents"]["a"]["grants"]["write"] = ["../escape/**"]
    response = client.put(
        "/api/experiments/deploy_config_gap", json={"experiment": body["experiment"]}
    )
    assert response.status_code == 422
    assert (project / "experiments" / "deploy_config_gap.yaml").read_bytes() == EXAMPLE.read_bytes()


def test_the_name_in_the_body_must_match_the_file(client: TestClient) -> None:  # UI-2
    body = client.get("/api/experiments/deploy_config_gap").json()
    response = client.put("/api/experiments/other_name", json={"experiment": body["experiment"]})
    assert response.status_code == 422


@pytest.mark.parametrize("name", ["../secret", "Bad Name", "a/b"])
def test_unsafe_experiment_names_are_refused(client: TestClient, name: str) -> None:
    assert client.get(f"/api/experiments/{name}").status_code in (404, 422)


def test_fixtures_are_listed(client: TestClient) -> None:  # UI-2
    assert client.get("/api/fixtures").json() == {"fixtures": ["webapp_small"]}


def test_real_providers_cannot_be_launched_yet(client: TestClient) -> None:  # phase 8 gate
    response = client.post(
        "/api/experiments/deploy_config_gap/launch", json={"seed": 1, "dry_run": False}
    )
    assert response.status_code == 400
    assert "phase 8" in response.json()["detail"]


def test_a_dry_run_batch_launches_and_its_results_can_be_read(
    client: TestClient, project: Path
) -> None:  # UI-3, UI-4
    exp = load_experiment(EXAMPLE)
    small = exp.model_copy(update={"repetitions": 1})
    body = small.model_dump(mode="json", exclude_none=True)
    body["limits"]["max_rounds"] = 2
    client.put("/api/experiments/deploy_config_gap", json={"experiment": body})

    launched = client.post(
        "/api/experiments/deploy_config_gap/launch", json={"seed": 5, "dry_run": True}
    )
    assert launched.status_code == 200
    batch_id = launched.json()["batch_id"]

    finished = wait_for_batch(client, batch_id)
    assert finished["status"] == "done"
    assert len(finished["outcomes"]) == 3  # base, full_capability, board_off
    assert "| base |" in finished["table"]
    assert batch_id in [b["batch_id"] for b in client.get("/api/batches").json()["batches"]]

    run_id = finished["outcomes"][0]["run_id"]
    chain = client.get(f"/api/batches/{batch_id}/runs/{run_id}/agents/a").json()
    assert chain["events"]
    assert {e["agent_id"] for e in chain["events"]} == {"a"}


def test_unknown_batches_and_runs_are_not_found(client: TestClient) -> None:  # UI-4
    assert client.get("/api/batches/no_such_batch").status_code == 404
    assert client.get("/api/batches/no_such_batch/runs/r000/agents/a").status_code == 404
