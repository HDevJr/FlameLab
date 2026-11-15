"""DatasetStore: invariantes I-1..I-10, referências, unidades e hash (dataset SINTÉTICO)."""

import copy

import pytest

from backend.app.dataset.hashing import sha256_file, verify_source
from backend.app.dataset.store import DatasetStore, DatasetValidationError
from backend.tests.dataset_fixtures import SYN_SHA, base_parts, confirm, write_dataset


def _load(tmp_path, parts=None, **kw):
    data = write_dataset(tmp_path, parts, **kw)
    return DatasetStore.load(data, sources_root=tmp_path)


def _errors(tmp_path, parts):
    with pytest.raises(DatasetValidationError) as ei:
        _load(tmp_path, parts)
    return "\n".join(ei.value.errors)


def _mut(fn):
    p = copy.deepcopy(base_parts())
    fn(p)
    return p


# ---------------------------------------------------------------- registro válido / versão
def test_valid_record_loads_and_version_is_stable(tmp_path):
    s1 = _load(tmp_path)
    assert len(s1.records) == 3 and s1.records["SYN-T1.airflow_velocity"].normalized.value == pytest.approx(0.09)
    s2 = DatasetStore.load(tmp_path / "data", sources_root=tmp_path)
    assert s1.dataset_version == s2.dataset_version and s1.dataset_version.startswith("sha256:")


# ---------------------------------------------------------------- hash
def test_hash_match(tmp_path):
    s = _load(tmp_path)
    assert s.source_checks["SYN-DOC"].status == "MATCH" and s.document_ok("SYN-DOC")


def test_hash_mismatch_is_reported_not_rewritten(tmp_path):
    s = _load(tmp_path, source_bytes=b"arquivo alterado")
    chk = s.source_checks["SYN-DOC"]
    assert chk.status == "MISMATCH" and chk.expected_sha256 == SYN_SHA and chk.actual_sha256 != SYN_SHA
    assert not s.document_ok("SYN-DOC")
    assert s.documents["SYN-DOC"].sha256 == SYN_SHA  # esperado preservado


def test_hash_file_missing(tmp_path):
    s = _load(tmp_path, source_bytes=None)
    assert s.source_checks["SYN-DOC"].status == "FILE_MISSING" and s.document_ok("SYN-DOC")


def test_path_outside_root_rejected(tmp_path):
    assert verify_source("X", "../fora.bin", None, tmp_path).status == "PATH_REJECTED"
    assert "local_path" in _errors(tmp_path, _mut(lambda p: p["documents"][0].update(local_path="../x.pdf")))


def test_i10_sha_without_computed_at(tmp_path):
    assert "I-10" in _errors(tmp_path, _mut(lambda p: p["documents"][0].update(sha256_computed_at=None)))


# ---------------------------------------------------------------- registros
def test_record_without_source_rejected(tmp_path):
    assert "sem evidência" in _errors(tmp_path, _mut(lambda p: p["parameters"][0].update(evidence_ids=[])))


def test_record_with_unknown_evidence_rejected(tmp_path):
    assert "evidência inexistente" in _errors(tmp_path, _mut(lambda p: p["parameters"][0].update(evidence_ids=["EV-X"])))


def test_i1_missing_field_must_be_null(tmp_path):
    def f(p):
        p["parameters"][0].update(status="AUSENTE")
    assert "I-1" in _errors(tmp_path, _mut(f))

    def ok(p):
        p["parameters"][0].update(status="AUSENTE", original=None, normalized=None)
    s = _load(tmp_path, _mut(ok))
    assert s.records["SYN-T1.airflow_velocity"].original is None


def test_gap_loads_as_absent(tmp_path):
    s = _load(tmp_path)
    g = s.gaps["GAP-SYN-T1-ambient_pressure"]
    assert g.status == "AUSENTE" and not hasattr(g, "original")


def test_i8_unit_conversion_checked(tmp_path):
    assert "I-8" in _errors(tmp_path, _mut(lambda p: p["parameters"][0].update(normalized={"value": 9, "unit": "m/s"})))
    assert "I-8" in _errors(tmp_path, _mut(lambda p: p["parameters"][0]["original"].update(unit="furlong/s")))
    assert "I-8" in _errors(tmp_path, _mut(lambda p: p["parameters"][0].update(normalized=None)))


def test_i7_evidence_from_other_test_rejected(tmp_path):
    assert "I-7" in _errors(tmp_path, _mut(lambda p: p["parameters"][0].update(evidence_ids=["EV-T2-spread"])))


def test_incomplete_review_rejected(tmp_path):
    def no_reviewer(p):
        p["parameters"][0].update(status="CONFERIDO_FONTE")
    assert "I-5" in _errors(tmp_path, _mut(no_reviewer))
    same = confirm(base_parts(), "SYN-T1.airflow_velocity", reviewer="fixture-extractor")
    assert "T-19" in _errors(tmp_path, same)


def test_i5_conferido_requires_page(tmp_path):
    p = confirm(base_parts(), "SYN-T1.airflow_velocity")
    p["evidence"][0]["locator"].update(page_pdf_index=None)
    assert "I-5" in _errors(tmp_path, p)


def test_review_on_other_document_version_rejected(tmp_path):
    p = confirm(base_parts(), "SYN-T1.airflow_velocity")
    p["parameters"][0]["review"]["checked_document_sha256"] = "0" * 64
    assert "outra versão" in _errors(tmp_path, p)


def test_evidence_from_other_document_version_rejected(tmp_path):
    assert "versão do documento" in _errors(
        tmp_path, _mut(lambda p: p["evidence"][0].update(document_sha256_at_extraction="1" * 64)))


@pytest.mark.parametrize("patch,code", [
    ({"status": "CALCULADO", "nature": "CALCULADO"}, "I-2"),
    ({"nature": "CALCULADO"}, "I-4"),
    ({"status": "INFERIDO", "nature": "INFERIDO"}, "I-3"),
    ({"nature": "CONCEITUAL"}, "I-9"),
])
def test_invariants_i2_i3_i4_i9(tmp_path, patch, code):
    assert code in _errors(tmp_path, _mut(lambda p: p["parameters"][0].update(**patch)))


def test_i6_observable_never_model_approved(tmp_path):
    p = confirm(base_parts(), "SYN-T1.flame_spread_rate")
    p["parameters"][1].update(status="APROVADO_MODELO", model_review={
        "reviewer": "x", "reviewed_at": "2026-11-14T02:00:00Z", "validity_domain_pt": "x"})
    assert "I-6" in _errors(tmp_path, p)


# ---------------------------------------------------------------- dataset inválido
def test_invalid_json_and_contract_version(tmp_path):
    data = write_dataset(tmp_path)
    (data / "tests" / "bad.json").write_text("{nao é json", encoding="utf-8")
    (data / "gaps" / "old.json").write_text('{"contract_version": "0.9", "items": []}', encoding="utf-8")
    with pytest.raises(DatasetValidationError) as ei:
        DatasetStore.load(data, sources_root=tmp_path)
    msg = "\n".join(ei.value.errors)
    assert "JSON ilegível" in msg and "contract_version" in msg


def test_duplicate_ids_and_unknown_test(tmp_path):
    def f(p):
        p["evidence"].append(copy.deepcopy(p["evidence"][0]))
        p["gaps"][0].update(test_uid="SYN-T9", gap_id="GAP-SYN-T9-ambient_pressure")
    msg = _errors(tmp_path, _mut(f))
    assert "duplicado" in msg and "ensaio inexistente" in msg


def test_sha256_file_helper(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"abc")
    assert sha256_file(f) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
