"""Revisão humana pela interface (API). Mesma política do script; trilha de auditoria; dataset SINTÉTICO."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.app.api.platform import Services
from backend.app.main import app
from backend.tests.dataset_fixtures import EXTRACTOR, write_dataset
from backend.tests.test_ingest import FakeProvider, fetch, make_pdf, upload

REC = "SYN-T1.airflow_velocity"
GOOD = {"action": "CONFIRM", "reviewer": "Pessoa Revisora", "observed_value": "9", "observed_unit": "cm/s",
        "observed_page_pdf": 1, "checked_pdf": True, "notes": "conferido", "interpretation_confirmed": True}


@pytest.fixture
def client(tmp_path):
    data = write_dataset(tmp_path)
    Services.dataset_dirs = (data, tmp_path)
    return TestClient(app)


def review(client, rid=REC, **patch):
    return client.post(f"/api/records/{rid}/review", json={**GOOD, **patch})


def params_file(tmp_path):
    return (tmp_path / "data" / "parameters" / "syn.json").read_text(encoding="utf-8")


def test_confirm_curated_record_updates_state_log_and_audit(client, tmp_path):
    r = review(client)
    assert r.status_code == 200 and r.json()["data"]["status"] == "CONFERIDO_FONTE"
    exp = client.get("/api/experiments/SYN-T1").json()["data"]
    p = next(x for x in exp["parameters"] if x["record_id"] == REC)
    assert p["status"] == "CONFERIDO_FONTE" and p["review"]["reviewer"] == "Pessoa Revisora"
    assert p["review"]["checked_document_sha256"]
    assert exp["review"]["reviewed"] == 1
    assert [e["outcome"] for e in p["events"]] == ["APPROVED"]
    log = (tmp_path / "curation_logs" / "SYN-T1_curation_log.md").read_text(encoding="utf-8")
    assert REC in log and "Pessoa Revisora" in log and "pela interface" in log


@pytest.mark.parametrize("patch,code", [
    ({"observed_value": "8"}, "VALUE_MISMATCH"),
    ({"observed_unit": "mm/s"}, "VALUE_MISMATCH"),
    ({"reviewer": EXTRACTOR}, "REVIEWER_NOT_INDEPENDENT"),
    ({"reviewer": "Claude"}, "REVIEWER_NOT_HUMAN"),
    ({"reviewer": "  "}, "REVIEWER_REQUIRED"),
    ({"observed_page_pdf": 2}, "PAGE_MISMATCH"),
    ({"checked_pdf": False}, "DECLARATION_REQUIRED"),
    ({"observed_value": ""}, "OBSERVED_REQUIRED"),
    ({"observed_page_pdf": None}, "OBSERVED_REQUIRED"),
])
def test_refusals_follow_the_script_policy_and_change_nothing(client, tmp_path, patch, code):
    before = params_file(tmp_path)
    r = review(client, **patch)
    assert r.status_code == 422 and r.json()["error"]["code"] == code
    assert params_file(tmp_path) == before
    status = client.get("/api/experiments/SYN-T1").json()["data"]["parameters"]
    assert next(x for x in status if x["record_id"] == REC)["status"] == "EXTRAIDO_NAO_REVISADO"


def test_refused_attempts_are_audited(client):
    review(client, observed_value="8")
    ev = client.get(f"/api/records/{REC}/events").json()["data"]
    assert ev[-1]["outcome"] == "REFUSED" and ev[-1]["code"] == "VALUE_MISMATCH" and ev[-1]["reviewer"] == "Pessoa Revisora"


def test_hash_mismatch_blocks_approval(client, tmp_path):
    (tmp_path / "src" / "syn.bin").write_bytes(b"arquivo alterado")
    r = review(client)
    assert r.status_code == 422 and r.json()["error"]["code"] == "DOCUMENT_HASH"


def test_cannot_confirm_twice(client):
    assert review(client).status_code == 200
    again = review(client)
    assert again.status_code == 422 and again.json()["error"]["code"] == "WRONG_STATE"


def test_doubt_keeps_record_pending_and_requires_reason(client):
    assert review(client, action="DOUBT", notes=None).json()["error"]["code"] == "NOTES_REQUIRED"
    r = review(client, action="DOUBT", notes="a célula está ilegível no PDF", observed_value=None)
    assert r.status_code == 200 and r.json()["data"]["status"] == "EXTRAIDO_NAO_REVISADO"
    ev = client.get(f"/api/records/{REC}/events").json()["data"]
    assert ev[-1]["action"] == "DOUBT" and "ilegível" in ev[-1]["notes"]


def test_divergence_is_recorded_without_promoting(client, tmp_path):
    before = params_file(tmp_path)
    assert review(client, action="DIVERGENCE", observed_value="", notes="x").json()["error"]["code"] == "OBSERVED_REQUIRED"
    r = review(client, action="DIVERGENCE", observed_value="12", notes="o PDF mostra 12 cm/s na tabela")
    assert r.status_code == 200 and r.json()["data"]["status"] == "EXTRAIDO_NAO_REVISADO"
    assert params_file(tmp_path) == before  # o registro nunca é "corrigido" automaticamente
    ev = client.get(f"/api/records/{REC}/events").json()["data"]
    assert ev[-1]["action"] == "DIVERGENCE" and ev[-1]["observed_value"] == "12"


def test_unknown_record_and_invalid_ids(client):
    assert review(client, rid="SYN-T1.nao_existe").status_code == 404
    assert client.post("/api/records/..%2Fx/review", json=GOOD).status_code in (404, 422)
    assert client.post(f"/api/records/{REC}/review", json={**GOOD, "action": "APROVAR"}).status_code == 422


# ---------------------------------------------------------------- parâmetros de artigo importado
def _imported(client, tmp_path, unit="degrees C"):
    out = {"experiments": [{"label": "Run A", "description": "d", "phenomena": ["fluid_flow"], "parameters": [
        {"name": "fluid_temperature", "role": "CONDICAO", "value": "25", "unit": unit, "page": 1,
         "quote": "The test fluid temperature was 25 degrees C"}], "missing": []}]}
    Services.provider = FakeProvider(out)
    rec = fetch(client, upload(client, make_pdf(tmp_path / "a.pdf")))
    return rec, rec["experiments"][0]["parameters"][0]["record_id"]


IMP = {"action": "CONFIRM", "reviewer": "Ana Souza", "observed_value": "25", "observed_unit": "degrees C",
       "observed_page_pdf": 1, "checked_pdf": True, "interpretation_confirmed": True}


def test_imported_parameter_review_uses_the_same_policy(client, tmp_path):
    rec, rid = _imported(client, tmp_path)
    for patch, code in [({"observed_value": "26"}, "VALUE_MISMATCH"), ({"observed_unit": "K"}, "VALUE_MISMATCH"),
                        ({"reviewer": "fake-model"}, "REVIEWER_NOT_INDEPENDENT"), ({"reviewer": "Gemini"}, "REVIEWER_NOT_HUMAN"),
                        ({"observed_page_pdf": 3}, "PAGE_MISMATCH"), ({"checked_pdf": False}, "DECLARATION_REQUIRED")]:
        r = client.post(f"/api/records/{rid}/review", json={**IMP, **patch})
        assert r.status_code == 422 and r.json()["error"]["code"] == code, (patch, r.json())
    ok = client.post(f"/api/records/{rid}/review", json=IMP)
    assert ok.status_code == 200 and ok.json()["data"]["status"] == "CONFERIDO_FONTE"
    exp = client.get(f"/api/experiments/{rec['experiments'][0]['experiment_id']}").json()["data"]
    p = exp["parameters"][0]
    assert p["status"] == "CONFERIDO_FONTE" and p["review"]["reviewer"] == "Ana Souza"
    assert p["review"]["checked_document_sha256"] == rec["sha256"]
    assert exp["review"]["reviewed"] == 1
    assert client.post(f"/api/records/{rid}/review", json=IMP).json()["error"]["code"] == "WRONG_STATE"


def test_imported_review_blocked_if_stored_pdf_changed(client, tmp_path):
    rec, rid = _imported(client, tmp_path)
    pdf = tmp_path / "var" / "imports" / rec["import_id"] / "source.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"\n%adulterado")
    r = client.post(f"/api/records/{rid}/review", json=IMP)
    assert r.status_code == 422 and r.json()["error"]["code"] == "DOCUMENT_HASH"


def test_imported_review_requires_literal_evidence(client, tmp_path):
    rec, rid = _imported(client, tmp_path)
    path = tmp_path / "var" / "imports" / rec["import_id"] / "import.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["experiments"][0]["parameters"][0]["evidence"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    r = client.post(f"/api/records/{rid}/review", json=IMP)
    assert r.status_code == 422 and r.json()["error"]["code"] == "EVIDENCE_INSUFFICIENT"


def test_review_does_not_touch_the_real_dataset(client, tmp_path):
    from backend.app.dataset.store import DEFAULT_DATA_DIR

    real = (DEFAULT_DATA_DIR / "parameters" / "BASS2-M1.json").read_text(encoding="utf-8-sig")
    review(client)
    assert (DEFAULT_DATA_DIR / "parameters" / "BASS2-M1.json").read_text(encoding="utf-8-sig") == real


def test_audit_events_is_read_only_and_newest_first(client):
    """GET /api/audit/events devolve a trilha sem alterá-la."""
    r = client.get("/api/audit/events?limit=5")
    assert r.status_code == 200
    data = r.json()["data"]
    assert set(data) == {"total", "events"} and len(data["events"]) <= 5
    ats = [e["at"] for e in data["events"]]
    assert ats == sorted(ats, reverse=True)
