"""Contratos do assistente científico (planning/04 §3.9 AIAnswer e planning/02 §4/§8).

Três grupos:
1. Entrada da API (`AskRequest`, `AskScope`).
2. Evidência recuperável (`EvidenceItem`), unidade mínima entregue ao modelo.
3. Saída do modelo (`LLMOutput`, contrato estrito pedido ao provedor) e a resposta
   publicada (`AIAnswer`), montada SOMENTE após o verificador determinístico.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROMPT_VERSION = "v2"  # v2: registros retidos (DIV-20)

_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,47}$"


# ---------------------------------------------------------------- enums
class ClaimType(str, Enum):
    OBSERVACAO = "OBSERVACAO"
    ASSOCIACAO = "ASSOCIACAO"
    HIPOTESE = "HIPOTESE"
    EXPLICACAO = "EXPLICACAO"
    LIMITACAO = "LIMITACAO"


class AnswerMode(str, Enum):
    LIVE = "LIVE"  # gerada pelo provedor nesta requisição e aprovada pelo verificador
    CACHE = "CACHE"  # gerada e verificada antes; reverificada contra o dataset atual
    UNAVAILABLE = "UNAVAILABLE"  # IA não utilizada (modo off, cache ausente ou falha)
    DETERMINISTIC = "DETERMINISTIC"  # abstenção decidida em código, sem chamar a IA (DIV-15)


class AbstainReason(str, Enum):
    NO_ELIGIBLE_EVIDENCE = "NO_ELIGIBLE_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    MISSING_DATA = "MISSING_DATA"
    PENDING_REVIEW = "PENDING_REVIEW"  # dado existe na fonte, aguarda revisão humana (DIV-20)
    EXTRAPOLATION = "EXTRAPOLATION"
    MODEL_ABSTAINED = "MODEL_ABSTAINED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


class UnavailableReason(str, Enum):
    MODE_OFF = "MODE_OFF"
    CACHE_MISS = "CACHE_MISS"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class EvidenceKind(str, Enum):
    RECORD_CARD = "RECORD_CARD"  # ficha determinística de um ParameterRecord (BL-05.01)
    GAP = "GAP"  # parâmetro AUSENTE
    PASSAGE = "PASSAGE"  # trecho literal de documento


# ---------------------------------------------------------------- entrada
class AskScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    investigation_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    test_uids: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("test_uids")
    @classmethod
    def _check_uids(cls, values: list[str]) -> list[str]:
        import re

        for v in values:
            if not re.fullmatch(_ID_PATTERN, v):
                raise ValueError("identificador de ensaio inválido")
        if len(set(values)) != len(values):
            raise ValueError("identificadores de ensaio repetidos")
        return values


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=1000)
    scope: AskScope = Field(default_factory=AskScope)
    lang: Literal["pt"] = "pt"

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 3:
            raise ValueError("pergunta muito curta")
        return v


# ---------------------------------------------------------------- evidência
class EvidenceQuantity(BaseModel):
    """Valor numérico que uma evidência sustenta (unidade original preservada)."""

    model_config = ConfigDict(frozen=True)

    value: float
    unit: str | None = None
    parameter: str | None = None


class EvidenceItem(BaseModel):
    """Unidade de evidência elegível. Nunca é produzida pelo modelo."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    kind: EvidenceKind
    investigation_id: str | None = None
    test_uid: str | None = None
    test_label: str | None = None
    parameter: str | None = None
    role: str | None = None
    nature: str | None = None  # OBSERVADO | CALCULADO | INFERIDO | CONCEITUAL
    status: str | None = None  # estados de revisão do DM
    text: str
    quantities: list[EvidenceQuantity] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)  # GAP e registros retidos (V5)
    source_evidence_ids: list[str] = Field(default_factory=list)
    locator: dict | None = None
    document_id: str | None = None
    synthetic: bool = False  # True somente em fixtures/smoke test; nunca dado NASA
    value_withheld: bool = False  # registro não conferido: existe na fonte, valor não liberado (DIV-20)


# ---------------------------------------------------------------- saída do modelo
class LLMNumber(BaseModel):
    value: float
    unit: str | None = None

    @field_validator("unit")
    @classmethod
    def _empty_unit(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None


class LLMClaim(BaseModel):
    type: ClaimType
    text_pt: str = Field(max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=12)
    numbers: list[LLMNumber] = Field(default_factory=list, max_length=12)


# Schema enviado ao provedor. É declarado à mão porque o schema gerado pelo Pydantic
# (anyOf/null, $defs, limites) foi rejeitado com HTTP 400 por gemini-3.5-flash-lite
# (diagnóstico em docs/evidence/BL-05_assistente_ia.md). A validação ESTRITA continua
# sendo feita por `LLMOutput.model_validate` na resposta.
LLM_OUTPUT_PROVIDER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": [t.value for t in ClaimType]},
                    "text_pt": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "numbers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"value": {"type": "number"}, "unit": {"type": "string"}},
                            "required": ["value", "unit"],
                        },
                    },
                },
                "required": ["type", "text_pt", "evidence_ids", "numbers"],
            },
        },
        "abstain": {"type": "boolean"},
        "abstain_reason": {"type": "string"},
    },
    "required": ["claims", "abstain", "abstain_reason"],
}


class LLMOutput(BaseModel):
    """JSON exigido do provedor. Qualquer desvio → INVALID_RESPONSE."""

    claims: list[LLMClaim] = Field(default_factory=list, max_length=12)
    abstain: bool = False
    abstain_reason: str | None = Field(default=None, max_length=500)

    @field_validator("abstain_reason")
    @classmethod
    def _empty_reason(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None

    @classmethod
    def provider_json_schema(cls) -> dict:
        return LLM_OUTPUT_PROVIDER_SCHEMA


# ---------------------------------------------------------------- resposta publicada
class Claim(BaseModel):
    type: ClaimType
    text_pt: str
    evidence_ids: list[str]
    numbers: list[LLMNumber]
    verification: Literal["PASS"] = "PASS"


class BlockedClaim(BaseModel):
    type: ClaimType | None = None
    text_pt: str
    reason: str  # código da primeira regra violada (ex.: V2_NUMBER_NOT_IN_EVIDENCE)
    reasons: list[str] = Field(default_factory=list)  # todas as violações


class RetrievedEvidence(BaseModel):
    id: str
    score: float
    kind: EvidenceKind
    test_uid: str | None = None
    status: str | None = None
    nature: str | None = None
    text: str
    locator: dict | None = None
    document_id: str | None = None
    synthetic: bool = False
    value_withheld: bool = False


class AIAnswer(BaseModel):
    answer_id: str
    question: str
    scope: AskScope
    mode: AnswerMode
    requested_mode: Literal["live", "cache", "off"]
    abstained: bool
    abstain_reason: AbstainReason | None = None
    unavailable_reason: UnavailableReason | None = None
    provider_error: str | None = None  # somente o tipo (AUTH, QUOTA, TIMEOUT...), nunca detalhes
    extrapolation_flags: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    blocked_claims: list[BlockedClaim] = Field(default_factory=list)
    retrieved: list[RetrievedEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    synthetic_evidence_used: bool = False
    provider: str | None = None
    model: str | None = None
    prompt_version: str = PROMPT_VERSION
    dataset_version: str | None = None
    created_at: datetime
    served_at: datetime
    latency_ms: int
