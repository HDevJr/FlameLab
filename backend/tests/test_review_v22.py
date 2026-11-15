"""Revisão científica assistida (v2.2): correção do VALUE_MISMATCH de 15/11/2026.

Caso real: `initial_temperature = 20.0 °C` (artigo importado, p. 5). O revisor digitou "20.0 °C" no campo de
valor com a unidade vazia e a conferência foi recusada como VALUE_MISMATCH, com a mensagem
"valor lido (20.0 °C ) diverge do registro (20.0 °C)". Causa: o extrator de números engolia a unidade para
dentro do valor e a descartava; a unidade vazia virava "adimensional" e °C não existia na tabela; e a
mensagem escondia qual campo falhou. Estes testes fixam o comportamento correto.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app import units
from backend.app.api.platform import Services
from backend.app.dataset.review import ReviewRejected, check_review
from backend.app.labels import friendly_label
from backend.app.main import app
from backend.app.quantities import compare_fields, parse_value_input
from backend.app.semantic import blocking, semantic_flags
from backend.tests.test_ingest import FakeProvider, fetch, make_pdf, upload

DEG_C = "°C"
QUOTE = ("During the flight the cells were partially filled via four independent fill ports. "
         "The temperature was then cycled from 20 to 80 °C in increments of 20 °C.")


def compare(value="20", unit=DEG_C, page=5, orig_value=20.0, orig_unit=DEG_C, pages=(5,)):
    return compare_fields(original_value=orig_value, original_unit=orig_unit, evidence_pages=set(pages),
                          observed_value=value, observed_unit=unit, observed_page=page)


def rows(result):
    return {r["field"]: r for r in result["comparisons"]}


# ================================================================ reprodução do erro original
def test_original_report_value_with_embedded_unit_and_empty_unit_field_is_read_explicitly():
    r = compare("20.0 " + DEG_C, None)
    assert r["accepted"] is True
    unit = rows(r)["unit"]
    assert unit["status"] == "MATCH" and unit["from_value_field"] is True and "campo de valor" in unit["detail_pt"]
    assert rows(r)["value"]["status"] == "MATCH" and rows(r)["value"]["received"] == "20"


def test_original_report_unit_missing_is_a_unit_error_not_a_value_error():
    r = compare("20.0", None)
    assert r["accepted"] is False and r["code"] == "UNIT_MISSING"
    by = rows(r)
    assert (by["value"]["status"], by["unit"]["status"], by["page"]["status"]) == ("MATCH", "MISSING", "MATCH")
    assert by["unit"]["expected"] == DEG_C and by["unit"]["received"] is None
    assert r["failed_fields"] == ["unit"]
    assert "unidade ausente" in r["message_pt"] and "VALUE_MISMATCH" not in r["message_pt"]


def test_check_review_raises_a_specific_code_with_structured_details():
    with pytest.raises(ReviewRejected) as exc:
        check_review(status="EXTRAIDO_NAO_REVISADO", extractor="modelo", reviewer="Pessoa", original_value=20.0,
                     original_unit=DEG_C, evidence_pages={5}, observed_value="20.0", observed_unit=None,
                     observed_page_pdf=5, hash_problem=None)
    assert exc.value.code == "UNIT_MISSING"
    d = exc.value.details
    assert d["accepted"] is False and d["code"] == "REVIEW_MISMATCH" and d["reason_code"] == "UNIT_MISSING"
    assert [c["field"] for c in d["comparisons"]] == ["value", "unit", "page"]


# ================================================================ número: equivalências e ambiguidades
@pytest.mark.parametrize("text", ["20", "20.0", "20,0", " 20 ", "+20", "2e1", "20.00"])
def test_numerically_equivalent_spellings_match(text):
    r = compare(text)
    assert r["accepted"] is True, r["comparisons"]


def test_value_and_unit_are_split_from_one_field():
    p = parse_value_input("20 " + DEG_C)
    assert (p.status, p.value, p.embedded_unit) == ("OK", 20.0, DEG_C)
    p = parse_value_input("20,0")
    assert (p.status, p.value, p.embedded_unit) == ("OK", 20.0, None)


@pytest.mark.parametrize("text,status", [("1,234", "AMBIGUOUS"), ("1.234,5", "AMBIGUOUS"), ("1,2,3", "AMBIGUOUS"),
                                         ("20 to 80", "AMBIGUOUS"), ("20-80", "AMBIGUOUS"), ("abc", "UNREADABLE"), ("", "EMPTY"),
                                         ("1e999", "UNREADABLE")])
def test_ambiguous_or_unreadable_values_are_never_guessed(text, status):
    assert parse_value_input(text).status == status


def test_ambiguous_value_is_refused_with_a_specific_code():
    r = compare("1,234", DEG_C, orig_value=1.234)
    assert r["code"] == "VALUE_AMBIGUOUS" and rows(r)["value"]["status"] == "AMBIGUOUS"
    r = compare("20 to 80", DEG_C)
    assert r["code"] == "VALUE_AMBIGUOUS"


def test_conflicting_units_between_value_and_unit_field_are_ambiguous():
    r = compare("20 " + DEG_C, "K")
    assert r["code"] == "VALUE_AMBIGUOUS" and "difere" in rows(r)["value"]["detail_pt"]


# ================================================================ unidades: Unicode, conversão, incompatibilidade
@pytest.mark.parametrize("unit", [DEG_C, "℃", "ºC", "˚C", "° C", "° C", "degC", "deg C",
                                  "degrees C", "Celsius", " °C "])
def test_unicode_and_spelling_variants_of_celsius_are_the_same_unit(unit):
    assert compare("20", unit)["accepted"] is True


def test_celsius_and_kelvin_are_converted_with_offset():
    r = compare("293.15", "K")
    assert r["accepted"] is True and rows(r)["unit"]["status"] == "CONVERTIBLE"
    assert rows(r)["value"]["expected_si"] == "293.15 K" and rows(r)["value"]["received_si"] == "293.15 K"
    assert compare("68", "°F")["accepted"] is True  # 68 °F = 20 °C
    assert units.normalize(20, DEG_C).value == pytest.approx(293.15)
    assert units.normalize(0, "K").value == 0


def test_same_number_in_kelvin_is_a_value_mismatch_after_conversion():
    r = compare("20", "K")  # 20 K = -253,15 °C ≠ 20 °C
    assert r["code"] == "VALUE_MISMATCH"
    assert rows(r)["unit"]["status"] == "CONVERTIBLE" and rows(r)["value"]["status"] == "MISMATCH"
    assert rows(r)["value"]["received_si"] == "20 K"


def test_incompatible_units_are_reported_as_such():
    r = compare("19", DEG_C, orig_value=19.0, orig_unit="°")  # ângulo × temperatura (caso real do contact angle)
    assert r["code"] == "UNIT_INCOMPATIBLE"
    assert "temperatura" in rows(r)["unit"]["detail_pt"] and "ângulo" in rows(r)["unit"]["detail_pt"]
    assert rows(r)["value"]["status"] == "MATCH"  # o número coincide; a unidade é que impede


def test_angle_units_match_and_convert():
    assert compare("19", "°", orig_value=19.0, orig_unit="deg")["accepted"] is True
    assert compare("0.3316125578789226", "rad", orig_value=19.0, orig_unit="deg")["accepted"] is True


def test_unsupported_unit_gets_a_specific_error_not_a_literal_text_comparison():
    r = compare("5", "mmHg", orig_value=5.0, orig_unit="mmHg")
    assert r["code"] == "UNIT_UNSUPPORTED" and rows(r)["unit"]["status"] == "UNSUPPORTED"
    r = compare("5", "furlong", orig_value=5.0, orig_unit="cm")
    assert r["code"] == "UNIT_UNSUPPORTED" and "informada" in rows(r)["unit"]["detail_pt"]


def test_dimensionless_records():
    assert compare("50350", None, orig_value=50350.0, orig_unit="none")["accepted"] is True
    assert compare("50350", "none", orig_value=50350.0, orig_unit="")["accepted"] is True
    assert compare("50350", "%", orig_value=50350.0, orig_unit="none")["code"] == "UNIT_UNEXPECTED"


def test_value_and_page_divergences_name_the_failing_field():
    r = compare("80")
    assert r["code"] == "VALUE_MISMATCH" and r["failed_fields"] == ["value"]
    assert rows(r)["value"]["status"] == "MISMATCH" and rows(r)["page"]["status"] == "MATCH"
    r = compare("20", page=6)
    assert r["code"] == "PAGE_MISMATCH" and r["failed_fields"] == ["page"] and rows(r)["page"]["expected"] == "5"
    r = compare("20", page=None)
    assert r["code"] == "OBSERVED_REQUIRED" and rows(r)["page"]["status"] == "MISSING"


def test_all_failing_fields_are_listed_at_once():
    r = compare("80", None, page=9)
    assert r["failed_fields"] == ["page", "unit", "value"] and r["code"] == "UNIT_MISSING"  # primeira prioridade


def test_text_values():
    r = compare_fields(original_value="PMMA (clear cast)", original_unit=None, evidence_pages={3}, observed_value="pmma",
                       observed_unit=None, observed_page=3)
    assert r["accepted"] is True and rows(r)["unit"]["status"] == "NOT_APPLICABLE"
    r = compare_fields(original_value="PMMA", original_unit=None, evidence_pages={3}, observed_value="PTFE",
                       observed_unit=None, observed_page=3)
    assert r["code"] == "VALUE_MISMATCH"


# ================================================================ semântica: "temperatura inicial" × intervalo
def test_initial_temperature_from_a_cycle_range_is_flagged_and_blocking():
    flags = semantic_flags(parameter="initial_temperature", label="Temperatura inicial", value=20.0, unit=DEG_C,
                           quotes=[QUOTE], method="LLM")
    codes = {f["code"]: f["severity"] for f in flags}
    assert codes["INITIAL_FROM_RANGE"] == "BLOCKING" and codes["VALUE_ALSO_INCREMENT"] == "INFO"
    assert "20 a 80" in next(f for f in flags if f["code"] == "INITIAL_FROM_RANGE")["detail_pt"]
    assert blocking(flags)


def test_text_that_states_the_initial_value_is_not_flagged():
    q = "The temperature was initially 20 °C and then cycled from 20 to 80 °C."
    flags = semantic_flags(parameter="initial_temperature", label="Temperatura inicial", value=20.0, unit=DEG_C, quotes=[q])
    assert not blocking(flags)


def test_relabeled_as_range_start_is_not_blocked():
    flags = semantic_flags(parameter="initial_temperature", label="Limite do ciclo", value=20.0, unit=DEG_C,
                           quotes=[QUOTE], label_source="HUMANO")  # só o rótulo humano conta
    assert not blocking(flags)
    assert blocking(semantic_flags(parameter="initial_temperature", label="Limite do ciclo", value=20.0, unit=DEG_C, quotes=[QUOTE]))


def test_increment_read_as_absolute_value_is_flagged():
    q = "Temperature was raised in steps of 20 °C every hour."
    flags = semantic_flags(parameter="temperature", label="Temperatura", value=20.0, unit=DEG_C, quotes=[q])
    assert [f["code"] for f in blocking(flags)] == ["INCREMENT_AS_ABSOLUTE"]
    assert not blocking(semantic_flags(parameter="temperature_increment", label="Incremento", value=20.0, unit=DEG_C, quotes=[q]))


def test_upper_endpoint_as_peak_without_statement_is_flagged():
    q = "The sample was varied from 20 to 80 °C."
    assert [f["code"] for f in blocking(semantic_flags(parameter="peak_temperature", label="Pico", value=80.0, unit=DEG_C, quotes=[q]))] == ["FINAL_FROM_RANGE"]
    assert [f["code"] for f in blocking(semantic_flags(parameter="initial_temperature", label="inicial", value=80.0, unit=DEG_C, quotes=[q]))] == ["ENDPOINT_MISMATCH"]


def test_plain_statement_is_clean():
    q = "The uncoated cells show a contact angle of approximately 19 ° with the liquid used."
    flags = semantic_flags(parameter="contact_angle", label="Ângulo", value=19.0, unit="°", quotes=[q], method="LLM")
    assert not blocking(flags) and [f["code"] for f in flags] == ["APPROXIMATE_VALUE"]


def test_other_values_in_the_quote_are_informative_only():
    q = "EQUILIBRIUM CONTACT ANGLES ARE 70 ° AT 20 °C AND 65 ° AT 100 °C"
    flags = semantic_flags(parameter="equilibrium_contact_angle", label="Ângulo", value=70.0, unit="°", quotes=[q], method="LLM")
    f = next(x for x in flags if x["code"] == "MULTIPLE_VALUES_IN_QUOTE")
    assert f["severity"] == "INFO" and "20 °C" in f["detail_pt"] and "65 °" in f["detail_pt"]


def test_textual_values_have_no_numeric_flags():
    assert semantic_flags(parameter="material", label="Material", value="PMMA", unit=None, quotes=["PMMA"]) == []


# ================================================================ rótulos amigáveis
@pytest.mark.parametrize("slug,expected", [
    ("initial_temperature", "Temperatura inicial"), ("peak_temperature_planned", "Temperatura de pico planejada"),
    ("peak_temperature_achieved", "Temperatura de pico alcançada"), ("contact_angle_accuracy", "Precisão de ângulo de contato"),
    ("uncoated_cells_contact_angle", "Ângulo de contato de células sem revestimento"), ("dihedral_angle", "Ângulo diedral"),
    ("airflow_velocity", "Velocidade de fluxo de ar"), ("unknown_thing", "Unknown thing"), ("", "")])
def test_friendly_labels(slug, expected):
    assert friendly_label(slug) == expected


# ================================================================ API: fluxo completo com o trecho real
@pytest.fixture
def client():
    return TestClient(app)


def _import_initial_temperature(client, tmp_path, label_pt=None):
    param = {"name": "initial_temperature", "role": "CONDICAO", "value": "20", "unit": DEG_C, "page": 1,
             "quote": "The temperature was then cycled from 20 to 80 " + DEG_C + " in increments of 20 " + DEG_C}
    if label_pt:
        param["label_pt"] = label_pt
    out = {"experiments": [{"label": "Run A", "description": "d", "phenomena": ["fluid_flow"], "missing": [], "parameters": [param]}]}
    Services.provider = FakeProvider(out)
    rec = fetch(client, upload(client, make_pdf(tmp_path / "a.pdf", body=QUOTE + " The cells were filled.")))
    return rec["experiments"][0]["parameters"][0]["record_id"], rec["experiments"][0]["experiment_id"]


BODY = {"action": "CONFIRM", "reviewer": "Ana Souza", "observed_value": "20", "observed_unit": DEG_C,
        "observed_page_pdf": 1, "checked_pdf": True}


def test_api_refusal_carries_field_by_field_diagnosis(client, tmp_path):
    rid, _ = _import_initial_temperature(client, tmp_path)
    r = client.post(f"/api/records/{rid}/review", json={**BODY, "observed_value": "20.0", "observed_unit": None})
    err = r.json()["error"]
    assert r.status_code == 422 and err["code"] == "UNIT_MISSING"
    d = err["details"]
    assert d["accepted"] is False and d["code"] == "REVIEW_MISMATCH" and d["failed_fields"] == ["unit"]
    assert {c["field"]: c["status"] for c in d["comparisons"]} == {"value": "MATCH", "unit": "MISSING", "page": "MATCH"}
    ev = client.get(f"/api/records/{rid}/events").json()["data"][-1]  # a tentativa fica na trilha, com as comparações
    assert ev["outcome"] == "REFUSED" and ev["code"] == "UNIT_MISSING" and ev["comparisons"][1]["status"] == "MISSING"


def test_preview_uses_the_backend_logic_and_writes_nothing(client, tmp_path):
    rid, _ = _import_initial_temperature(client, tmp_path)
    p = client.post(f"/api/records/{rid}/review/preview", json={"reviewer": "Ana Souza", "observed_value": "293.15",
                                                               "observed_unit": "K", "observed_page_pdf": 1}).json()["data"]
    assert p["fields_accepted"] is True and p["comparisons"][1]["status"] == "CONVERTIBLE"
    assert p["accepted"] is False and [f["code"] for f in p["blocking_flags"]] == ["INITIAL_FROM_RANGE"]
    bad = client.post(f"/api/records/{rid}/review/preview", json={"observed_value": "20", "observed_unit": "mm", "observed_page_pdf": 1}).json()["data"]
    assert bad["field_code"] == "UNIT_INCOMPATIBLE" and bad["failed_fields"] == ["unit"]
    assert client.get(f"/api/records/{rid}/events").json()["data"] == []  # preview não audita nem altera
    assert client.post("/api/records/NAO-EXISTE.x/review/preview", json={}).status_code == 404


def test_numerically_correct_confirmation_is_still_blocked_by_semantic_ambiguity(client, tmp_path):
    rid, eid = _import_initial_temperature(client, tmp_path)
    r = client.post(f"/api/records/{rid}/review", json=BODY)
    err = r.json()["error"]
    assert r.status_code == 422 and err["code"] == "SEMANTIC_AMBIGUITY"
    assert err["details"]["semantic_flags"][0]["code"] == "INITIAL_FROM_RANGE"
    assert all(c["status"] in ("MATCH",) for c in err["details"]["comparisons"])  # o número NÃO era o problema
    p = next(x for x in client.get(f"/api/experiments/{eid}").json()["data"]["parameters"] if x["record_id"] == rid)
    assert p["status"] == "EXTRAIDO_NAO_REVISADO"
    assert [f["code"] for f in p["semantic_flags"]][0] == "INITIAL_FROM_RANGE"
    ev = client.get(f"/api/records/{rid}/events").json()["data"][-1]
    assert ev["code"] == "SEMANTIC_AMBIGUITY" and ev["semantic_flags"]


def test_catalog_exposes_friendly_name_technical_name_and_separate_unit(client, tmp_path):
    rid, eid = _import_initial_temperature(client, tmp_path)
    p = next(x for x in client.get(f"/api/experiments/{eid}").json()["data"]["parameters"] if x["record_id"] == rid)
    assert p["label_pt"] == "Temperatura inicial" and p["technical_name"] == "initial_temperature"
    assert p["label_source"] == "GLOSSARIO"
    assert p["original"]["value"] == 20.0 and p["original"]["unit"] == DEG_C  # valor e unidade separados
    assert p["unit_info"]["display"] == DEG_C and p["unit_info"]["dimension_pt"] == "temperatura" and p["unit_info"]["supported"]
    assert p["normalized"]["unit"] == "K" and p["normalized"]["value"] == pytest.approx(293.15)


def test_ai_supplied_portuguese_label_is_kept_and_attributed(client, tmp_path):
    rid, eid = _import_initial_temperature(client, tmp_path, label_pt="Temperatura de partida")
    p = next(x for x in client.get(f"/api/experiments/{eid}").json()["data"]["parameters"] if x["record_id"] == rid)
    assert p["label_pt"] == "Temperatura de partida" and p["label_source"] == "IA"


def test_context_endpoint_returns_text_before_and_after_the_quote(client, tmp_path):
    rid, _ = _import_initial_temperature(client, tmp_path)
    c = client.get(f"/api/records/{rid}/context").json()["data"]
    assert c["found"] is True and c["page"] == 1
    assert "cycled from 20 to 80" in c["quote"] and "The cells were filled" in c["after"]
    assert "four independent fill ports" in c["before"]  # contexto anterior da mesma página


# ================================================================ corrigir a extração preserva o original
def test_correction_preserves_original_and_resolves_the_semantic_block(client, tmp_path):
    rid, eid = _import_initial_temperature(client, tmp_path)
    r = client.post(f"/api/records/{rid}/review", json={
        "action": "CORRECT", "reviewer": "Bruno Lima", "corrected_label_pt": "Temperatura mínima do ciclo",
        "notes": "O trecho descreve um ciclo de 20 a 80 °C; não afirma temperatura inicial."})
    d = r.json()["data"]
    assert r.status_code == 200 and d["outcome"] == "CORRECTED" and d["status"] == "EXTRAIDO_NAO_REVISADO"
    assert d["before"]["label_pt"] == "Temperatura inicial" and d["after"]["label_pt"] == "Temperatura mínima do ciclo"
    assert not blocking(d["semantic_flags"])
    p = next(x for x in client.get(f"/api/experiments/{eid}").json()["data"]["parameters"] if x["record_id"] == rid)
    assert p["label_pt"] == "Temperatura mínima do ciclo" and p["label_source"] == "HUMANO"
    assert p["original_extraction"]["label_pt"] == "Temperatura inicial"  # o que a IA/glossário propôs fica preservado
    assert p["original_extraction"]["original"]["value"] == 20.0 and p["original_extraction"]["extraction"]["by"] == "fake-model"
    assert p["corrections"][0]["by"] == "Bruno Lima" and p["corrections"][0]["notes"]
    assert p["extraction"]["corrected_by"] == ["Bruno Lima"]
    # quem corrigiu não confirma o mesmo valor (independência), outra pessoa sim
    same = client.post(f"/api/records/{rid}/review", json={**BODY, "reviewer": "Bruno Lima"})
    assert same.json()["error"]["code"] == "REVIEWER_NOT_INDEPENDENT"
    ok = client.post(f"/api/records/{rid}/review", json=BODY)
    assert ok.status_code == 200 and ok.json()["data"]["status"] == "CONFERIDO_FONTE"
    events = client.get(f"/api/records/{rid}/events").json()["data"]
    assert [e["outcome"] for e in events] == ["CORRECTED", "REFUSED", "APPROVED"]


def test_correcting_a_confirmed_value_reopens_the_review_and_keeps_the_history(client, tmp_path):
    rid, eid = _import_initial_temperature(client, tmp_path)
    client.post(f"/api/records/{rid}/review", json={"action": "CORRECT", "reviewer": "Bruno Lima",
                                                    "corrected_label_pt": "Temperatura mínima do ciclo", "notes": "ajuste"})
    assert client.post(f"/api/records/{rid}/review", json=BODY).status_code == 200
    r = client.post(f"/api/records/{rid}/review", json={"action": "CORRECT", "reviewer": "Carla Dias", "corrected_value": "25",
                                                        "corrected_unit": "K", "notes": "transcrição errada"})
    d = r.json()["data"]
    assert d["reopened"] is True and d["status"] == "EXTRAIDO_NAO_REVISADO" and d["after"]["unit"] == "K"
    p = next(x for x in client.get(f"/api/experiments/{eid}").json()["data"]["parameters"] if x["record_id"] == rid)
    assert p["review"] is None and p["review_history"][0]["reviewer"] == "Ana Souza"
    assert p["original"]["value"] == 25.0 and p["original_extraction"]["original"]["value"] == 20.0
    assert p["normalized"] == {"value": 25.0, "unit": "K"}


@pytest.mark.parametrize("patch,code", [
    ({"reviewer": "Gemini"}, "REVIEWER_NOT_HUMAN"), ({"notes": ""}, "NOTES_REQUIRED"), ({"reviewer": ""}, "REVIEWER_REQUIRED"),
    ({"corrected_unit": "furlong"}, "UNIT_UNSUPPORTED"), ({"corrected_value": "1,234"}, "VALUE_AMBIGUOUS"),
    ({"corrected_value": "20", "corrected_unit": DEG_C, "corrected_label_pt": None}, "NO_CHANGE"),
])
def test_invalid_corrections_are_refused_and_change_nothing(client, tmp_path, patch, code):
    rid, eid = _import_initial_temperature(client, tmp_path)
    body = {"action": "CORRECT", "reviewer": "Bruno Lima", "corrected_value": "21", "notes": "motivo", **patch}
    r = client.post(f"/api/records/{rid}/review", json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == code
    p = next(x for x in client.get(f"/api/experiments/{eid}").json()["data"]["parameters"] if x["record_id"] == rid)
    assert p["original"]["value"] == 20.0 and "corrections" not in p


def test_curated_records_cannot_be_corrected_from_the_interface(client):
    r = client.post("/api/records/BASS2-M1.thickness/review", json={"action": "CORRECT", "reviewer": "Bruno Lima",
                                                                    "corrected_value": "2", "notes": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "CURATED_READONLY"


def test_prefilled_confirmation_is_recorded_in_the_audit_trail(client, tmp_path):
    rid, _ = _import_initial_temperature(client, tmp_path)
    client.post(f"/api/records/{rid}/review", json={"action": "CORRECT", "reviewer": "Bruno Lima",
                                                    "corrected_label_pt": "Temperatura mínima do ciclo", "notes": "ajuste"})
    r = client.post(f"/api/records/{rid}/review", json={**BODY, "prefilled_unchanged": True})
    assert r.status_code == 200
    ev = client.get(f"/api/records/{rid}/events").json()["data"][-1]
    assert ev["outcome"] == "APPROVED" and ev["prefilled_unchanged"] is True
    assert [c["status"] for c in ev["comparisons"]] == ["MATCH", "MATCH", "MATCH"]


def test_confirmation_without_declaration_is_refused_and_audited(client, tmp_path):
    rid, _ = _import_initial_temperature(client, tmp_path)
    r = client.post(f"/api/records/{rid}/review", json={**BODY, "checked_pdf": False})
    assert r.json()["error"]["code"] == "DECLARATION_REQUIRED"
    assert client.get(f"/api/records/{rid}/events").json()["data"][-1]["code"] == "DECLARATION_REQUIRED"


def test_experiment_hypothesis_ranges_for_temperature_units(client, tmp_path):
    """Faixa física de temperatura: acima do zero absoluto na própria unidade (°C pode ser negativo)."""
    from backend.app.simulation.compatibility import range_rule

    assert range_rule("K")[1:] == (0.0, None) and range_rule(DEG_C)[1] == pytest.approx(-273.15)
    assert "zero absoluto" in range_rule(DEG_C)[0]


def test_value_taken_from_a_list_is_flagged_as_informative():
    q = "(b) During heating up to 40, 60, 80, 90 and even 95 °C."
    f = next(x for x in semantic_flags(parameter="temperature", label="Temperatura", value=40.0, unit=DEG_C, quotes=[q], method="LLM")
             if x["code"] == "VALUE_FROM_LIST")
    assert f["severity"] == "INFO" and "40, 60, 80, 90, 95" in f["detail_pt"]
    assert not any(x["code"] == "VALUE_FROM_LIST" for x in semantic_flags(parameter="t", label="t", value=80.0, unit=DEG_C,
                                                                            quotes=["cycled from 20 to 80 °C"]))
