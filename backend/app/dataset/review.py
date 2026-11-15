"""Registro de revisão humana (promoção EXTRAIDO_NAO_REVISADO → CONFERIDO_FONTE).

Nunca é chamado automaticamente pela aplicação. Exige que o revisor:
- seja diferente de quem extraiu (T-19);
- informe (ou confirme) o valor, a unidade e a página do PDF — comparados CAMPO A CAMPO em
  `quantities.compare_fields` (dimensão + conversão; sem comparar texto de unidade);
- trabalhe sobre o arquivo com hash igual ao registrado (MATCH).
Qualquer divergência recusa a promoção. Após gravar, o dataset é recarregado e
validado; se a validação falhar, o arquivo original é restaurado.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.app.dataset.store import DEFAULT_DATA_DIR, REPO_ROOT, DatasetStore
from backend.app.integrity import assess
from backend.app.quantities import compare_fields
from backend.app.semantic import blocking, semantic_flags


class ReviewRejected(Exception):
    def __init__(self, message: str, code: str = "REVIEW_REJECTED", details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details


@dataclass
class ReviewResult:
    record_id: str
    reviewer: str
    reviewed_at: str
    checked_document_sha256: str


def check_review(
    *,
    status: str,
    extractor: "str | list[str] | None",
    reviewer: str,
    original_value,
    original_unit: str | None,
    evidence_pages: set,
    observed_value: str,
    observed_unit: str | None,
    observed_page_pdf: int,
    hash_problem: str | None,
) -> str:
    """Política ÚNICA de revisão (dataset curado e parâmetros importados). Devolve o nome do
    revisor normalizado ou lança `ReviewRejected`. Não grava nada."""
    if status != "EXTRAIDO_NAO_REVISADO":
        raise ReviewRejected(f"estado atual {status}; só EXTRAIDO_NAO_REVISADO pode ser promovido", "WRONG_STATE")
    reviewer = (reviewer or "").strip()
    if not reviewer:
        raise ReviewRejected("revisor obrigatório", "REVIEWER_REQUIRED")
    authors = [extractor] if isinstance(extractor, str) else list(extractor or [])
    if any(a and reviewer.lower() == a.strip().lower() for a in authors):
        raise ReviewRejected("revisor deve ser diferente de quem extraiu (T-19)", "REVIEWER_NOT_INDEPENDENT")
    if reviewer.lower().startswith(("claude", "gemini", "llm", "ia ", "ai ")):
        raise ReviewRejected("a revisão deve ser feita por uma pessoa da equipe", "REVIEWER_NOT_HUMAN")
    if hash_problem:
        raise ReviewRejected(hash_problem, "DOCUMENT_HASH")
    result = compare_fields(original_value=original_value, original_unit=original_unit,
                            evidence_pages=set(evidence_pages), observed_value=observed_value,
                            observed_unit=observed_unit, observed_page=observed_page_pdf)
    if not result["accepted"]:
        raise ReviewRejected(result["message_pt"], result["code"], {
            "accepted": False, "code": "REVIEW_MISMATCH", "reason_code": result["code"],
            "comparisons": result["comparisons"], "failed_fields": result["failed_fields"]})
    return reviewer


def scientific_gate(*, parameter: str, label: str | None, label_source: str | None, role: str, original: dict | None,
                    quotes: list[str], method: str | None, condition: dict | None, interpretation_confirmed: bool,
                    unit_verified_in_pdf: bool = False, comparisons: list | None = None) -> None:
    """Portão CIENTÍFICO da confirmação (depois de valor/unidade/página): integridade da grandeza, da unidade
    e da condição; ambiguidade semântica; e confirmação EXPLÍCITA da interpretação. Confirmar o número
    nunca valida, sozinho, o significado do parâmetro."""
    info = assess(parameter=parameter, role=role, original=original, quotes=quotes, method=method, condition=condition,
                  review={"components": {"unit_verified_in_pdf": unit_verified_in_pdf}})
    base = {"accepted": False, "code": "REVIEW_MISMATCH", "comparisons": comparisons or []}
    blocked = [f for f in info["findings"] if f["severity"] == "BLOCKING"]
    if blocked:
        raise ReviewRejected(
            "integridade da extração inconsistente: " + "; ".join(f["title_pt"] for f in blocked) +
            ". Corrija a extração (ou, para unidade ilegível no texto, confirme-a no PDF).", "INTEGRITY_INCONSISTENT",
            {**base, "reason_code": "INTEGRITY_INCONSISTENT", "integrity_findings": blocked})
    flags = blocking(semantic_flags(parameter=parameter, label=label, value=(original or {}).get("value"),
                                    unit=(original or {}).get("unit"), quotes=quotes, method=method, label_source=label_source))
    if flags:
        raise ReviewRejected(
            "interpretação científica inconclusiva: " + "; ".join(f["title_pt"] for f in flags) +
            ". Corrija a extração ou mantenha o valor pendente.", "SEMANTIC_AMBIGUITY",
            {**base, "reason_code": "SEMANTIC_AMBIGUITY", "semantic_flags": flags})
    if not interpretation_confirmed:
        raise ReviewRejected(
            "confirme também a INTERPRETAÇÃO: o trecho sustenta o significado atribuído ao parâmetro? "
            "A conferência do número e da unidade não valida o significado sozinha.", "INTERPRETATION_NOT_CONFIRMED",
            {**base, "reason_code": "INTERPRETATION_NOT_CONFIRMED"})


def apply_review(
    record_id: str,
    reviewer: str,
    observed_value: str,
    observed_unit: str | None,
    observed_page_pdf: int,
    notes: str | None = None,
    data_dir: Path = DEFAULT_DATA_DIR,
    sources_root: Path = REPO_ROOT,
    now: datetime | None = None,
    interpretation_confirmed: bool = False,
    unit_verified_in_pdf: bool = False,
) -> ReviewResult:
    store = DatasetStore.load(data_dir, sources_root)
    rec = store.records.get(record_id)
    if rec is None:
        raise ReviewRejected(f"registro inexistente: {record_id}", "RECORD_NOT_FOUND")
    evs = [store.evidence[e] for e in rec.evidence_ids]
    checked_sha = None
    hash_problem = None
    for d in {e.document_id for e in evs}:
        chk = store.source_checks.get(d)
        if chk is None or chk.status != "MATCH":
            hash_problem = f"documento {d}: hash não confere ({chk.status if chk else 'sem verificação'})"
            break
        checked_sha = chk.actual_sha256
    reviewer = check_review(
        status=rec.status, extractor=rec.extraction.by if rec.extraction else None, reviewer=reviewer,
        original_value=rec.original.value if rec.original else None,
        original_unit=rec.original.unit if rec.original else None,
        evidence_pages={e.locator.page_pdf_index for e in evs}, observed_value=observed_value,
        observed_unit=observed_unit, observed_page_pdf=observed_page_pdf, hash_problem=hash_problem)
    scientific_gate(
        parameter=rec.parameter, label=rec.label_pt, label_source="CURADORIA", role=rec.role,
        original={"value": rec.original.value, "unit": rec.original.unit} if rec.original else None,
        quotes=[e.quote for e in evs if e.quote], method=rec.extraction.method if rec.extraction else None,
        condition=None, interpretation_confirmed=interpretation_confirmed, unit_verified_in_pdf=unit_verified_in_pdf)

    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = next(p for p in sorted((Path(data_dir) / "parameters").glob("*.json"))
                if any(i.get("record_id") == record_id
                       for i in json.loads(p.read_text(encoding="utf-8-sig"))["items"]))
    backup = path.read_text(encoding="utf-8-sig")
    payload = json.loads(backup)
    for item in payload["items"]:
        if item["record_id"] == record_id:
            item["status"] = "CONFERIDO_FONTE"
            item["review"] = {"reviewer": reviewer, "reviewed_at": stamp, "notes": notes,
                              "checked_document_sha256": checked_sha}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        DatasetStore.load(data_dir, sources_root)
    except Exception:
        path.write_text(backup, encoding="utf-8")
        raise
    return ReviewResult(record_id, reviewer, stamp, checked_sha or "")
