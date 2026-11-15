"""Relatório de INCONSISTÊNCIAS de integridade científica em registros já revisados (somente leitura).

Para cada parâmetro: o que a fonte sustenta (unidade, condição, interpretação), o que a confirmação humana efetivamente
cobriu (número/unidade × interpretação) e que correção AUDITÁVEL se propõe. Nada é alterado: registros históricos só
mudam por ação humana explícita (CORRECT/REOPEN), que fica na trilha.
"""

from __future__ import annotations

from typing import Any

from backend.app.catalog.service import Catalog
from backend.app.nasa.provenance.log import utc_now
from backend.app.quantities import clean_text
from backend.app.review_service import read_events
from backend.app.semantic import blocking

PROPOSAL = {
    "INITIAL_FROM_RANGE": ("CORRECT_OR_REOPEN", "Corrigir a extração para refletir o que o trecho diz (ex.: “Temperatura mínima do ciclo”) ou reabrir e manter pendente."),
    "FINAL_FROM_RANGE": ("CORRECT_OR_REOPEN", "Corrigir o nome (limite superior de um intervalo) ou reabrir e manter pendente."),
    "ENDPOINT_MISMATCH": ("CORRECT_OR_REOPEN", "O número está na outra extremidade do intervalo: corrigir o nome ou reabrir."),
    "INCREMENT_AS_ABSOLUTE": ("CORRECT_OR_REOPEN", "O número é um incremento (diferença): corrigir o nome (ex.: “incremento”) ou reabrir."),
    "UNIT_SYMBOL_UNREADABLE": ("REOPEN_THEN_CONFIRM", "Abrir o PDF na página, ver a unidade, reabrir e reconfirmar marcando “vi a unidade no PDF”."),
    "UNIT_NOT_IN_EVIDENCE": ("CORRECT_OR_REOPEN", "A unidade não está no trecho: corrigir a unidade (ou removê-la) ou reabrir."),
    "UNIT_MISSING_FOR_QUANTITY": ("CORRECT_OR_REOPEN", "Informar a unidade que a fonte traz, ou reabrir."),
    "UNIT_DIMENSION_MISMATCH": ("CORRECT_OR_REOPEN", "Corrigir a unidade ou o nome do parâmetro, ou reabrir."),
    "UNIT_UNSUPPORTED": ("CORRECT_OR_REOPEN", "Corrigir para uma unidade suportada ou ampliar a tabela de unidades."),
    "CONDITION_NOT_RECORDED": ("CORRECT", "Corrigir a extração registrando a condição associada (ex.: “a 20 °C”); a conferência é reaberta."),
    "CONDITION_MISMATCH": ("CORRECT", "Corrigir o valor e a unidade da condição conforme o trecho citado; a conferência é reaberta."),
    "VALUE_NOT_IN_QUOTE": ("REOPEN", "O número não está no trecho citado: reabrir."),
}


def build_integrity_report(catalog: Catalog) -> dict[str, Any]:
    events = read_events()
    by_record: dict[str, list[dict[str, Any]]] = {}
    for e in events:
        by_record.setdefault(e.get("record_id", ""), []).append(e)

    records: list[dict[str, Any]] = []
    for doc in catalog.documents():
        for summary in doc["experiments"]:
            exp = catalog.experiment(summary["experiment_id"])
            for p in (exp or {}).get("parameters", []):
                records.append(_assess_record(doc, exp, p, by_record.get(p["record_id"], [])))

    order = {"INCONSISTENT_CONFIRMED": 0, "LEGACY_REVIEW": 1, "ATTENTION": 2, "OK": 3}
    records.sort(key=lambda r: (order[r["classification"]], r["record_id"]))
    counts: dict[str, int] = {}
    for r in records:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    confirmed = [r for r in records if r["status"] in ("CONFERIDO_FONTE", "APROVADO_MODELO")]
    return {
        "generated_at": utc_now(), "read_only": True,
        "summary": {"records": len(records), "confirmed": len(confirmed), "by_classification": counts,
                    "confirmed_with_blocking_inconsistency": counts.get("INCONSISTENT_CONFIRMED", 0),
                    "confirmed_without_interpretation_confirmation": sum(
                        1 for r in confirmed if (r["review"] or {}).get("scope") != "FULL")},
        "records": records,
        "note_pt": ("Nenhum registro foi alterado. A correção é uma ação humana explícita (Corrigir extração ou Reabrir revisão), "
                    "que preserva o original e fica na trilha de auditoria."),
    }


def _assess_record(doc: dict[str, Any], exp: dict[str, Any], p: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    confirmed = p["status"] in ("CONFERIDO_FONTE", "APROVADO_MODELO")
    findings = list((p.get("integrity") or {}).get("findings") or [])
    flags = blocking(p.get("semantic_flags") or [])
    block_codes = [f["code"] for f in findings if f["severity"] == "BLOCKING"] + [f["code"] for f in flags]
    scope = p.get("review_scope")
    anomalies: list[dict[str, Any]] = []
    o = p.get("original") or {}
    for e in events:
        if e.get("outcome") != "APPROVED":
            continue
        if isinstance(o.get("value"), str):
            if e.get("observed_unit"):
                anomalies.append({"code": "UNIT_SUBMITTED_FOR_TEXT_VALUE", "at": e["at"],
                                  "detail_pt": f"Na aprovação foi submetida a unidade “{e['observed_unit']}” para um valor textual; a unidade não se aplica e não foi validada (regra antiga ignorava unidade em texto)."})
            if clean_text(e.get("observed_value")).lower() != clean_text(o["value"]).lower():
                anomalies.append({"code": "PARTIAL_TEXT_CONFIRMATION", "at": e["at"],
                                  "detail_pt": f"Foi confirmado apenas o trecho “{e.get('observed_value')}” de “{o['value']}” (a regra antiga aceitava substring)."})
    if confirmed and block_codes:
        cls = "INCONSISTENT_CONFIRMED"
    elif confirmed and scope != "FULL":
        cls = "LEGACY_REVIEW"
    elif findings or p.get("semantic_flags"):
        cls = "ATTENTION"
    else:
        cls = "OK"
    proposals = []
    for code in dict.fromkeys(block_codes):
        kind, text = PROPOSAL.get(code, ("REOPEN", "Reabrir a revisão."))
        proposals.append({"finding": code, "action": kind, "proposal_pt": text})
    if confirmed and scope != "FULL" and not block_codes:
        proposals.append({"finding": "REVIEW_LEGACY", "action": "REOPEN_THEN_CONFIRM",
                          "proposal_pt": "A revisão comparou número, unidade e página, mas NÃO confirmou a interpretação. Reabrir e reconfirmar marcando a confirmação da interpretação."})
    ev = (p.get("evidence") or [{}])[0]
    rv = p.get("review") or {}
    return {
        "record_id": p["record_id"], "document_id": doc["document_id"], "experiment_id": exp["experiment_id"],
        "parameter": p["parameter"], "label_pt": p.get("label_pt"), "role": p["role"], "status": p["status"],
        "value": o.get("value"), "unit_raw": o.get("unit"), "unit_state": (p.get("unit_info") or {}).get("state"),
        "unit_source": (p.get("integrity") or {}).get("unit_source"), "page": ev.get("page_pdf"), "quote": ev.get("quote"),
        "review": {"reviewer": rv.get("reviewer"), "reviewed_at": rv.get("reviewed_at"), "scope": scope,
                   "components": rv.get("components")} if rv else None,
        "classification": cls, "integrity_findings": findings,
        "semantic_flags": p.get("semantic_flags") or [], "audit_anomalies": anomalies,
        "attempts": {"refused": sum(1 for e in events if e.get("outcome") == "REFUSED"),
                     "approved": sum(1 for e in events if e.get("outcome") == "APPROVED")},
        "proposals": proposals,
    }
