"""Dataset SINTÉTICO em diretório temporário (somente testes). Nada aqui é dado NASA.

Documento "SYN-DOC" = arquivo de bytes arbitrários criado no tmp, com sha256 real calculado.
Ensaios SYN-T1 e SYN-T2 existem apenas para exercitar validações.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

SYN_BYTES = b"FLAMELAB SYNTHETIC SOURCE - NOT A NASA DOCUMENT\n"
SYN_SHA = hashlib.sha256(SYN_BYTES).hexdigest()
EXTRACTOR = "fixture-extractor"


def _env(items):
    return {"contract_version": "1.0", "items": items}


def base_parts() -> dict:
    ev = lambda eid, test, col, page=1: {  # noqa: E731
        "evidence_id": eid, "document_id": "SYN-DOC", "test_uid": test,
        "locator": {"section": "1", "table": "X", "row_label": test, "column_label": col,
                    "page_printed": page, "page_pdf_index": page, "precision": "TABLE_CELL"},
        "quote": f"{test} | {col}", "method": "MANUAL_TRANSCRIPTION", "document_sha256_at_extraction": SYN_SHA}
    rec = lambda test, param, label, val, unit, norm, eid, role="CONDICAO": {  # noqa: E731
        "record_id": f"{test}.{param}", "test_uid": test, "investigation_id": "SYN-INV", "parameter": param,
        "label_pt": label, "role": role, "nature": "OBSERVADO", "status": "EXTRAIDO_NAO_REVISADO",
        "original": {"value": val, "unit": unit, "raw_text": str(val)},
        "normalized": norm, "evidence_ids": [eid],
        "extraction": {"method": "MANUAL_TRANSCRIPTION", "by": EXTRACTOR, "at": "2026-11-14T00:00:00Z"}}
    return {
        "documents": [{"document_id": "SYN-DOC", "title": "Synthetic", "kind": "SYNTHETIC", "url": "about:blank",
                       "local_path": "src/syn.bin", "sha256": SYN_SHA, "sha256_computed_at": "2026-11-14T00:00:00Z"}],
        "investigations": [{"investigation_id": "SYN-INV", "documents": ["SYN-DOC"]}],
        "tests": [{"test_uid": "SYN-T1", "investigation_id": "SYN-INV", "label": "T1"},
                  {"test_uid": "SYN-T2", "investigation_id": "SYN-INV", "label": "T2"}],
        "parameters": [
            rec("SYN-T1", "airflow_velocity", "Velocidade do ar", 9, "cm/s", {"value": 0.09, "unit": "m/s"}, "EV-T1-flow"),
            rec("SYN-T1", "flame_spread_rate", "Velocidade de propagação", 0.071, "mm/s",
                {"value": 7.1e-05, "unit": "m/s"}, "EV-T1-spread", role="OBSERVAVEL"),
            rec("SYN-T2", "flame_spread_rate", "Velocidade de propagação", 0.05, "mm/s",
                {"value": 5e-05, "unit": "m/s"}, "EV-T2-spread", role="OBSERVAVEL"),
        ],
        "evidence": [ev("EV-T1-flow", "SYN-T1", "Velocity"), ev("EV-T1-spread", "SYN-T1", "Spread"),
                     ev("EV-T2-spread", "SYN-T2", "Spread")],
        "gaps": [{"gap_id": "GAP-SYN-T1-ambient_pressure", "test_uid": "SYN-T1", "parameter": "ambient_pressure",
                  "label_pt": "Pressão", "keywords": ["pressão", "pressure"], "searched_in": ["SYN-DOC"],
                  "explanation_pt": "Pressão não informada (sintético)."}],
    }


def confirm(parts: dict, record_id: str, reviewer: str = "Revisora Sintética") -> dict:
    parts = copy.deepcopy(parts)
    for r in parts["parameters"]:
        if r["record_id"] == record_id:
            r["status"] = "CONFERIDO_FONTE"
            r["review"] = {"reviewer": reviewer, "reviewed_at": "2026-11-14T01:00:00Z", "checked_document_sha256": SYN_SHA}
    return parts


def write_dataset(root: Path, parts: dict | None = None, source_bytes: bytes | None = SYN_BYTES) -> Path:
    """Grava o dataset em root/data e o 'documento' em root/src/syn.bin. Retorna root/data."""
    parts = parts if parts is not None else base_parts()
    data = root / "data"
    for name in ("documents", "investigations"):
        (data).mkdir(parents=True, exist_ok=True)
        (data / f"{name}.json").write_text(json.dumps(_env(parts[name]), ensure_ascii=False), encoding="utf-8")
    for name in ("tests", "parameters", "evidence", "gaps"):
        (data / name).mkdir(parents=True, exist_ok=True)
        (data / name / "syn.json").write_text(json.dumps(_env(parts[name]), ensure_ascii=False), encoding="utf-8")
    if source_bytes is not None:
        (root / "src").mkdir(exist_ok=True)
        (root / "src" / "syn.bin").write_bytes(source_bytes)
    return data
