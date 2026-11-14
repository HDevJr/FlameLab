"""BL-02.03 — DatasetStore: carrega, valida (fail-fast) e indexa `data/`.

Layout (planning/02 §15), cada arquivo com envelope {"contract_version": "1.0", "items": [...]}:
  data/documents.json · data/investigations.json · data/tests/*.json ·
  data/parameters/*.json · data/evidence/*.json · data/gaps/*.json
`data/ai_cache/` e `data/source_manifest.json` não fazem parte do dataset_version.

Validações entre arquivos:
- IDs únicos; referências existentes (ensaio, investigação, documento, evidência).
- I-5: CONFERIDO_FONTE exige evidência com precisão TABLE_CELL/PAGE e page_pdf_index.
- I-7: a evidência de um registro pertence ao MESMO ensaio do registro.
- `document_sha256_at_extraction` e `review.checked_document_sha256`, quando preenchidos,
  precisam ser iguais ao sha256 registrado do documento.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from backend.app.dataset.hashing import SourceCheck, verify_source
from backend.app.dataset.models import (
    CONTRACT_VERSION,
    Document,
    Evidence,
    Gap,
    Investigation,
    ParameterRecord,
    Test,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "data"

M = TypeVar("M", bound=BaseModel)


class DatasetValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("dataset inválido:\n  - " + "\n  - ".join(errors))


@dataclass
class DatasetStore:
    documents: dict[str, Document] = field(default_factory=dict)
    investigations: dict[str, Investigation] = field(default_factory=dict)
    tests: dict[str, Test] = field(default_factory=dict)
    records: dict[str, ParameterRecord] = field(default_factory=dict)
    evidence: dict[str, Evidence] = field(default_factory=dict)
    gaps: dict[str, Gap] = field(default_factory=dict)
    dataset_version: str | None = None
    source_checks: dict[str, SourceCheck] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (self.records or self.gaps)

    # ------------------------------------------------------------ carga
    @classmethod
    def load(cls, data_dir: Path = DEFAULT_DATA_DIR, sources_root: Path = REPO_ROOT,
             verify_hashes: bool = True) -> "DatasetStore":
        data_dir = Path(data_dir)
        errors: list[str] = []
        canon: list[tuple[str, object]] = []

        def read(path: Path, model: type[M]) -> list[M]:
            rel = path.relative_to(data_dir).as_posix()
            try:
                raw = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{rel}: JSON ilegível ({type(exc).__name__})")
                return []
            if not isinstance(raw, dict) or raw.get("contract_version") != CONTRACT_VERSION:
                errors.append(f"{rel}: contract_version ausente ou diferente de {CONTRACT_VERSION}")
                return []
            items = raw.get("items")
            if not isinstance(items, list):
                errors.append(f"{rel}: campo 'items' deve ser lista")
                return []
            canon.append((rel, raw))
            out: list[M] = []
            for n, item in enumerate(items):
                try:
                    out.append(model.model_validate(item))
                except ValidationError as exc:
                    ident = item.get(next(iter(model.model_fields)), f"#{n}") if isinstance(item, dict) else f"#{n}"
                    for e in exc.errors():
                        loc = ".".join(str(p) for p in e["loc"]) or "-"
                        errors.append(f"{rel}: {ident}: {loc}: {e['msg']}")
            return out

        def files(name: str) -> list[Path]:
            single = data_dir / f"{name}.json"
            folder = data_dir / name
            found = [single] if single.is_file() else []
            if folder.is_dir():
                found += sorted(folder.glob("*.json"))
            return found

        store = cls()
        groups = [
            ("documents", Document, store.documents, "document_id"),
            ("investigations", Investigation, store.investigations, "investigation_id"),
            ("tests", Test, store.tests, "test_uid"),
            ("parameters", ParameterRecord, store.records, "record_id"),
            ("evidence", Evidence, store.evidence, "evidence_id"),
            ("gaps", Gap, store.gaps, "gap_id"),
        ]
        for name, model, target, key in groups:
            for path in files(name):
                for obj in read(path, model):
                    ident = getattr(obj, key)
                    if ident in target:
                        errors.append(f"{name}: identificador duplicado '{ident}'")
                    target[ident] = obj

        store._cross_validate(errors)
        if errors:
            raise DatasetValidationError(errors)

        if canon:
            payload = json.dumps(sorted(canon, key=lambda x: x[0]), sort_keys=True, ensure_ascii=False)
            store.dataset_version = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if verify_hashes:
            for doc in store.documents.values():
                store.source_checks[doc.document_id] = verify_source(
                    doc.document_id, doc.local_path, doc.sha256, sources_root)
        return store

    # ------------------------------------------------------------ validação cruzada
    def _cross_validate(self, errors: list[str]) -> None:
        for inv in self.investigations.values():
            for d in inv.documents:
                if d not in self.documents:
                    errors.append(f"investigations: {inv.investigation_id}: documento inexistente '{d}'")
            for fld in (inv.platform, inv.gravity_environment):
                for eid in (fld.evidence_ids if fld else []):
                    ev = self.evidence.get(eid)
                    if ev is None:
                        errors.append(f"investigations: {inv.investigation_id}: evidência inexistente '{eid}'")
        for t in self.tests.values():
            if t.investigation_id not in self.investigations:
                errors.append(f"tests: {t.test_uid}: investigação inexistente '{t.investigation_id}'")
            if t.source_table and t.source_table.document_id not in self.documents:
                errors.append(f"tests: {t.test_uid}: documento inexistente '{t.source_table.document_id}'")
        for ev in self.evidence.values():
            doc = self.documents.get(ev.document_id)
            if doc is None:
                errors.append(f"evidence: {ev.evidence_id}: documento inexistente '{ev.document_id}'")
            elif ev.document_sha256_at_extraction and doc.sha256 and ev.document_sha256_at_extraction != doc.sha256:
                errors.append(f"evidence: {ev.evidence_id}: extraída de versão do documento diferente da registrada")
            if ev.test_uid is not None and ev.test_uid not in self.tests:
                errors.append(f"evidence: {ev.evidence_id}: ensaio inexistente '{ev.test_uid}'")
        for r in self.records.values():
            if r.test_uid not in self.tests:
                errors.append(f"parameters: {r.record_id}: ensaio inexistente '{r.test_uid}'")
            elif self.tests[r.test_uid].investigation_id != r.investigation_id:
                errors.append(f"parameters: {r.record_id}: investigation_id diverge do ensaio")
            evs = []
            for eid in r.evidence_ids:
                ev = self.evidence.get(eid)
                if ev is None:
                    errors.append(f"parameters: {r.record_id}: evidência inexistente '{eid}'")
                    continue
                evs.append(ev)
                if ev.test_uid != r.test_uid:  # I-7
                    errors.append(f"parameters: {r.record_id}: I-7 evidência '{eid}' pertence a '{ev.test_uid}'")
            if r.status in ("CONFERIDO_FONTE", "APROVADO_MODELO"):  # I-5
                if not any(e.locator.precision in ("TABLE_CELL", "PAGE") and e.locator.page_pdf_index for e in evs):
                    errors.append(f"parameters: {r.record_id}: I-5 exige evidência TABLE_CELL/PAGE com page_pdf_index")
                docs = {e.document_id for e in evs}
                chk = r.review.checked_document_sha256
                for d in docs:
                    doc = self.documents.get(d)
                    if chk and doc and doc.sha256 and chk != doc.sha256:
                        errors.append(f"parameters: {r.record_id}: revisão feita sobre outra versão do documento")
        for g in self.gaps.values():
            if g.test_uid not in self.tests:
                errors.append(f"gaps: {g.gap_id}: ensaio inexistente '{g.test_uid}'")
            if f"{g.test_uid}.{g.parameter}" in self.records and \
                    self.records[f"{g.test_uid}.{g.parameter}"].status != "AUSENTE":
                errors.append(f"gaps: {g.gap_id}: parâmetro já tem registro com valor (lacuna contraditória)")

    # ------------------------------------------------------------ consultas
    def records_for(self, test_uid: str) -> list[ParameterRecord]:
        return [r for r in self.records.values() if r.test_uid == test_uid]

    def gaps_for(self, test_uid: str) -> list[Gap]:
        return [g for g in self.gaps.values() if g.test_uid == test_uid]

    def document_ok(self, document_id: str) -> bool:
        """False somente quando o hash foi verificado e DIVERGE (ou caminho rejeitado)."""
        chk = self.source_checks.get(document_id)
        return not (chk and chk.status in ("MISMATCH", "PATH_REJECTED"))
