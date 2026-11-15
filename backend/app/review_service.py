"""Revisão humana pela interface.

UMA política: `dataset.review.check_review` (a mesma do `scripts/review_record.py`).
- Registro do dataset curado: `apply_review` (grava em `data/parameters`, revalida e restaura se falhar)
  e anexa a linha ao log de curadoria do ensaio.
- Registro de artigo importado: mesma checagem; a promoção grava em `var/imports/<id>/import.json`.
Toda tentativa (confirmada, recusada, dúvida, divergência) vai para a trilha de auditoria
`var/audit/review_events.jsonl`. A identidade do revisor é DECLARADA (não há autenticação).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable

from backend.app import workspace
from backend.app.dataset.review import ReviewRejected, apply_review, check_review
from backend.app.dataset.store import DEFAULT_DATA_DIR, REPO_ROOT, DatasetStore
from backend.app.ingest.pdf import sha256_bytes_file
from backend.app.nasa.provenance.log import utc_now

ACTIONS = ("CONFIRM", "DOUBT", "DIVERGENCE")
_lock = threading.Lock()


def _events_file() -> Path:
    return workspace.area("audit") / "review_events.jsonl"


def append_event(event: dict[str, Any]) -> dict[str, Any]:
    event = {"at": utc_now(), **event}
    with _lock, _events_file().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def events_for(record_id: str) -> list[dict[str, Any]]:
    path = _events_file()
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("record_id") == record_id:
            out.append(ev)
    return out


class ReviewService:
    def __init__(self, store: Callable[[], DatasetStore], reload_dataset: Callable[[], None],
                 data_dir: Path = DEFAULT_DATA_DIR, sources_root: Path = REPO_ROOT,
                 curation_log_dir: Path | None = None):
        self._store = store
        self._reload = reload_dataset
        self._data_dir = data_dir
        self._sources_root = sources_root
        self._log_dir = curation_log_dir or REPO_ROOT / "docs" / "curation"

    # ---------------------------------------------------------------- localizar
    def _imported(self, record_id: str):
        for folder in workspace.area("imports").iterdir():
            rec = workspace.read_json(folder / "import.json")
            for exp in (rec or {}).get("experiments") or []:
                for p in exp["parameters"]:
                    if p["record_id"] == record_id:
                        return rec, exp, p
        return None

    # ---------------------------------------------------------------- ação
    def submit(self, record_id: str, action: str, reviewer: str, observed_value: str | None,
               observed_unit: str | None, observed_page_pdf: int | None, notes: str | None,
               checked_pdf: bool) -> dict[str, Any]:
        record_id = workspace.safe_id(record_id)
        if action not in ACTIONS:
            raise ReviewRejected("ação inválida", "INVALID_ACTION")
        reviewer = (reviewer or "").strip()
        notes = (notes or "").strip() or None
        base = {"record_id": record_id, "reviewer": reviewer, "action": action, "notes": notes,
                "observed_value": observed_value, "observed_unit": observed_unit,
                "observed_page_pdf": observed_page_pdf}
        curated = self._store().records.get(record_id)
        imported = None if curated else self._imported(record_id)
        if curated is None and imported is None:
            raise ReviewRejected(f"registro inexistente: {record_id}", "RECORD_NOT_FOUND")

        if action in ("DOUBT", "DIVERGENCE"):
            if not reviewer:
                raise ReviewRejected("revisor obrigatório", "REVIEWER_REQUIRED")
            if not notes:
                raise ReviewRejected("descreva o motivo (dúvida ou divergência)", "NOTES_REQUIRED")
            if action == "DIVERGENCE" and not (observed_value or "").strip():
                raise ReviewRejected("informe o valor que você leu no PDF", "OBSERVED_REQUIRED")
            current = curated.status if curated else imported[2]["status"]
            ev = append_event({**base, "outcome": "RECORDED", "state_after": current})
            return {"outcome": "RECORDED", "status": current, "event": ev}

        # CONFIRM
        if not checked_pdf:
            raise ReviewRejected("declare que conferiu o PDF original", "DECLARATION_REQUIRED")
        if observed_page_pdf is None or not (observed_value or "").strip():
            raise ReviewRejected("informe o valor, a unidade e a página que você leu", "OBSERVED_REQUIRED")
        try:
            result = (self._confirm_curated if curated else self._confirm_imported)(
                imported, record_id, reviewer, observed_value or "", observed_unit, observed_page_pdf, notes)
        except ReviewRejected as exc:
            append_event({**base, "outcome": "REFUSED", "code": exc.code, "message": str(exc)})
            raise
        ev = append_event({**base, "outcome": "APPROVED", "state_after": "CONFERIDO_FONTE",
                           "checked_document_sha256": result["checked_document_sha256"]})
        return {"outcome": "APPROVED", "status": "CONFERIDO_FONTE", **result, "event": ev}

    def _confirm_curated(self, _imported, record_id, reviewer, value, unit, page, notes) -> dict[str, Any]:
        res = apply_review(record_id, reviewer, value, unit, page, notes, self._data_dir, self._sources_root)
        test_uid = self._store().records[record_id].test_uid
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log = self._log_dir / f"{test_uid}_curation_log.md"
        if not log.exists():
            log.write_text("# Log de curadoria\n\n| Data (UTC) | Registro | Estado | Responsável | Detalhe | Documento | Notas |\n"
                           "|---|---|---|---|---|---|---|\n", encoding="utf-8")
        with log.open("a", encoding="utf-8") as fh:
            fh.write(f"| {res.reviewed_at} | {res.record_id} | CONFERIDO_FONTE | {res.reviewer} | "
                     f"valor lido: {value} {unit or ''} · PDF p. {page} (pela interface) | "
                     f"sha256 {res.checked_document_sha256[:12]}… | {notes or ''} |\n")
        self._reload()
        return {"reviewed_at": res.reviewed_at, "checked_document_sha256": res.checked_document_sha256,
                "reviewer": res.reviewer}

    def _confirm_imported(self, imported, record_id, reviewer, value, unit, page, notes) -> dict[str, Any]:
        rec, exp, param = imported
        pdf = workspace.area("imports") / workspace.safe_id(rec["import_id"]) / "source.pdf"
        problem = None
        actual = None
        if not pdf.is_file():
            problem = "o PDF importado não está mais disponível para conferência"
        else:
            actual = sha256_bytes_file(pdf)
            if actual != rec["sha256"]:
                problem = "documento: hash do arquivo importado não confere com o registrado"
        evidence = [e for e in param.get("evidence") or [] if e.get("page_pdf") and e.get("quote")
                    and e.get("literal_check") == "PASS"]
        if not evidence and not problem:
            raise ReviewRejected("o parâmetro não tem evidência suficiente (página e citação literal)",
                                 "EVIDENCE_INSUFFICIENT")
        orig = param.get("original") or {}
        reviewer = check_review(
            status=param["status"], extractor=(param.get("extraction") or {}).get("by"), reviewer=reviewer,
            original_value=orig.get("value"), original_unit=orig.get("unit"),
            evidence_pages={e["page_pdf"] for e in evidence}, observed_value=value, observed_unit=unit,
            observed_page_pdf=page, hash_problem=problem)
        stamp = utc_now()
        param["status"] = "CONFERIDO_FONTE"
        param["review"] = {"reviewer": reviewer, "reviewed_at": stamp, "notes": notes,
                           "checked_document_sha256": actual}
        workspace.write_json(workspace.area("imports") / rec["import_id"] / "import.json", rec)
        return {"reviewed_at": stamp, "checked_document_sha256": actual, "reviewer": reviewer}
