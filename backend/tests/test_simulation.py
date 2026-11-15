"""Simulação: gerador de casos, compatibilidade, worker (executor SIMULADO) e segurança da API.

Nenhum teste aqui executa FDS: o executor é `FakeExecutor` (rotulado demo). A execução real
está em tests marcados `real_fds` e em docs/evidence/.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.api.platform import Services
from backend.app.main import app
from backend.app.simulation.case_builder import CaseValidationError, build_case, validate_values
from backend.app.simulation.executor import FakeExecutor
from backend.app.simulation.models import RunState
from backend.app.simulation.registry import INTEGRATION, MODELS

MODEL = INTEGRATION.model_id


@pytest.fixture
def client():
    return TestClient(app)


def use(executor):
    Services.executor = executor
    return executor


def new_scenario(client, values=None, model=MODEL, experiment_id=None):
    body = {"model_id": model, "values": values or {}}
    if experiment_id:
        body["experiment_id"] = experiment_id
    return client.post("/api/scenarios", json=body)


# ---------------------------------------------------------------- gerador de casos
def test_case_builder_is_deterministic_and_complete():
    a, sha_a = build_case(INTEGRATION, {"hrrpua": 1000, "soot_yield": 0.01, "t_end": 10}, "fl_x")
    b, sha_b = build_case(INTEGRATION, {"t_end": 10}, "fl_x")  # o resto vem dos padrões
    assert a == b and sha_a == sha_b
    assert "HRRPUA=1000." in a and "T_END=10." in a and "&TAIL /" in a and "NFRAMES=100" in a
    assert "not a NASA experiment reproduction" in a


def test_case_builder_changes_only_requested_values():
    base, _ = build_case(INTEGRATION, {}, "fl_x")
    mod, _ = build_case(INTEGRATION, {"hrrpua": 500}, "fl_x")
    diff = [(x, y) for x, y in zip(base.splitlines(), mod.splitlines()) if x != y]
    assert len(diff) == 1 and "HRRPUA=1000." in diff[0][0] and "HRRPUA=500." in diff[0][1]


@pytest.mark.parametrize("values", [
    {"hrrpua": 99999}, {"hrrpua": -1}, {"t_end": 0}, {"soot_yield": float("nan")}, {"hrrpua": float("inf")},
    {"unknown": 1}, {"hrrpua": True},
])
def test_case_builder_rejects_out_of_range_or_unknown(values):
    with pytest.raises(CaseValidationError):
        validate_values(INTEGRATION, values)


def test_case_builder_rejects_unsafe_chid_and_unimplemented_model():
    with pytest.raises(CaseValidationError):
        build_case(INTEGRATION, {}, "x'; &HEAD")
    with pytest.raises(CaseValidationError):
        build_case(MODELS["fds-flame-spread-thin-solid"], {}, "fl_x")


# ---------------------------------------------------------------- compatibilidade
def test_reference_experiment_is_not_simulable_and_says_why(client):
    c = client.get("/api/experiments/BASS2-M1/compatibility").json()["data"]
    assert c["status"] == "MISSING_PARAMETERS"
    assert c["actions"] == {"analyze": True, "prepare": True, "alter": True, "simulate": False}
    assert "duct_geometry" in c["missing"] and "sample_length" in c["missing"]
    assert "flame_spread_rate" in [o["parameter"] for o in c["reference_observables"]]
    assert any("nunca condição de entrada" in r for r in c["reasons_pt"])
    assert "flame_spread_rate" not in c["editable_conditions"]  # resultado observado não é entrada


def _import_with_ai(client, tmp_path, phenomena):
    from backend.tests.test_ingest import FakeProvider, fetch, make_pdf, upload

    out = {"experiments": [{"label": "Run A", "description": "d", "phenomena": phenomena, "parameters": [
        {"name": "fluid_temperature", "role": "CONDICAO", "value": "25", "unit": "degrees C", "page": 1,
         "quote": "The test fluid temperature was 25 degrees C"}], "missing": []}]}
    Services.provider = FakeProvider(out)
    rec = fetch(client, upload(client, make_pdf(tmp_path / "a.pdf")))
    return rec["experiments"][0]["experiment_id"]


def test_non_fire_physics_is_unsupported_and_explained(client, tmp_path):
    eid = _import_with_ai(client, tmp_path, ["fluid_capillary"])
    c = client.get(f"/api/experiments/{eid}/compatibility").json()["data"]
    assert c["status"] == "UNSUPPORTED_PHYSICS" and c["actions"]["simulate"] is False
    assert c["actions"]["analyze"] is True
    assert any("Análise" in r for r in c["reasons_pt"])


def test_unclassified_phenomena_requires_review(client, tmp_path):
    eid = _import_with_ai(client, tmp_path, [])
    assert client.get(f"/api/experiments/{eid}/compatibility").json()["data"]["status"] == "REQUIRES_REVIEW"


def test_fire_physics_with_gaps_never_becomes_compatible(client, tmp_path):
    eid = _import_with_ai(client, tmp_path, ["flame_spread"])
    c = client.get(f"/api/experiments/{eid}/compatibility").json()["data"]
    assert c["status"] == "MISSING_PARAMETERS" and c["actions"]["simulate"] is False


# ---------------------------------------------------------------- cenários
def test_base_and_derived_scenarios_preserve_the_base(client):
    use(FakeExecutor())
    base = new_scenario(client).json()["data"]
    derived = new_scenario(client, {"hrrpua": 500, "t_end": 5}).json()["data"]
    assert base["kind"] == "BASE" and base["changes"] == []
    assert derived["kind"] == "DERIVED" and derived["status"] == "HIPOTESE_COMPUTACIONAL"
    assert {c["name"]: (c["from_value"], c["to_value"]) for c in derived["changes"]} == {
        "hrrpua": (1000.0, 500.0), "t_end": (10.0, 5.0)}
    assert derived["experiment_id"] is None and derived["scope"] == "DEMO" and "não é dado experimental" in derived["note_pt"]
    assert client.get(f"/api/scenarios/{base['scenario_id']}").json()["data"]["values"]["hrrpua"] == 1000.0


def test_scenario_validation_errors_and_unknowns(client):
    assert new_scenario(client, {"hrrpua": 99999}).status_code == 422
    assert new_scenario(client, model="nao-existe").status_code == 404
    assert new_scenario(client, experiment_id="NAO-EXISTE").status_code == 404
    assert client.post("/api/scenarios", json={"model_id": MODEL, "values": {"hrrpua": "alto"}}).status_code == 422


def test_unimplemented_reproduction_model_creates_blocked_scenario(client):
    use(FakeExecutor())
    sc = new_scenario(client, model="fds-flame-spread-thin-solid", experiment_id="BASS2-M1").json()["data"]
    assert sc["executable"] is False and sc["blocked_reasons_pt"]
    run = client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]}).json()["data"]
    assert run["state"] == "BLOCKED" and "gerador" in run["failure_reason"]


# ---------------------------------------------------------------- worker
def test_run_goes_through_states_and_is_labelled_demo(client):
    ex = use(FakeExecutor())
    sc = new_scenario(client).json()["data"]
    resp = client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]})
    assert resp.status_code == 202
    run = Services.sim().wait(resp.json()["data"]["run_id"])
    assert run["state"] == "COMPLETED" and run["demo"] is True and ex.calls
    assert run["fds_sha256"] and run["fds_version"] == "FAKE"
    stamps = run["timestamps"]
    for state in ("QUEUED", "VALIDATING", "RUNNING_FDS", "PROCESSING_RESULTS", "RENDERING", "COMPLETED"):
        assert state in stamps
    assert [a["kind"] for a in run["artifacts"]] == ["FDS_INPUT"]  # sem vídeo falso
    assert "não é reprodução" in run["label_pt"]


@pytest.mark.parametrize("state", [RunState.RUNNING_FDS, RunState.RENDERING])
def test_failure_is_explicit_and_creates_no_video(client, state):
    use(FakeExecutor(fail_at=state))
    sc = new_scenario(client).json()["data"]
    run = Services.sim().wait(client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]}).json()["data"]["run_id"])
    assert run["state"] == "FAILED" and "falha simulada" in run["failure_reason"]
    assert not any(a["kind"] == "VIDEO_MP4" for a in run["artifacts"])


def test_unavailable_executor_blocks_run(client):
    use(FakeExecutor(available=False))
    sc = new_scenario(client).json()["data"]
    run = client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]}).json()["data"]
    assert run["state"] == "BLOCKED" and "indisponível" in run["failure_reason"]
    assert client.get("/api/simulation/status").json()["data"]["available"] is False


def test_interrupted_runs_are_failed_on_restart(client):
    from backend.app import workspace
    from backend.app.simulation.service import SimulationService

    ex = FakeExecutor()
    svc = SimulationService(ex, Services.catalog(), start_worker=False)
    workspace.write_json(workspace.area("runs") / "RUN-old" / "run.json",
                         {"run_id": "RUN-old", "state": "RUNNING_FDS"})
    svc._recover()
    assert svc.get_run("RUN-old")["state"] == "FAILED"


# ---------------------------------------------------------------- segurança
def test_api_never_accepts_fds_text_or_paths(client):
    use(FakeExecutor())
    r = client.post("/api/simulations", json={"scenario_id": "SCN-x", "fds": "&HEAD CHID='x' /"})
    assert r.status_code == 422  # entradas arbitrárias são recusadas antes da resolução
    for bad in ("../x", "a/b", "..", "a b"):
        assert client.post("/api/simulations", json={"scenario_id": bad}).status_code == 422
    r = client.post("/api/scenarios", json={"model_id": MODEL, "values": {"fds_text": 1}})
    assert r.status_code == 422


def test_artifact_download_only_for_listed_artifacts_of_completed_runs(client):
    use(FakeExecutor())
    sc = new_scenario(client).json()["data"]
    run = Services.sim().wait(client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]}).json()["data"]["run_id"])
    rid = run["run_id"]
    name = run["artifacts"][0]["name"]
    assert client.get(f"/api/simulations/{rid}/artifacts/{name}").status_code == 200
    for other in ("run.json", "..%2Frun.json", "result.mp4", "nao_existe.txt"):
        assert client.get(f"/api/simulations/{rid}/artifacts/{other}").status_code in (404, 422)


def test_old_policy_replaced_but_unknown_ids_are_404(client):
    use(FakeExecutor())
    assert client.get("/api/simulations/RUN-nope").status_code == 404
    assert client.get("/api/simulation/models").json()["data"][0]["model_id"] == MODEL
