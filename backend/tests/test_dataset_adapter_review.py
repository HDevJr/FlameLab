"""Adaptador DatasetStore → assistente e fluxo de revisão humana (dataset SINTÉTICO, provedor SIMULADO)."""

import json

import pytest

from backend.app.assistant.schemas import AskRequest
from backend.app.assistant.service import AssistantService
from backend.app.dataset.adapter import DatasetEvidenceSource
from backend.app.dataset.review import ReviewRejected, apply_review
from backend.app.dataset.store import DatasetStore
from backend.tests.assistant_fixtures import FakeProvider, claim, output, settings
from backend.tests.dataset_fixtures import base_parts, confirm, write_dataset

T1 = {"test_uids": ["SYN-T1"]}


def _source(tmp_path, parts=None, **kw):
    data = write_dataset(tmp_path, parts, **kw)
    return DatasetEvidenceSource(DatasetStore.load(data, sources_root=tmp_path))


def _svc(tmp_path, source, provider):
    return AssistantService(settings(tmp_path, "live"), source, provider)


def test_adapter_preserves_ids_and_links(tmp_path):
    src = _source(tmp_path, confirm(base_parts(), "SYN-T1.flame_spread_rate"))
    items = {i.evidence_id: i for i in src.items()}
    card = items["REC-SYN-T1.flame_spread_rate"]
    assert card.test_uid == "SYN-T1" and card.test_label == "T1"
    assert card.source_evidence_ids == ["EV-T1-spread"] and card.document_id == "SYN-DOC"
    assert card.quantities[0].value == pytest.approx(0.071) and card.quantities[0].unit == "mm/s"
    assert "GAP-SYN-T1-ambient_pressure" in items
    pending = items["REC-SYN-T1.airflow_velocity"]  # não conferido → valor retido
    assert pending.value_withheld and not pending.quantities and "9 cm/s" not in pending.text
    assert src.known_tests() == {"SYN-T1": "T1", "SYN-T2": "T2"}


def test_unreviewed_records_never_support_observations(tmp_path):
    fake = FakeProvider(output(claim("OBSERVACAO", "Em T1, a propagação foi 0,071 mm/s.",
                                     ["REC-SYN-T1.flame_spread_rate"], [(0.071, "mm/s")])))
    ans = _svc(tmp_path, _source(tmp_path), fake).ask(AskRequest(question="propagação", scope=T1))
    ret = {r.id: r for r in ans.retrieved}
    assert ret["REC-SYN-T1.flame_spread_rate"].value_withheld and "0,071" not in ret["REC-SYN-T1.flame_spread_rate"].text
    assert "0,071" not in fake.calls[0][1] and "0.071" not in fake.calls[0][1]  # valor não chega ao modelo
    assert not ans.claims
    assert {"V2_NUMBER_NOT_IN_EVIDENCE", "V4_OBSERVATION_WITHOUT_REVIEWED_RECORD"} <= set(ans.blocked_claims[0].reasons)
    assert any("valor retido" in w for w in ans.warnings)


def test_reviewed_record_supports_validated_answer(tmp_path):
    src = _source(tmp_path, confirm(base_parts(), "SYN-T1.flame_spread_rate"))
    fake = FakeProvider(output(claim("OBSERVACAO", "Em T1, a propagação foi 0,071 mm/s.",
                                     ["REC-SYN-T1.flame_spread_rate"], [(0.071, "mm/s")])))
    ans = _svc(tmp_path, src, fake).ask(AskRequest(question="Qual a propagação?", scope=T1))
    assert ans.mode.value == "LIVE" and not ans.abstained and len(ans.claims) == 1
    assert ans.claims[0].evidence_ids == ["REC-SYN-T1.flame_spread_rate"]
    assert ans.dataset_version == src.dataset_version
    assert "SYN-T2" not in fake.calls[0][1]  # ensaio fora do escopo não é enviado


def test_question_without_eligible_evidence_abstains(tmp_path):
    parts = base_parts()  # SYN-T2 sem registros nem lacunas
    parts["parameters"] = [r for r in parts["parameters"] if r["test_uid"] != "SYN-T2"]
    parts["evidence"] = [e for e in parts["evidence"] if e["test_uid"] != "SYN-T2"]
    fake = FakeProvider(output())
    ans = _svc(tmp_path, _source(tmp_path, parts), fake).ask(
        AskRequest(question="Qual a propagação?", scope={"test_uids": ["SYN-T2"]}))
    assert ans.mode.value == "DETERMINISTIC" and ans.abstain_reason.value == "NO_ELIGIBLE_EVIDENCE"
    assert not fake.calls


def test_hash_mismatch_omits_records(tmp_path):
    src = _source(tmp_path, confirm(base_parts(), "SYN-T1.flame_spread_rate"), source_bytes=b"alterado")
    assert not any(i.evidence_id.startswith("REC-") for i in src.items())
    assert any("hash" in w for w in src.warnings)


# ---------------------------------------------------------------- revisão humana
def _review(tmp_path, **kw):
    data = write_dataset(tmp_path)
    args = dict(record_id="SYN-T1.airflow_velocity", reviewer="Pessoa Revisora", observed_value="9",
                observed_unit="cm/s", observed_page_pdf=1, data_dir=data, sources_root=tmp_path, interpretation_confirmed=True)
    args.update(kw)
    return data, args


def test_review_success_promotes_and_revalidates(tmp_path):
    data, args = _review(tmp_path, observed_value="0,09", observed_unit="m/s")
    res = apply_review(**args)
    rec = DatasetStore.load(data, sources_root=tmp_path).records["SYN-T1.airflow_velocity"]
    assert rec.status == "CONFERIDO_FONTE" and rec.review.reviewer == "Pessoa Revisora"
    assert rec.review.checked_document_sha256 == res.checked_document_sha256


@pytest.mark.parametrize("patch,msg", [
    ({"observed_value": "8"}, "diverge"),
    ({"observed_unit": "mm/s"}, "diverge"),
    ({"reviewer": "fixture-extractor"}, "T-19"),
    ({"reviewer": "Claude"}, "pessoa"),
    ({"observed_page_pdf": 2}, "página"),
    ({"record_id": "SYN-T1.inexistente"}, "inexistente"),
])
def test_review_rejections_leave_file_unchanged(tmp_path, patch, msg):
    data, args = _review(tmp_path, **patch)
    before = (data / "parameters" / "syn.json").read_text(encoding="utf-8")
    with pytest.raises(ReviewRejected, match=msg):
        apply_review(**args)
    assert (data / "parameters" / "syn.json").read_text(encoding="utf-8") == before


def test_review_refused_when_hash_mismatch(tmp_path):
    data, args = _review(tmp_path)
    (tmp_path / "src" / "syn.bin").write_bytes(b"outro arquivo")
    with pytest.raises(ReviewRejected, match="hash"):
        apply_review(**args)


def test_review_cannot_repromote(tmp_path):
    data, args = _review(tmp_path)
    apply_review(**args)
    with pytest.raises(ReviewRejected, match="estado atual"):
        apply_review(**args)
    assert json.loads((data / "parameters" / "syn.json").read_text(encoding="utf-8"))["items"][0]["status"] == "CONFERIDO_FONTE"
