"""BL-05.01 — fichas textuais determinísticas a partir de registros do contrato (planning/04).

As fichas são o ÚNICO meio de um valor numérico chegar ao modelo como evidência
quantitativa: o texto é gerado aqui, a partir de campos estruturados, e os números
sustentados são copiados de `original` (nunca re-extraídos do texto).

Entradas aceitas são subconjuntos de ParameterRecord (§3.4), Evidence (§3.5),
Gap (§3.6) e Passage (§3.7). O carregamento/validação completos do dataset são
BL-02.03 (DatasetStore), ainda não implementado.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.assistant.schemas import EvidenceItem, EvidenceKind, EvidenceQuantity

STATUS_VALUES = {
    "EXTRAIDO_NAO_REVISADO", "CONFERIDO_FONTE", "INFERIDO", "AUSENTE", "APROVADO_MODELO", "CALCULADO",
}
NATURE_VALUES = {"OBSERVADO", "CALCULADO", "INFERIDO", "CONCEITUAL"}
ROLE_VALUES = {"CONDICAO", "OBSERVAVEL", "METADADO"}


class OriginalValue(BaseModel):
    model_config = ConfigDict(extra="ignore")
    value: float | str
    unit: str | None = None
    raw_text: str | None = None


class LocatorInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    section: str | None = None
    table: str | None = None
    figure: str | None = None
    row_label: str | None = None
    column_label: str | None = None
    page_printed: int | None = None
    page_pdf_index: int | None = None
    precision: str | None = None


class RecordInput(BaseModel):
    """Subconjunto de ParameterRecord + localização da evidência principal."""

    model_config = ConfigDict(extra="ignore")
    record_id: str
    test_uid: str
    test_label: str
    investigation_id: str | None = None
    parameter: str
    label_pt: str
    role: str
    nature: str
    status: str
    original: OriginalValue | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    document_id: str | None = None
    locator: LocatorInput | None = None
    caveats_pt: list[str] = Field(default_factory=list)
    synthetic: bool = False


class GapInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    gap_id: str
    test_uid: str
    test_label: str
    investigation_id: str | None = None
    parameter: str
    label_pt: str
    keywords: list[str] = Field(default_factory=list)
    explanation_pt: str
    synthetic: bool = False


class PassageInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    passage_id: str
    document_id: str
    investigation_id: str | None = None
    test_uid: str | None = None
    section: str | None = None
    page_pdf_index: int | None = None
    page_printed: int | None = None
    text: str
    synthetic: bool = False


def _fmt(value: float) -> str:
    s = f"{value:.10g}"
    return s.replace(".", ",")


def _locator_text(record: RecordInput) -> str:
    loc = record.locator
    if loc is None:
        return f"Fonte: {record.document_id or 'não informada'}"
    parts = [record.document_id or "documento não informado"]
    if loc.section:
        parts.append(f"seção {loc.section}")
    if loc.table:
        parts.append(f"Tabela {loc.table}")
    if loc.row_label:
        parts.append(f"linha {loc.row_label}")
    if loc.page_printed is not None:
        parts.append(f"página impressa {loc.page_printed}")
    if loc.page_pdf_index is not None:
        parts.append(f"página PDF {loc.page_pdf_index}")
    return "Fonte: " + ", ".join(parts)


def record_card(record: RecordInput) -> EvidenceItem:
    if record.status not in STATUS_VALUES or record.nature not in NATURE_VALUES or record.role not in ROLE_VALUES:
        raise ValueError(f"registro {record.record_id}: estado/natureza/papel fora do contrato")
    if record.status == "AUSENTE":
        raise ValueError(f"registro {record.record_id}: AUSENTE deve ser representado como lacuna (GapInput)")
    quantities: list[EvidenceQuantity] = []
    if record.original is None:
        value_text = "valor não informado"
    elif isinstance(record.original.value, str):
        value_text = record.original.value
    else:
        unit = record.original.unit
        value_text = f"{_fmt(record.original.value)} {unit}".strip() if unit else _fmt(record.original.value)
        quantities.append(
            EvidenceQuantity(value=float(record.original.value), unit=unit, parameter=record.parameter)
        )
    text = (
        f"Ensaio {record.test_label} ({record.test_uid}) — {record.label_pt} "
        f"[papel={record.role}; natureza={record.nature}; estado={record.status}]: {value_text}. "
        f"{_locator_text(record)}."
    )
    if record.caveats_pt:
        text += " Ressalvas: " + " ".join(record.caveats_pt)
    return EvidenceItem(
        evidence_id=f"REC-{record.record_id}",
        kind=EvidenceKind.RECORD_CARD,
        investigation_id=record.investigation_id,
        test_uid=record.test_uid,
        test_label=record.test_label,
        parameter=record.parameter,
        role=record.role,
        nature=record.nature,
        status=record.status,
        text=text,
        quantities=quantities,
        source_evidence_ids=record.evidence_ids,
        locator=record.locator.model_dump(exclude_none=True) if record.locator else None,
        document_id=record.document_id,
        synthetic=record.synthetic,
    )


def gap_card(gap: GapInput) -> EvidenceItem:
    keywords = sorted({k.lower() for k in [*gap.keywords, gap.label_pt] if k})
    return EvidenceItem(
        evidence_id=gap.gap_id,
        kind=EvidenceKind.GAP,
        investigation_id=gap.investigation_id,
        test_uid=gap.test_uid,
        test_label=gap.test_label,
        parameter=gap.parameter,
        status="AUSENTE",
        text=(
            f"Ensaio {gap.test_label} ({gap.test_uid}) — {gap.label_pt}: AUSENTE "
            f"(não informado no corpus curado). {gap.explanation_pt}"
        ),
        keywords=keywords,
        synthetic=gap.synthetic,
    )


def passage_item(passage: PassageInput) -> EvidenceItem:
    """Trecho literal. Números contidos nele NÃO sustentam afirmações (ver verifier, V2)."""
    locator = {k: v for k, v in {
        "section": passage.section,
        "page_pdf_index": passage.page_pdf_index,
        "page_printed": passage.page_printed,
    }.items() if v is not None}
    return EvidenceItem(
        evidence_id=passage.passage_id,
        kind=EvidenceKind.PASSAGE,
        investigation_id=passage.investigation_id,
        test_uid=passage.test_uid,
        nature=None,  # trecho literal não revisado por ensaio; não é registro OBSERVADO conferido
        status=None,
        text=passage.text,
        locator=locator or None,
        document_id=passage.document_id,
        synthetic=passage.synthetic,
    )
