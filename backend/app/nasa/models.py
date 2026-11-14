"""Contratos do enriquecimento NASA (ADR-09). Genéricos: nenhum identificador de
documento ou investigação é fixado aqui."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MatchState(str, Enum):
    MATCH_CONFIRMED = "MATCH_CONFIRMED"  # identificador forte presente no documento E metadados coerentes
    MATCH_CANDIDATE = "MATCH_CANDIDATE"  # semelhança de título/autores; exige revisão humana
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    ADDITIONAL_DATA_FOUND = "ADDITIONAL_DATA_FOUND"
    NOT_QUERIED = "NOT_QUERIED"  # fonte sem API documentada ou sem critério de consulta


class MatchType(str, Enum):
    IDENTIFIER = "IDENTIFIER"  # ID NTRS, número de relatório ou DOI encontrado no documento
    TITLE_AUTHORS = "TITLE_AUTHORS"
    TITLE_ONLY = "TITLE_ONLY"
    DOI_REGISTRY = "DOI_REGISTRY"  # registro DataCite cujo publicador é o repositório NASA
    NONE = "NONE"


class AccessMode(str, Enum):
    ONLINE = "ONLINE"
    FIXTURE = "FIXTURE"
    DOCUMENTATION = "DOCUMENTATION"  # só leitura de documentação; nenhuma chamada de dados


class DocumentMeta(BaseModel):
    """O que se sabe do artigo antes do enriquecimento (vindo do PDF ou do dataset)."""

    document_id: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    ntrs_id: str | None = None
    report_numbers: list[str] = Field(default_factory=list)
    doi: str | None = None
    year: int | None = None


class ApiOperation(BaseModel):
    source: str
    method: str
    url: str
    mode: AccessMode
    http_status: int | None = None
    ok: bool = False
    error: str | None = None
    response_sha256: str | None = None
    response_bytes: int | None = None
    at: str
    elapsed_ms: int | None = None


class SourceMatch(BaseModel):
    source: str  # NTRS | PSI | TECHPORT
    state: MatchState
    match_type: MatchType = MatchType.NONE
    source_record_id: str | None = None
    source_url: str | None = None
    title: str | None = None
    score: float | None = None
    reasons_pt: list[str] = Field(default_factory=list)  # por que foi (ou não) considerado relacionado
    rejected_candidates: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    curation_decision: str = "PENDENTE"  # nunca preenchido automaticamente
    note_pt: str | None = None


class EnrichmentRecord(BaseModel):
    """Comparação por campo. Correspondência de projeto ≠ concordância de medição."""

    field: str
    label_pt: str
    scope: str  # DOCUMENT_METADATA | EXPERIMENT_PARAMETER
    experiment_id: str | None = None
    original_value: Any = None
    original_source: str | None = None
    complementary_value: Any = None
    complementary_source: str | None = None
    complementary_source_id: str | None = None
    match_type: MatchType = MatchType.NONE
    state: MatchState
    review_status: str = "NAO_REVISADO"
    divergence_pt: str | None = None
    curation_decision: str = "PENDENTE"


class EnrichmentReport(BaseModel):
    document_id: str
    generated_at: str
    mode: AccessMode
    document: DocumentMeta
    matches: list[SourceMatch]
    records: list[EnrichmentRecord]
    related_documents: list[dict[str, Any]] = Field(default_factory=list)
    operations: list[ApiOperation]
    warnings_pt: list[str] = Field(default_factory=list)
    promoted_records: int = 0  # invariável: o enriquecimento nunca promove registros
