"""BL-02.01 — modelos Pydantic do contrato científico v1 (planning/04 §1–§3).

Invariantes por registro (I-1, I-2, I-3, I-4, I-6, I-8, I-9, I-10) ficam aqui.
Invariantes entre arquivos (I-5 evidência/página, I-7 ensaio da evidência,
referências) ficam em `store.py`.

Extensão aditiva (planning/04 §3.6, DIV-19): `Gap.label_pt` e `Gap.keywords`,
necessários à regra V5 do verificador da IA.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app import units

CONTRACT_VERSION = "1.0"

Status = Literal["EXTRAIDO_NAO_REVISADO", "CONFERIDO_FONTE", "INFERIDO", "AUSENTE", "APROVADO_MODELO", "CALCULADO"]
Nature = Literal["OBSERVADO", "CALCULADO", "INFERIDO", "CONCEITUAL"]
Role = Literal["CONDICAO", "OBSERVAVEL", "METADADO"]
Precision = Literal["TABLE_CELL", "PAGE", "SECTION", "DOCUMENT"]
ExtractionMethod = Literal["MANUAL_TRANSCRIPTION", "ASSISTED_TEXT_LAYER", "PARSER_TABLE", "LLM"]

_HEX64 = r"^[0-9a-f]{64}$"
_ID = r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,95}$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------------ Document (§3.1)
class Document(_Strict):
    document_id: str = Field(pattern=_ID)
    title: str
    kind: str
    url: str
    doi: str | None = None
    version: str | None = None
    local_path: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = Field(default=None, pattern=_HEX64)
    sha256_computed_at: datetime | None = None
    retrieved_at: datetime | None = None
    license_note: str | None = None
    lang: str = "en"

    @model_validator(mode="after")
    def _i10(self) -> "Document":
        if self.sha256 and self.sha256_computed_at is None:
            raise ValueError("I-10: sha256 preenchido sem sha256_computed_at")
        if self.local_path and (self.local_path.startswith(("/", "\\")) or ".." in self.local_path.replace("\\", "/").split("/")):
            raise ValueError("local_path deve ser relativo ao repositório e sem '..'")
        return self


# ------------------------------------------------------------------ Investigation (§3.2)
class ValueWithEvidence(_Strict):
    value: str
    evidence_ids: list[str] = Field(default_factory=list)


class Investigation(_Strict):
    investigation_id: str = Field(pattern=_ID)
    aliases: list[str] = Field(default_factory=list)
    doi: str | None = None
    url: str | None = None
    platform: ValueWithEvidence | None = None
    gravity_environment: ValueWithEvidence | None = None
    documents: list[str] = Field(default_factory=list)
    description_pt: str | None = None


# ------------------------------------------------------------------ Test (§3.3)
class SourceTable(_Strict):
    document_id: str
    table: str


class Test(_Strict):
    __test__ = False  # impede que o pytest tente coletar a entidade "Test" como classe de teste

    test_uid: str = Field(pattern=_ID)
    investigation_id: str
    label: str
    source_table: SourceTable | None = None
    phenomena: list[str] = Field(default_factory=list)
    material_family: str | None = None
    tags: list[str] = Field(default_factory=list)
    selection_reason: str | None = None


# ------------------------------------------------------------------ ParameterRecord (§3.4)
class OriginalValue(_Strict):
    value: float | str
    unit: str | None = None
    raw_text: str | None = None


class NormalizedValue(_Strict):
    value: float
    unit: str


class Extraction(_Strict):
    method: ExtractionMethod
    by: str = Field(min_length=1)
    at: datetime


class Review(_Strict):
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    notes: str | None = None
    checked_document_sha256: str | None = Field(default=None, pattern=_HEX64)


class ModelReview(_Strict):
    reviewer: str = Field(min_length=1)
    reviewed_at: datetime
    validity_domain_pt: str = Field(min_length=1)


class ParameterRecord(_Strict):
    record_id: str = Field(pattern=_ID)
    test_uid: str
    investigation_id: str
    parameter: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label_pt: str
    label_source: str | None = None
    role: Role
    nature: Nature
    status: Status
    original: OriginalValue | None = None
    normalized: NormalizedValue | None = None
    qualifiers: dict[str, str] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    extraction: Extraction | None = None
    review: Review = Field(default_factory=Review)
    model_review: ModelReview | None = None
    rationale: str | None = None
    sim_run_id: str | None = None
    caveats_pt: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _invariants(self) -> "ParameterRecord":
        rid = f"{self.test_uid}.{self.parameter}"
        if self.record_id != rid:
            raise ValueError(f"record_id deve ser '{rid}'")
        # I-1
        if self.status == "AUSENTE":
            if self.original is not None or self.normalized is not None:
                raise ValueError("I-1: AUSENTE exige original=null e normalized=null")
        elif self.original is None:
            raise ValueError("I-1: original=null só é permitido com status AUSENTE")
        # I-2 / I-4
        if self.status == "CALCULADO" and (self.nature != "CALCULADO" or not self.sim_run_id):
            raise ValueError("I-2: CALCULADO exige nature=CALCULADO e sim_run_id")
        if self.nature == "CALCULADO" and self.status != "CALCULADO":
            raise ValueError("I-4: nature=CALCULADO só admite status CALCULADO")
        # I-3
        if self.status == "INFERIDO" and (self.nature != "INFERIDO" or not (self.rationale or "").strip()):
            raise ValueError("I-3: INFERIDO exige nature=INFERIDO e rationale")
        # I-6
        if self.status == "APROVADO_MODELO":
            if self.role == "OBSERVAVEL":
                raise ValueError("I-6: observável nunca é APROVADO_MODELO")
            if self.model_review is None or not self.review.reviewer:
                raise ValueError("I-6: APROVADO_MODELO exige revisão prévia e model_review")
        # I-9
        if self.nature == "CONCEITUAL":
            raise ValueError("I-9: nature=CONCEITUAL não é permitida em ParameterRecord")
        # I-8
        if self.original is not None:
            if isinstance(self.original.value, str):
                if self.normalized is not None:
                    raise ValueError("I-8: valor textual não tem normalização numérica")
            else:
                q = units.normalize(float(self.original.value), self.original.unit)
                if q is None:
                    raise ValueError(f"I-8: unidade '{self.original.unit}' fora da tabela v1")
                if self.normalized is None:
                    raise ValueError("I-8: normalized ausente para valor numérico")
                if self.normalized.unit != q.unit or not math.isclose(
                    self.normalized.value, q.value, rel_tol=1e-9, abs_tol=1e-15
                ):
                    raise ValueError(f"I-8: normalized diverge do recalculado ({q.value} {q.unit})")
        # revisão (I-5 parte do registro; T-19 transcritor ≠ revisor)
        if self.status in ("CONFERIDO_FONTE", "APROVADO_MODELO"):
            if not (self.review.reviewer or "").strip() or self.review.reviewed_at is None:
                raise ValueError("I-5: CONFERIDO_FONTE exige review.reviewer e review.reviewed_at")
            if self.extraction and self.review.reviewer.strip().lower() == self.extraction.by.strip().lower():
                raise ValueError("T-19: revisor deve ser diferente de quem extraiu")
        if not self.evidence_ids and self.status != "AUSENTE":
            raise ValueError("registro sem evidência (fonte) não é aceito")
        return self


# ------------------------------------------------------------------ Evidence (§3.5)
class Locator(_Strict):
    section: str | None = None
    table: str | None = None
    figure: str | None = None
    row_label: str | None = None
    column_label: str | None = None
    page_printed: int | None = Field(default=None, ge=1)
    page_pdf_index: int | None = Field(default=None, ge=1)  # 1 = primeira página do visualizador
    bbox: list[float] | None = None
    precision: Precision


class Evidence(_Strict):
    evidence_id: str = Field(pattern=_ID)
    document_id: str
    test_uid: str | None = None  # None = evidência de nível de investigação
    locator: Locator
    quote: str | None = None
    quote_lang: str = "en"
    method: ExtractionMethod
    document_sha256_at_extraction: str | None = Field(default=None, pattern=_HEX64)

    @model_validator(mode="after")
    def _cell(self) -> "Evidence":
        if self.locator.precision == "TABLE_CELL" and not (
            self.locator.table and self.locator.row_label and self.locator.column_label
        ):
            raise ValueError("TABLE_CELL exige table, row_label e column_label")
        return self


# ------------------------------------------------------------------ Gap (§3.6)
class Gap(_Strict):
    gap_id: str = Field(pattern=_ID)
    test_uid: str
    parameter: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    status: Literal["AUSENTE"] = "AUSENTE"
    label_pt: str
    keywords: list[str] = Field(default_factory=list)
    purpose_blocked: list[str] = Field(default_factory=list)
    searched_in: list[str] = Field(min_length=1)
    explanation_pt: str
    possible_sources_pt: str | None = None

    @model_validator(mode="after")
    def _id(self) -> "Gap":
        if self.gap_id != f"GAP-{self.test_uid}-{self.parameter}":
            raise ValueError(f"gap_id deve ser 'GAP-{self.test_uid}-{self.parameter}'")
        return self
