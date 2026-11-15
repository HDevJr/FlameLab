"""Auditoria de integridade científica (v2.3): grandeza × unidade × condição × interpretação × revisão.

Parte dos casos vem do artigo DYLCO IML-2 realmente importado (trechos e unidades reais), em que o revisor
viu valores de temperatura e ângulo SEM unidade e um conjunto de 14 registros conferidos com ressalvas.
"""

import json

import pytest
from fastapi.testclient import TestClient

from backend.app import units, workspace
from backend.app.api.platform import Services
from backend.app.dataset.review import ReviewRejected, scientific_gate
from backend.app.gap_decisions import relations
from backend.app.ingest import extraction
from backend.app.integrity import assess, condition_candidates, expected_dimension, unit_in_quotes, unit_info
from backend.app.main import app
from backend.app.review_service import append_event
from backend.tests.test_ingest import FakeProvider, fetch, make_pdf, upload

DEG_C, DEG = "°C", "°"
Q_CYCLE = "The temperature was then cycled from 20 to 80 °C in increments of 20 °C."
Q_PEAK = "Though the originally planned peak temperature was 80 °C, the system temperature was further increased to 95 °C."
Q_ANGLE = "The uncoated cells show a contact angle of approximately 19 ° with the liquid used."
Q_EQUIL = "ALL CONTACT ANGLE MEASUREMENTS ARE ACCURATE TO +2* WITH REPEATABILITY. EQUILIBRIUM CONTACT ANGLES ARE 70 ° AT 20 °C AND 65 ° AT 100 °C"
Q_LIST = "(b) During heating up to 40, 60, 80, 90 and even 95 °C."
Q_DIHEDRAL = "(a) Filling of the right-hand cells with dihedral angles 2a = 65 ° (left) and 2a = 60 ° (right)."


def a(parameter, value, unit, quotes, role="CONDICAO", condition=None, review=None, method="LLM"):
    return assess(parameter=parameter, role=role, original={"value": value, "unit": unit}, quotes=quotes, method=method,
                  condition=condition, review=review)


def codes(r):
    return {f["code"] for f in r["findings"]}


# ================================================================ Tarefa 2 — grandezas e unidades
def test_temperature_in_celsius_is_a_physical_quantity_with_unit_in_the_evidence():
    r = a("peak_temperature_planned", 80.0, DEG_C, [Q_PEAK])
    assert r["unit_info"]["state"] == "PHYSICAL" and r["unit_info"]["display"] == DEG_C and r["unit_info"]["dimension"] == "temperature"
    assert r["unit_source"] == "QUOTE" and r["status"] == "OK" and r["pdf_value"]["literal"] == "80"
    assert units.normalize(80.0, DEG_C).value == pytest.approx(353.15)


def test_shared_unit_in_a_range_and_in_a_list_is_supported_by_the_quote():
    assert unit_in_quotes(20.0, "degC", [Q_CYCLE])["source"] == "QUOTE"  # "from 20 to 80 °C"
    assert unit_in_quotes(40.0, "degC", [Q_LIST])["source"] == "QUOTE"  # "40, 60, 80, 90 and even 95 °C"
    assert unit_in_quotes(95.0, "degC", [Q_LIST])["source"] == "QUOTE"


@pytest.mark.parametrize("unit", [DEG, "deg", "degrees", "º", "graus"])
def test_angles_in_degrees_are_recognised_in_every_spelling(unit):
    r = a("uncoated_cells_contact_angle", 19.0, unit, [Q_ANGLE])
    assert r["unit_info"]["state"] == "PHYSICAL" and r["unit_info"]["dimension"] == "angle" and r["unit_info"]["display"] == DEG
    assert r["status"] == "OK" and r["unit_source"] == "QUOTE"


def test_angle_does_not_become_celsius_when_a_word_starting_with_c_follows():
    q = "contact angle of 19 ° CELLS were filled"  # "° C" + "ELLS" não é °C
    assert unit_in_quotes(19.0, "deg", [q])["source"] == "QUOTE"
    assert unit_in_quotes(19.0, "degC", [q])["source"] == "NOT_FOUND"


def test_refractive_index_is_dimensionless_not_missing():
    r = a("refractive_index", 1.4587, None, ["INDEX OF REFRACTION MATCHED N = 1.4587 AT 25 °C"], role="METADADO")
    assert r["unit_info"]["state"] == "DIMENSIONLESS" and r["unit_info"]["expected_dimension"] == "dimensionless"
    assert "UNIT_MISSING_FOR_QUANTITY" not in codes(r)
    assert a("refractive_index", 1.4587, "none", [], role="METADADO")["unit_info"]["state"] == "DIMENSIONLESS"


def test_dimensionless_quantity_with_a_physical_unit_is_inconsistent():
    r = a("refractive_index", 1.4587, DEG_C, ["N = 1.4587 AT 25 °C"], role="METADADO")
    assert "UNIT_DIMENSION_MISMATCH" in codes(r) and r["status"] == "INCONSISTENT"


def test_physical_quantity_without_unit_is_flagged_not_silently_dimensionless():
    for unit in (None, "", "none"):
        r = a("initial_temperature", 20.0, unit, [Q_CYCLE])
        assert r["unit_info"]["state"] == "MISSING" and "UNIT_MISSING_FOR_QUANTITY" in codes(r) and r["status"] == "INCONSISTENT"
    r = a("test_fluid_code", 50350.0, "none", ["code 50350"], role="METADADO")
    assert r["unit_info"]["state"] == "DIMENSIONLESS" and codes(r) == {"IDENTIFIER_AS_NUMBER"} and r["status"] == "ATTENTION"


def test_text_values_have_no_unit_to_check():
    r = assess(parameter="surface_modifier", role="METADADO", original={"value": "FC-724", "unit": "none"}, quotes=["coated with FC-724"],
               method="LLM", condition=None, review=None)
    assert r["unit_info"]["state"] == "NOT_APPLICABLE" and r["findings"] == []


def test_unknown_numeric_quantity_without_unit_is_not_assumed_dimensionless():
    r = a("unclassified_measurement", 3.0, None, ["measurement 3"])
    assert r["unit_info"]["state"] == "MISSING" and r["status"] == "ATTENTION"
    assert "UNIT_UNCLASSIFIED" in codes(r)
    assert a("burning_faces", 1.0, None, [], method="MANUAL_TRANSCRIPTION")["unit_info"]["state"] == "DIMENSIONLESS"
    assert unit_info("x", {"value": 1, "unit": "adimensional"})["state"] == "DIMENSIONLESS"


def test_incompatible_unit_for_the_quantity_the_real_gemini_case():
    # extração real (15/11): equilibrium_contact_angle = 70.0 °C — um ângulo com unidade de temperatura
    r = a("equilibrium_contact_angle", 70.0, DEG_C, ["EQUILIBRIUM CONTACT ANGLES ARE 70 ° AT 20 °C"])
    f = next(x for x in r["findings"] if x["code"] == "UNIT_DIMENSION_MISMATCH")
    assert f["severity"] == "BLOCKING" and "ângulo" in f["detail_pt"] and "temperatura" in f["detail_pt"]


def test_unsupported_unit_is_reported_and_blocks():
    r = a("contact_angle", 5.0, "furlong", ["5 furlong"])
    assert r["unit_info"]["state"] == "UNSUPPORTED" and "UNIT_UNSUPPORTED" in codes(r)


def test_unit_inferred_by_the_ai_but_absent_from_the_quote_is_flagged():
    r = a("airflow_velocity", 9.0, "cm/s", ["the sample was tested at 9 in the duct"])
    assert "UNIT_NOT_IN_EVIDENCE" in codes(r) and r["unit_source"] == "NOT_FOUND"
    assert "UNIT_NOT_IN_EVIDENCE" not in codes(a("airflow_velocity", 9.0, "cm/s", ["the flow was 9 cm/s"]))


def test_unreadable_symbol_instead_of_the_unit_blocks_until_a_human_confirms_it_in_the_pdf():
    r = a("contact_angle_accuracy", 2.0, "deg", [Q_EQUIL])
    assert r["unit_source"] == "SYMBOL_UNREADABLE" and "UNIT_SYMBOL_UNREADABLE" in codes(r)
    ok = a("contact_angle_accuracy", 2.0, "deg", [Q_EQUIL], review={"components": {"unit_verified_in_pdf": True}})
    assert "UNIT_SYMBOL_UNREADABLE" not in codes(ok)


def test_curated_table_records_are_not_checked_against_free_text():
    r = a("airflow_velocity", 9.0, "cm/s", ["Table 5.1 | row M1 | 9"], method="ASSISTED_TEXT_LAYER")
    assert "UNIT_NOT_IN_EVIDENCE" not in codes(r) and r["unit_source"] == "NOT_CHECKED"


def test_expected_dimension_comes_from_the_parameter_name_only_when_unambiguous():
    assert expected_dimension("uncoated_cells_contact_angle") == "angle"
    assert expected_dimension("contact_angle_accuracy") == "angle"
    assert expected_dimension("peak_temperature_planned") == "temperature"
    assert expected_dimension("flame_spread_rate") is None
    assert expected_dimension("angle_of_temperature") is None  # duas grandezas: ambíguo, não adivinha
    assert unit_info("x", {"value": 1.0, "unit": "mm"})["state"] == "PHYSICAL"


# ================================================================ condições de referência
def test_value_tied_to_a_reference_condition_is_detected_with_its_unit():
    c = condition_candidates(70.0, [Q_EQUIL])
    assert c == [{"text": "AT 20 °C", "value": 20.0, "unit": DEG_C, "dimension": "temperature"}]
    assert condition_candidates(65.0, [Q_EQUIL])[0]["value"] == 100.0
    assert condition_candidates(19.0, [Q_ANGLE]) == []


def test_unrecorded_condition_blocks_and_recording_it_resolves():
    r = a("equilibrium_contact_angle", 70.0, DEG, [Q_EQUIL])
    f = next(x for x in r["findings"] if x["code"] == "CONDITION_NOT_RECORDED")
    assert f["severity"] == "BLOCKING" and "AT 20" in f["detail_pt"]
    ok = a("equilibrium_contact_angle", 70.0, DEG, [Q_EQUIL], condition={"text": "a 20 °C", "value": 20.0, "unit": DEG_C})
    assert "CONDITION_NOT_RECORDED" not in codes(ok)


@pytest.mark.parametrize("condition", [
    {"text": "a 100 °C", "value": 100.0, "unit": DEG_C},
    {"text": "a 20 graus", "value": 20.0, "unit": DEG},
    {"text": "condição verificada", "value": None, "unit": None},
])
def test_unrelated_condition_cannot_bypass_the_scientific_gate(condition):
    r = a("equilibrium_contact_angle", 70.0, DEG, [Q_EQUIL], condition=condition)
    assert "CONDITION_MISMATCH" in codes(r) and r["status"] == "INCONSISTENT"


def test_reference_condition_accepts_physical_equivalence_in_kelvin():
    r = a("equilibrium_contact_angle", 70.0, DEG, [Q_EQUIL], condition={"text": "a 293.15 K", "value": 293.15, "unit": "K"})
    assert r["status"] == "OK"


def test_the_parameter_that_IS_the_condition_is_not_flagged():
    assert "CONDITION_NOT_RECORDED" not in codes(a("temperature", 20.0, DEG_C, ["a value of 20 °C at 25 °C"]))


def test_extraction_condition_must_be_literal_in_the_quote():
    out = extraction.ExtractionOutput.model_validate({"experiments": [{"label": "R", "description": "d", "phenomena": [], "missing": [], "parameters": [
        {"name": "equilibrium_contact_angle", "role": "CONDICAO", "value": "70", "unit": DEG, "page": 1, "quote": "EQUILIBRIUM CONTACT ANGLES ARE 70 ° AT 20 °C",
         "condition": {"text": "AT 20 °C", "value": "20", "unit": DEG_C}},
        {"name": "other_angle", "role": "CONDICAO", "value": "70", "unit": DEG, "page": 1, "quote": "EQUILIBRIUM CONTACT ANGLES ARE 70 ° AT 20 °C",
         "condition": {"text": "AT 500 °C", "value": "500", "unit": DEG_C}}]}]})
    exps, rejected = extraction.validate(out, {1: "x EQUILIBRIUM CONTACT ANGLES ARE 70 ° AT 20 °C y"}, "DOC", "m", "2026-11-15T00:00:00Z")
    p = {x["parameter"]: x for x in exps[0]["parameters"]}
    assert p["equilibrium_contact_angle"]["condition"]["value"] == 20.0 and p["equilibrium_contact_angle"]["condition"]["source"] == "IA"
    assert p["other_angle"]["condition"] is None and rejected[0]["reason"] == "CONDITION_NOT_LITERAL"


# ================================================================ Tarefa 3 — número ≠ interpretação
def gate(**kw):
    base = dict(parameter="initial_temperature", label="Temperatura inicial", label_source="GLOSSARIO", role="CONDICAO",
                original={"value": 20.0, "unit": DEG_C}, quotes=[Q_CYCLE], method="LLM", condition=None, interpretation_confirmed=True)
    base.update(kw)
    scientific_gate(**base)


def test_gate_blocks_the_cycle_range_read_as_initial_temperature_even_with_the_number_and_unit_right():
    with pytest.raises(ReviewRejected) as exc:
        gate()
    assert exc.value.code == "SEMANTIC_AMBIGUITY" and exc.value.details["semantic_flags"][0]["code"] == "INITIAL_FROM_RANGE"


def test_gate_requires_the_interpretation_to_be_confirmed_explicitly():
    with pytest.raises(ReviewRejected) as exc:
        gate(parameter="peak_temperature_planned", label="Temperatura de pico planejada", original={"value": 80.0, "unit": DEG_C},
             quotes=[Q_PEAK], interpretation_confirmed=False)
    assert exc.value.code == "INTERPRETATION_NOT_CONFIRMED" and "sozinha" in str(exc.value)
    gate(parameter="peak_temperature_planned", label="Temperatura de pico planejada", original={"value": 80.0, "unit": DEG_C}, quotes=[Q_PEAK])


def test_gate_reports_integrity_before_semantics():
    with pytest.raises(ReviewRejected) as exc:
        gate(original={"value": 20.0, "unit": None})
    assert exc.value.code == "INTEGRITY_INCONSISTENT" and exc.value.details["integrity_findings"][0]["code"] == "UNIT_MISSING_FOR_QUANTITY"


def test_gate_accepts_clean_curated_table_records_once_interpretation_is_confirmed():
    from backend.app.dataset.store import DatasetStore

    store = DatasetStore.load()
    for r in store.records_for("BASS2-M1"):
        evs = [store.evidence[e] for e in r.evidence_ids]
        scientific_gate(parameter=r.parameter, label=r.label_pt, label_source="CURADORIA", role=r.role,
                        original={"value": r.original.value, "unit": r.original.unit}, quotes=[e.quote for e in evs if e.quote],
                        method=r.extraction.method, condition=None, interpretation_confirmed=True)


# ================================================================ API: fluxo completo com os trechos reais
BODY = {"action": "CONFIRM", "reviewer": "Ana Souza", "observed_page_pdf": 1, "checked_pdf": True, "interpretation_confirmed": True}


@pytest.fixture
def client(tmp_path):
    from backend.tests.dataset_fixtures import write_dataset

    Services.dataset_dirs = (write_dataset(tmp_path), tmp_path)
    return TestClient(app)


def _pdf_body(*quotes):
    return " ".join(quotes)


def _import(client, tmp_path, params, missing=None, phenomena=None, body=None):
    out = {"experiments": [{"label": "Run A", "description": "d", "phenomena": phenomena or ["fluid_flow"],
                            "parameters": params, "missing": missing or []}]}
    Services.provider = FakeProvider(out)
    rec = fetch(client, upload(client, make_pdf(tmp_path / "a.pdf", body=body or _pdf_body(Q_PEAK, Q_ANGLE))))
    return rec, {p["parameter"]: p["record_id"] for p in rec["experiments"][0]["parameters"]}


def P(name, value, unit, quote, role="CONDICAO", **extra):
    return {"name": name, "role": role, "value": value, "unit": unit, "page": 1, "quote": quote, **extra}


PEAK = P("peak_temperature_planned", "80", DEG_C, "planned peak temperature was 80 " + DEG_C)
ANGLE = P("uncoated_cells_contact_angle", "19", DEG, "contact angle of approximately 19 " + DEG)


def test_api_exposes_unit_state_integrity_and_review_scope_separately(client, tmp_path):
    rec, ids = _import(client, tmp_path, [PEAK, ANGLE])
    exp = client.get(f"/api/experiments/{rec['experiments'][0]['experiment_id']}").json()["data"]
    by = {p["parameter"]: p for p in exp["parameters"]}
    t, ang = by["peak_temperature_planned"], by["uncoated_cells_contact_angle"]
    assert t["unit_info"]["state"] == "PHYSICAL" and t["unit_info"]["display"] == DEG_C and t["unit_info"]["dimension_pt"] == "temperatura"
    assert ang["unit_info"]["display"] == DEG and ang["unit_info"]["dimension_pt"] == "ângulo"
    assert t["integrity"]["pdf_value"]["literal"] == "80" and t["integrity"]["status"] == "OK" and t["review_scope"] is None
    assert t["original"]["value"] == 80.0 and t["original"]["unit"] == DEG_C  # valor e unidade nunca se misturam


def test_confirmation_covers_number_unit_and_interpretation_and_records_exactly_that(client, tmp_path):
    rec, ids = _import(client, tmp_path, [PEAK])
    rid = ids["peak_temperature_planned"]
    no = client.post(f"/api/records/{rid}/review", json={**BODY, "observed_value": "80", "observed_unit": DEG_C, "interpretation_confirmed": False})
    assert no.status_code == 422 and no.json()["error"]["code"] == "INTERPRETATION_NOT_CONFIRMED"
    ok = client.post(f"/api/records/{rid}/review", json={**BODY, "observed_value": "80", "observed_unit": DEG_C})
    assert ok.status_code == 200
    p = client.get(f"/api/experiments/{rec['experiments'][0]['experiment_id']}").json()["data"]["parameters"][0]
    assert p["review"]["components"] == {"number": True, "unit": True, "interpretation": True, "condition": None,
                                         "unit_verified_in_pdf": False, "prefilled_unchanged": False}
    assert p["review_scope"] == "FULL"
    ev = client.get(f"/api/records/{rid}/events").json()["data"][-1]
    assert ev["outcome"] == "APPROVED" and ev["observed_value"] == "80" and ev["observed_unit"] == DEG_C and ev["interpretation_confirmed"] is True


def test_unreadable_unit_symbol_needs_an_explicit_unit_verification(client, tmp_path):
    acc = P("contact_angle_accuracy", "2", "deg", "ALL CONTACT ANGLE MEASUREMENTS ARE ACCURATE TO +2* WITH REPEATABILITY", role="METADADO")
    rec, ids = _import(client, tmp_path, [acc], body="ALL CONTACT ANGLE MEASUREMENTS ARE ACCURATE TO +2* WITH REPEATABILITY")
    rid = ids["contact_angle_accuracy"]
    body = {**BODY, "observed_value": "2", "observed_unit": "deg"}
    r = client.post(f"/api/records/{rid}/review", json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "INTEGRITY_INCONSISTENT"
    assert r.json()["error"]["details"]["integrity_findings"][0]["code"] == "UNIT_SYMBOL_UNREADABLE"
    ok = client.post(f"/api/records/{rid}/review", json={**body, "unit_verified_in_pdf": True})
    assert ok.status_code == 200
    p = client.get(f"/api/experiments/{rec['experiments'][0]['experiment_id']}").json()["data"]["parameters"][0]
    assert p["review"]["components"]["unit_verified_in_pdf"] is True and p["integrity"]["status"] == "OK"


def test_condition_must_be_recorded_before_confirming_and_correction_preserves_the_original(client, tmp_path):
    eq = P("equilibrium_contact_angle", "70", DEG, "EQUILIBRIUM CONTACT ANGLES ARE 70 " + DEG + " AT 20 " + DEG_C + " AND 65 " + DEG + " AT 100 " + DEG_C)
    rec, ids = _import(client, tmp_path, [eq], body="EQUILIBRIUM CONTACT ANGLES ARE 70 " + DEG + " AT 20 " + DEG_C + " AND 65 " + DEG + " AT 100 " + DEG_C)
    rid, eid = ids["equilibrium_contact_angle"], rec["experiments"][0]["experiment_id"]
    body = {**BODY, "observed_value": "70", "observed_unit": DEG}
    r = client.post(f"/api/records/{rid}/review", json=body)
    assert r.json()["error"]["code"] == "INTEGRITY_INCONSISTENT"
    assert r.json()["error"]["details"]["integrity_findings"][0]["code"] == "CONDITION_NOT_RECORDED"
    c = client.post(f"/api/records/{rid}/review", json={"action": "CORRECT", "reviewer": "Bruno Lima", "corrected_condition_text": "a 20 " + DEG_C,
                                                         "corrected_condition_value": "20", "corrected_condition_unit": DEG_C, "notes": "valor vale a 20 °C"})
    assert c.status_code == 200 and c.json()["data"]["integrity_findings"] == []
    p = client.get(f"/api/experiments/{eid}").json()["data"]["parameters"][0]
    assert p["condition"] == {"text": "a 20 " + DEG_C, "value": 20.0, "unit": DEG_C, "source": "HUMANO", "by": "Bruno Lima"}
    assert p["original_extraction"]["condition"] is None and p["original_extraction"]["original"]["value"] == 70.0
    assert client.post(f"/api/records/{rid}/review", json=body).status_code == 200  # outra pessoa confirma


def test_reopen_returns_a_confirmed_record_to_pending_with_history(client, tmp_path):
    rec, ids = _import(client, tmp_path, [PEAK])
    rid, eid = ids["peak_temperature_planned"], rec["experiments"][0]["experiment_id"]
    client.post(f"/api/records/{rid}/review", json={**BODY, "observed_value": "80", "observed_unit": DEG_C})
    for patch, code in [({"reviewer": "Gemini"}, "REVIEWER_NOT_HUMAN"), ({"notes": ""}, "NOTES_REQUIRED"), ({"reviewer": ""}, "REVIEWER_REQUIRED")]:
        r = client.post(f"/api/records/{rid}/review", json={"action": "REOPEN", "reviewer": "Carla Dias", "notes": "motivo", **patch})
        assert r.status_code == 422 and r.json()["error"]["code"] == code
    ok = client.post(f"/api/records/{rid}/review", json={"action": "REOPEN", "reviewer": "Carla Dias", "notes": "interpretação não confirmada"})
    assert ok.status_code == 200 and ok.json()["data"]["status"] == "EXTRAIDO_NAO_REVISADO"
    p = client.get(f"/api/experiments/{eid}").json()["data"]["parameters"][0]
    assert p["review"] is None and p["review_history"][0]["reviewer"] == "Ana Souza" and p["review_history"][0]["reopen_reason"]
    again = client.post(f"/api/records/{rid}/review", json={"action": "REOPEN", "reviewer": "Carla Dias", "notes": "x"})
    assert again.json()["error"]["code"] == "WRONG_STATE"
    trail = [e["outcome"] for e in client.get(f"/api/records/{rid}/events").json()["data"]]
    assert [o for o in trail if o != "REFUSED"] == ["APPROVED", "REOPENED"] and trail.count("REFUSED") == 2  # recusas de política (não humano, estado errado) ficam na trilha; campo vazio é recusado antes


def test_curated_record_cannot_be_reopened_from_the_interface(client):
    r = client.post("/api/records/SYN-T1.airflow_velocity/review", json={"action": "REOPEN", "reviewer": "Carla Dias", "notes": "x"})
    assert r.json()["error"]["code"] == "CURATED_READONLY"


# ================================================================ Tarefa 4 — lacunas contraditórias
def test_gap_that_overlaps_a_parameter_is_related_not_merged_not_deleted(client, tmp_path):
    dih = P("dihedral_angle", "65", DEG, "dihedral angles 2a = 65 " + DEG + " (left) and 2a = 60 " + DEG + " (right)")
    rec, ids = _import(client, tmp_path, [dih], missing=[{"name": "cell_dihedral_angle", "reason": "not stated in the pages read"},
                                                          {"name": "exact_fluid_volume", "reason": "not stated"}], body=Q_DIHEDRAL)
    eid = rec["experiments"][0]["experiment_id"]
    exp = client.get(f"/api/experiments/{eid}").json()["data"]
    gaps = {g["parameter"]: g for g in exp["gaps"]}
    g = gaps["cell_dihedral_angle"]
    assert g["coverage_state"] == "POSSIVEL_SOBREPOSICAO" and g["decision"] is None
    rel = g["related_parameters"][0]
    assert rel["record_id"] == ids["dihedral_angle"] and rel["relation"] == "SAME_QUANTITY_SCOPE_TO_CONFIRM" and rel["scope_differs"] is True
    assert "TODOS os objetos" in rel["explanation_pt"] and rel["value"] == 65.0
    assert gaps["exact_fluid_volume"]["related_parameters"] == [] and gaps["exact_fluid_volume"]["coverage_state"] == "ABERTA"
    # decisão humana: cobertura PARCIAL (65° e 60° são de duas células; só 65° foi extraído)
    bad = client.post(f"/api/gaps/{g['gap_id']}/decision", json={"decision": "PARTIAL", "reviewer": "Gemini", "notes": "ok ok"})
    assert bad.status_code == 422
    ok = client.post(f"/api/gaps/{g['gap_id']}/decision", json={"decision": "PARTIAL", "reviewer": "Ana Souza", "record_id": ids["dihedral_angle"],
                                                                 "notes": "A Fig. 3(a) mostra duas células (65° e 60°); só uma foi extraída."})
    assert ok.status_code == 201
    after = {x["parameter"]: x for x in client.get(f"/api/experiments/{eid}").json()["data"]["gaps"]}["cell_dihedral_angle"]
    assert after["coverage_state"] == "PARCIALMENTE_COBERTA" and after["decision"]["reviewer"] == "Ana Souza"
    assert len(client.get(f"/api/experiments/{eid}").json()["data"]["gaps"]) == 2  # nada foi apagado


def test_gap_relation_unit():
    gap = {"parameter": "cell_dihedral_angle"}
    params = [{"record_id": "r1", "parameter": "dihedral_angle", "label_pt": "x", "original": {"value": 65.0, "unit": DEG}, "evidence": [{"page_pdf": 18}]},
              {"record_id": "r2", "parameter": "contact_angle", "label_pt": "y", "original": {"value": 19.0, "unit": DEG}, "evidence": [{"page_pdf": 5}]}]
    assert [r["record_id"] for r in relations(gap, params)] == ["r1"]  # "ângulo" sozinho não basta: precisa da mesma grandeza (2+ termos)
    assert relations({"parameter": "dihedral_angle"}, params[:1])[0]["relation"] == "SAME_QUANTITY"


# ================================================================ Tarefa 5 — prontidão em cinco dimensões
def test_five_independent_readiness_dimensions_and_unsupported_physics_is_preserved(client, tmp_path):
    rec, ids = _import(client, tmp_path, [PEAK, ANGLE], phenomena=["fluid_capillary", "fluid_flow", "heat_transfer"])
    eid = rec["experiments"][0]["experiment_id"]
    for name, val, unit in (("peak_temperature_planned", "80", DEG_C), ("uncoated_cells_contact_angle", "19", DEG)):
        assert client.post(f"/api/records/{ids[name]}/review", json={**BODY, "observed_value": val, "observed_unit": unit}).status_code == 200
    c = client.get(f"/api/experiments/{eid}/compatibility").json()["data"]
    dims = {d["key"]: d for d in c["readiness"]["dimensions"]}
    assert list(dims) == ["extraction_integrity", "scientific_review", "coverage", "fds_compatibility", "execution_readiness"]
    assert dims["extraction_integrity"]["status"] == "OK" and dims["scientific_review"]["status"] == "COMPLETA"  # tudo conferido, íntegro
    assert dims["fds_compatibility"]["status"] == "UNSUPPORTED_PHYSICS" and c["status"] == "UNSUPPORTED_PHYSICS"
    assert dims["execution_readiness"]["status"] == "BLOQUEADA" and c["actions"]["simulate"] is False and c["readiness"]["can_simulate"] is False
    assert "Conferir os parâmetros não basta" in dims["execution_readiness"]["summary_pt"]


def test_legacy_review_and_inconsistency_make_the_review_dimension_conditional(client, tmp_path):
    rec, ids = _import(client, tmp_path, [PEAK, P("temperature", "20", None, Q_CYCLE)], body=_pdf_body(Q_PEAK, Q_CYCLE))
    eid = rec["experiments"][0]["experiment_id"]
    path = tmp_path / "var" / "imports" / rec["import_id"] / "import.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for p in data["experiments"][0]["parameters"]:  # simula o histórico: conferido pela regra antiga (sem confirmar a interpretação)
        p["status"] = "CONFERIDO_FONTE"
        p["review"] = {"reviewer": "Revisor Antigo", "reviewed_at": "2026-11-15T01:00:00Z", "notes": None, "checked_document_sha256": rec["sha256"]}
    path.write_text(json.dumps(data), encoding="utf-8")
    exp = client.get(f"/api/experiments/{eid}").json()["data"]
    assert {p["parameter"]: p["review_scope"] for p in exp["parameters"]} == {"peak_temperature_planned": "LEGACY", "temperature": "LEGACY"}
    dims = {d["key"]: d for d in client.get(f"/api/experiments/{eid}/compatibility").json()["data"]["readiness"]["dimensions"]}
    assert dims["extraction_integrity"]["status"] == "INCONSISTENTE"  # temperatura sem unidade
    assert dims["scientific_review"]["status"] == "COMPLETA_COM_RESSALVAS" and "anterior à confirmação da interpretação" in dims["scientific_review"]["summary_pt"]


# ================================================================ relatório de inconsistências (somente leitura)
def test_integrity_report_lists_affected_records_proposes_audited_fixes_and_changes_nothing(client, tmp_path):
    rec, ids = _import(client, tmp_path, [PEAK, P("surface_modifier", "FC-724", "none", "coated with FC-724", role="METADADO"),
                                          P("temperature", "20", None, Q_CYCLE),
                                          P("equilibrium_contact_angle", "70", DEG, "EQUILIBRIUM CONTACT ANGLES ARE 70 " + DEG + " AT 20 " + DEG_C)],
                       body=_pdf_body(Q_PEAK, "coated with FC-724", Q_CYCLE, "EQUILIBRIUM CONTACT ANGLES ARE 70 " + DEG + " AT 20 " + DEG_C))
    path = tmp_path / "var" / "imports" / rec["import_id"] / "import.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for p in data["experiments"][0]["parameters"]:
        p["status"] = "CONFERIDO_FONTE"
        p["review"] = {"reviewer": "Revisor Antigo", "reviewed_at": "2026-11-15T01:00:00Z", "notes": None, "checked_document_sha256": rec["sha256"]}
    path.write_text(json.dumps(data), encoding="utf-8")
    append_event({"record_id": ids["surface_modifier"], "reviewer": "Revisor Antigo", "action": "CONFIRM", "outcome": "APPROVED",
                  "observed_value": "FC-724", "observed_unit": "deg", "observed_page_pdf": 1})
    append_event({"record_id": ids["peak_temperature_planned"], "reviewer": "Revisor Antigo", "action": "CONFIRM", "outcome": "APPROVED",
                  "observed_value": "80", "observed_unit": DEG_C, "observed_page_pdf": 1})
    before = path.read_text(encoding="utf-8")
    audit_before = (tmp_path / "var" / "audit" / "review_events.jsonl").read_text(encoding="utf-8")
    rep = client.get("/api/audit/integrity").json()["data"]
    assert path.read_text(encoding="utf-8") == before and (tmp_path / "var" / "audit" / "review_events.jsonl").read_text(encoding="utf-8") == audit_before
    assert rep["read_only"] is True
    by = {r["parameter"]: r for r in rep["records"] if r["document_id"] == rec["document"]["document_id"]}
    assert by["temperature"]["classification"] == "INCONSISTENT_CONFIRMED" and by["temperature"]["unit_state"] == "MISSING"
    assert by["equilibrium_contact_angle"]["classification"] == "INCONSISTENT_CONFIRMED"
    assert by["equilibrium_contact_angle"]["proposals"][0] == {"finding": "CONDITION_NOT_RECORDED", "action": "CORRECT", "proposal_pt": by["equilibrium_contact_angle"]["proposals"][0]["proposal_pt"]}
    assert by["peak_temperature_planned"]["classification"] == "LEGACY_REVIEW" and by["peak_temperature_planned"]["proposals"][0]["action"] == "REOPEN_THEN_CONFIRM"
    anomalies = {a["code"] for a in by["surface_modifier"]["audit_anomalies"]}
    assert "UNIT_SUBMITTED_FOR_TEXT_VALUE" in anomalies
    assert rep["summary"]["confirmed_without_interpretation_confirmation"] == 4 and rep["summary"]["confirmed_with_blocking_inconsistency"] == 2


def test_version_endpoint_advertises_capabilities_the_frontend_requires(client):
    import re
    from backend.app.dataset.store import REPO_ROOT

    d = client.get("/api/version").json()
    frontend = (REPO_ROOT / "frontend/src/lib.ts").read_text(encoding="utf-8")
    required = json.loads(re.search(r"REQUIRED_CAPABILITIES = (\[[^\]]+\])", frontend).group(1))
    assert set(required) <= set(d["capabilities"])
    assert d["app_version"] == app.version
    assert client.get("/api/health").json() == {"status": "ok", "stage": "F00"}
