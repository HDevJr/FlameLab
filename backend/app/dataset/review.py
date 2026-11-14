"""Registro de revisão humana (promoção EXTRAIDO_NAO_REVISADO → CONFERIDO_FONTE).

Nunca é chamado automaticamente pela aplicação. Exige que o revisor:
- seja diferente de quem extraiu (T-19);
- informe o valor e a unidade que LEU no PDF, e a página do PDF onde leu;
- trabalhe sobre o arquivo com hash igual ao registrado (MATCH).
Qualquer divergência recusa a promoção. Após gravar, o dataset é recarregado e
validado; se a validação falhar, o arquivo original é restaurado.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.app.assistant.numbers import extract_numbers
from backend.app.dataset.store import DEFAULT_DATA_DIR, REPO_ROOT, DatasetStore
from backend.app import units


class ReviewRejected(Exception):
    pass


@dataclass
class ReviewResult:
    record_id: str
    reviewer: str
    reviewed_at: str
    checked_document_sha256: str


def _parse_observed(value: str) -> float | None:
    found = extract_numbers(value.strip())
    if len(found) == 1 and found[0].value is not None and found[0].raw.strip() == value.strip():
        return found[0].value
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


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
) -> ReviewResult:
    store = DatasetStore.load(data_dir, sources_root)
    rec = store.records.get(record_id)
    if rec is None:
        raise ReviewRejected(f"registro inexistente: {record_id}")
    if rec.status != "EXTRAIDO_NAO_REVISADO":
        raise ReviewRejected(f"estado atual {rec.status}; só EXTRAIDO_NAO_REVISADO pode ser promovido")
    reviewer = reviewer.strip()
    if not reviewer:
        raise ReviewRejected("revisor obrigatório")
    if rec.extraction and reviewer.lower() == rec.extraction.by.strip().lower():
        raise ReviewRejected("revisor deve ser diferente de quem extraiu (T-19)")
    if reviewer.lower().startswith(("claude", "gemini", "llm", "ia ", "ai ")):
        raise ReviewRejected("a revisão deve ser feita por uma pessoa da equipe")

    evs = [store.evidence[e] for e in rec.evidence_ids]
    docs = {e.document_id for e in evs}
    checked_sha = None
    for d in docs:
        chk = store.source_checks.get(d)
        if chk is None or chk.status != "MATCH":
            raise ReviewRejected(f"documento {d}: hash não confere ({chk.status if chk else 'sem verificação'})")
        checked_sha = chk.actual_sha256
    if observed_page_pdf not in {e.locator.page_pdf_index for e in evs}:
        raise ReviewRejected("página do PDF informada não corresponde a nenhuma evidência do registro")

    original = rec.original
    if original is None:
        raise ReviewRejected("registro sem valor original")
    if isinstance(original.value, str):
        if observed_value.strip().lower() not in original.value.lower():
            raise ReviewRejected("valor textual lido não corresponde ao registro")
    else:
        val = _parse_observed(observed_value)
        if val is None:
            raise ReviewRejected("valor observado ilegível ou ambíguo")
        a = units.normalize(val, observed_unit)
        b = units.normalize(float(original.value), original.unit)
        if a is None or b is None or not units.same_quantity(a, b, rel_tol=1e-9):
            raise ReviewRejected(
                f"valor lido ({observed_value} {observed_unit or ''}) diverge do registro "
                f"({original.value} {original.unit or ''}); registro NÃO promovido")

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
