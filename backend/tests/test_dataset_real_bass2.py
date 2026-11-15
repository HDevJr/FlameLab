"""Dataset REAL em data/ (curadoria BASS-II/M1). Provedor SIMULADO; sem rede.

Estes testes conferem a ESTRUTURA e a rastreabilidade da curadoria. Eles não substituem
a revisão humana no PDF: enquanto ela não existir, o teste de resposta com evidência
conferida é pulado (NOT_RUN).
"""

import pytest

from backend.app.assistant.schemas import AskRequest
from backend.app.assistant.service import AssistantService
from backend.app.dataset.adapter import DatasetEvidenceSource
from backend.app.dataset.store import REPO_ROOT, DatasetStore
from backend.tests.assistant_fixtures import FakeProvider, claim, output, settings

EXPECTED = {
    "material": ("PMMA", None), "thickness": (1, "mm"), "width": (2.2, "cm"), "burning_faces": (1, None),
    "airflow_velocity": (9, "cm/s"), "flame_spread_rate": (0.071, "mm/s"), "burn_duration": (6.4, "min"),
    "o2_initial": (22.2, "vol%"), "o2_final": (21.9, "vol%"),
}
M1 = {"investigation_id": "PSI-25", "test_uids": ["BASS2-M1"]}


@pytest.fixture(scope="module")
def store():
    return DatasetStore.load()


def test_real_dataset_loads_with_nine_m1_records(store):
    recs = {r.parameter: r for r in store.records_for("BASS2-M1")}
    assert set(recs) == set(EXPECTED)
    for p, (val, unit) in EXPECTED.items():
        r = recs[p]
        if isinstance(val, str):
            assert val in r.original.value
        else:
            assert r.original.value == pytest.approx(val) and r.original.unit == unit
        assert r.status in ("EXTRAIDO_NAO_REVISADO", "CONFERIDO_FONTE")
        if r.status == "CONFERIDO_FONTE":
            assert r.review.reviewer and r.review.reviewer != r.extraction.by


def test_table_cells_point_to_table_5_1_row_m1(store):
    for r in store.records_for("BASS2-M1"):
        evs = [store.evidence[e] for e in r.evidence_ids]
        if r.parameter == "material":
            assert all(e.locator.table is None and e.locator.precision == "PAGE" for e in evs)
            continue
        (e,) = evs
        assert (e.locator.table, e.locator.row_label, e.locator.page_pdf_index, e.locator.page_printed) == ("5.1", "M1", 65, 57)
        assert e.locator.column_label == r.label_source and e.test_uid == "BASS2-M1"


def test_gaps_registered_without_values(store):
    gaps = store.gaps_for("BASS2-M1")
    assert len(gaps) >= 11
    assert {"ambient_pressure", "pmma_pyrolysis_properties", "duct_geometry", "o2_time_profile"} <= {g.parameter for g in gaps}


def test_real_pdf_hash_matches_if_present(store):
    chk = store.source_checks["NASA-TM-20210011385"]
    if chk.status == "FILE_MISSING":
        pytest.skip("NOT_RUN: PDF não está presente nesta máquina (sources/*.pdf é ignorado pelo Git)")
    assert chk.status == "MATCH"


def test_unreviewed_real_values_cannot_be_asserted(store, tmp_path):
    unreviewed = [r for r in store.records_for("BASS2-M1") if r.parameter == "flame_spread_rate"
                  and r.status != "CONFERIDO_FONTE"]
    if not unreviewed:
        pytest.skip("propagação de M1 já conferida; cenário coberto pelo teste seguinte")
    fake = FakeProvider(output(claim("OBSERVACAO", "Em M1, a propagação foi 0,071 mm/s.",
                                     ["REC-BASS2-M1.flame_spread_rate"], [(0.071, "mm/s")])))
    svc = AssistantService(settings(tmp_path, "live"), DatasetEvidenceSource(store), fake)
    ans = svc.ask(AskRequest(question="Qual a velocidade de propagação em M1?", scope=M1))
    assert not ans.claims
    assert {"V2_NUMBER_NOT_IN_EVIDENCE", "V4_OBSERVATION_WITHOUT_REVIEWED_RECORD"} <= set(ans.blocked_claims[0].reasons)
    assert all(r.value_withheld for r in ans.retrieved if r.kind.value == "RECORD_CARD")
    user_prompt = fake.calls[0][1]
    assert "0,071" not in user_prompt and "0.071" not in user_prompt
    assert ans.dataset_version == store.dataset_version


def test_real_pending_value_is_not_called_absent(store, tmp_path):
    fake = FakeProvider(output(
        claim("LIMITACAO", "A velocidade de propagação da chama no ensaio M1 está ausente no relatório.",
              ["GAP-BASS2-M1-sample_length"]),
        claim("LIMITACAO", "A velocidade de propagação de M1 consta na Tabela 5.1, mas aguarda revisão humana.",
              ["REC-BASS2-M1.flame_spread_rate"]),
    ))
    if store.records["BASS2-M1.flame_spread_rate"].status == "CONFERIDO_FONTE":
        pytest.skip("registro já conferido")
    svc = AssistantService(settings(tmp_path, "live"), DatasetEvidenceSource(store), fake)
    ans = svc.ask(AskRequest(question="Qual foi a velocidade de propagação da chama no ensaio M1?", scope=M1))
    reasons = ans.blocked_claims[0].reasons
    assert "V5_GAP_CITATION_MISMATCH" in reasons and "V5_PENDING_IS_NOT_ABSENT" in reasons
    assert ans.abstained and ans.abstain_reason.value == "PENDING_REVIEW"
    assert [c.text_pt for c in ans.claims] == ["A velocidade de propagação de M1 consta na Tabela 5.1, mas aguarda revisão humana."]


def test_answer_with_human_reviewed_real_evidence(store, tmp_path):
    rec = store.records.get("BASS2-M1.flame_spread_rate")
    if rec is None or rec.status != "CONFERIDO_FONTE":
        pytest.skip("NOT_RUN: aguardando revisão humana de BASS2-M1.flame_spread_rate no PDF")
    fake = FakeProvider(output(claim("OBSERVACAO", "Em M1, a propagação foi 0,071 mm/s.",
                                     ["REC-BASS2-M1.flame_spread_rate"], [(0.071, "mm/s")])))
    svc = AssistantService(settings(tmp_path, "live"), DatasetEvidenceSource(store), fake)
    ans = svc.ask(AskRequest(question="Qual a velocidade de propagação em M1?", scope=M1))
    assert ans.mode.value == "LIVE" and len(ans.claims) == 1 and not ans.abstained


def test_repo_root_is_project_root():
    assert (REPO_ROOT / "planning").is_dir()


def test_server_refuses_to_start_with_invalid_dataset(monkeypatch):
    from fastapi.testclient import TestClient

    from backend.app.api import assistant as api
    from backend.app.dataset.store import DatasetValidationError
    from backend.app.main import app

    def broken(*a, **k):
        raise DatasetValidationError(["sintético: dataset inválido"])

    api.get_dataset_store.cache_clear()
    monkeypatch.setattr(api.DatasetStore, "load", broken)
    try:
        with pytest.raises(DatasetValidationError):
            with TestClient(app):
                pass
    finally:
        api.get_dataset_store.cache_clear()
