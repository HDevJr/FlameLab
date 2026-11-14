"""Catálogo unificado: documentos e experimentos do dataset curado (`data/`) e dos artigos
importados (`var/imports/`). Nenhum identificador de documento é fixado aqui.

"Experiment" é o nome de API da entidade `Test` do contrato v1 (mesma entidade, sem duplicação).
"""

from __future__ import annotations

import re
from typing import Any

from backend.app import workspace
from backend.app.dataset.store import DatasetStore
from backend.app.nasa.models import DocumentMeta

PROVENANCE_LABELS = {
    "VERIFIED": "Publicação NASA verificada (arquivo idêntico ao do NTRS)",
    "CANDIDATE": "Identificado no NTRS; arquivo ainda não comparado por hash",
    "MISMATCH": "Arquivo difere do publicado no NTRS",
    "PENDING": "Procedência NASA pendente de verificação",
}


def _ntrs_id_from_url(url: str | None) -> str | None:
    m = re.search(r"ntrs\.nasa\.gov/citations/(\d+)", url or "")
    return m.group(1) if m else None


class Catalog:
    def __init__(self, store: DatasetStore):
        self._store = store

    # ---------------------------------------------------------------- importados
    def _imports(self) -> list[dict[str, Any]]:
        out = []
        for folder in sorted(workspace.area("imports").iterdir()):
            data = workspace.read_json(folder / "import.json")
            if data:
                out.append(data)
        return out

    def _import_for_document(self, document_id: str) -> dict[str, Any] | None:
        return next((i for i in self._imports() if i["document"]["document_id"] == document_id), None)

    # ---------------------------------------------------------------- documentos
    def provenance(self, document_id: str) -> dict[str, Any]:
        saved = workspace.read_json(workspace.area("provenance") / f"{workspace.safe_id(document_id)}.json")
        if saved:
            return saved
        doc = self._store.documents.get(document_id)
        if doc and _ntrs_id_from_url(doc.url):
            return {"state": "CANDIDATE", "label_pt": PROVENANCE_LABELS["CANDIDATE"],
                    "ntrs_id": _ntrs_id_from_url(doc.url), "checked_at": None,
                    "reasons_pt": ["O dataset curado declara a URL do NTRS para este documento.",
                                   "A comparação do arquivo com o NTRS ainda não foi executada nesta instalação."]}
        return {"state": "PENDING", "label_pt": PROVENANCE_LABELS["PENDING"], "ntrs_id": None,
                "checked_at": None, "reasons_pt": ["Nenhuma verificação de procedência registrada."]}

    def documents(self) -> list[dict[str, Any]]:
        out = []
        for doc in self._store.documents.values():
            check = self._store.source_checks.get(doc.document_id)
            imp = self._import_for_document(doc.document_id)
            out.append({
                "document_id": doc.document_id, "title": doc.title, "origin": "CURATED", "kind": doc.kind,
                "url": doc.url, "sha256": doc.sha256, "size_bytes": doc.size_bytes,
                "local_file_check": check.status if check else "NOT_COMPUTED",
                "nasa_provenance": self.provenance(doc.document_id),
                "import_id": imp["import_id"] if imp else None,
                "experiments": [self._summary(self.experiment(t.test_uid))
                                for t in self._store.tests.values() if self._document_of(t.test_uid) == doc.document_id],
            })
        curated = set(self._store.documents)
        for imp in self._imports():
            d = imp["document"]
            if d["document_id"] in curated:
                continue
            out.append({
                "document_id": d["document_id"], "title": d.get("title") or imp["filename"], "origin": "IMPORTED",
                "kind": "IMPORTED_PDF", "url": (imp.get("nasa_provenance") or {}).get("ntrs_url"),
                "sha256": imp["sha256"], "size_bytes": imp["size_bytes"], "local_file_check": "MATCH",
                "nasa_provenance": imp.get("nasa_provenance") or self.provenance(d["document_id"]),
                "import_id": imp["import_id"], "import_status": imp["status"],
                "experiments": [self._summary(e) for e in imp.get("experiments") or []],
            })
        return out

    def document(self, document_id: str) -> dict[str, Any] | None:
        return next((d for d in self.documents() if d["document_id"] == document_id), None)

    def document_meta(self, document_id: str) -> DocumentMeta | None:
        doc = self._store.documents.get(document_id)
        if doc:
            return DocumentMeta(document_id=doc.document_id, title=doc.title, doi=doc.doi,
                                ntrs_id=_ntrs_id_from_url(doc.url))
        imp = self._import_for_document(document_id)
        if not imp:
            return None
        d = imp["document"]
        ids = d.get("identifiers") or {}
        return DocumentMeta(document_id=document_id, title=d.get("title"),
                            ntrs_id=(ids.get("ntrs_ids") or [None])[0],
                            report_numbers=ids.get("report_numbers") or [],
                            doi=(ids.get("dois") or [None])[0], year=d.get("year"))

    def local_file(self, document_id: str):
        """Caminho do PDF local do documento (resolvido pelo servidor, nunca vindo do cliente)."""
        from backend.app.dataset.store import REPO_ROOT

        doc = self._store.documents.get(document_id)
        if doc and doc.local_path:
            path = (REPO_ROOT / doc.local_path).resolve()
            return path if path.is_relative_to(REPO_ROOT.resolve()) and path.is_file() else None
        imp = self._import_for_document(document_id)
        if imp:
            path = workspace.area("imports") / workspace.safe_id(imp["import_id"]) / "source.pdf"
            return path if path.is_file() else None
        return None

    # ---------------------------------------------------------------- experimentos
    def _document_of(self, test_uid: str) -> str | None:
        test = self._store.tests[test_uid]
        if test.source_table:
            return test.source_table.document_id
        inv = self._store.investigations.get(test.investigation_id)
        return inv.documents[0] if inv and inv.documents else None

    @staticmethod
    def _summary(exp: dict[str, Any]) -> dict[str, Any]:
        return {"experiment_id": exp["experiment_id"], "label": exp["label"],
                "phenomena": exp.get("phenomena") or [], "review": exp.get("review") or _review(exp)}

    def experiment(self, experiment_id: str) -> dict[str, Any] | None:
        test = self._store.tests.get(experiment_id)
        if test:
            return self._curated(test.test_uid)
        for imp in self._imports():
            for exp in imp.get("experiments") or []:
                if exp["experiment_id"] == experiment_id:
                    return {**exp, "review": _review(exp), "document_title": imp["document"].get("title")}
        return None

    def experiments_for(self, document_id: str) -> list[dict[str, Any]]:
        doc = self.document(document_id)
        return [e for e in (self.experiment(s["experiment_id"]) for s in (doc or {}).get("experiments", [])) if e]

    def _curated(self, test_uid: str) -> dict[str, Any]:
        store, test = self._store, self._store.tests[test_uid]
        document_id = self._document_of(test_uid)
        params = []
        for r in store.records_for(test_uid):
            evidence = []
            for eid in r.evidence_ids:
                ev = store.evidence.get(eid)
                if not ev:
                    continue
                loc = ev.locator
                where = [f"§{loc.section}" if loc.section else None,
                         f"Tabela {loc.table}" if loc.table else None,
                         f"linha {loc.row_label}" if loc.row_label else None,
                         f"p. {loc.page_printed}" if loc.page_printed else None,
                         f"PDF {loc.page_pdf_index}" if loc.page_pdf_index else None]
                evidence.append({"evidence_id": ev.evidence_id, "document_id": ev.document_id,
                                 "page_pdf": loc.page_pdf_index, "page_printed": loc.page_printed,
                                 "column_label": loc.column_label, "quote": ev.quote,
                                 "locator_pt": ", ".join(w for w in where if w)})
            params.append({
                "record_id": r.record_id, "parameter": r.parameter, "label_pt": r.label_pt,
                "role": r.role, "nature": r.nature, "status": r.status,
                "original": r.original.model_dump() if r.original else None,
                "normalized": r.normalized.model_dump() if r.normalized else None,
                "evidence": evidence, "caveats_pt": list(r.caveats_pt),
                "extraction": {"method": r.extraction.method, "by": r.extraction.by} if r.extraction else None,
                "reviewer": r.review.reviewer if r.review else None,
            })
        gaps = [{"gap_id": g.gap_id, "parameter": g.parameter, "label_pt": g.label_pt,
                 "explanation_pt": g.explanation_pt, "purpose_blocked": list(g.purpose_blocked),
                 "searched_in": list(g.searched_in), "origin": "CURADORIA"} for g in store.gaps_for(test_uid)]
        doc = store.documents.get(document_id) if document_id else None
        exp = {
            "experiment_id": test_uid, "label": test.label, "origin": "CURATED",
            "document_id": document_id, "document_title": doc.title if doc else None,
            "investigation_id": test.investigation_id, "phenomena": list(test.phenomena),
            "material_family": test.material_family, "description": test.selection_reason,
            "parameters": params, "gaps": gaps, "dataset_version": store.dataset_version,
        }
        exp["review"] = _review(exp)
        return exp

    def flat_parameters(self, document_id: str) -> list[dict[str, Any]]:
        out = []
        for exp in self.experiments_for(document_id):
            for p in exp["parameters"]:
                orig = p.get("original") or {}
                value = orig.get("value")
                out.append({"experiment_id": exp["experiment_id"], "parameter": p["parameter"],
                            "label_pt": p["label_pt"], "status": p["status"], "source": "artigo",
                            "value": f"{value} {orig.get('unit')}" if orig.get("unit") else value})
        return out


def _review(exp: dict[str, Any]) -> dict[str, int]:
    params = exp.get("parameters") or []
    reviewed = sum(1 for p in params if p["status"] in ("CONFERIDO_FONTE", "APROVADO_MODELO"))
    return {"total": len(params), "reviewed": reviewed, "pending": len(params) - reviewed,
            "gaps": len(exp.get("gaps") or [])}
