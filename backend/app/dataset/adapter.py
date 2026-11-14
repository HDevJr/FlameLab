"""BL-02 → BL-05: adaptador DatasetStore → EvidenceSource do assistente.

- Converte ParameterRecord → ficha determinística (`record_card`) e Gap → lacuna (`gap_card`),
  preservando test_uid, record_id (REC-<record_id>) e os evidence_ids de origem.
- NÃO decide elegibilidade: a recuperação do assistente só aceita fichas CONFERIDO_FONTE +
  OBSERVADO. Registros EXTRAIDO_NAO_REVISADO entram como itens, mas são excluídos lá
  (e contados no aviso "não elegível").
- Registros cujo documento-fonte tem hash DIVERGENTE são omitidos (não há como garantir
  que a evidência corresponde ao arquivo conferido).
"""

from __future__ import annotations

from backend.app.assistant.cards import GapInput, LocatorInput, RecordInput, gap_card, record_card
from backend.app.assistant.schemas import EvidenceItem
from backend.app.dataset.store import DatasetStore


class DatasetEvidenceSource:
    def __init__(self, store: DatasetStore):
        self._store = store
        self.warnings: list[str] = []
        self._items = self._build()

    @property
    def dataset_version(self) -> str | None:
        return self._store.dataset_version

    def items(self) -> list[EvidenceItem]:
        return list(self._items)

    def known_tests(self) -> dict[str, str]:
        return {uid: t.label for uid, t in self._store.tests.items()}

    def _build(self) -> list[EvidenceItem]:
        s = self._store
        out: list[EvidenceItem] = []
        for r in sorted(s.records.values(), key=lambda r: r.record_id):
            test = s.tests[r.test_uid]
            evs = [s.evidence[e] for e in r.evidence_ids]
            if any(not s.document_ok(e.document_id) for e in evs):
                self.warnings.append(f"{r.record_id} omitido: hash do documento-fonte diverge")
                continue
            if r.status == "AUSENTE":
                out.append(gap_card(GapInput(
                    gap_id=f"GAP-{r.test_uid}-{r.parameter}", test_uid=r.test_uid, test_label=test.label,
                    investigation_id=r.investigation_id, parameter=r.parameter, label_pt=r.label_pt,
                    explanation_pt="Registro marcado como AUSENTE no dataset.")))
                continue
            primary = evs[0]
            quote = f' Trecho da fonte: "{primary.quote}".' if primary.quote else ""
            caveats = list(r.caveats_pt) + [f"{k}: {v}" for k, v in sorted(r.qualifiers.items())]
            out.append(record_card(RecordInput(
                record_id=r.record_id, test_uid=r.test_uid, test_label=test.label,
                investigation_id=r.investigation_id, parameter=r.parameter, label_pt=r.label_pt,
                role=r.role, nature=r.nature, status=r.status,
                original=r.original.model_dump() if r.original else None,
                evidence_ids=list(r.evidence_ids), document_id=primary.document_id,
                locator=LocatorInput(**primary.locator.model_dump(exclude={"bbox"})),
                caveats_pt=caveats + ([quote.strip()] if quote else []),
            )))
        for g in sorted(s.gaps.values(), key=lambda g: g.gap_id):
            out.append(gap_card(GapInput(
                gap_id=g.gap_id, test_uid=g.test_uid, test_label=s.tests[g.test_uid].label,
                investigation_id=s.tests[g.test_uid].investigation_id, parameter=g.parameter,
                label_pt=g.label_pt, keywords=g.keywords, explanation_pt=g.explanation_pt)))
        return out
