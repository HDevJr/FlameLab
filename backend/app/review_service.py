"""Revisão humana pela interface (v2.2: revisão científica assistida).

UMA política de aceitação: `dataset.review.check_review` → `quantities.compare_fields` (campo a campo,
com dimensão e conversão de unidades) + `semantic.semantic_flags` (o trecho sustenta o conceito?).
- Registro do dataset curado: `apply_review` (grava em `data/parameters`, revalida e restaura se falhar)
  e anexa a linha ao log de curadoria do ensaio.
- Registro de artigo importado: mesma checagem; a promoção grava em `var/imports/<id>/import.json`.
Ações: CONFIRM (confirmar a interpretação), CORRECT (corrigir a extração — preserva o original e
reabre a revisão), DOUBT (dúvida), DIVERGENCE (divergência). Toda tentativa (aceita, recusada, dúvida,
divergência, correção) vai para `var/audit/review_events.jsonl`, com as comparações por campo.
A identidade do revisor é DECLARADA (não há autenticação). O frontend pode pré-preencher os campos com
a extração (para não exigir redigitação); o servidor registra se o revisor os alterou
(`prefilled_unchanged`) e continua sendo a autoridade final.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable

from backend.app import units, workspace
from backend.app.dataset.review import ReviewRejected, apply_review, check_review
from backend.app.dataset.store import DEFAULT_DATA_DIR, REPO_ROOT, DatasetStore
from backend.app.ingest.pdf import sha256_bytes_file
from backend.app.labels import friendly_label
from backend.app.nasa.provenance.log import utc_now
from backend.app.quantities import clean_text, compare_fields, parse_value_input
from backend.app.semantic import blocking, semantic_flags

ACTIONS = ("CONFIRM", "CORRECT", "DOUBT", "DIVERGENCE")
_lock = threading.Lock()
_AI_PREFIX = ("claude", "gemini", "llm", "ia ", "ai ")


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


class RecordView:
    """Visão uniforme de um registro (curado ou importado) para a política de revisão."""

    def __init__(self, record_id: str, curated: bool, parameter: str, label: str | None, role: str, status: str,
                 value: Any, unit: str | None, pages: set, quotes: list[str], extractors: list[str],
                 method: str | None, sha_problem: str | None, checked_sha: str | None, imported=None,
                 label_source: str | None = None):
        self.record_id, self.curated, self.parameter, self.label, self.role = record_id, curated, parameter, label, role
        self.status, self.value, self.unit, self.pages, self.quotes = status, value, unit, pages, quotes
        self.extractors, self.method, self.sha_problem, self.checked_sha, self.imported = extractors, method, sha_problem, checked_sha, imported
        self.label_source = label_source

    def flags(self, label: str | None = None) -> list[dict[str, Any]]:
        return semantic_flags(parameter=self.parameter, label=label if label is not None else self.label,
                              value=self.value, unit=self.unit, quotes=self.quotes, method=self.method,
                              label_source=self.label_source)


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

    def _view(self, record_id: str) -> RecordView:
        store = self._store()
        rec = store.records.get(record_id)
        if rec is not None:
            evs = [store.evidence[e] for e in rec.evidence_ids if e in store.evidence]
            problem, sha = None, None
            for d in {e.document_id for e in evs}:
                chk = store.source_checks.get(d)
                if chk is None or chk.status != "MATCH":
                    problem = f"documento {d}: hash não confere ({chk.status if chk else 'sem verificação'})"
                    break
                sha = chk.actual_sha256
            value = rec.original.value if rec.original else None
            return RecordView(record_id, True, rec.parameter, rec.label_pt, rec.role, rec.status, value,
                              rec.original.unit if rec.original else None,
                              {e.locator.page_pdf_index for e in evs}, [e.quote for e in evs if e.quote],
                              [rec.extraction.by] if rec.extraction else [], rec.extraction.method if rec.extraction else None,
                              problem, sha)
        found = self._imported(record_id)
        if found is None:
            raise ReviewRejected(f"registro inexistente: {record_id}", "RECORD_NOT_FOUND")
        imp, _exp, p = found
        pdf = workspace.area("imports") / workspace.safe_id(imp["import_id"]) / "source.pdf"
        problem, actual = None, None
        if not pdf.is_file():
            problem = "o PDF importado não está mais disponível para conferência"
        else:
            actual = sha256_bytes_file(pdf)
            if actual != imp["sha256"]:
                problem = "documento: hash do arquivo importado não confere com o registrado"
        ev = [e for e in p.get("evidence") or [] if e.get("page_pdf") and e.get("quote") and e.get("literal_check") == "PASS"]
        orig = p.get("original") or {}
        ext = p.get("extraction") or {}
        authors = [ext.get("by")] + list(ext.get("corrected_by") or [])
        label = p.get("label_pt") if p.get("label_source") in ("IA", "HUMANO") else friendly_label(p["parameter"])
        return RecordView(record_id, False, p["parameter"], label, p["role"], p["status"], orig.get("value"),
                          orig.get("unit"), {e["page_pdf"] for e in ev}, [e["quote"] for e in ev],
                          [a for a in authors if a], ext.get("method"), problem, actual, imported=found,
                          label_source=p.get("label_source"))

    # ---------------------------------------------------------------- pré-visualização (não grava nada)
    def preview(self, record_id: str, reviewer: str | None, observed_value: str | None,
                observed_unit: str | None, observed_page_pdf: int | None) -> dict[str, Any]:
        v = self._view(workspace.safe_id(record_id))
        cmp = compare_fields(original_value=v.value, original_unit=v.unit, evidence_pages=v.pages,
                             observed_value=observed_value, observed_unit=observed_unit, observed_page=observed_page_pdf)
        flags = v.flags()
        issue = None
        name = (reviewer or "").strip()
        if v.status != "EXTRAIDO_NAO_REVISADO":
            issue = "WRONG_STATE"
        elif name and any(a and name.lower() == a.strip().lower() for a in v.extractors):
            issue = "REVIEWER_NOT_INDEPENDENT"
        elif name and name.lower().startswith(_AI_PREFIX):
            issue = "REVIEWER_NOT_HUMAN"
        elif v.sha_problem:
            issue = "DOCUMENT_HASH"
        block = blocking(flags)
        return {"record_id": record_id, "status": v.status, "comparisons": cmp["comparisons"],
                "fields_accepted": cmp["accepted"], "field_code": cmp["code"], "field_message_pt": cmp["message_pt"],
                "failed_fields": cmp["failed_fields"], "semantic_flags": flags, "blocking_flags": block,
                "reviewer_issue": issue,
                "accepted": bool(cmp["accepted"] and not block and not issue and any(pg is not None for pg in v.pages) and name)}

    # ---------------------------------------------------------------- ação
    def submit(self, record_id: str, action: str, reviewer: str, observed_value: str | None,
               observed_unit: str | None, observed_page_pdf: int | None, notes: str | None,
               checked_pdf: bool, prefilled_unchanged: bool = False, corrected_label_pt: str | None = None,
               corrected_value: str | None = None, corrected_unit: str | None = None) -> dict[str, Any]:
        record_id = workspace.safe_id(record_id)
        if action not in ACTIONS:
            raise ReviewRejected("ação inválida", "INVALID_ACTION")
        reviewer = (reviewer or "").strip()
        notes = (notes or "").strip() or None
        base = {"record_id": record_id, "reviewer": reviewer, "action": action, "notes": notes,
                "observed_value": observed_value, "observed_unit": observed_unit,
                "observed_page_pdf": observed_page_pdf, "prefilled_unchanged": bool(prefilled_unchanged)}
        view = self._view(record_id)

        if action in ("DOUBT", "DIVERGENCE"):
            if not reviewer:
                raise ReviewRejected("revisor obrigatório", "REVIEWER_REQUIRED")
            if not notes:
                raise ReviewRejected("descreva o motivo (dúvida ou divergência)", "NOTES_REQUIRED")
            if action == "DIVERGENCE" and not clean_text(observed_value):
                raise ReviewRejected("informe o valor que você leu no PDF", "OBSERVED_REQUIRED")
            extra = {}
            if action == "DIVERGENCE":
                cmp = compare_fields(original_value=view.value, original_unit=view.unit, evidence_pages=view.pages,
                                     observed_value=observed_value, observed_unit=observed_unit, observed_page=observed_page_pdf)
                extra = {"comparisons": cmp["comparisons"]}
            ev = append_event({**base, **extra, "outcome": "RECORDED", "state_after": view.status})
            return {"outcome": "RECORDED", "status": view.status, "event": ev}

        if action == "CORRECT":
            return self._correct(view, base, reviewer, notes, corrected_label_pt, corrected_value, corrected_unit)

        # ---- CONFIRM
        try:
            if not checked_pdf:
                raise ReviewRejected("declare que verificou a evidência no PDF original", "DECLARATION_REQUIRED")
            if observed_page_pdf is None or not clean_text(observed_value):
                raise ReviewRejected("informe o valor, a unidade e a página que você leu no PDF", "OBSERVED_REQUIRED")
            reviewer = self._check_confirm(view, reviewer, observed_value or "", observed_unit, observed_page_pdf)
            result = (self._promote_curated if view.curated else self._promote_imported)(
                view, reviewer, observed_value or "", observed_unit, observed_page_pdf, notes)
        except ReviewRejected as exc:
            append_event({**base, "outcome": "REFUSED", "code": exc.code, "message": str(exc),
                          **({"comparisons": exc.details.get("comparisons"), "semantic_flags": exc.details.get("semantic_flags")}
                             if exc.details else {})})
            raise
        cmp = compare_fields(original_value=view.value, original_unit=view.unit, evidence_pages=view.pages,
                             observed_value=observed_value, observed_unit=observed_unit, observed_page=observed_page_pdf)
        ev = append_event({**base, "outcome": "APPROVED", "state_after": "CONFERIDO_FONTE",
                           "checked_document_sha256": result["checked_document_sha256"],
                           "comparisons": cmp["comparisons"],
                           "semantic_flags_info": [f["code"] for f in view.flags()]})
        return {"outcome": "APPROVED", "status": "CONFERIDO_FONTE", **result, "event": ev}

    def _check_confirm(self, v: RecordView, reviewer: str, value: str, unit: str | None, page: int) -> str:
        if not any(pg is not None for pg in v.pages) and not v.sha_problem and v.status == "EXTRAIDO_NAO_REVISADO":
            raise ReviewRejected("o parâmetro não tem evidência suficiente (página e citação literal)", "EVIDENCE_INSUFFICIENT")
        name = check_review(status=v.status, extractor=v.extractors, reviewer=reviewer, original_value=v.value,
                            original_unit=v.unit, evidence_pages=v.pages, observed_value=value, observed_unit=unit,
                            observed_page_pdf=page, hash_problem=v.sha_problem)
        flags = blocking(v.flags())
        if flags:
            raise ReviewRejected(
                "interpretação científica inconclusiva: " + "; ".join(f["title_pt"] for f in flags) +
                ". Corrija a extração ou mantenha o valor pendente.", "SEMANTIC_AMBIGUITY",
                {"accepted": False, "code": "REVIEW_MISMATCH", "reason_code": "SEMANTIC_AMBIGUITY",
                 "comparisons": compare_fields(original_value=v.value, original_unit=v.unit, evidence_pages=v.pages,
                                               observed_value=value, observed_unit=unit, observed_page=page)["comparisons"],
                 "semantic_flags": flags})
        return name

    # ---------------------------------------------------------------- promoção
    def _promote_curated(self, v: RecordView, reviewer, value, unit, page, notes) -> dict[str, Any]:
        res = apply_review(v.record_id, reviewer, value, unit, page, notes, self._data_dir, self._sources_root)
        test_uid = self._store().records[v.record_id].test_uid
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

    def _promote_imported(self, v: RecordView, reviewer, value, unit, page, notes) -> dict[str, Any]:
        rec, _exp, param = v.imported
        stamp = utc_now()
        param["status"] = "CONFERIDO_FONTE"
        param["review"] = {"reviewer": reviewer, "reviewed_at": stamp, "notes": notes,
                           "checked_document_sha256": v.checked_sha}
        workspace.write_json(workspace.area("imports") / rec["import_id"] / "import.json", rec)
        return {"reviewed_at": stamp, "checked_document_sha256": v.checked_sha, "reviewer": reviewer}

    # ---------------------------------------------------------------- corrigir a extração
    def _correct(self, v: RecordView, base: dict[str, Any], reviewer: str, notes: str | None,
                 label: str | None, value: str | None, unit: str | None) -> dict[str, Any]:
        def refuse(msg: str, code: str):
            append_event({**base, "outcome": "REFUSED", "code": code, "message": msg})
            raise ReviewRejected(msg, code)

        if v.curated:
            refuse("registros do dataset curado são corrigidos pela curadoria nos arquivos de dados, não pela interface",
                   "CURATED_READONLY")
        if not reviewer:
            raise ReviewRejected("revisor obrigatório", "REVIEWER_REQUIRED")
        if reviewer.lower().startswith(_AI_PREFIX):
            refuse("a correção deve ser feita por uma pessoa da equipe", "REVIEWER_NOT_HUMAN")
        if not notes:
            raise ReviewRejected("descreva o motivo da correção", "NOTES_REQUIRED")
        label = clean_text(label) or None
        value = clean_text(value) or None
        unit = clean_text(unit) or None
        rec, _exp, p = v.imported
        before = {"label_pt": v.label, "value": v.value, "unit": v.unit}
        new_value, new_unit, raw = v.value, v.unit, None
        if value is not None:
            if isinstance(v.value, str):
                new_value, raw = value, value
            else:
                parsed = parse_value_input(value)
                if parsed.status != "OK":
                    refuse(f"valor corrigido inválido: {parsed.detail_pt}", "VALUE_UNREADABLE" if parsed.status != "AMBIGUOUS" else "VALUE_AMBIGUOUS")
                new_value, raw = parsed.value, value
                if parsed.embedded_unit and not unit:
                    unit = parsed.embedded_unit
        if unit is not None:
            if units.canonical_unit(unit) is None:
                refuse(f"a unidade corrigida ({unit}) não é suportada pela tabela de unidades", "UNIT_UNSUPPORTED")
            new_unit = unit
        changed = (label is not None and label != v.label) or new_value != v.value or new_unit != v.unit
        if not changed:
            raise ReviewRejected("nenhuma alteração: informe um nome, valor ou unidade diferentes dos atuais", "NO_CHANGE")

        # snapshot do que a IA extraiu (uma só vez) — o original nunca é perdido
        p.setdefault("original_extraction", {
            "label_pt": p.get("label_pt"), "label_source": p.get("label_source"), "original": dict(p.get("original") or {}),
            "normalized": p.get("normalized"), "extraction": dict(p.get("extraction") or {}), "snapshot_at": utc_now()})
        was_confirmed = p["status"] == "CONFERIDO_FONTE"
        if was_confirmed:
            p.setdefault("review_history", []).append({**(p.get("review") or {}), "superseded_at": utc_now(),
                                                        "superseded_by_correction_of": reviewer})
            p["review"] = None
            p["status"] = "EXTRAIDO_NAO_REVISADO"
        if label is not None:
            p["label_pt"], p["label_source"] = label, "HUMANO"
        orig = dict(p.get("original") or {})
        if new_value != v.value:
            orig["value"], orig["raw_text"] = new_value, raw
        if new_unit != v.unit:
            orig["unit"] = new_unit
        p["original"] = orig
        if isinstance(new_value, (int, float)) and not isinstance(new_value, bool):
            q = units.normalize(float(new_value), new_unit)
            p["normalized"] = {"value": q.value, "unit": q.unit} if q else None
        ext = p.setdefault("extraction", {})
        ext["corrected_by"] = sorted({*(ext.get("corrected_by") or []), reviewer})
        after = {"label_pt": p.get("label_pt"), "value": orig.get("value"), "unit": orig.get("unit")}
        p.setdefault("corrections", []).append({"at": utc_now(), "by": reviewer, "notes": notes, "before": before, "after": after,
                                                  "reopened": was_confirmed})
        workspace.write_json(workspace.area("imports") / rec["import_id"] / "import.json", rec)
        flags = semantic_flags(parameter=p["parameter"], label=p.get("label_pt"), value=orig.get("value"),
                               unit=orig.get("unit"), quotes=v.quotes, method="LLM", label_source=p.get("label_source"))
        ev = append_event({**base, "outcome": "CORRECTED", "state_after": p["status"], "before": before, "after": after,
                           "reopened_confirmed_review": was_confirmed})
        return {"outcome": "CORRECTED", "status": p["status"], "event": ev, "before": before, "after": after,
                "semantic_flags": flags, "reopened": was_confirmed}
