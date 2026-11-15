"""Jornada v2.1: experimentos NASA × demonstração FDS, cenários de hipótese, lotes de extração,
resumo da análise, tempos e progresso de execução, renderização em tempo real. Tudo simulado/fixture."""

import time

import pytest
from fastapi.testclient import TestClient

from backend.app import workspace
from backend.app.api.platform import Services
from backend.app.assistant.provider import ProviderError, ProviderErrorKind
from backend.app.ingest import extraction
from backend.app.main import app
from backend.app.simulation.case_builder import FRAMES_PER_SIMULATED_SECOND, build_case, frame_count
from backend.app.simulation.executor import SMV_FRAME_STEP, VIDEO_FPS, FakeExecutor
from backend.app.simulation.registry import INTEGRATION
from backend.tests.test_ingest import FakeProvider, fetch, make_pdf, upload

M1 = "BASS2-M1"


@pytest.fixture
def client():
    return TestClient(app)


# ================================================================ experimento NASA × demonstração FDS
def exp_scenario(client, exp=M1, changes=None, **kw):
    return client.post(f"/api/experiments/{exp}/scenarios", json={"changes": changes or [], **kw})


def test_editable_conditions_exclude_observed_results_and_metadata(client):
    c = client.get(f"/api/experiments/{M1}/compatibility").json()["data"]
    names = {e["parameter"] for e in c["editable"]}
    assert {"thickness", "width", "airflow_velocity", "o2_initial"} <= names
    assert not names & {"flame_spread_rate", "burn_duration", "o2_final", "material"}
    one = next(e for e in c["editable"] if e["parameter"] == "airflow_velocity")
    assert one["unit"] == "cm/s" and one["value"] == 9
    assert one["status"] == Services.store().records[f"{M1}.airflow_velocity"].status
    assert one["rule_pt"] and one["source_pt"]


def test_hypothesis_scenario_preserves_original_and_is_not_executable(client):
    original = client.get(f"/api/experiments/{M1}").json()["data"]["parameters"]
    base_status = next(p["status"] for p in original if p["parameter"] == "airflow_velocity")
    r = exp_scenario(client, changes=[{"parameter": "airflow_velocity", "value": 12}], hypothesis="Fluxo maior")
    assert r.status_code == 201
    sc = r.json()["data"]
    assert sc["scope"] == "EXPERIMENT" and sc["kind"] == "DERIVED" and sc["experiment_id"] == M1
    assert sc["status"] == "HIPOTESE_COMPUTACIONAL" and sc["hypothesis_pt"] == "Fluxo maior"
    ch = sc["changes"][0]
    assert (ch["from_value"], ch["to_value"], ch["unit"], ch["base_status"]) == (9.0, 12.0, "cm/s", base_status)
    assert sc["executable"] is False and sc["blocked_reasons_pt"]
    exp = client.get(f"/api/experiments/{M1}").json()["data"]
    assert exp["parameters"] == original
    assert next(p for p in exp["parameters"] if p["parameter"] == "airflow_velocity")["original"]["value"] == 9
    run = client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]}).json()["data"]
    assert run["state"] == "BLOCKED" and run["failure_reason"]  # nada é simulado em silêncio


@pytest.mark.parametrize("change,fragment", [
    ({"parameter": "flame_spread_rate", "value": 1}, "resultado observado"),
    ({"parameter": "burn_duration", "value": 1}, "resultado observado"),
    ({"parameter": "material", "value": 1}, "não é uma condição numérica"),
    ({"parameter": "airflow_velocity", "value": -3}, "fora da faixa"),
    ({"parameter": "airflow_velocity", "value": 0}, "fora da faixa"),
    ({"parameter": "o2_initial", "value": 150}, "fora da faixa"),
    ({"parameter": "airflow_velocity", "value": 9}, "nenhuma alteração"),
    ({"parameter": "nao_existe", "value": 1}, "inexistente"),
])
def test_invalid_hypothesis_changes_are_refused(client, change, fragment):
    r = exp_scenario(client, changes=[change])
    assert r.status_code == 422 and fragment in r.json()["error"]["message"]


def test_valid_oxygen_change_uses_percent_rule(client):
    r = exp_scenario(client, changes=[{"parameter": "o2_initial", "value": 18.5}])
    assert r.status_code == 201 and r.json()["data"]["changes"][0]["unit"].lower().startswith("vol")


def test_generic_demo_is_never_linked_to_a_nasa_experiment(client):
    Services.executor = FakeExecutor()
    r = client.post("/api/scenarios", json={"model_id": INTEGRATION.model_id, "values": {}, "experiment_id": M1})
    assert r.status_code == 422 and "independente" in r.json()["error"]["message"]
    ok = client.post("/api/scenarios", json={"model_id": INTEGRATION.model_id, "values": {"hrrpua": 500}})
    sc = ok.json()["data"]
    assert sc["scope"] == "DEMO" and sc["experiment_id"] is None and sc["executable"] is True
    run = Services.sim().wait(client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]}).json()["data"]["run_id"])
    assert run["scope"] == "DEMO"


def test_reference_experiment_simulation_stays_blocked_with_reasons(client):
    c = client.get(f"/api/experiments/{M1}/compatibility").json()["data"]
    assert c["actions"]["simulate"] is False and c["status"] == "MISSING_PARAMETERS"
    assert any("lacuna" in r.lower() or "faltam" in r.lower() for r in c["reasons_pt"])


# ================================================================ lotes de extração e cobertura
class SeqProvider:
    name, model = "fake", "fake-model"

    def __init__(self, outputs):
        self.outputs, self.calls = list(outputs), []

    def generate_json(self, system, user, schema, timeout):
        self.calls.append(user)
        item = self.outputs.pop(0)
        if isinstance(item, ProviderErrorKind):
            raise ProviderError(item)
        return schema.model_validate(item)

    def last_usage(self):
        return {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}


def pages_30():
    return {n: f"Page {n} text. The cell width was {n} mm in this section." for n in range(1, 31)}


def out(label, pn, name="cell_width"):
    return {"experiments": [{"label": label, "description": "d", "phenomena": ["fluid_flow"], "missing": [],
                             "parameters": [{"name": name, "role": "CONDICAO", "value": str(pn), "unit": "mm", "page": pn,
                                             "quote": f"The cell width was {pn} mm"}]}]}


def test_plan_batches_covers_every_page_with_text_in_order():
    pages = pages_30()
    pages[5] = "   "  # página sem texto (figura)
    batches, empty = extraction.plan_batches(pages)
    assert empty == [5] and [n for b in batches for n in b] == [n for n in range(1, 31) if n != 5]
    assert all(len(b) <= extraction.BATCH_MAX_PAGES for b in batches) and len(batches) == 3


def test_batched_extraction_full_coverage_keeps_real_page_numbers_and_merges_experiments():
    prov = SeqProvider([out("Run A", 3), out("run a", 15, "other_width"), out("Run B", 27, "third")])
    r = extraction.run_batched(prov, pages_30(), "DOC-X", "2026-11-14T00:00:00Z")
    cov = r["coverage"]
    assert cov["mode"] == "AI_FULL" and cov["processed_ranges"] == "1–30" and cov["pages_not_processed"] == []
    labels = [e["label"] for e in r["experiments"]]
    assert labels == ["Run A", "Run B"]  # "run a" foi fundido ao experimento já existente
    run_a = r["experiments"][0]
    assert [p["evidence"][0]["page_pdf"] for p in run_a["parameters"]] == [3, 15]
    assert [p["record_id"] for p in run_a["parameters"]] == ["DOC-X-E1.cell_width", "DOC-X-E1.other_width"]
    assert len(r["batches"]) == 3 and r["batches"][0]["usage"]["total_tokens"] == 110
    assert "Run A" in prov.calls[1] and "Lote 2 de 3" in prov.calls[1]  # rótulos já vistos são informados


def test_batch_cap_leaves_explicit_partial_coverage():
    r = extraction.run_batched(SeqProvider([out("Run A", 3)]), pages_30(), "DOC-X", "t", max_batches=1)
    cov = r["coverage"]
    assert cov["mode"] == "AI_PARTIAL" and cov["processed_ranges"] == "1–12" and cov["not_processed_ranges"] == "13–30"
    assert any("limite" in x for x in cov["reasons_pt"]) and r["batches_planned_total"] == 3


def test_failed_batch_is_not_counted_as_read_and_others_continue():
    r = extraction.run_batched(SeqProvider([out("Run A", 3), ProviderErrorKind.UNAVAILABLE, out("Run A", 27, "z")]),
                               pages_30(), "DOC-X", "t")
    cov = r["coverage"]
    assert cov["mode"] == "AI_PARTIAL" and cov["not_processed_ranges"] == "13–24"
    assert r["batches"][1]["error"] == "UNAVAILABLE"


def test_auth_error_aborts_and_marks_remaining_pages_unread():
    r = extraction.run_batched(SeqProvider([ProviderErrorKind.AUTH]), pages_30(), "DOC-X", "t")
    assert r["coverage"]["mode"] == "NONE" and r["coverage"]["not_processed_ranges"] == "1–30" and r["experiments"] == []


def test_citation_from_another_batch_is_rejected():
    bad = out("Run A", 20)  # página 20 não está no lote 1 (1–12)
    r = extraction.run_batched(SeqProvider([bad]), pages_30(), "DOC-X", "t", max_batches=1)
    assert r["experiments"][0]["parameters"] == [] and r["rejected"][0]["reason"] == "PAGE_NOT_PROVIDED"


def pdf_out():
    """Saída coerente com o texto de make_pdf (a citação precisa ser literal)."""
    return {"experiments": [{"label": "Run A", "description": "d", "phenomena": ["fluid_flow"], "missing": [],
                             "parameters": [{"name": "fluid_temperature", "role": "CONDICAO", "value": "25",
                                             "unit": "degrees C", "page": 1,
                                             "quote": "The test fluid temperature was 25 degrees C"}]}]}


def test_import_exposes_coverage_and_batches(client, tmp_path):
    Services.provider = FakeProvider(pdf_out())
    rec = fetch(client, upload(client, make_pdf(tmp_path / "a.pdf")))
    cov = rec["coverage"]
    assert cov["mode"] == "AI_FULL" and cov["processed_ranges"] == "1" and cov["total_pages"] == 1
    step = next(s for s in rec["steps"] if s["key"] == "EXTRACT")
    assert step["state"] == "DONE" and any("lote 1" in t for t in step["technical"])


# ================================================================ etapas, tempos e resumo
def test_import_steps_are_readable_and_timed(client, tmp_path):
    rec = fetch(client, upload(client, make_pdf(tmp_path / "a.pdf")))
    keys = [s["key"] for s in rec["steps"]]
    assert keys == ["RECEIVE", "IDENTIFY", "ORIGIN", "READ", "EXTRACT", "SOURCES", "COMPARE", "REPORT"]
    assert [s["label_pt"] for s in rec["steps"]][:3] == ["Arquivo recebido", "Identificando o documento",
                                                         "Verificando a origem NASA"]
    for s in rec["steps"]:
        assert s["state"] in ("DONE", "SKIPPED") and isinstance(s["duration_ms"], int) and s["summary_pt"]
        assert isinstance(s["technical"], list)
    assert rec["metrics"]["total_ms"] >= 0 and set(rec["metrics"]["per_step_ms"]) == set(keys)
    assert next(s for s in rec["steps"] if s["key"] == "EXTRACT")["state"] == "SKIPPED"  # IA desligada


def test_analysis_summary_for_imported_document(client, tmp_path):
    Services.provider = FakeProvider(pdf_out())
    rec = fetch(client, upload(client, make_pdf(tmp_path / "a.pdf")))
    a = client.get(f"/api/documents/{rec['document']['document_id']}/analysis").json()["data"]
    assert a["totals"]["experiments"] == 1 and a["totals"]["parameters"] == 1 and a["totals"]["reviewed"] == 0
    assert a["provenance"]["state"] in ("CANDIDATE", "VERIFIED", "PENDING")
    assert a["coverage"]["mode"] == "AI_FULL" and a["experiments"][0]["fds"]["can_simulate"] is False
    assert any("conferido" in s and "pessoa" in s for s in a["conclusions_pt"])
    assert any("Procedência verificada não significa números conferidos" in s for s in a["not_validated_pt"])
    assert a["steps"] and a["metrics"]["total_ms"] is not None


def test_analysis_summary_for_reference_document(client):
    reviewed = sum(r.status in ("CONFERIDO_FONTE", "APROVADO_MODELO") for r in Services.store().records_for(M1))
    a = client.get("/api/documents/NASA-TM-20210011385/analysis").json()["data"]
    assert a["coverage"]["mode"] == "CURATED" and "dataset curado" in a["coverage"]["summary_pt"]
    assert a["totals"]["parameters"] == 9 and a["totals"]["reviewed"] == reviewed and a["totals"]["gaps"] == 12
    assert a["experiments"][0]["fds"]["status"] == "MISSING_PARAMETERS" and a["experiments"][0]["fds"]["can_simulate"] is False
    assert not any("promov" in s for s in a["conclusions_pt"])
    assert client.get("/api/documents/DOC-nao-existe/analysis").status_code == 404


# ================================================================ tempos e progresso da execução
def test_run_records_timings_and_progress_is_none_when_not_running(client):
    Services.executor = FakeExecutor()
    sc = client.post("/api/scenarios", json={"model_id": INTEGRATION.model_id, "values": {}}).json()["data"]
    run = Services.sim().wait(client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]}).json()["data"]["run_id"])
    t = run["timings_ms"]
    assert run["state"] == "COMPLETED" and t["queue_wait"] >= 0 and t["preparation"] >= 0 and t["total"] >= 0
    assert run["progress"] is None


def test_running_run_reports_real_fds_progress_from_its_log(client):
    Services.executor = FakeExecutor()
    sim = Services.sim()
    sc = client.post("/api/scenarios", json={"model_id": INTEGRATION.model_id, "values": {"t_end": 20}}).json()["data"]
    rid = "RUN-progress-test"
    workspace.write_json(workspace.area("runs") / rid / "run.json",
                         {"run_id": rid, "scenario_id": sc["scenario_id"], "state": "RUNNING_FDS",
                          "parameters": {"t_end": 20.0}})
    (workspace.area("runs") / rid / "fds.log").write_text(
        " Time Step:    100, Simulation Time:  4.75000 s\n Time Step:    200, Simulation Time:  5.00000 s\n", encoding="utf-8")
    p = sim.get_run(rid)["progress"]
    assert p["simulated_time_s"] == 5.0 and p["t_end_s"] == 20.0 and p["fraction"] == 0.25
    (workspace.area("runs") / rid / "fds.log").write_text("sem linhas de tempo", encoding="utf-8")
    assert sim.get_run(rid)["progress"] is None  # sem informação confiável → sem progresso (indeterminado)


def test_failure_after_start_still_records_total_time(client):
    from backend.app.simulation.models import RunState

    Services.executor = FakeExecutor(fail_at=RunState.RENDERING)
    sc = client.post("/api/scenarios", json={"model_id": INTEGRATION.model_id, "values": {}}).json()["data"]
    run = Services.sim().wait(client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]}).json()["data"]["run_id"])
    assert run["state"] == "FAILED" and run["timings_ms"]["total"] >= 0


# ================================================================ renderização em tempo real (sem quadros inventados)
def test_video_is_real_time_one_frame_per_tenth_of_simulated_second():
    assert FRAMES_PER_SIMULATED_SECOND == VIDEO_FPS == 10 and SMV_FRAME_STEP == 1
    assert frame_count(10) == 100 and frame_count(5) == 50 and frame_count(60) == 600
    text, _ = build_case(INTEGRATION, {"t_end": 10}, "fl_x")
    assert "NFRAMES=100" in text and "T_END=10." in text
    # vídeo de N quadros a 10 fps dura N/10 s = t_end: 1 s de vídeo = 1 s de tempo físico (1x)
    assert frame_count(10) / VIDEO_FPS == 10.0


def test_artifacts_support_range_requests_for_video_seeking(client):
    Services.executor = FakeExecutor()
    sc = client.post("/api/scenarios", json={"model_id": INTEGRATION.model_id, "values": {}}).json()["data"]
    run = Services.sim().wait(client.post("/api/simulations", json={"scenario_id": sc["scenario_id"]}).json()["data"]["run_id"])
    name = run["artifacts"][0]["name"]
    r = client.get(f"/api/simulations/{run['run_id']}/artifacts/{name}", headers={"Range": "bytes=0-9"})
    assert r.status_code == 206 and len(r.content) == 10 and r.headers["accept-ranges"] == "bytes"


def test_quota_limit_waits_and_retries_the_same_batch_once():
    waits = []
    prov = SeqProvider([ProviderErrorKind.QUOTA, out("Run A", 3), out("Run A", 15, "b"), out("Run A", 27, "c")])
    r = extraction.run_batched(prov, pages_30(), "DOC-X", "t", quota_wait_s=7, sleep=waits.append,
                               on_wait=lambda i, s: waits.append(("wait", i, s)))
    assert r["coverage"]["mode"] == "AI_FULL" and r["batches"][0]["waited_s"] == 7.0
    assert ("wait", 1, 7) in waits and 7 in waits


def test_quota_twice_aborts_and_marks_the_rest_as_not_read():
    prov = SeqProvider([out("Run A", 3), ProviderErrorKind.QUOTA, ProviderErrorKind.QUOTA])
    r = extraction.run_batched(prov, pages_30(), "DOC-X", "t", quota_wait_s=1, sleep=lambda s: None)
    cov = r["coverage"]
    assert cov["mode"] == "AI_PARTIAL" and cov["processed_ranges"] == "1–12" and cov["not_processed_ranges"] == "13–30"
    assert any("QUOTA" in x for x in cov["reasons_pt"])


def test_step_timer_is_not_reset_by_progress_updates():
    """Regressão: 'Lote i de n' atualiza o resumo da etapa em andamento sem reiniciar o cronômetro."""
    from backend.app.ingest.service import STEPS, ImportService

    svc = ImportService(lambda: None, lambda: None, None, run_async=False)
    rec = {"import_id": "IMP-timer", "steps": [{"key": k, "label_pt": l, "state": "PENDING", "summary_pt": None,
                                                 "technical": [], "limitation_pt": None, "started_at": None,
                                                 "finished_at": None, "duration_ms": None} for k, l in STEPS]}
    svc._step(rec, "EXTRACT", "RUNNING", "início")
    first_start = rec["steps"][4]["started_at"]
    time.sleep(0.06)
    svc._step(rec, "EXTRACT", "RUNNING", "Lote 2 de 3")
    time.sleep(0.06)
    svc._step(rec, "EXTRACT", "DONE", "fim")
    step = rec["steps"][4]
    assert step["started_at"] == first_start and step["duration_ms"] >= 110
